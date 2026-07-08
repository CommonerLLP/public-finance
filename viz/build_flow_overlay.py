"""Instance overlay: attach a state-year's actual rupees to the inter-tier flow graph.

Reuses the existing balance Sankey output (built by viz/build_sankey.py from the
state's own books) for the amounts — does NOT re-derive them. Maps each balance
source onto a references/flow_graph/ edge by edge_id, then writes TWO artifacts:

  references/flow_graph/instances/<state>_<fy>.json   — edges with amount_cr
      (provenance: every rupee carries its concept_id + verified chart head)
  references/lmmha/lod/sankey_<state>_flow_<fy>.json  — a render-ready payload
      in the SAME {meta,nodes,links} shape core.build_balance emits, so the ONE
      deployed renderer (references/lmmha/lod/flow.html + flow.js, served at
      data.commonerllp.org) draws it as the "flow" view. No bespoke HTML here.

The flow view differs from the balance view by breaking out the Union (Centre) as
the upstream tier: the two central transfers (devolution, FC grants) visibly
originate at the Centre and flow down into the state — the vertical, inter-tier
generalisation of the single-tier balance Sankey.

    python -m viz.build_flow_overlay --state gujarat --fy 2024-25

Amounts inherit the source Sankey's caveat (indicative; not line-verified).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOD = REPO / "references" / "lmmha" / "lod"
INST = REPO / "references" / "flow_graph" / "instances"

# colours match the deployed balance view (sankey_<state>_balance JSON legend)
C_UNION = "#3b6fb0"     # Centre / central transfers (blue)
C_OWN = "#2f8f8f"       # state own revenue (teal)
C_BORROW = "#b03a3a"    # net borrowing (red)
USE_COLOR = {"Social Services": "#2e7d5b", "Economic Services": "#c8843a",
             "General Services": "#6c6f7d"}

# Balance-Sankey source node name -> flow_graph edge_id. Tracks the node names the
# balance adapter emits (viz/sankey/adapters/*). Update here if those names change.
BALANCE_SOURCE_TO_EDGE = {
    "Own tax": "own.state",
    "Own non-tax": "own.state_nontax",
    "Tax devolution": "devolution.union_state",
    "Grants from Centre": "fcgrant.union_state",
    "Net borrowing": "borrow.market_state",
}
# which sources originate at the Union tier (drawn from the Centre node)
UNION_ORIGIN = {"devolution.union_state", "fcgrant.union_state"}


def load_balance(state: str, fy: str) -> dict:
    f = LOD / f"sankey_{state}_balance_{fy}.json"
    if not f.exists():
        raise SystemExit(f"no balance Sankey at {f} — build it first: "
                         f"python -m viz.build_sankey --state {state} --fy {fy} --view balance")
    return json.loads(f.read_text())


def overlay(state: str, fy: str) -> dict:
    """Edge-attributed provenance instance: each balance source mapped to a flow-graph edge."""
    bal = load_balance(state, fy)
    edges = {e["edge_id"]: e for e in
             json.loads((REPO / "references/flow_graph/edges.json").read_text())["edges"]}
    nodes = bal["nodes"]
    name = lambda i: nodes[i]["name"] if isinstance(i, int) else i

    sources, uses = [], []
    for l in bal["links"]:
        s, t = name(l["source"]), name(l["target"])
        if t == nodes[0]["name"]:                 # source -> exchequer
            eid = BALANCE_SOURCE_TO_EDGE.get(s)
            if not eid:
                raise SystemExit(f"unmapped balance source '{s}' — add it to BALANCE_SOURCE_TO_EDGE")
            e = edges[eid]
            sources.append({"edge_id": eid, "label": s, "amount_cr": round(l["value"], 1),
                            "from": e["from"], "concept_id": e["concept_id"],
                            "lands_under": e.get("lands_under"), "union_origin": eid in UNION_ORIGIN})
        else:                                     # exchequer -> use
            uses.append({"label": t, "amount_cr": round(l["value"], 1)})

    from_centre = round(sum(s["amount_cr"] for s in sources if s["union_origin"]), 1)
    total = round(sum(s["amount_cr"] for s in sources), 1)
    return {
        "generated_by": "viz/build_flow_overlay.py",
        "state": bal["meta"]["state"], "fy": bal["meta"]["fy"], "unit": "INR crore",
        "total_cr": total, "from_centre_cr": from_centre,
        "from_centre_pct": round(100 * from_centre / total, 1),
        "sources": sources, "uses": uses,
        "source_doc": bal["meta"].get("source"),
        "caveat": bal["meta"].get("caveat", "") + " Overlay maps balance sources onto references/flow_graph/ edges.",
    }


def flow_payload(ov: dict) -> dict:
    """Canonical {meta,nodes,links} for the deployed flow.js — vertical, Centre broken out.

    Union (Centre) -> [devolution, FC grants] -> exchequer ; own/market -> exchequer
    ; exchequer -> [Social, Economic, General].
    """
    ex = f"{ov['state']} exchequer"
    nodes, idx, links = [], {}, []

    def node(n, kind, color):
        if n not in idx:
            idx[n] = len(nodes)
            nodes.append({"name": n, "kind": kind, "color": color})
        return idx[n]

    node("Union (Centre)", "union", C_UNION)
    node(ex, "pool", "#444")
    for s in ov["sources"]:
        if s["union_origin"]:
            color, kind = C_UNION, "transfer"
        elif "borrow" in s["edge_id"]:
            color, kind = C_BORROW, "borrow"
        else:
            color, kind = C_OWN, "own"
        node(s["label"], kind, color)
        if s["union_origin"]:                              # Centre -> stream -> exchequer
            links.append({"source": idx["Union (Centre)"], "target": idx[s["label"]],
                          "value": s["amount_cr"]})
        links.append({"source": idx[s["label"]], "target": idx[ex], "value": s["amount_cr"]})
    for u in ov["uses"]:                                   # exchequer -> use
        node(u["label"], "use", USE_COLOR.get(u["label"], "#6c6f7d"))
        links.append({"source": idx[ex], "target": idx[u["label"]], "value": u["amount_cr"]})

    return {
        "meta": {
            "state": ov["state"], "fy": ov["fy"], "unit": ov["unit"],
            "total_cr": ov["total_cr"],
            "side": "inter-tier: Union (Centre) -> State -> uses",
            "headline": f"{ov['from_centre_pct']}% of {ov['state']}'s budget originates at the Centre "
                        f"(₹{ov['from_centre_cr']:,.0f} cr of ₹{ov['total_cr']:,.0f} cr): tax devolution "
                        f"+ Finance-Commission grants. Own revenue and market borrowing fund the rest.",
            "source": ov.get("source_doc"),
            "caveat": ov["caveat"],
            "legend": [
                {"label": "Union (Centre) / central transfers", "color": C_UNION},
                {"label": "State own revenue", "color": C_OWN},
                {"label": "Net borrowing", "color": C_BORROW},
                {"label": "Social Services", "color": USE_COLOR["Social Services"]},
                {"label": "Economic Services", "color": USE_COLOR["Economic Services"]},
                {"label": "General Services", "color": USE_COLOR["General Services"]},
            ],
        },
        "nodes": nodes, "links": links,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="gujarat")
    ap.add_argument("--fy", default="2024-25")
    a = ap.parse_args()
    INST.mkdir(parents=True, exist_ok=True)
    ov = overlay(a.state, a.fy)
    (INST / f"{a.state}_{a.fy}.json").write_text(json.dumps(ov, indent=2, ensure_ascii=False))
    payload = flow_payload(ov)
    out = LOD / f"sankey_{a.state}_flow_{a.fy}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {(INST / f'{a.state}_{a.fy}.json').relative_to(REPO)} (provenance)")
    print(f"wrote {out.relative_to(REPO)} — flow view, {ov['from_centre_pct']}% from Centre, "
          f"₹{ov['total_cr']:,.0f} cr total, {len(payload['nodes'])} nodes / {len(payload['links'])} links")


if __name__ == "__main__":
    main()
