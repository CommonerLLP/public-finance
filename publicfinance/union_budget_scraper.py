"""
Union Budget Statement of Budget Estimates (SBE) — analysis layer.

Acquisition (downloading the SBE spreadsheets, with provenance) is delegated to
commoner-probe's ``BudgetProbe`` via :mod:`probe_runner`. What stays here is the
XLS -> scheme-row analysis (``parse_demand_xls``), which ``extract_scheme_data``
consumes.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH
from probe_runner import run_union_budget

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_COL_SCHEME_NAME = 5
_COL_ACTUALS_REV = 12
_COL_ACTUALS_CAP = 14
_COL_ACTUALS_TOT = 16
_COL_BE_PREV_REV = 18
_COL_BE_PREV_CAP = 20
_COL_BE_PREV_TOT = 22
_COL_RE_PREV_REV = 25
_COL_RE_PREV_CAP = 27
_COL_RE_PREV_TOT = 29
_COL_BE_CURR_REV = 31
_COL_BE_CURR_CAP = 33
_COL_BE_CURR_TOT = 35

_SKIP_KEYWORDS = (
    "CENTRE",
    "TRANSFERS",
    "Total",
    "Grand Total",
    "Centrally Sponsored",
    "Autonomous",
    "Others",
    "Establishment",
    "Gross",
    "Net",
    "Recoveries",
    "Receipts",
    "Social",
    "Secretariat",
    "Ministry",
    "(In",
    "B. Developmental",
)


def _prev_year(fiscal_year: str) -> str:
    """'2026-27' → '2025-26'"""
    start = int(fiscal_year[:4])
    return f"{start - 1}-{str(start)[-2:]}"


def _actuals_year(fiscal_year: str) -> str:
    """'2026-27' → '2024-25' (actuals are 2 years before current budget)"""
    return _prev_year(_prev_year(fiscal_year))


def _is_numeric(val) -> bool:
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False


def _to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _is_scheme_row(row) -> bool:
    """Return True if this row looks like a valid scheme data line."""
    raw = row.iloc[_COL_SCHEME_NAME]
    if pd.isna(raw):
        return False
    name = str(raw).strip()
    if not name or name.lower() == "nan":
        return False
    for kw in _SKIP_KEYWORDS:
        if kw in name:
            return False
    totals = [_COL_ACTUALS_TOT, _COL_BE_PREV_TOT, _COL_RE_PREV_TOT, _COL_BE_CURR_TOT]
    if not any(_is_numeric(row.iloc[c]) for c in totals if c < len(row)):
        return False
    return True


def parse_demand_xls(path, budget_year: str, demand_no: str) -> list[dict]:
    """
    Parse a Union Budget SBE XLS file and return scheme-level allocation rows.

    Returns a list of dicts with keys:
        scheme_name, col_type, fiscal_year, revenue_cr, capital_cr, total_cr,
        level, demand_no
    """
    df = pd.read_excel(path, header=None, dtype=object)

    actuals_fy = _actuals_year(budget_year)
    prev_fy = _prev_year(budget_year)
    curr_fy = budget_year

    rows = []
    for _, row in df.iterrows():
        if not _is_scheme_row(row):
            continue
        scheme_name = str(row.iloc[_COL_SCHEME_NAME]).strip()

        periods = [
            ("actual",  actuals_fy, _COL_ACTUALS_REV, _COL_ACTUALS_CAP, _COL_ACTUALS_TOT),
            ("be",      prev_fy,    _COL_BE_PREV_REV,  _COL_BE_PREV_CAP,  _COL_BE_PREV_TOT),
            ("re",      prev_fy,    _COL_RE_PREV_REV,  _COL_RE_PREV_CAP,  _COL_RE_PREV_TOT),
            ("be",      curr_fy,    _COL_BE_CURR_REV,  _COL_BE_CURR_CAP,  _COL_BE_CURR_TOT),
        ]
        for col_type, fiscal_year, col_rev, col_cap, col_tot in periods:
            rows.append({
                "scheme_name": scheme_name,
                "col_type": col_type,
                "fiscal_year": fiscal_year,
                "revenue_cr": _to_float(row.iloc[col_rev]) if col_rev < len(row) else None,
                "capital_cr": _to_float(row.iloc[col_cap]) if col_cap < len(row) else None,
                "total_cr":   _to_float(row.iloc[col_tot]) if col_tot < len(row) else None,
                "level": "central",
                "demand_no": demand_no,
            })
    return rows


def run(
    demand_no: str,
    out_dir: Path,
    db_path: Path = DEFAULT_DB_PATH,
    dry_run: bool = False,
) -> None:
    """Acquire all archive years for a demand via commoner-probe and index them.

    Acquisition + SHA-256 provenance is delegated to ``BudgetProbe`` (see
    :mod:`probe_runner`); this wrapper just reports per-file status.
    """
    records, indexed = run_union_budget(demand_no, out_dir, db_path=db_path, dry_run=dry_run)
    for rec in records:
        status = rec.get("status")
        if status == "dry_run":
            print(f"[dry-run] {rec['fiscal_year']} would fetch {rec['url']}")
        elif status in ("downloaded", "skipped_exists"):
            print(f"[{status}] {rec['fiscal_year']} -> {rec['dest']}")
        elif status == "not_found":
            print(f"[not-found] {rec['fiscal_year']} {rec['url']}")
        else:
            print(f"[{status}] {rec['fiscal_year']} {rec.get('error', '')}".rstrip())
    if not dry_run:
        print(f"\nIndexed {indexed} file(s) for demand {demand_no}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Union Budget SBE XLS files for a demand number."
    )
    parser.add_argument("--demand", default="101", help="Demand number (default: 101)")
    parser.add_argument(
        "--out", default="data/union_budget", help="Output directory for XLS files"
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite DB path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print URLs without downloading",
    )
    args = parser.parse_args()

    run(
        demand_no=args.demand,
        out_dir=PROJECT_ROOT / args.out,
        db_path=Path(args.db),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
