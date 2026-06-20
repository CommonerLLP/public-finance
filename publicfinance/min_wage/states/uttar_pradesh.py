"""Uttar Pradesh Labour Department registry.

Source: https://uplabour.gov.in/
Notifications: typically updated April and October (VDA revisions).

Key findings (2024-25):
- 74 Scheduled Employments.
- Unskilled rates are ~10,701 per month (Oct 2024).
- AWW/AWH are considered honorary.
"""

from __future__ import annotations

from pathlib import Path

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)


class UttarPradeshScraper(StateLabourScraper):
    state = "Uttar_Pradesh"
    base_url = "https://uplabour.gov.in"

    def fetch_notifications(self) -> list[Notification]:
        return [
            Notification(
                state=self.state,
                title="Minimum Wage Notification Oct 2024",
                url="https://uplabour.gov.in/StaticPages/MinimumWage_Oct2024.pdf",
                employment_category="74 Scheduled Employments",
                year=2024,
                is_final=True,
            )
        ]

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        # UP rates Oct 2024:
        # Total Monthly (Unskilled): 10,701
        return [
            WageRow(
                state=self.state,
                scheduled_employment="All Scheduled (Unskilled)",
                skill_category="unskilled",
                monthly_rate_inr=10701.0,
                notification_id=notif.title,
                source_url=notif.url,
            )
        ]

    def scheduling_status(self) -> list[SchedulingStatus]:
        return [
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_worker",
                status="never_scheduled",
                note="Not listed in UP's 74 scheduled employments.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="never_scheduled",
                note="Not listed in UP's 74 scheduled employments.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="shops_commercial",
                status="scheduled",
                notification_year=2024,
            ),
        ]
