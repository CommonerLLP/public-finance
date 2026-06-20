"""Static data scraper for states without active Labour Dept crawling.
Loads data from local CSVs to populate the registry and parity gap reports.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)


class StaticScraper(StateLabourScraper):
    """Handles states using pre-compiled CSV data."""

    def __init__(self, data_root: Path, state_name: str):
        self.state = state_name
        super().__init__(data_root)

    def download(self, url: str, local_path: Path) -> bool:
        """Skip network download for local data."""
        return True

    def fetch_notifications(self) -> list[Notification]:
        return [
            Notification(
                state=self.state,
                title="Static Minimum Wage Data 2024",
                url="local://data/state_minimum_wage_unskilled_2024.csv",
                employment_category="Unskilled Benchmark",
                year=2024,
                is_final=True,
            )
        ]

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        csv_path = self.data_root / "state_minimum_wage_unskilled_2024.csv"
        if not csv_path.exists():
            return []

        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["state"].lower() == self.state.lower().replace("_", " "):
                    low = row.get("unskilled_daily_low")
                    high = row.get("unskilled_daily_high")
                    if not low:
                        continue
                    daily = float(low)
                    # Monthly estimate = Daily * 26
                    monthly = daily * 26
                    return [
                        WageRow(
                            state=self.state,
                            scheduled_employment="Unskilled (Static Benchmark)",
                            skill_category="unskilled",
                            daily_rate_inr=daily,
                            monthly_rate_inr=monthly,
                            notification_id="2024 Static Aggregation",
                            source_url=notif.url,
                            note=row.get("note", ""),
                        )
                    ]
        return []

    def scheduling_status(self) -> list[SchedulingStatus]:
        # By default, assume AWW/AWH are never scheduled for these static states
        # unless we have evidence otherwise.
        return [
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_worker",
                status="never_scheduled",
                note="Assumed never scheduled; registry updated from static data 2026-05-16.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="never_scheduled",
                note="Assumed never scheduled; registry updated from static data 2026-05-16.",
            ),
        ]
