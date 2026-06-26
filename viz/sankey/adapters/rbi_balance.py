"""Adapter: RBI State-Finances aggregates -> BalanceModel.

Reads a per-state/FY JSON of the 11 RBI appendix aggregates (rbi_data/) and
derives the two-sided sources->uses model. Net borrowing is the residual:
gross fiscal deficit = total uses - all non-debt receipts (NOT gross debt
receipts, which double-count intra-year ways-and-means churn).
"""

from __future__ import annotations

import json
from pathlib import Path

from viz.sankey.model import BalanceModel, Flow

REPO = Path(__file__).resolve().parents[3]
RBI_DIR = Path(__file__).resolve().parents[1] / "rbi_data"

SRC = "#3b6fb0"      # central transfers
OWN = "#2f8f8f"      # own revenue
BORROW = "#b03a3a"   # net borrowing
MISC = "#9a9082"
SOC, ECO, GEN = "#2e7d5b", "#c8843a", "#6c6f7d"


def load(state: str, fy: str) -> BalanceModel:
    path = RBI_DIR / f"{state.lower()}_{fy.split()[0]}.json"
    if not path.exists():
        raise SystemExit(
            f"no RBI aggregates for {state} {fy} ({path.name}). The balance view needs "
            f"RBI State-Finances Appendix I-IV figures; add {path.relative_to(REPO)} "
            f"(see assam_2023-24.json for the schema).")
    d = json.loads(path.read_text())

    social = d["rev_dev_social"] + d["cap_social"]
    economic = d["rev_dev_econ"] + d["cap_econ"]
    general = (d["rev_exp"] - d["rev_dev_social"] - d["rev_dev_econ"]) \
        + (d["cap_outlay"] - d["cap_social"] - d["cap_econ"])
    uses_total = social + economic + general
    non_debt = d["own_tax"] + d["own_nontax"] + d["devolution"] + d["grants"] + d["recovery"]
    net_borrowing = uses_total - non_debt

    sources = [
        Flow("Own tax", d["own_tax"], "own", OWN),
        Flow("Own non-tax", d["own_nontax"], "own", OWN),
        Flow("Tax devolution", d["devolution"], "transfer", SRC),
        Flow("Grants from Centre", d["grants"], "transfer", SRC),
        Flow("Net borrowing", net_borrowing, "borrow", BORROW),
        Flow("Loan recovery", d["recovery"], "misc", MISC),
    ]
    uses = [
        Flow("Social Services", social, "use", SOC),
        Flow("Economic Services", economic, "use", ECO),
        Flow("General Services", general, "use", GEN),
    ]
    transfers = d["devolution"] + d["grants"]
    own = d["own_tax"] + d["own_nontax"]
    return BalanceModel(
        state=state, fy=d.get("fy", fy), sources=sources, uses=uses,
        source=d["source"],
        caveat="Net borrowing is the gross fiscal deficit (total spending minus all non-debt "
               "receipts), not gross debt receipts. RBI Accounts; verify before citing.",
        legend=[
            {"label": "Own revenue", "color": OWN},
            {"label": "Central transfers", "color": SRC},
            {"label": "Net borrowing", "color": BORROW},
            {"label": "Social Services", "color": SOC},
            {"label": "Economic Services", "color": ECO},
            {"label": "General Services", "color": GEN},
        ],
    )
