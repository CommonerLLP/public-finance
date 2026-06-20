"""
Extraction layer — reads indexed budget documents and writes scheme-level
allocation rows to scheme_allocations.

Usage:
    .venv/bin/python publicfinance/extract_scheme_data.py --level central
    .venv/bin/python publicfinance/extract_scheme_data.py --state Rajasthan
"""

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
import pdfplumber

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db, get_canonical, upsert_scheme_allocation
from union_budget_scraper import parse_demand_xls


def _demand_from_path(path: Path) -> str:
    m = re.search(r"sbe(\d+)", path.stem)
    return m.group(1) if m else "unknown"


def extract_xls_doc(*, doc_id, path, budget_year, demand_no, db_path) -> int:
    path = Path(path)
    rows = parse_demand_xls(path, budget_year=budget_year, demand_no=demand_no)
    written = 0
    for row in rows:
        canonical = get_canonical(row["scheme_name"], db_path)
        if canonical is None:
            continue
        upsert_scheme_allocation(
            doc_id=doc_id,
            level=row["level"],
            state=None if row["level"] == "central" else row.get("state"),
            fiscal_year=row["fiscal_year"],
            demand_no=row["demand_no"],
            scheme_name=row["scheme_name"],
            scheme_canonical=canonical,
            col_type=row["col_type"],
            revenue_cr=row["revenue_cr"],
            capital_cr=row["capital_cr"],
            total_cr=row["total_cr"],
            db_path=db_path,
        )
        written += 1
    return written


_WCD_HEADERS = [
    "women and child development",
    "महिला एवं बाल विकास",
    "wcd",
]

_SCHEME_KEYWORDS = [
    "anganwadi", "icds", "poshan", "child development",
    "saksham", "umbrella icds",
]


def _find_wcd_pages(pdf) -> list[int]:
    """Return 0-indexed page numbers where the WCD section header appears."""
    pages = []
    for i, page in enumerate(pdf.pages):
        text = (page.extract_text() or "").lower()
        if any(h in text for h in _WCD_HEADERS):
            pages.append(i)
    return pages


def _parse_scheme_line(line: str) -> tuple[str, float] | None:
    """
    Extract (scheme_name, total_cr) from a text line, or None.
    Only matches lines with a scheme keyword followed by a number at the end.
    """
    m = re.search(r"^(.+?)\s+([\d,]+\.?\d*)\s*$", line.strip())
    if not m:
        return None
    name = m.group(1).strip()
    if not any(kw in name.lower() for kw in _SCHEME_KEYWORDS):
        return None
    try:
        total = float(m.group(2).replace(",", ""))
    except ValueError:
        return None
    return name, total


def extract_pdf_wcd_demand(
    *, doc_id: str, path: Path, state: str,
    fiscal_year: str = "unknown",
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """
    Extract WCD scheme lines from a state budget PDF.
    Returns number of rows written (0 if file missing or no WCD section found).
    """
    if not path.exists():
        return 0

    written = 0
    try:
        with pdfplumber.open(str(path)) as pdf:
            wcd_pages = _find_wcd_pages(pdf)
            if not wcd_pages:
                return 0
            for page_idx in wcd_pages:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row or not row[0]:
                                continue
                            name = str(row[0]).strip()
                            if not any(kw in name.lower() for kw in _SCHEME_KEYWORDS):
                                continue
                            vals = [
                                c for c in row[1:]
                                if c and str(c).strip() not in ("", "nan")
                            ]
                            if not vals:
                                continue
                            try:
                                total = float(str(vals[-1]).replace(",", ""))
                            except ValueError:
                                continue
                            canonical = get_canonical(name, db_path)
                            if canonical is None:
                                continue
                            upsert_scheme_allocation(
                                doc_id=doc_id, level="state", state=state,
                                fiscal_year=fiscal_year, demand_no=None,
                                scheme_name=name, scheme_canonical=canonical,
                                col_type="be", revenue_cr=None, capital_cr=None,
                                total_cr=total, db_path=db_path,
                            )
                            written += 1
                else:
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        result = _parse_scheme_line(line)
                        if result is None:
                            continue
                        name, total = result
                        canonical = get_canonical(name, db_path)
                        if canonical is None:
                            continue
                        upsert_scheme_allocation(
                            doc_id=doc_id, level="state", state=state,
                            fiscal_year=fiscal_year, demand_no=None,
                            scheme_name=name, scheme_canonical=canonical,
                            col_type="be", revenue_cr=None, capital_cr=None,
                            total_cr=total, db_path=db_path,
                        )
                        written += 1
    except Exception as exc:
        print(f"  PDF extraction error ({path.name}): {exc}")
        return written

    return written


def run(level=None, state=None, db_path=DEFAULT_DB_PATH):
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        query = (
            "SELECT b.id, b.local_path, b.file_extension, b.state, b.fiscal_year, "
            "d.parser_route "
            "FROM budget_docs b "
            "LEFT JOIN doc_extraction_probe d ON b.id = d.doc_id"
        )
        params = []
        if level == "central":
            query += " WHERE b.state = 'central'"
        elif state:
            query += " WHERE b.state = ?"
            params.append(state)
        doc_rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    for doc_id, local_path, file_ext, doc_state, fiscal_year, parser_route in doc_rows:
        if not local_path:
            print(f"[skip] {doc_id}: no local_path")
            continue
        path = Path(local_path)
        if not path.exists():
            print(f"[skip] {doc_id}: file not found at {local_path}")
            continue
        if file_ext in ("xls", "xlsx"):
            demand_no = _demand_from_path(path)
            count = extract_xls_doc(
                doc_id=doc_id,
                path=path,
                budget_year=fiscal_year,
                demand_no=demand_no,
                db_path=db_path,
            )
            print(f"[extracted] {doc_id}: {count} rows written")
        else:
            if parser_route in ("text_pdf", "table_pdf", "scanned_pdf"):
                count = extract_pdf_wcd_demand(
                    doc_id=doc_id,
                    path=path,
                    state=doc_state or "unknown",
                    fiscal_year=fiscal_year or "unknown",
                    db_path=db_path,
                )
                print(f"[extracted] {doc_id}: {count} rows written")
            else:
                route_info = parser_route or file_ext or "unknown"
                print(f"[skip] {doc_id}: route={route_info}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract scheme-level allocation rows from indexed budget documents."
    )
    parser.add_argument(
        "--level",
        choices=["central", "state"],
        help="Filter by government level",
    )
    parser.add_argument("--state", help="Filter by state name")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    args = parser.parse_args()
    run(level=args.level, state=args.state, db_path=Path(args.db))


if __name__ == "__main__":
    main()
