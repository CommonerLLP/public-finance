"""RBI "State Finances: A Study of Budgets" — acquisition delegated to commoner-probe.

Document discovery (parsing the RBI publication page) and download are delegated
to commoner-probe's ``BudgetProbe`` via :mod:`probe_runner`, which downloads each
document with SHA-256 provenance and indexes it into the ``budget_docs`` table.
The prior local lxml + ScrappingUtils implementation has been removed; this file
is now a thin CLI wrapper.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH  # noqa: E402
from probe_runner import run_rbi  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "data" / "rbi"
RBI_STATE_FINANCES_URL = (
    "https://www.rbi.org.in/scripts/AnnualPublications.aspx"
    "?head=State+Finances+%3a+A+Study+of+Budgets"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Acquire RBI State Finances budget documents (delegated to commoner-probe)."
    )
    parser.add_argument("--url", default=RBI_STATE_FINANCES_URL, help="RBI publication page URL to crawl.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Output directory for downloaded files.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite metadata database path.")
    parser.add_argument("--dry-run", action="store_true", help="List discovered documents without downloading.")
    return parser.parse_args()


def main():
    args = parse_args()
    records, indexed = run_rbi(
        out_dir=args.out_dir,
        db_path=Path(args.db),
        dry_run=args.dry_run,
        rbi_url=args.url,
    )
    for rec in records:
        status = rec.get("status")
        if status in ("downloaded", "skipped_exists"):
            print(f"[{status}] {rec['fiscal_year']} | {rec.get('section', '')} | {rec['filename']}")
        elif status == "dry_run":
            print(f"[dry-run] {rec['url']}")
        else:
            print(f"[{status}] {rec.get('url', '')} {rec.get('error', '')}".rstrip())
    print(f"\nDiscovered {len(records)} RBI document(s); indexed {indexed}.")


if __name__ == "__main__":
    main()
