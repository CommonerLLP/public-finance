"""Adapter: observed.json (CivicDataLab expenditure) -> SectorModel.

This is the original Assam path: build_observed_data.py emits observed.json with
per-code Budget-Estimate series in INR lakh. We filter to one state/FY and
convert lakh -> crore.
"""

from __future__ import annotations

import json
from pathlib import Path

from viz.sankey.model import ExpenditureLine, SectorModel

REPO = Path(__file__).resolve().parents[3]
OBSERVED = REPO / "references" / "lmmha" / "lod" / "observed.json"


def load(state: str, fy: str) -> SectorModel:
    observed = json.loads(OBSERVED.read_text())["observed"]
    lines = []
    for code, rec in observed.items():
        if rec.get("state") != state:
            continue
        be = next((s["be"] for s in rec["series"] if s["fy"] == fy), 0) / 100.0  # lakh -> cr
        if be:
            lines.append(ExpenditureLine(major_head=code.split("-")[0], amount_cr=be))
    if not lines:
        raise SystemExit(f"observed.json has no {state} rows for {fy}")
    return SectorModel(
        state=state, fy=fy, lines=lines, basis="Budget Estimate",
        source="CivicDataLab / openbudgetsindia — state expenditure (Budget Estimate)",
        caveat="Single-source, illustrative; not cross-checked against RBI State Finances. "
               "Inflow side (tax / central devolution / grants / net borrowing) shown separately.",
    )
