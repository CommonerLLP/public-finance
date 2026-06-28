"""Adapter: a jurisdiction's normalised off-budget slice -> OffBudgetModel.

Jurisdiction-agnostic. Reads references/offbudget/<jurisdiction>.json — the same
schema for a state, a UT, or the Union. Adding a jurisdiction-year is dropping a
file (or a year into one), never editing this adapter or the core.

Schema (offbudget-jurisdiction-v1):
  {
    "jurisdiction": {"code","type":"state|ut|union","label"},
    "guarantee_ceiling_cr": <num|null>, "guarantee_statute": "...",
    "outstanding_series_cr": {"<fy>": <num>, ...},          # multi-year context
    "years": {"<fy>": {
        "outstanding_cr","pct_of_revenue_receipts",
        "beneficiaries":[{"label","amount_cr","kind"}],     # kind -> core colour
        "off_budget_note","source"}},
    "caveat": "..."
  }
"""

from __future__ import annotations

import json
from pathlib import Path

from viz.sankey.model import Beneficiary, OffBudgetModel

REPO = Path(__file__).resolve().parents[3]
OFFBUDGET = REPO / "references" / "offbudget"


def available() -> dict:
    """{jurisdiction_code: [fy, ...]} for every slice on disk — drives the manifest."""
    out = {}
    for f in sorted(OFFBUDGET.glob("*.json")):
        data = json.loads(f.read_text())
        out[data["jurisdiction"]["code"]] = sorted(data.get("years", {}))
    return out


def load(jurisdiction: str, fy: str) -> OffBudgetModel:
    f = OFFBUDGET / f"{jurisdiction.lower()}.json"
    if not f.exists():
        raise SystemExit(f"no off-budget slice at {f} — acquire it first "
                         f"(see references/offbudget/README.md)")
    data = json.loads(f.read_text())
    years = data.get("years", {})
    if fy not in years:
        raise SystemExit(f"no off-budget year {fy} for {jurisdiction}; have {sorted(years)}")
    y = years[fy]
    j = data["jurisdiction"]
    benes = [Beneficiary(label=b["label"], amount_cr=b["amount_cr"],
                         kind=b.get("kind", "other"), color="")
             for b in y.get("beneficiaries", [])]
    return OffBudgetModel(
        jurisdiction=j["label"], jtype=j.get("type", "state"), fy=fy,
        ceiling_cr=data.get("guarantee_ceiling_cr"),
        outstanding_cr=y["outstanding_cr"],
        beneficiaries=benes,
        series_cr=data.get("outstanding_series_cr", {}),
        measure=data.get("measure", "outstanding guarantees"),
        pct_label=data.get("pct_label", "revenue receipts"),
        pct_of=y.get("pct_of", y.get("pct_of_revenue_receipts")),
        off_budget_note=y.get("off_budget_note", ""),
        statute=data.get("guarantee_statute", ""),
        source=y.get("source", data.get("source", "")),
        caveat=data.get("caveat", ""),
    )
