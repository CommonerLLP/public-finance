"""Batch-extract public-library heads from CAG Finance Accounts Vol-II PDFs.

Consumes a directory of Vol-II PDFs acquired by commoner-probe's ``cag`` adapter
(read from its ``manifest.jsonl`` for state / year / volume / path) and runs
:func:`cag_finance_accounts.extract_library_heads` on each. Emits one CSV row
per (state, fiscal year) carrying receipts / revenue / capital / loans in crore,
the capital-to-revenue ratio, and per-head provenance (the raw source line).

This is the national extension of ``references/lmmha/lod/cag_library_four_head.csv``:
where that file previously held a single Rajasthan Budget-Estimate row, this fills
it with CAG *actuals*, state by state, for a common fiscal year.

No hardcoded paths (org data-directory rule): pass ``--cag-dir`` (the
commoner-probe ``cag`` output directory, which may live on an external volume)
and ``--out`` (the CSV to write). CAG Finance Accounts are ``lakh``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .cag_finance_accounts import extract_library_heads

FIELDS = [
    "state", "fy",
    "lib_receipts_cr", "lib_rev_exp_cr", "lib_cap_exp_cr", "lib_loans_cr",
    "cap_to_rev_pct", "rev_self_validated", "cap_self_validated",
    "source_statement", "source_url", "cap_source_line", "rev_source_line",
]


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


def _pct(cap: float | None, rev: float | None) -> float | None:
    if cap is None or not rev:
        return None
    return round(100.0 * cap / rev, 2)


def build(cag_dir: Path, out: Path) -> list[dict]:
    records = _load_vol2(cag_dir)
    # Merge multi-part Vol-II (Karnataka) by summing each head across parts.
    by_state_year: dict[tuple, dict] = {}
    for rec in sorted(records, key=lambda r: (r["state"], r["year"], r["filename"])):
        # The manifest's `dest` is relative to the adapter's run cwd; resolve the
        # PDF under cag_dir instead (its parent dir name is the state slug).
        pdf = cag_dir / Path(rec["dest"]).parent.name / rec["filename"]
        if not pdf.exists():
            print(f"  MISSING {rec['state']} {rec['year']}: {pdf}")
            continue
        heads = extract_library_heads(pdf, unit="lakh")
        key = (rec["state"], rec["year"])
        row = by_state_year.setdefault(key, {
            "state": rec["state"], "fy": rec["year"],
            "lib_receipts_cr": None, "lib_rev_exp_cr": None,
            "lib_cap_exp_cr": None, "lib_loans_cr": None,
            "rev_self_validated": None, "cap_self_validated": None,
            "source_statement": "CAG Finance Accounts Vol-II (Statements 15/16)",
            "source_url": rec["url"], "cap_source_line": "", "rev_source_line": "",
        })

        def _acc(col, head):
            if head is None or head.value_crore is None:
                return
            row[col] = round((row[col] or 0.0) + head.value_crore, 4)

        _acc("lib_receipts_cr", heads.receipts)
        _acc("lib_rev_exp_cr", heads.revenue)
        _acc("lib_cap_exp_cr", heads.capital)
        _acc("lib_loans_cr", heads.loans)
        # self-validation flags: AND across parts (Karnataka), False if any part unvalidated
        if heads.revenue:
            row["rev_self_validated"] = (row["rev_self_validated"] if row["rev_self_validated"] is not None else True) and heads.revenue.self_validated
        if heads.capital:
            row["cap_self_validated"] = (row["cap_self_validated"] if row["cap_self_validated"] is not None else True) and heads.capital.self_validated
        if heads.capital and heads.capital.raw_line:
            row["cap_source_line"] = heads.capital.raw_line[:90]
        if heads.revenue and heads.revenue.raw_line:
            row["rev_source_line"] = heads.revenue.raw_line[:90]

    rows = []
    for key in sorted(by_state_year):
        row = by_state_year[key]
        row["cap_to_rev_pct"] = _pct(row["lib_cap_exp_cr"], row["lib_rev_exp_cr"])
        rows.append(row)

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

    # Report + national aggregate. A trailing flag marks capital reads that are
    # NOT self-validated against the document's own per-cent column (needs a human
    # eyeball); "?" marks capital that could not be extracted at all.
    print(f"{'State':22} {'FY':8} {'revenue':>10} {'capital':>10} {'cap%rev':>8}  flag")
    tot_rev = tot_cap = tot_cap_sv = 0.0
    n_cap = n_cap_sv = 0
    for r in rows:
        rev, cap = r["lib_rev_exp_cr"], r["lib_cap_exp_cr"]
        flag = "" if cap is None else ("✓" if r["cap_self_validated"] else "review")
        if cap is None:
            flag = "? capital not extracted"
        print(f"{r['state']:22} {r['fy']:8} {('' if rev is None else f'{rev:10.2f}')} "
              f"{('' if cap is None else f'{cap:10.2f}')} "
              f"{('' if r['cap_to_rev_pct'] is None else f'{r['cap_to_rev_pct']:7.1f}%')}  {flag}")
        if rev:
            tot_rev += rev
        if cap is not None:
            tot_cap += cap
            n_cap += 1
            if r["cap_self_validated"]:
                tot_cap_sv += cap
                n_cap_sv += 1
    print("-" * 70)
    print(f"{'NATIONAL (' + str(len(rows)) + ' states)':22} {'':8} {tot_rev:10.2f} {tot_cap:10.2f} "
          f"{(100.0*tot_cap/tot_rev if tot_rev else 0):7.1f}%")
    print(f"\ncapital extracted for {n_cap}/{len(rows)} states "
          f"({n_cap_sv} self-validated, {n_cap - n_cap_sv} need review, {len(rows) - n_cap} not extractable)")
    print(f"revenue self-validated for {sum(1 for r in rows if r['rev_self_validated'])}/{len(rows)} states")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
