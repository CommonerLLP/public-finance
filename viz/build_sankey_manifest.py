"""Generate references/lmmha/lod/sankey_manifest.json from the built Sankey files.

The manifest is the JOIN TABLE the renderer (flow.js) reads: which jurisdictions
exist, and for each, which views x years have a JSON file. Generating it (instead
of hand-editing) is what lets the picker scale to all states / UTs / the Union for
many years — adding coverage is "build the JSON, regenerate", never an edit here.

File convention:  sankey_<jurisdiction>_<viewfile>_<fy>.json
  - jurisdiction: a single token; multi-word uses hyphens (e.g. tamil-nadu, andaman-nicobar)
  - viewfile: sector | balance | flow | offbudget   (sector -> manifest view "detailed")
  - fy: YYYY-YY

    python -m viz.build_sankey_manifest
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOD = REPO / "references" / "lmmha" / "lod"

VIEWFILE_TO_VIEW = {"sector": "detailed", "balance": "balance", "flow": "flow",
                    "offbudget": "offbudget"}
FY = re.compile(r"\d{4}-\d{2}$")

# jurisdiction code -> (label, type). Unlisted codes default to title-case + "state".
REGISTRY = {
    "union": ("Union of India", "union"),
    "delhi": ("Delhi (NCT)", "ut"),
    "puducherry": ("Puducherry", "ut"),
    "jammu-kashmir": ("Jammu & Kashmir", "ut"),
}
JTYPE_ORDER = {"union": 0, "state": 1, "ut": 2}


def label_and_type(code: str) -> tuple[str, str]:
    if code in REGISTRY:
        return REGISTRY[code]
    return code.replace("-", " ").title(), "state"


def scan() -> dict:
    juris: dict[str, dict] = {}
    for f in sorted(LOD.glob("sankey_*.json")):
        parts = f.stem[len("sankey_"):].split("_")
        if len(parts) < 3 or not FY.match(parts[-1]):
            continue  # skip legacy files without the <juris>_<view>_<fy> shape
        fy, viewfile, code = parts[-1], parts[-2], "_".join(parts[:-2])
        view = VIEWFILE_TO_VIEW.get(viewfile)
        if not view:
            continue
        juris.setdefault(code, {}).setdefault(view, set()).add(fy)
    return juris


def build() -> dict:
    juris = scan()
    states = []
    for code in sorted(juris):
        label, jtype = label_and_type(code)
        views = {v: sorted(years) for v, years in sorted(juris[code].items())}
        states.append({"state": code, "label": label, "type": jtype, "views": views})
    states.sort(key=lambda s: (JTYPE_ORDER.get(s["type"], 1), s["label"]))
    return {"_generated_by": "viz/build_sankey_manifest.py", "states": states}


def main() -> None:
    manifest = build()
    out = LOD / "sankey_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    rows = ", ".join(f"{s['state']}[{'/'.join(s['views'])}]" for s in manifest["states"])
    print(f"Wrote {out.relative_to(REPO)} — {len(manifest['states'])} jurisdictions: {rows}")


if __name__ == "__main__":
    main()
