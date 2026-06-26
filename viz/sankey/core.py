"""Source-agnostic Sankey domain logic.

`classify()` and the node/link assembly are the reusable core, lifted from the
original Assam-only build_sankey_data.py / build_sankey_balance.py. They operate
only on the normalised models in `model.py`.
"""

from __future__ import annotations

from collections import defaultdict

from viz.sankey.model import BalanceModel, SectorModel

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


def _node_factory(nodes, idx):
    def node(name, kind, color):
        if name not in idx:
            idx[name] = len(nodes)
            nodes.append({"name": name, "kind": kind, "color": color})
        return idx[name]

    return node


def build_sector(model: SectorModel) -> dict:
    """SectorModel -> D3 Sankey payload (total -> sector -> sub-sector)."""
    by_sub = defaultdict(float)
    by_macro = defaultdict(float)
    for line in model.lines:
        if not line.amount_cr:
            continue
        macro, sub = classify(model_major(line.major_head))
        by_sub[(macro, sub)] += line.amount_cr
        by_macro[macro] += line.amount_cr

    pool = "Total Disbursements"
    nodes, idx, links = [], {}, []
    node = _node_factory(nodes, idx)
    node(pool, "pool", "#444")
    for macro in SECTOR_ORDER:
        if not by_macro.get(macro):
            continue
        col = SECTOR_COLOR[macro]
        node(SECTOR_LABEL[macro], macro, col)
        links.append({"source": idx[pool], "target": idx[SECTOR_LABEL[macro]],
                      "value": round(by_macro[macro], 1)})
        subs = sorted(((sub, v) for (m, sub), v in by_sub.items() if m == macro),
                      key=lambda x: -x[1])
        for sub, v in subs:
            node(sub, macro, col)
            links.append({"source": idx[SECTOR_LABEL[macro]], "target": idx[sub],
                          "value": round(v, 1)})

    # dual-mandate figures: creditor's claim vs the social wage (sub-sector level)
    dual = {
        "interest": round(by_sub.get(("general", "Interest payments"), 0.0), 1),
        "repayment": round(by_sub.get(("debt", "Public debt repayment"), 0.0), 1),
        "health": round(by_sub.get(("social", "Health & family welfare"), 0.0), 1),
        "water": round(by_sub.get(("social", "Water supply & sanitation"), 0.0), 1),
    }

    return {
        "meta": {
            "state": model.state,
            "fy": model.fy,
            "unit": "INR crore",
            "side": "outflows only (expenditure dataset; receipts not yet wired)",
            "basis": model.basis,
            "total_cr": round(sum(by_macro.values()), 1),
            "dual": dual,
            "source": model.source,
            "classification": "Functional sectors per RBI State Finances / CAG / CPR Accountability "
                              "Initiative (General, Social, Economic Services, Grants-in-aid).",
            "caveat": model.caveat,
            "legend": [{"key": m, "label": SECTOR_LABEL[m], "color": SECTOR_COLOR[m]}
                       for m in SECTOR_ORDER if by_macro.get(m)],
        },
        "nodes": nodes,
        "links": links,
    }


def model_major(major_head: str) -> str:
    """Normalise a major head to the bare 4-digit code classify() expects."""
    return major_head.split("-")[0].strip()


def build_balance(model: BalanceModel) -> dict:
    """BalanceModel -> two-sided sources -> exchequer -> uses payload."""
    pool = f"{model.state} exchequer"
    nodes, idx, links = [], {}, []
    node = _node_factory(nodes, idx)

    node(pool, "pool", "#444")
    for f in model.sources:
        node(f.label, f.kind, f.color)
        links.append({"source": idx[f.label], "target": idx[pool], "value": f.amount_cr})
    for f in model.uses:
        node(f.label, "use", f.color)
        links.append({"source": idx[pool], "target": idx[f.label], "value": f.amount_cr})

    src_total = sum(f.amount_cr for f in model.sources)
    uses_total = sum(f.amount_cr for f in model.uses)
    assert abs(src_total - uses_total) <= 2, f"unbalanced: {src_total} vs {uses_total}"

    return {
        "meta": {
            "state": model.state, "fy": model.fy, "unit": "INR crore",
            "total_cr": uses_total,
            "side": "balanced sources -> uses",
            "headline": model.headline,
            "source": model.source,
            "caveat": model.caveat,
            "legend": model.legend,
        },
        "nodes": nodes, "links": links,
    }
