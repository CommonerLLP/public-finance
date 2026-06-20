"""ABC + dataclasses for state Labour Department scrapers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Literal, Optional

import requests

UA = "Mozilla/5.0 (research; CommonerLLP public-finance)"

# Categorical scheduling status for a (state, comparable_employment_type) pair.
SchedulingStatusEnum = Literal[
    "scheduled",            # employment is scheduled and rates are notified
    "preliminary",          # preliminary notification posted (not yet final)
    "excluded",             # final notification removing employment from MW Act
    "preliminary_excluded", # preliminary notification removing from MW Act
    "never_scheduled",      # no notification ever
    "unknown",              # not determined
]

# Comparable employment types we track across states.
# Anganwadi-specific schedules are rare; we triangulate via these.
ComparableEmployment = Literal[
    "anganwadi_worker",     # AWW directly scheduled
    "anganwadi_helper",     # AWH directly scheduled
    "asha_worker",
    "mid_day_meal",         # cook-cum-helper / MDM workers
    "scheme_worker_general",
    "domestic_work",
    "shops_commercial",     # general urban unskilled benchmark
    "agricultural",         # general rural unskilled benchmark
    "honorary_worker",      # state-specific category
]


@dataclass
class Notification:
    """A single notification listed on a Labour Department site."""
    state: str
    title: str
    url: str
    employment_category: str            # the scheduled employment name as posted
    year: Optional[int] = None
    is_preliminary: bool = False
    is_final: bool = False
    is_amendment: bool = False
    is_excluded: bool = False           # notification *removes* employment from MW Act
    language: str = "en"


@dataclass
class WageRow:
    """A parsed wage row from one notification PDF/HTML."""
    state: str
    scheduled_employment: str
    skill_category: str                 # unskilled / semi-skilled / skilled / highly-skilled
    zone: str = ""                      # area A/B/C, urban/rural, or specific zone name
    daily_rate_inr: Optional[float] = None
    monthly_rate_inr: Optional[float] = None
    basic_inr: Optional[float] = None
    vda_inr: Optional[float] = None
    effective_date: Optional[date] = None
    notification_id: str = ""
    source_url: str = ""
    source_local_path: str = ""
    page_no: Optional[int] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    note: str = ""


@dataclass
class SchedulingStatus:
    """Categorical status of a comparable employment in a state."""
    state: str
    comparable_employment: str          # one of ComparableEmployment values
    status: str                         # one of SchedulingStatusEnum values
    notification_url: str = ""          # URL of the notification establishing this status
    notification_year: Optional[int] = None
    note: str = ""


class StateLabourScraper(ABC):
    """Per-state scraper. Subclass + register in registry.py."""

    state: str = ""
    base_url: str = ""
    sleep_seconds: float = 2.0

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.state_dir = data_root / "min_wage" / self._slug()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA
        self._last_request_time = 0.0

    def _slug(self) -> str:
        return self.state.lower().replace(" ", "_").replace("&", "and")

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        wait = self.sleep_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.time()

    def get(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        return self.session.get(url, timeout=60, **kwargs)

    def download(self, url: str, local_path: Path) -> bool:
        """Download URL → local_path. Returns False if already present (skip)."""
        if local_path.exists() and local_path.stat().st_size > 0:
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        r = self.get(url)
        r.raise_for_status()
        local_path.write_bytes(r.content)
        return True

    @abstractmethod
    def fetch_notifications(self) -> list[Notification]: ...

    @abstractmethod
    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]: ...

    @abstractmethod
    def scheduling_status(self) -> list[SchedulingStatus]:
        """Return the categorical map for this state."""
        ...

    def local_path_for(self, notif: Notification) -> Path:
        ext = notif.url.split(".")[-1].split("?")[0].lower()
        if ext not in {"pdf", "html", "htm"}:
            ext = "pdf"
        # Use a deterministic slug from the title + year
        slug_parts = [str(notif.year) if notif.year else "0",
                      notif.employment_category.lower().replace(" ", "_").replace("/", "_")[:60]]
        if notif.is_preliminary:
            slug_parts.append("preliminary")
        if notif.is_excluded:
            slug_parts.append("excluded")
        slug = "_".join(slug_parts) + "." + ext
        return self.state_dir / slug
