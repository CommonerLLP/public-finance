# Generated helper — two-sided "sources -> uses" Sankey for one state/year.
# DO NOT hand-edit the output (references/lmmha/lod/sankey_assam_balance.json); rerun this script.
#
# ---------------------------------------------------------------------------
# A BALANCED fiscal-flow Sankey. Sources (left) fund the exchequer (pool);
# the exchequer funds the functional sectors (right). Sources = Uses by the
# fiscal identity, with NET BORROWING (the gross fiscal deficit) as the
# financing residual — NOT gross debt receipts, which double-count intra-year
# ways-and-means churn and inflate the "profligate state" narrative.
#
# Source: RBI, "State Finances: A Study of Budgets 2024-25", Appendices I-IV,
#   ASSAM, 2023-24 (Accounts), in INR crore. Gold-standard, cross-state-comparable.
#   Revenue Receipts (App I), Capital Receipts (App III, recovery of loans),
#   Revenue Expenditure (App II), Capital Outlay (App IV).
#   These aggregates are logged in memory/verified_facts.md.
# ---------------------------------------------------------------------------

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "references" / "lmmha" / "lod" / "sankey_assam_balance.json"

STATE, FY = "Assam", "2023-24 (Accounts)"

# --- verified RBI aggregates, INR crore ---
OWN_TAX = 28178
OWN_NONTAX = 5903
DEVOLUTION = 35331        # share in central taxes (untied)
GRANTS = 22123            # grants-in-aid from the Centre (largely tied)
RECOVERY = 3282           # recovery of loans (non-debt capital receipt)

REV_EXP = 94163           # total revenue expenditure (App II)
REV_DEV_SOCIAL = 43509    # developmental: social services (revenue)
REV_DEV_ECON = 12200      # developmental: economic services (revenue)
CAP_OUTLAY = 21444        # total capital outlay (App IV)
CAP_SOCIAL = 4611         # capital outlay: social services
CAP_ECON = 13783          # capital outlay: economic services

# functional sectors (revenue + capital), RBI definition
SOCIAL = REV_DEV_SOCIAL + CAP_SOCIAL                       # 48,120
ECONOMIC = REV_DEV_ECON + CAP_ECON                         # 25,983
GENERAL = (REV_EXP - REV_DEV_SOCIAL - REV_DEV_ECON) + (CAP_OUTLAY - CAP_SOCIAL - CAP_ECON)  # 41,504

USES_TOTAL = SOCIAL + ECONOMIC + GENERAL
# net borrowing = gross fiscal deficit = total uses - all non-debt receipts
NET_BORROWING = USES_TOTAL - (OWN_TAX + OWN_NONTAX + DEVOLUTION + GRANTS + RECOVERY)

POOL = "Assam exchequer"
SRC = "#3b6fb0"      # central transfers (highlight the dependence)
OWN = "#2f8f8f"      # own revenue
BORROW = "#b03a3a"   # net borrowing
MISC = "#9a9082"

sources = [
    ("Own tax", OWN_TAX, OWN, "own"),
    ("Own non-tax", OWN_NONTAX, OWN, "own"),
    ("Tax devolution", DEVOLUTION, SRC, "transfer"),
    ("Grants from Centre", GRANTS, SRC, "transfer"),
    ("Net borrowing", NET_BORROWING, BORROW, "borrow"),
    ("Loan recovery", RECOVERY, MISC, "misc"),
]
uses = [
    ("Social Services", SOCIAL, "#2e7d5b"),
    ("Economic Services", ECONOMIC, "#c8843a"),
    ("General Services", GENERAL, "#6c6f7d"),
]


def main():
    nodes, idx, links = [], {}, []

    def node(name, kind, color):
        if name not in idx:
            idx[name] = len(nodes)
            nodes.append({"name": name, "kind": kind, "color": color})
        return idx[name]

    node(POOL, "pool", "#444")
    for name, val, color, kind in sources:
        node(name, kind, color)
        links.append({"source": idx[name], "target": idx[POOL], "value": val})
    for name, val, color in uses:
        node(name, "use", color)
        links.append({"source": idx[POOL], "target": idx[name], "value": val})

    src_total = sum(v for _, v, _, _ in sources)
    assert abs(src_total - USES_TOTAL) <= 2, f"unbalanced: {src_total} vs {USES_TOTAL}"

    transfers = DEVOLUTION + GRANTS
    own = OWN_TAX + OWN_NONTAX
    payload = {
        "meta": {
            "state": STATE, "fy": FY, "unit": "INR crore",
            "total_cr": USES_TOTAL,
            "side": "balanced sources -> uses",
            "source": "RBI, State Finances: A Study of Budgets, Appendices I-IV (Assam, 2023-24 Accounts)",
            "headline": (f"{transfers/USES_TOTAL*100:.0f}% of Assam's budget is funded by the Centre "
                         f"(₹{transfers:,} cr devolution + grants); own revenue is "
                         f"{own/USES_TOTAL*100:.0f}% (₹{own:,} cr); net borrowing is "
                         f"{NET_BORROWING/USES_TOTAL*100:.0f}% (₹{NET_BORROWING:,} cr)."),
            "caveat": ("Net borrowing is the gross fiscal deficit (total spending minus all non-debt "
                       "receipts), not gross debt receipts. RBI Accounts; verify before citing."),
            "legend": [
                {"label": "Own revenue", "color": OWN},
                {"label": "Central transfers", "color": SRC},
                {"label": "Net borrowing", "color": BORROW},
                {"label": "Social Services", "color": "#2e7d5b"},
                {"label": "Economic Services", "color": "#c8843a"},
                {"label": "General Services", "color": "#6c6f7d"},
            ],
        },
        "nodes": nodes, "links": links,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}  total=Rs {USES_TOTAL:,} cr  net_borrowing=Rs {NET_BORROWING:,} cr")
    print(f"  Centre transfers {transfers:,} ({transfers/USES_TOTAL*100:.0f}%) | own {own:,} "
          f"({own/USES_TOTAL*100:.0f}%) | borrowing {NET_BORROWING:,} ({NET_BORROWING/USES_TOTAL*100:.0f}%)")


if __name__ == "__main__":
    main()
