import sqlite3
import tempfile
from pathlib import Path
from budget_crawler.metadata import (
    ensure_db,
    seed_canonical_map,
    get_canonical,
    upsert_scheme_allocation,
)


def _tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return Path(f.name)


def test_new_tables_created():
    db = _tmp_db()
    ensure_db(db)
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert "scheme_allocations" in tables
    assert "scheme_expenditures" in tables
    assert "scheme_canonical_map" in tables


def test_seed_canonical_map_inserts_icds_variants():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT source_name, canonical FROM scheme_canonical_map"
    ).fetchall()
    conn.close()
    canonicals = {r[1] for r in rows}
    assert "icds_anganwadi_services" in canonicals
    assert len(rows) >= 5


def test_seed_canonical_map_idempotent():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    seed_canonical_map(db)
    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM scheme_canonical_map"
    ).fetchone()[0]
    conn.close()
    assert count >= 5


def test_get_canonical_known_variant():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    assert get_canonical("ICDS", db) == "icds_anganwadi_services"
    assert get_canonical("Umbrella ICDS", db) == "icds_anganwadi_services"
    assert get_canonical("Saksham Anganwadi and POSHAN 2.0", db) == "icds_anganwadi_services"


def test_get_canonical_unknown_returns_none():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    assert get_canonical("Some Random Scheme", db) is None


def test_upsert_scheme_allocation_inserts():
    db = _tmp_db()
    ensure_db(db)
    upsert_scheme_allocation(
        doc_id="test_doc_001",
        level="central",
        state=None,
        fiscal_year="2024-25",
        demand_no="101",
        scheme_name="Umbrella ICDS",
        scheme_canonical="icds_anganwadi_services",
        col_type="be",
        revenue_cr=21000.0,
        capital_cr=0.0,
        total_cr=21000.0,
        db_path=db,
    )
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT scheme_canonical, total_cr FROM scheme_allocations"
    ).fetchone()
    conn.close()
    assert row == ("icds_anganwadi_services", 21000.0)


def test_upsert_scheme_allocation_idempotent():
    db = _tmp_db()
    ensure_db(db)
    kwargs = dict(
        doc_id="test_doc_001",
        level="central",
        state=None,
        fiscal_year="2024-25",
        demand_no="101",
        scheme_name="Umbrella ICDS",
        scheme_canonical="icds_anganwadi_services",
        col_type="be",
        revenue_cr=21000.0,
        capital_cr=0.0,
        total_cr=21000.0,
        db_path=db,
    )
    upsert_scheme_allocation(**kwargs)
    upsert_scheme_allocation(**kwargs)
    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM scheme_allocations"
    ).fetchone()[0]
    conn.close()
    assert count == 1
