"""Adapter: Gujarat demand-book parse (data/gujarat/demands) -> SectorModel.

Source is twenty27's text-layer parse of the Gujarat Demands for Grants,
ingested into data/gujarat/demands/gujarat_demands_<YYYY-YYYY>.json. Records are
already in INR crore (amount_cr), one per minor head with an estimate basis.

A given year's Budget Estimate appears in up to two books (its own and the
following year's), and parse completeness varies. We scan every book, take the
slice matching (year, basis) from the book that captured the most such rows, and
aggregate that single book to major-head level (mixing books would double-count).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from viz.sankey.model import ExpenditureLine, SectorModel

REPO = Path(__file__).resolve().parents[3]
DEMANDS = REPO / "data" / "gujarat" / "demands"


def _full_fy(fy: str) -> str:
    """'2022-23' -> '2022-2023'; pass through if already long."""
    a, b = fy.split("-")
    return f"{a}-{b}" if len(b) == 4 else f"{a}-{a[:2]}{b}"


def _best_slice(full: str, basis: str) -> list[dict]:
    """The (year, basis) records from whichever book captured the most of them."""
    best: list[dict] = []
    for path in DEMANDS.glob("gujarat_demands_*.json"):
        recs = [r for r in json.loads(path.read_text()).get("records", [])
                if r.get("fiscal_year") == full and r.get("estimate_basis") == basis]
        if len(recs) > len(best):
            best = recs
    return best


def load(state: str, fy: str, basis: str = "BE") -> SectorModel:
    full = _full_fy(fy)
    recs = _best_slice(full, basis)
    if not recs:
        raise SystemExit(f"no {basis} rows for {full} in any demand book under "
                         f"{DEMANDS.relative_to(REPO)}")
    by_major = defaultdict(float)
    for r in recs:
        mh = str(r.get("major_head_code") or "").strip()
        if mh.isdigit():
            by_major[mh] += r.get("amount_cr") or 0.0
    lines = [ExpenditureLine(major_head=mh, amount_cr=v) for mh, v in by_major.items()]
    basis_label = {"BE": "Budget Estimate", "RE": "Revised Estimate", "Actuals": "Actuals"}.get(basis, basis)
    return SectorModel(
        state=state, fy=fy, lines=lines, basis=basis_label,
        source="Gujarat Finance Dept, Demands for Grants (text-layer parse, via twenty27)",
        caveat="Single automated parse of the demand books, not yet verified against the rendered "
               "pages or a second source (RBI/CAG). Indicative until logged in verified_facts.md.",
    )
