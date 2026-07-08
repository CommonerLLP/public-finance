"""Source-agnostic Sankey domain logic.

`classify()` and the node/link assembly are the reusable core, lifted from the
original Assam-only build_sankey_data.py / build_sankey_balance.py. They operate
only on the normalised models in `model.py`.
"""

from __future__ import annotations

from collections import defaultdict

from viz.sankey.model import BalanceModel, OffBudgetModel, SectorModel

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


# off-budget beneficiary kind -> colour (one family; reused across jurisdictions)
OFFBUDGET_COLOR = {
    "psu_power": "#c8843a",   # amber — power utilities
    "psu_other": "#b06a3a",   # burnt amber — other PSUs
    "ulb": "#3b6fb0",         # blue — urban local bodies
    "spv": "#9a5b8f",         # mauve — special purpose vehicles
    "board": "#2f8f8f",       # teal — statutory boards
    "coop": "#6c6f7d",        # slate — cooperatives
    "other": "#9aa0ab",       # grey — residual / unnamed
}


def build_offbudget(model: OffBudgetModel) -> dict:
    """OffBudgetModel -> Sankey payload: outstanding guarantees fan to beneficiaries.

    Source node = the jurisdiction's outstanding guarantees (a contingent stock,
    NOT budget spending). Targets = named beneficiaries + an 'Other' residual.
    Ceiling/headroom and the multi-year series ride in meta for context.
    """
    root = f"{model.jurisdiction} — {model.measure}"
    nodes, idx, links = [], {}, []
    node = _node_factory(nodes, idx)
    node(root, "pool", "#444")

    named = sorted(model.beneficiaries, key=lambda b: -b.amount_cr)
    for b in named:
        node(b.label, b.kind, b.color or OFFBUDGET_COLOR.get(b.kind, "#9aa0ab"))
        links.append({"source": idx[root], "target": idx[b.label],
                      "value": round(b.amount_cr, 1)})
    other = round(model.outstanding_cr - sum(b.amount_cr for b in named), 1)
    if other > 0.5:
        node("Other guaranteed bodies", "other", OFFBUDGET_COLOR["other"])
        links.append({"source": idx[root], "target": idx["Other guaranteed bodies"],
                      "value": other})

    ceiling = model.ceiling_cr
    headroom = round(ceiling - model.outstanding_cr, 1) if ceiling else None
    kinds = {b.kind for b in named}
    legend = [{"label": k.replace("_", " ").title(), "color": OFFBUDGET_COLOR[k]}
              for k in OFFBUDGET_COLOR if k in kinds]
    if other > 0.5:
        legend.append({"label": "Other", "color": OFFBUDGET_COLOR["other"]})

    pct = model.pct_of
    headline = (f"{model.jurisdiction}'s {model.measure}: "
                f"₹{model.outstanding_cr:,.0f} cr"
                + (f" — {pct}% of {model.pct_label}" if pct else "")
                + (f"; ₹{headroom:,.0f} cr headroom under the ₹{ceiling:,.0f} cr ceiling"
                   if headroom is not None else "")
                + ". Outside the on-budget total — the part of the books the budget "
                  "does not show.")

    return {
        "meta": {
            "state": model.jurisdiction, "fy": model.fy, "unit": "INR crore",
            "jtype": model.jtype,
            "total_cr": round(model.outstanding_cr, 1),
            "side": "contingent liabilities (off-budget) — NOT part of the budget total",
            "headline": headline,
            "ceiling_cr": ceiling, "headroom_cr": headroom,
            "series_cr": model.series_cr,
            "off_budget_note": model.off_budget_note,
            "statute": model.statute,
            "source": model.source,
            "caveat": model.caveat,
            "legend": legend,
        },
        "nodes": nodes, "links": links,
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
