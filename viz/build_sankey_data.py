# Generated helper — builds the Sankey "money flow" payload for one state/year.
# DO NOT hand-edit the output (references/lmmha/lod/sankey_assam.json); rerun this script.
#
# ---------------------------------------------------------------------------
# SANKEY DATA CONTRACT  (general; instantiated here for Assam expenditure)
# ---------------------------------------------------------------------------
# Every budget line carries an LMMHA code -> account class (first digit) and a
# major head. Major heads roll up into the STANDARD functional classification
# used by RBI "State Finances", the CAG, CPR Accountability Initiative and
# OpenBudgetsIndia:
#
#   General Services  (interest, pensions, administration, police, organs of state)
#   Social Services   (education, health, water & sanitation, housing/urban, welfare)
#   Economic Services (agriculture, rural dev, irrigation, energy, industry, transport, ...)
#   Grants-in-aid     (compensation & assignments to local bodies)
#   Public Debt & Loans (debt repayment + loans disbursed)   [financing, not a "sector"]
#
# Flow tiers: 0 = total; 1 = functional sector; 2 = sub-sector. Link value =
# INR crore for the FY. Revenue (2xxx/3xxx) and capital (4xxx/5xxx) heads map to
# the SAME sector (4202 capital and 2202 revenue are both Education), which is
# how budgets are read functionally.
#
# Coverage: Assam *expenditure* dataset (uses side). The receipts/inflow half
# (own tax, central devolution, grants, net borrowing) is built separately from
# RBI State Finances. Single-source, illustrative until cross-checked.
# ---------------------------------------------------------------------------

import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOD = REPO / "references" / "lmmha" / "lod"
OBSERVED = LOD / "observed.json"
OUT = LOD / "sankey_assam.json"

FY = "2022-23"

# macro-sector -> display colour (one family per sector; sub-sectors share it)
SECTOR_COLOR = {
    "general": "#6c6f7d",   # slate
    "social": "#2e7d5b",    # green
    "economic": "#c8843a",  # amber
    "grants": "#4a8fb0",    # blue
    "debt": "#9a5b8f",      # mauve
}
SECTOR_LABEL = {
    "general": "General Services",
    "social": "Social Services",
    "economic": "Economic Services",
    "grants": "Grants-in-aid",
    "debt": "Public Debt & Loans",
}
SECTOR_ORDER = ["social", "economic", "general", "grants", "debt"]


def classify(mh):
    """major head code -> (macro_sector_key, sub_sector_label).
    Standard LMMHA functional ranges; capital heads (4/5xxx) map to their
    revenue twin (subtract 2000) so 4202 and 2202 both read as Education."""
    n = int(mh)
    d = mh[0]
    if d in "67":  # financing side, not a service sector
        if mh == "7999":
            return "debt", "Appropriation to Contingency Fund"
        if d == "6" and n < 6076:
            return "debt", "Public debt repayment"
        return "debt", "Loans disbursed by the State"
    n2 = n - 2000 if d in "45" else n  # normalise capital to revenue twin

    if 2011 <= n2 <= 2079:
        if n2 in (2048, 2049):
            return "general", "Interest payments"
        if n2 == 2071:
            return "general", "Pensions & retirement benefits"
        if n2 == 2055:
            return "general", "Police"
        return "general", "Administration & organs of state"
    if 2202 <= n2 <= 2252:
        if 2202 <= n2 <= 2205:
            return "social", "Education, sports, art & culture"
        if 2210 <= n2 <= 2211:
            return "social", "Health & family welfare"
        if n2 == 2215:
            return "social", "Water supply & sanitation"
        if n2 in (2216, 2217):
            return "social", "Housing & urban development"
        if n2 in (2225, 2230, 2235, 2236, 2245, 2250, 2251, 2252):
            return "social", "Welfare, social security & nutrition"
        return "social", "Other social services"
    if 2401 <= n2 <= 2435:
        return "economic", "Agriculture & allied"
    if 2501 <= n2 <= 2575:
        return "economic", "Rural & area development"
    if 2700 <= n2 <= 2711:
        return "economic", "Irrigation & flood control"
    if 2801 <= n2 <= 2810:
        return "economic", "Energy / power"
    if 2851 <= n2 <= 2885:
        return "economic", "Industry & minerals"
    if 3051 <= n2 <= 3075:
        return "economic", "Transport"
    if 3201 <= n2 <= 3475:
        return "economic", "Communications, science & other economic"
    if 3601 <= n2 <= 3606:
        return "grants", "Compensation & assignments to local bodies"
    return "economic", "Other economic services"


def main():
    observed = json.loads(OBSERVED.read_text())["observed"]

    by_sub = defaultdict(float)      # (macro, sub) -> cr
    by_macro = defaultdict(float)    # macro -> cr
    for code, rec in observed.items():
        if rec.get("state") != "Assam":
            continue
        mh = code.split("-")[0]
        macro, sub = classify(mh)
        be = next((s["be"] for s in rec["series"] if s["fy"] == FY), 0) / 100.0  # lakh -> cr
        if not be:
            continue
        by_sub[(macro, sub)] += be
        by_macro[macro] += be

    POOL = "Total Disbursements"
    nodes, idx, links = [], {}, []

    def node(name, kind, color):
        if name not in idx:
            idx[name] = len(nodes)
            nodes.append({"name": name, "kind": kind, "color": color})
        return idx[name]

    node(POOL, "pool", "#444")
    for macro in SECTOR_ORDER:
        if not by_macro.get(macro):
            continue
        col = SECTOR_COLOR[macro]
        node(SECTOR_LABEL[macro], macro, col)
        links.append({"source": idx[POOL], "target": idx[SECTOR_LABEL[macro]],
                      "value": round(by_macro[macro], 1)})
        subs = sorted(((sub, v) for (m, sub), v in by_sub.items() if m == macro),
                      key=lambda x: -x[1])
        for sub, v in subs:
            node(sub, macro, col)
            links.append({"source": idx[SECTOR_LABEL[macro]], "target": idx[sub],
                          "value": round(v, 1)})

    payload = {
        "meta": {
            "state": "Assam",
            "fy": FY,
            "unit": "INR crore",
            "side": "outflows only (expenditure dataset; receipts not yet wired)",
            "total_cr": round(sum(by_macro.values()), 1),
            "source": "CivicDataLab / openbudgetsindia — Assam expenditure (Budget Estimate)",
            "classification": "Functional sectors per RBI State Finances / CAG / CPR Accountability "
                              "Initiative (General, Social, Economic Services, Grants-in-aid).",
            "caveat": "Single-source, illustrative; not cross-checked against RBI State Finances. "
                      "Inflow side (tax / central devolution / grants / net borrowing) shown separately.",
            "legend": [{"key": m, "label": SECTOR_LABEL[m], "color": SECTOR_COLOR[m]}
                       for m in SECTOR_ORDER if by_macro.get(m)],
        },
        "nodes": nodes,
        "links": links,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}  nodes={len(nodes)} links={len(links)} "
          f"total=Rs {payload['meta']['total_cr']:,.0f} cr")
    for m in SECTOR_ORDER:
        if by_macro.get(m):
            print(f"  {SECTOR_LABEL[m]:22} Rs {by_macro[m]:>9,.0f} cr")
            for sub, v in sorted(((s, v) for (mm, s), v in by_sub.items() if mm == m), key=lambda x: -x[1]):
                print(f"      {sub:48} {v:>8,.0f}")


if __name__ == "__main__":
    main()
