"""CLI: python -m publicfinance.min_wage.run --state kerala [--all]"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
from pathlib import Path

from . import registry
from .base import SchedulingStatus, WageRow

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RATES_CSV = DATA_DIR / "state_min_wages.csv"
STATUS_CSV = DATA_DIR / "state_scheme_worker_scheduling.csv"


def _write_rows(path: Path, dc_class, rows):
    cols = [f.name for f in fields(dc_class)]
    existing: list[dict] = []
    if path.exists():
        with open(path) as f:
            existing = list(csv.DictReader(f))
        # Drop any rows for states we are re-running (caller passes only one state per run).
        states_in_run = {getattr(r, "state") for r in rows}
        existing = [e for e in existing if e.get("state") not in states_in_run]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(existing)
        for r in rows:
            d = asdict(r)
            # str-ify date/datetime for CSV
            for k, v in list(d.items()):
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            w.writerow(d)


def run_state(state_key: str) -> tuple[int, int, int]:
    cls = registry.get(state_key)
    scraper = cls(data_root=DATA_DIR)
    print(f"=== {scraper.state} ===")

    status_rows = scraper.scheduling_status()
    print(f"  scheduling-status rows: {len(status_rows)}")
    for s in status_rows:
        print(f"    [{s.status:>22}] {s.comparable_employment}")

    notifs = scraper.fetch_notifications()
    print(f"  notifications matched: {len(notifs)}")

    wage_rows: list[WageRow] = []
    downloaded = 0
    for n in notifs:
        local_path = scraper.local_path_for(n)
        try:
            downloaded_now = scraper.download(n.url, local_path)
            if downloaded_now:
                downloaded += 1
                print(f"    ↓ {local_path.name}")
            else:
                print(f"    · {local_path.name} (cached)")
        except Exception as e:
            print(f"    ✗ {n.url}: {e}")
            continue
        rows = scraper.parse(n, local_path)
        print(f"      {len(rows)} wage rows parsed ({'excluded' if n.is_excluded else n.employment_category})")
        wage_rows.extend(rows)

    _write_rows(STATUS_CSV, SchedulingStatus, status_rows)
    _write_rows(RATES_CSV, WageRow, wage_rows)
    return len(status_rows), downloaded, len(wage_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", help="State key (e.g. kerala)")
    ap.add_argument("--all", action="store_true", help="Run all registered states")
    args = ap.parse_args()
    if not args.state and not args.all:
        ap.error("provide --state or --all")
    states = registry.all_states() if args.all else [args.state]
    totals = {"status": 0, "downloads": 0, "rates": 0}
    for s in states:
        st, dl, rt = run_state(s)
        totals["status"] += st
        totals["downloads"] += dl
        totals["rates"] += rt
    print(f"\nTotals: {totals}")
    print(f"  → {RATES_CSV}")
    print(f"  → {STATUS_CSV}")


if __name__ == "__main__":
    main()
