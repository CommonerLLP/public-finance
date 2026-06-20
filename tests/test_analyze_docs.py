import sqlite3
import tempfile
from pathlib import Path
from publicfinance.metadata import ensure_db, upsert_probe_result
from publicfinance.llm_providers import RegexProvider

def _make_tmp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Path(tmp.name)

def test_doc_extraction_probe_table_created():
    db = _make_tmp_db()
    ensure_db(db)
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "doc_extraction_probe" in tables

def test_upsert_probe_result_inserts_row():
    db = _make_tmp_db()
    ensure_db(db)
    upsert_probe_result(
        doc_id="test_doc_001",
        file_size_bytes=102400,
        page_count=12,
        pdftotext_chars_p1=850,
        pdftotext_sample="Revenue receipts 1234",
        pdfplumber_tables_p1=2,
        has_devanagari=False,
        parser_route="table_pdf",
        austerity_score=1,
        extravagance_score=0,
        error=None,
        db_path=db,
    )
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT doc_id, austerity_score, extravagance_score FROM doc_extraction_probe WHERE doc_id='test_doc_001'"
    ).fetchone()
    conn.close()
    assert row == ("test_doc_001", 1, 0)


from publicfinance.analyze_docs import classify_route, probe_pdf


def test_classify_route_text_pdf():
    assert classify_route(
        file_extension="pdf",
        pdftotext_chars_p1=900,
        pdfplumber_tables_p1=0,
        has_devanagari=False,
    ) == "text_pdf"


def test_classify_route_table_pdf():
    assert classify_route(
        file_extension="pdf",
        pdftotext_chars_p1=300,
        pdfplumber_tables_p1=3,
        has_devanagari=False,
    ) == "table_pdf"


def test_classify_route_devanagari():
    assert classify_route(
        file_extension="pdf",
        pdftotext_chars_p1=400,
        pdfplumber_tables_p1=1,
        has_devanagari=True,
    ) == "devanagari_pdf"


def test_classify_route_scanned():
    assert classify_route(
        file_extension="pdf",
        pdftotext_chars_p1=30,
        pdfplumber_tables_p1=0,
        has_devanagari=False,
    ) == "scanned_pdf"


def test_classify_route_xls():
    assert classify_route(
        file_extension="xlsx",
        pdftotext_chars_p1=None,
        pdfplumber_tables_p1=None,
        has_devanagari=False,
    ) == "xls"


def test_probe_pdf_missing_file_returns_error():
    result = probe_pdf(Path("/nonexistent/path/file.pdf"), RegexProvider())
    assert result["parser_route"] == "unknown"
    assert result["error"] is not None
