"""Driver: build a money-flow Sankey for any state/year/view.

Ports & adapters: this picks an input adapter, gets a normalised model, hands it
to the source-agnostic core, and writes references/lmmha/lod/sankey_<state>_<view>.json.
Adding a state = adding an adapter entry below, not editing the core.

    python -m viz.build_sankey --state gujarat --fy 2022-23 --view sector
    python -m viz.build_sankey --state assam   --fy 2023-24 --view balance
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from viz.sankey import core
from viz.sankey.adapters import gujarat_demands, gujarat_receipts, observed_json, rbi_balance

REPO = Path(__file__).resolve().parents[1]
LOD = REPO / "references" / "lmmha" / "lod"

# (state, view) -> callable(state, fy) -> model.  state names are lower-case.
SECTOR_ADAPTERS = {
    "assam": observed_json.load,
    "gujarat": gujarat_demands.load,
}
# balance adapters: a state funds its own sources from whatever document it has
BALANCE_ADAPTERS = {
    "gujarat": gujarat_receipts.load,   # Gujarat's own receipts book
}


def build(state: str, fy: str, view: str) -> dict:
    key = state.lower()
    if view == "sector":
        adapter = SECTOR_ADAPTERS.get(key)
        if adapter is None:
            raise SystemExit(f"no sector adapter for {state}; have {sorted(SECTOR_ADAPTERS)}")
        return core.build_sector(adapter(state.title(), fy))
    if view == "balance":
        adapter = BALANCE_ADAPTERS.get(key, rbi_balance.load)  # default: RBI State Finances
        return core.build_balance(adapter(state.title(), fy))
    raise SystemExit(f"unknown view {view!r} (sector|balance)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a state money-flow Sankey payload")
    ap.add_argument("--state", required=True)
    ap.add_argument("--fy", required=True, help="e.g. 2022-23")
    ap.add_argument("--view", choices=("sector", "balance"), default="sector")
    args = ap.parse_args()

    payload = build(args.state, args.fy, args.view)
    out = LOD / f"sankey_{args.state.lower()}_{args.view}_{args.fy}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    m = payload["meta"]
    print(f"Wrote {out.relative_to(REPO)}  state={m['state']} fy={m['fy']} "
          f"view={args.view} total=Rs {m['total_cr']:,.0f} cr "
          f"nodes={len(payload['nodes'])} links={len(payload['links'])}")


if __name__ == "__main__":
    main()
