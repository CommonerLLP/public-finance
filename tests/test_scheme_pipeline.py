import sqlite3
import tempfile
import openpyxl
from pathlib import Path
from publicfinance.metadata import (
    ensure_db,
    seed_canonical_map,
    get_canonical,
    upsert_scheme_allocation,
    index_budget_doc,
    make_doc_id,
    _ICDS_CANONICAL_SEEDS,
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
    assert count == len(_ICDS_CANONICAL_SEEDS)


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


# ---------------------------------------------------------------------------
# union_budget_scraper tests
# ---------------------------------------------------------------------------

from publicfinance.union_budget_scraper import parse_demand_xls


def _make_fixture_xls() -> Path:
    """Minimal SBE-format fixture matching real file's 36-column layout."""
    wb = openpyxl.Workbook()
    ws = wb.active

    NUM_COLS = 36

    def blank_row():
        return [None] * NUM_COLS

    # Row 0: blank
    ws.append(blank_row())
    # Row 1: title
    row1 = blank_row()
    row1[1] = "Notes on Demands For Grants 2025-2026"
    ws.append(row1)
    # Row 2: blank
    ws.append(blank_row())
    # Row 3: ministry header
    row3 = blank_row()
    row3[1] = "Ministry of Women and Child Development\nDemand No. 101"
    ws.append(row3)
    # Row 4: units
    row4 = blank_row()
    row4[3] = "(In ₹ Crores)"
    ws.append(row4)
    # Row 5: year labels
    row5 = blank_row()
    row5[12] = "Actuals 2023-2024"
    row5[18] = "Budget Estimates 2024-2025"
    row5[25] = "Revised Estimates 2024-2025"
    row5[31] = "Budget Estimates 2025-2026"
    ws.append(row5)
    # Row 6: Revenue/Capital/Total headers
    row6 = blank_row()
    row6[12] = "Revenue"; row6[14] = "Capital"; row6[16] = "Total"
    row6[18] = "Revenue"; row6[20] = "Capital"; row6[22] = "Total"
    row6[25] = "Revenue"; row6[27] = "Capital"; row6[29] = "Total"
    row6[31] = "Revenue"; row6[33] = "Capital"; row6[35] = "Total"
    ws.append(row6)
    # Rows 7-11: preamble/section headers
    for _ in range(5):
        ws.append(blank_row())
    # Row 12: section header (should be skipped)
    row12 = blank_row()
    row12[3] = "TRANSFERS TO STATES/UTs"
    ws.append(row12)
    # Row 13: sub-header (should be skipped)
    row13 = blank_row()
    row13[3] = "Centrally Sponsored Schemes"
    ws.append(row13)
    # Row 14: the ICDS scheme line
    row14 = blank_row()
    row14[3] = "10 ."
    row14[5] = "Saksham Anganwadi and POSHAN 2.0"
    row14[12] = 19000.0;  row14[14] = 0.0;  row14[16] = 19000.0
    row14[18] = 21000.0;  row14[20] = 0.0;  row14[22] = 21000.0
    row14[25] = 20000.0;  row14[27] = 0.0;  row14[29] = 20000.0
    row14[31] = 22000.0;  row14[33] = 0.0;  row14[35] = 22000.0
    ws.append(row14)

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    wb.save(tmp.name)
    return Path(tmp.name)


def test_parse_demand_xls_returns_rows():
    xls = _make_fixture_xls()
    rows = parse_demand_xls(xls, budget_year="2025-26", demand_no="101")
    assert len(rows) > 0


def test_parse_demand_xls_extracts_scheme_name():
    xls = _make_fixture_xls()
    rows = parse_demand_xls(xls, budget_year="2025-26", demand_no="101")
    names = {r["scheme_name"] for r in rows}
    assert "Saksham Anganwadi and POSHAN 2.0" in names


def test_parse_demand_xls_correct_values():
    xls = _make_fixture_xls()
    rows = parse_demand_xls(xls, budget_year="2025-26", demand_no="101")
    be_curr = next(
        r for r in rows
        if r["scheme_name"] == "Saksham Anganwadi and POSHAN 2.0"
        and r["col_type"] == "be"
        and r["fiscal_year"] == "2025-26"
    )
    assert be_curr["total_cr"] == 22000.0
    assert be_curr["level"] == "central"
    assert be_curr["demand_no"] == "101"


def test_parse_demand_xls_produces_three_col_types():
    xls = _make_fixture_xls()
    rows = parse_demand_xls(xls, budget_year="2025-26", demand_no="101")
    col_types = {r["col_type"] for r in rows}
    assert col_types == {"actual", "be", "re"}


# ---------------------------------------------------------------------------
# extract_scheme_data tests
# ---------------------------------------------------------------------------

from publicfinance.extract_scheme_data import extract_xls_doc, extract_pdf_wcd_demand


def test_extract_xls_doc_writes_allocations():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    xls = _make_fixture_xls()
    doc_id = make_doc_id("test", "central", "101", "2025-26")
    index_budget_doc(
        doc_id=doc_id,
        state="central",
        fiscal_year="2025-26",
        document_type="demand_for_grants",
        source_url="https://example.com/sbe101.xlsx",
        local_path=str(xls),
        file_extension="xlsx",
        db_path=db,
    )
    extract_xls_doc(doc_id=doc_id, path=xls, budget_year="2025-26",
                    demand_no="101", db_path=db)
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM scheme_allocations").fetchone()[0]
    row = conn.execute(
        "SELECT scheme_canonical FROM scheme_allocations LIMIT 1"
    ).fetchone()
    conn.close()
    assert count > 0
    assert row[0] == "icds_anganwadi_services"


def test_extract_pdf_wcd_missing_file_returns_zero():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    n = extract_pdf_wcd_demand(
        doc_id="missing_doc",
        path=Path("/nonexistent/file.pdf"),
        state="Rajasthan",
        db_path=db,
    )
    assert n == 0


def test_extract_xls_doc_idempotent():
    db = _tmp_db()
    ensure_db(db)
    seed_canonical_map(db)
    xls = _make_fixture_xls()
    doc_id = make_doc_id("test", "central", "101", "2025-26")
    index_budget_doc(
        doc_id=doc_id,
        state="central",
        fiscal_year="2025-26",
        document_type="demand_for_grants",
        source_url="https://example.com/sbe101.xlsx",
        local_path=str(xls),
        file_extension="xlsx",
        db_path=db,
    )
    extract_xls_doc(doc_id=doc_id, path=xls, budget_year="2025-26",
                    demand_no="101", db_path=db)
    conn = sqlite3.connect(db)
    first_count = conn.execute(
        "SELECT COUNT(*) FROM scheme_allocations"
    ).fetchone()[0]
    conn.close()
    extract_xls_doc(doc_id=doc_id, path=xls, budget_year="2025-26",
                    demand_no="101", db_path=db)
    conn = sqlite3.connect(db)
    second_count = conn.execute(
        "SELECT COUNT(*) FROM scheme_allocations"
    ).fetchone()[0]
    conn.close()
    assert first_count == second_count
    assert first_count > 0
