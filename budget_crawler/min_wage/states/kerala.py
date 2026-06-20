"""Kerala Labour Commissionerate scraper.

Source: https://lc.kerala.gov.in/en/minimum-wage-notifications
~280 PDF notifications covering ~80 scheduled employments.

Key finding from the index (logged 2026-05-15):
- Anganwadi Worker / Helper: NEVER scheduled under Kerala MW Act.
- Mid Day Meal Scheme in Schools: scheduled (2016 Final) but a
  PRELIMINARY EXCLUSION notification has been posted to remove MDM
  workers from MW Act protection. Direction of travel: backward.
- Comparable benchmarks for AWW take-home: Mid Day Meal (closest
  scheme worker), Domestic Works, Shops & Commercial Establishments.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)

LISTING_URL = "https://lc.kerala.gov.in/en/minimum-wage-notifications"

# Targets: recent final notifications most relevant to AWW comparison.
# Match by case-insensitive substring against the link text.
TARGET_TITLES = [
    "Mid Day Meal Scheme in Schools 2016 (Final)",
    "Mid Day Meal Scheme- Excluded from Minimum Wages Act (Preliminary)",
    "Domestic Works 201",
    "Shops & Commercial Establishment 2016 (Final)",
    "Agricultural Operations 2025 (Final)",
]


class KeralaScraper(StateLabourScraper):
    state = "Kerala"
    base_url = "https://lc.kerala.gov.in"
    sleep_seconds = 3.0

    def fetch_notifications(self) -> list[Notification]:
        r = self.get(LISTING_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        all_pdfs = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue
            title = a.get_text(" ", strip=True)
            if not title or title.lower() in {"english", "malayalam"}:
                continue
            full_url = urljoin(self.base_url, href)
            all_pdfs.append((title, full_url))

        wanted = []
        for target in TARGET_TITLES:
            for title, url in all_pdfs:
                if target.lower() in title.lower():
                    wanted.append(self._make_notification(title, url))
                    break
        return wanted

    def _make_notification(self, title: str, url: str) -> Notification:
        m = re.search(r"\b(19|20)\d{2}\b", title)
        year = int(m.group(0)) if m else None
        is_prelim = "preliminary" in title.lower() or "prelim" in title.lower()
        is_final = "final" in title.lower()
        is_excluded = "excluded" in title.lower() or "exempt" in title.lower()
        is_amend = "amendment" in title.lower()
        return Notification(
            state=self.state,
            title=title,
            url=url,
            employment_category=re.split(r"\s*\d{4}", title)[0].strip(" -"),
            year=year,
            is_preliminary=is_prelim,
            is_final=is_final,
            is_amendment=is_amend,
            is_excluded=is_excluded,
        )

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        """Extract wage rates from a downloaded PDF.

        Strategy: pdftotext -layout, then look for rows containing a
        skill category keyword (Unskilled / Semi-Skilled / Skilled /
        Highly Skilled) followed by numeric values. Returns empty list
        if no extractable table found — caller logs and we revisit.
        """
        if notif.is_excluded:
            # Exclusion notifications carry no rate.
            return []

        try:
            text = subprocess.run(
                ["pdftotext", "-layout", str(local_path), "-"],
                capture_output=True, text=True, check=True, timeout=60,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return []

        rows: list[WageRow] = []
        skill_patterns = {
            "unskilled": r"\bunskilled\b",
            "semi_skilled": r"\bsemi[- ]?skilled\b",
            "skilled": r"\bskilled\b",
            "highly_skilled": r"\bhighly[ -]?skilled\b",
        }
        # Pass 1: English skill-keyword anchored extraction.
        # Pass 2 (fallback): pair-pattern extraction — for Malayalam tables
        # where the row description is in Malayalam but numeric rates are
        # in Latin digits. We grab (daily_in_range, monthly_in_range) pairs.
        def _nums(line):
            return [float(n.replace(",", ""))
                    for n in re.findall(r"\b\d{1,5}(?:[.,]\d{1,2})?\b", line)]

        seen_pairs = set()
        for line in text.splitlines():
            ll = line.strip().lower()
            if not ll:
                continue

            # Pass 1
            matched_skill = None
            for skill, pat in skill_patterns.items():
                if re.search(pat, ll):
                    matched_skill = skill
                    break

            nums = _nums(line)
            daily_candidates = [n for n in nums if 80 <= n <= 2000]
            monthly_candidates = [n for n in nums if 3000 <= n <= 60000]

            if matched_skill:
                daily = daily_candidates[0] if daily_candidates else None
                monthly = monthly_candidates[0] if monthly_candidates else None
                rows.append(WageRow(
                    state=self.state, scheduled_employment=notif.employment_category,
                    skill_category=matched_skill,
                    daily_rate_inr=daily, monthly_rate_inr=monthly,
                    notification_id=notif.title, source_url=notif.url,
                    source_local_path=str(local_path),
                    note=f"line: {line.strip()[:120]}",
                ))
                continue

            # Pass 2: numeric-pair rows. Require BOTH a daily-range and
            # a monthly-range number on the same line; daily ≤ monthly/15
            # (rough sanity: monthly should be 20-30× daily).
            if daily_candidates and monthly_candidates:
                daily = daily_candidates[0]
                monthly = monthly_candidates[0]
                if not (15 * daily <= monthly <= 35 * daily):
                    continue
                pair = (daily, monthly)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                rows.append(WageRow(
                    state=self.state, scheduled_employment=notif.employment_category,
                    skill_category="unspecified",
                    daily_rate_inr=daily, monthly_rate_inr=monthly,
                    notification_id=notif.title, source_url=notif.url,
                    source_local_path=str(local_path),
                    note=f"pair-extracted; line: {line.strip()[:120]}",
                ))
        return rows

    def scheduling_status(self) -> list[SchedulingStatus]:
        """Categorical map for Kerala — derived from index scout 2026-05-15.

        Findings logged:
        - AWW/AWH: never scheduled under Kerala MW Act despite ~80
          scheduled employments on the books.
        - MDM workers: scheduled (2016 Final) → preliminary exclusion
          notification posted (date TBD from PDF).
        - Domestic, Shops & Commercial, Agriculture: scheduled with
          regular notifications.
        """
        return [
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_worker",
                status="never_scheduled",
                note="No notification under Kerala MW Act for AWW; index scanned 2026-05-15.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="never_scheduled",
                note="No notification under Kerala MW Act for AWH; index scanned 2026-05-15.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="mid_day_meal",
                status="preliminary_excluded",
                notification_url="http://lc.kerala.gov.in/sites/default/files/inline-files/document-1.pdf",
                note="Preliminary notification removes MDM workers from MW Act. Was scheduled 2016 (Final).",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="domestic_work",
                status="scheduled",
                notification_url="http://lc.kerala.gov.in/images/pdf/minwages/house.pdf",
                notification_year=2017,
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="shops_commercial",
                status="scheduled",
                notification_year=2016,
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="agricultural",
                status="scheduled",
                notification_year=2025,
            ),
        ]
