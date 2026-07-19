"""probe_runner delegates Union/RBI acquisition to commoner-probe's BudgetProbe.

The Union dry-run path is fully offline (the SBE URL table is static in the
probe), so we can assert the bridge yields ``budget_source_file`` records and
indexes nothing — without touching the network or a real DB.
"""

from publicfinance.probe_runner import run_union_budget


def test_run_union_budget_dry_run_is_offline_and_indexes_nothing(tmp_path):
    db = tmp_path / "t.db"
    records, indexed = run_union_budget("101", tmp_path, db_path=db, dry_run=True)

    assert records
    assert all(r["kind"] == "budget_source_file" for r in records)
    assert all(r["status"] == "dry_run" for r in records)
    assert indexed == 0
    assert not db.exists()  # dry-run writes no budget_docs rows


def test_run_union_budget_covers_static_archive_years(tmp_path):
    records, _ = run_union_budget("101", tmp_path, db_path=tmp_path / "t.db", dry_run=True)
    years = {r["fiscal_year"] for r in records}
    # The probe's UNION_BUDGET_YEARS table (ported from this repo's old _ARCHIVE_YEARS).
    assert {"2026-27", "2020-21"} <= years
