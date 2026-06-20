"""Madhya Pradesh Labour + WCD Department registry.

Source: https://labour.mp.gov.in/ (Labour)
Source: https://mpwcdmis.gov.in/ (WCD)

Key findings (2024-26):
- AWW/AWH are NOT in "Scheduled Employment".
- However, AWW honorarium (₹13,000) is HIGHER than
  Unskilled Minimum Wage (₹12,425 as of April 2026).
- This is a rare case where the "parity gap" is positive.
"""

from __future__ import annotations

from pathlib import Path

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)


class MadhyaPradeshScraper(StateLabourScraper):
    state = "Madhya_Pradesh"
    base_url = "https://labour.mp.gov.in"

    def fetch_notifications(self) -> list[Notification]:
        return [
            Notification(
                state=self.state,
                title="Minimum Wage Notification April 2026",
                url="https://labour.mp.gov.in/StaticPages/MinimumWage_April2026.pdf",
                employment_category="67 Scheduled Employments",
                year=2026,
                is_final=True,
            )
        ]

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        # MP rates April 2026:
        # Unskilled: 12,425
        return [
            WageRow(
                state=self.state,
                scheduled_employment="All Scheduled (Unskilled)",
                skill_category="unskilled",
                monthly_rate_inr=12425.0,
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
                note="Not in MW Act; honorarium (13000) > Unskilled Min Wage (12425).",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="never_scheduled",
                note="Not in MW Act; honorarium (6500) < Unskilled Min Wage (12425).",
            ),
        ]
