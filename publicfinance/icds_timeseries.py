"""
Extract ICDS / Saksham Anganwadi and POSHAN 2.0 budget time series
from Union Budget Demand 101 XLS files.

Handles two column layouts that appear across years:
  - 36-col layout (2022-23, 2023-24, 2026-27): scheme name at col 5
  - 42-col layout (2024-25, 2025-26): scheme name at col 6

Output: CSV to stdout + human-readable summary.
"""

import csv
import io
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "union_budget"

ICDS_KEYWORDS = ("Saksham Anganwadi", "POSHAN 2.0", "Umbrella ICDS")

# Each entry: (xls_filename, budget_year)
# Skipping 2020-21 and 2021-22: demand 101 was Ministry of Youth Affairs those years.
FILES = [
    ("sbe101_2022-23.xls",  "2022-23"),
    ("sbe101_2023-24.xls",  "2023-24"),
    ("sbe101_2024-25.xlsx", "2024-25"),
    ("sbe101_2025-26.xlsx", "2025-26"),
    ("sbe101_2026-27.xlsx", "2026-27"),
]

# Column layout A — 36 columns, name at col 5
_A = dict(
    name=5,
    actuals_rev=12, actuals_cap=14, actuals_tot=16,
    be_prev_rev=18, be_prev_cap=20, be_prev_tot=22,
    re_prev_rev=25, re_prev_cap=27, re_prev_tot=29,
    be_curr_rev=31, be_curr_cap=33, be_curr_tot=35,
)

# Column layout B — 42 columns, name at col 6
_B = dict(
    name=6,
    actuals_rev=15, actuals_cap=17, actuals_tot=19,
    be_prev_rev=21, be_prev_cap=23, be_prev_tot=25,
    re_prev_rev=29, re_prev_cap=31, re_prev_tot=33,
    be_curr_rev=35, be_curr_cap=39, be_curr_tot=41,
)


def _prev_year(fy: str) -> str:
    start = int(fy[:4])
    return f"{start - 1}-{str(start)[-2:]}"


def _actuals_year(fy: str) -> str:
    return _prev_year(_prev_year(fy))


def _v(row, col):
    if col >= len(row):
        return None
    val = row.iloc[col]
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def extract_file(path: Path, budget_year: str) -> list[dict]:
    df = pd.read_excel(path, header=None, dtype=object)
    ncols = df.shape[1]
    cols = _B if ncols >= 40 else _A

    actuals_fy = _actuals_year(budget_year)
    prev_fy = _prev_year(budget_year)

    for _, row in df.iterrows():
        cell = row.iloc[cols["name"]] if cols["name"] < ncols else None
        if pd.isna(cell):
            continue
        name = str(cell).strip()
        if not any(k in name for k in ICDS_KEYWORDS):
            continue

        return [
            {
                "scheme": name,
                "budget_year": budget_year,
                "col_type": "actual",
                "fiscal_year": actuals_fy,
                "revenue_cr": _v(row, cols["actuals_rev"]),
                "capital_cr": _v(row, cols["actuals_cap"]),
                "total_cr":   _v(row, cols["actuals_tot"]),
            },
            {
                "scheme": name,
                "budget_year": budget_year,
                "col_type": "be",
                "fiscal_year": prev_fy,
                "revenue_cr": _v(row, cols["be_prev_rev"]),
                "capital_cr": _v(row, cols["be_prev_cap"]),
                "total_cr":   _v(row, cols["be_prev_tot"]),
            },
            {
                "scheme": name,
                "budget_year": budget_year,
                "col_type": "re",
                "fiscal_year": prev_fy,
                "revenue_cr": _v(row, cols["re_prev_rev"]),
                "capital_cr": _v(row, cols["re_prev_cap"]),
                "total_cr":   _v(row, cols["re_prev_tot"]),
            },
            {
                "scheme": name,
                "budget_year": budget_year,
                "col_type": "be",
                "fiscal_year": budget_year,
                "revenue_cr": _v(row, cols["be_curr_rev"]),
                "capital_cr": _v(row, cols["be_curr_cap"]),
                "total_cr":   _v(row, cols["be_curr_tot"]),
            },
        ]
    return []


def build_timeseries() -> list[dict]:
    all_rows = []
    for filename, budget_year in FILES:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"[missing] {filename}", file=sys.stderr)
            continue
        rows = extract_file(path, budget_year)
        if not rows:
            print(f"[warn] no ICDS row found in {filename}", file=sys.stderr)
        else:
            print(f"[ok] {filename} → {len(rows)} records", file=sys.stderr)
            all_rows.extend(rows)
    return all_rows


def dedupe(rows: list[dict]) -> list[dict]:
    """Each (fiscal_year, col_type) pair appears in multiple budget documents.
    Keep the most recent budget_year's reading (latest is most authoritative)."""
    seen = {}
    for r in rows:
        key = (r["fiscal_year"], r["col_type"])
        # later entries overwrite earlier ones; FILES is in ascending year order
        seen[key] = r
    return sorted(seen.values(), key=lambda r: (r["fiscal_year"], r["col_type"]))


def print_summary(rows: list[dict]) -> None:
    # Build per-year lookup
    by_fy: dict[str, dict] = {}
    for r in rows:
        fy = r["fiscal_year"]
        if fy not in by_fy:
            by_fy[fy] = {}
        by_fy[fy][r["col_type"]] = r["total_cr"]

    print("\nICDS / Saksham Anganwadi + POSHAN 2.0 — Union Budget Demand 101")
    print("(₹ crore, total = revenue + capital)")
    print(f"\n{'Year':<10} {'Actuals':>12} {'BE':>12} {'RE':>12} {'BE vs Act':>12} {'RE vs BE':>12}")
    print("-" * 72)

    for fy in sorted(by_fy):
        d = by_fy[fy]
        act = d.get("actual")
        be  = d.get("be")
        re  = d.get("re")

        act_s = f"{act:>10,.2f}" if act is not None else f"{'—':>10}"
        be_s  = f"{be:>10,.2f}"  if be  is not None else f"{'—':>10}"
        re_s  = f"{re:>10,.2f}"  if re  is not None else f"{'—':>10}"

        be_vs_act = ""
        if be is not None and act is not None:
            pct = (act - be) / be * 100
            be_vs_act = f"{pct:+.1f}%"

        re_vs_be = ""
        if re is not None and be is not None:
            pct = (re - be) / be * 100
            re_vs_be = f"{pct:+.1f}%"

        print(f"{fy:<10} {act_s} {be_s} {re_s} {be_vs_act:>12} {re_vs_be:>12}")


def write_csv(rows: list[dict], path: Path) -> None:
    fields = ["fiscal_year", "col_type", "budget_year", "scheme",
              "revenue_cr", "capital_cr", "total_cr"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n[saved] {path}", file=sys.stderr)


def main() -> None:
    rows = build_timeseries()
    rows = dedupe(rows)
    print_summary(rows)
    out = PROJECT_ROOT / "data" / "icds_budget_timeseries.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out)


if __name__ == "__main__":
    main()
