"""Rajasthan Labour Department scraper.

Source: https://labour.rajasthan.gov.in/
Notifications: typically under https://labour.rajasthan.gov.in/MinimumWage.aspx

Key findings (scanned 2026-05-16):
- 52 Scheduled Employments.
- "Creche Attendants" (Unskilled) and "Creche-in-charge" (Semi-Skilled)
  are listed.
- AWW/AWH are considered honorary but the Creche classification is
  the closest legal benchmark for their labor.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)


class RajasthanScraper(StateLabourScraper):
    state = "Rajasthan"
    base_url = "https://labour.rajasthan.gov.in"

    def fetch_notifications(self) -> list[Notification]:
        # For MVP, we return a virtual notification for the latest known rates
        # from the 2024-25 period (effective 01.10.2024).
        return [
            Notification(
                state=self.state,
                title="Minimum Wage Notification 01.10.2024",
                url="https://labour.rajasthan.gov.in/MinimumWage_2024.pdf",
                employment_category="All 52 Scheduled Employments",
                year=2024,
                is_final=True,
            )
        ]

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        # Rajasthan 2024 rates (from search results):
        # Unskilled: 285/day, 7410/month
        # Semi-Skilled: 297/day, 7722/month
        # Skilled: 309/day, 8034/month
        return [
            WageRow(
                state=self.state,
                scheduled_employment="Creche Attendant / Unskilled",
                skill_category="unskilled",
                daily_rate_inr=285.0,
                monthly_rate_inr=7410.0,
                notification_id=notif.title,
                source_url=notif.url,
            ),
            WageRow(
                state=self.state,
                scheduled_employment="Creche-in-charge / Semi-Skilled",
                skill_category="semi_skilled",
                daily_rate_inr=297.0,
                monthly_rate_inr=7722.0,
                notification_id=notif.title,
                source_url=notif.url,
            ),
        ]

    def scheduling_status(self) -> list[SchedulingStatus]:
        return [
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_worker",
                status="scheduled",
                note="Scheduled as 'Creche-in-charge' (Semi-Skilled) in some districts/periods.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="scheduled",
                note="Scheduled as 'Creche Attendant' (Unskilled) in some districts/periods.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="shops_commercial",
                status="scheduled",
                notification_year=2024,
            ),
        ]
