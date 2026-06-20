"""Tamil Nadu Labour + Social Welfare Department registry.

Note: AWW/AWH are NOT in "Scheduled Employment" in TN.
They are "para-government employees" on a "Special Time Scale of Pay".
Source: G.O. (Ms) No. 31 dated 12.03.2025.
"""

from __future__ import annotations

from pathlib import Path

from ..base import (
    Notification,
    SchedulingStatus,
    StateLabourScraper,
    WageRow,
)


class TamilNaduScraper(StateLabourScraper):
    state = "Tamil_Nadu"
    base_url = "https://labour.tn.gov.in"

    def fetch_notifications(self) -> list[Notification]:
        # Since AWW are on Time Scale, they don't appear in MW Act notifications.
        # We return a virtual notification for the latest Time Scale revision.
        return [
            Notification(
                state=self.state,
                title="G.O. (Ms) No. 31 (Social Welfare)",
                url="https://socialwelfare.tn.gov.in/go_31_2025.pdf",
                employment_category="Anganwadi Worker (Time Scale)",
                year=2025,
                is_final=True,
            )
        ]

    def parse(self, notif: Notification, local_path: Path) -> list[WageRow]:
        # TN Time Scale 2025:
        # AWW: 7700 - 24200
        # AWH: 4100 - 12500
        return [
            WageRow(
                state=self.state,
                scheduled_employment="Anganwadi Worker",
                skill_category="time_scale_level_4",
                monthly_rate_inr=7700.0,
                notification_id=notif.title,
                source_url=notif.url,
                note="Base of Special Time Scale (7700-24200)",
            ),
            WageRow(
                state=self.state,
                scheduled_employment="Anganwadi Helper",
                skill_category="time_scale_level_2",
                monthly_rate_inr=4100.0,
                notification_id=notif.title,
                source_url=notif.url,
                note="Base of Special Time Scale (4100-12500)",
            ),
        ]

    def scheduling_status(self) -> list[SchedulingStatus]:
        return [
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_worker",
                status="never_scheduled",
                note="Not in MW Act; on Special Time Scale since 7th Pay Commission.",
            ),
            SchedulingStatus(
                state=self.state,
                comparable_employment="anganwadi_helper",
                status="never_scheduled",
                note="Not in MW Act; on Special Time Scale since 7th Pay Commission.",
            ),
        ]
