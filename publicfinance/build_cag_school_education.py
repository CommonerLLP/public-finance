"""Batch-extract school-education heads from CAG Finance Accounts Vol-II PDFs.

The school-education sibling of :mod:`build_cag_library_national` (REQ-0047 from
theright2read): same acquisition manifest, same reader, same self-validation, a
different head set —

* ``2202-01`` Elementary Education, ``2202-02`` Secondary Education and
  ``2202-80`` General, read as printed SUB-MAJOR totals (each has a dozen minor
  heads, so no single minor line carries the figure);
* ``4202-01-201`` / ``4202-01-202``, the school capital minors, read as blocks
  closed by their ``Total - 201`` / ``Total - 202`` lines.

Finance Accounts give the HEAD, not the scheme: a Samagra Shiksha or a State's
own school programme is not separable here. That needs State Demands for Grants.

No hardcoded paths (org data-directory rule): pass ``--cag-dir`` (the
commoner-probe ``cag`` output directory, which may live on an external volume)
and ``--out`` (the CSV to write). CAG Finance Accounts are ``lakh``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .cag_finance_accounts import SCHOOL_SPECS, extract_school_heads

# (csv column, HeadSpec label) in report order.
HEADS = [
    ("elem_rev_cr", "elementary_rev"),
    ("sec_rev_cr", "secondary_rev"),
    ("gen_rev_cr", "general_rev"),
    ("elem_cap_cr", "elementary_cap"),
    ("sec_cap_cr", "secondary_cap"),
]
FIELDS = (
    ["state", "fy"]
    + [c for c, _ in HEADS]
    + [f"{c.rsplit('_cr', 1)[0]}_self_validated" for c, _ in HEADS]
    + ["source_statement", "source_url"]
    + [f"{c.rsplit('_cr', 1)[0]}_source_line" for c, _ in HEADS]
)


def _load_vol2(cag_dir: Path) -> list[dict]:
    """Vol-II records from commoner-probe's manifest.jsonl (downloaded only)."""
    manifest = cag_dir / "manifest.jsonl"
    if not manifest.exists():
        raise SystemExit(f"no manifest at {manifest} — run the commoner-probe `cag` pull first")
    seen: dict[tuple, dict] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("volume") != "II" or r.get("status") not in ("downloaded", "skipped_exists"):
            continue
        # Karnataka ships Vol-II as two parts; keep both, keyed by filename.
        seen[(r["state"], r["year"], r["filename"])] = r
    return list(seen.values())


def build(cag_dir: Path, out: Path) -> list[dict]:
    records = _load_vol2(cag_dir)
    by_state_year: dict[tuple, dict] = {}
    for rec in sorted(records, key=lambda r: (r["state"], r["year"], r["filename"])):
        # The manifest's `dest` is relative to the adapter's run cwd; resolve the
        # PDF under cag_dir instead (its parent dir name is the state slug).
        pdf = cag_dir / Path(rec["dest"]).parent.name / rec["filename"]
        if not pdf.exists():
            print(f"  MISSING {rec['state']} {rec['year']}: {pdf}")
            continue
        heads = extract_school_heads(pdf, unit="lakh")
        key = (rec["state"], rec["year"])
        row = by_state_year.setdefault(key, {
            "state": rec["state"], "fy": rec["year"],
            "source_statement": "CAG Finance Accounts Vol-II (Statements 15/16)",
            "source_url": rec["url"],
        })
        for col, label in HEADS:
            stem = col.rsplit("_cr", 1)[0]
            head = heads.get(label)
            row.setdefault(col, None)
            row.setdefault(f"{stem}_self_validated", None)
            row.setdefault(f"{stem}_source_line", "")
            if head is None:
                continue
            if head.value_crore is not None:
                # Multi-part Vol-II (Karnataka): sum the head across parts.
                row[col] = round((row[col] or 0.0) + head.value_crore, 4)
            prev = row[f"{stem}_self_validated"]
            row[f"{stem}_self_validated"] = (True if prev is None else prev) and head.self_validated
            if head.raw_line:
                row[f"{stem}_source_line"] = head.raw_line.strip()[:90]

    rows = [by_state_year[k] for k in sorted(by_state_year)]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cag-dir", required=True, help="commoner-probe `cag` output dir (has manifest.jsonl)")
    ap.add_argument("--out", required=True, help="output CSV path")
    args = ap.parse_args()
    rows = build(Path(args.cag_dir), Path(args.out))

    print(f"\n{'State':22} {'FY':8} {'2202-01':>12} {'2202-02':>12} {'4202-01-201':>12}  unproved")
    counts = {label: [0, 0] for _, label in HEADS}  # [extracted, proved]
    for r in rows:
        unproved = [c.rsplit("_cr", 1)[0] for c, _ in HEADS
                    if r.get(c) is not None and not r.get(f"{c.rsplit('_cr', 1)[0]}_self_validated")]
        missing = [c.rsplit("_cr", 1)[0] for c, _ in HEADS if r.get(c) is None]
        def _f(col):
            v = r.get(col)
            return "" if v is None else f"{v:12.2f}"
        print(f"{r['state']:22} {r['fy']:8} {_f('elem_rev_cr')} {_f('sec_rev_cr')} {_f('elem_cap_cr')}  "
              f"{','.join(unproved) or '-'}{('  missing: ' + ','.join(missing)) if missing else ''}")
        for col, label in HEADS:
            if r.get(col) is not None:
                counts[label][0] += 1
                counts[label][1] += bool(r.get(f"{col.rsplit('_cr', 1)[0]}_self_validated"))

    print(f"\n{len(rows)} state-years from {len(SCHOOL_SPECS)} heads")
    for _, label in HEADS:
        got, proved = counts[label]
        print(f"  {label:16s} extracted {got:3d}/{len(rows)}  self-validated {proved:3d}")


if __name__ == "__main__":
    main()
