"""Adapter: Gujarat's own budget books -> BalanceModel (two-sided money flow).

Sources come from the Receipts statement (Budget Publication 02, "Receipt under
Consolidated Fund …"), parsed by receipt head:
  - own tax      = tax-revenue major heads minus the central share
  - devolution   = "901 - Share of Net Proceeds assigned to States" (central taxes)
  - grants       = head 1601, Grants-in-aid from Central Government
  - own non-tax  = non-tax revenue sector majors
Uses come from the Demands for Grants (the gujarat_demands adapter), rolled up
to Social / Economic / General (debt repayment excluded — it is financing, not a
service use). Net borrowing is the residual: total uses minus all non-debt
receipts (the gross fiscal deficit), not gross debt receipts.

No RBI: the whole picture is built from Gujarat's own documents.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from viz.sankey import core
from viz.sankey.adapters import gujarat_demands
from viz.sankey.model import BalanceModel, Flow

REPO = Path(__file__).resolve().parents[3]
BUDGET = REPO / "data" / "gujarat" / "finance_dept"
_NUM = re.compile(r"\d[\d,]*\.\d+")
# central taxes: the State receives only its 901 devolution share, no own component
_CENTRAL = {"0005", "0008", "0020", "0021", "0028", "0037", "0038", "0044", "0045"}

SRC, OWN, BORROW = "#3b6fb0", "#2f8f8f", "#b03a3a"
SOC, ECO, GEN = "#2e7d5b", "#c8843a", "#6c6f7d"


def _receipts_pdf(fy: str) -> Path:
    # budget PDF dirs use the short FY (2024-25), unlike the demands JSON (2024-2025)
    matches = list((BUDGET / fy / "budget").glob("02 - Receipt under Consolidated Fund*.pdf"))
    if not matches:
        raise SystemExit(f"no Gujarat receipts statement for {fy} under {BUDGET / fy}")
    return matches[0]


def _parse_sources(fy: str) -> dict:
    """Sum receipt heads from the receipts statement (₹ crore, current-year BE column).

    The book repeats each 'Net Total' across a summary and a detail section, so we
    dedupe to one value per (account, sector, major head) before summing.
    """
    seen: dict[tuple, float] = {}
    account = sector = None
    with pdfplumber.open(_receipts_pdf(fy)) as pdf:
        for page in pdf.pages:
            for ln in (page.extract_text() or "").split("\n"):
                if "Revenue Account" in ln:
                    account = "rev"
                elif "Capital Account" in ln:
                    account = "cap"
                s = re.search(r"SECTOR-+([A-Z])-", ln)
                if s:
                    sector = s.group(1)
                m = re.search(r"Net Total\s*:\s*(\d{4})\b", ln)
                if not m:
                    continue
                nums = _NUM.findall(ln)
                if not nums:
                    continue
                key = (account, sector, m.group(1))
                seen[key] = max(seen.get(key, 0.0), float(nums[-1].replace(",", "")))

    rev_tax = {mh: v for (acc, sec, mh), v in seen.items() if acc == "rev" and sec == "A"}
    rev_nontax = {mh: v for (acc, sec, mh), v in seen.items() if acc == "rev" and sec == "B"}
    return {
        "devolution": round(sum(v for mh, v in rev_tax.items() if mh in _CENTRAL), 1),
        "own_tax": round(sum(v for mh, v in rev_tax.items() if mh not in _CENTRAL), 1),
        "own_nontax": round(sum(rev_nontax.values()), 1),
        "grants": round(next((v for (acc, sec, mh), v in seen.items() if mh == "1601"), 0.0), 1),
    }


def load(state: str, fy: str) -> BalanceModel:
    s = _parse_sources(fy)

    # uses: classify the demands BE, exclude debt-repayment financing
    model = gujarat_demands.load(state, fy, "BE")
    b = {"social": 0.0, "economic": 0.0, "general": 0.0}
    for ln in model.lines:
        macro, _ = core.classify(core.model_major(ln.major_head))
        if macro == "debt":
            continue
        b["general" if macro == "grants" else macro] += ln.amount_cr
    social, economic, general = round(b["social"], 1), round(b["economic"], 1), round(b["general"], 1)
    uses_total = round(social + economic + general, 1)

    net_borrowing = round(uses_total - (s["own_tax"] + s["own_nontax"] + s["devolution"] + s["grants"]), 1)
    transfers = s["devolution"] + s["grants"]
    own = s["own_tax"] + s["own_nontax"]

    bm = BalanceModel(
        state=state, fy=f"{fy} (Budget Estimates)",
        sources=[
            Flow("Own tax", s["own_tax"], "own", OWN),
            Flow("Own non-tax", s["own_nontax"], "own", OWN),
            Flow("Tax devolution", s["devolution"], "transfer", SRC),
            Flow("Grants from Centre", s["grants"], "transfer", SRC),
            Flow("Net borrowing", net_borrowing, "borrow", BORROW),
        ],
        uses=[
            Flow("Social Services", social, "use", SOC),
            Flow("Economic Services", economic, "use", ECO),
            Flow("General Services", general, "use", GEN),
        ],
        source="Gujarat Finance Dept — Receipts (Consolidated Fund) + Demands for Grants",
        caveat="Built entirely from Gujarat's own budget books. Net borrowing = total spending minus all "
               "non-debt receipts (the gross fiscal deficit), not gross debt receipts. Indicative; not yet line-verified.",
        legend=[
            {"label": "Own revenue", "color": OWN},
            {"label": "Central transfers", "color": SRC},
            {"label": "Net borrowing", "color": BORROW},
            {"label": "Social Services", "color": SOC},
            {"label": "Economic Services", "color": ECO},
            {"label": "General Services", "color": GEN},
        ],
    )
    bm.headline = (f"{transfers / uses_total * 100:.0f}% of Gujarat's budget comes from the Centre "
                   f"(₹{transfers:,.0f} cr); own revenue {own / uses_total * 100:.0f}% (₹{own:,.0f} cr); "
                   f"net borrowing {net_borrowing / uses_total * 100:.0f}% (₹{net_borrowing:,.0f} cr).")
    return bm
