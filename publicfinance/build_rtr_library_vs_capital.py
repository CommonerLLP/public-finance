"""Build the RTR library-vs-capital rows for REQ-0003.

Two deliverables:

1. ``rtr_library_vs_capital.csv`` -- the ORIGINAL RTR contract (state-budget
   Budget Estimate, revenue section, ₹ crore): library revenue (2205-00-105),
   the excluded MSME foil (2851), and the capital-industry comparator
   (2852 + 2853 + 2875). Rajasthan 2026-27 is derived here from the state's own
   detailed demand volumes on disk -- a fully local, primary-source extraction.

2. ``cag_library_four_head.csv`` -- the EXTENSION contract (CAG audited actuals,
   four account-code heads). The schema is written here; the actuals rows for
   UP / Gujarat / Kerala / AP are BLOCKED this cycle because ``cag.gov.in`` is
   unreachable from the current egress (geo-fenced; HTTP 000 connect timeout).
   The Rajasthan library heads it does carry are BUDGET BE, not CAG actuals, and
   are labelled as such -- provenance is never silently mixed.

Library heads (2205-00-105 revenue, 4202-04-105 capital) come from the committed
Surya-OCR observed JSON, because pdftotext garbles the Devanagari library label;
the industry major-head totals are code-anchored and read live from the PDF.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

from publicfinance.account_code_extract import extract_major_head_totals, to_crore
from publicfinance.metadata import DEFAULT_DB_PATH, ensure_db

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "references" / "lmmha" / "lod"
BUDGET = REPO / "data" / "state_budgets"

RAJ_FY = "2026-27"
ECON_VOL = BUDGET / "Rajasthan" / RAJ_FY / "State Budget" / "Volume 2d _ Revenue Expenditure-Economic Services.pdf"
OBSERVED_JSON = OUT_DIR / f"rajasthan_observed_{RAJ_FY}.json"

INDUSTRY_MAJORS = ["2851", "2852", "2853", "2875"]
CAPITAL_COMPARATOR = ["2852", "2853", "2875"]


def _thousand_to_crore(thousand_rupees: float) -> float:
    return round(to_crore(thousand_rupees, "thousand"), 4)


def build_rajasthan_row() -> dict:
    # industry major-head totals (BE, revenue), read live from the primary PDF
    majors = extract_major_head_totals(ECON_VOL, INDUSTRY_MAJORS, unit="thousand")

    # library heads from the committed Surya-OCR observed JSON
    observed = json.loads(OBSERVED_JSON.read_text(encoding="utf-8"))
    lib_rev_t = observed["targets"]["2205-00-105"]["selected_amount_thousand_rupees"]
    lib_cap_t = observed["targets"]["4202-04-105"]["selected_amount_thousand_rupees"]

    capital_cr = round(sum(majors[c].value_crore for c in CAPITAL_COMPARATOR), 2)
    row = {
        "state": "Rajasthan",
        "fy": RAJ_FY,
        "estimate_basis": "BE",
        "libraries_rev_cr": round(_thousand_to_crore(lib_rev_t), 2),   # 2205-00-105
        "libraries_cap_cr": round(_thousand_to_crore(lib_cap_t), 2),   # 4202-04-105
        "msme_cr": round(majors["2851"].value_crore, 2),              # 2851 (excluded foil)
        "capital_cr": capital_cr,                                      # 2852+2853+2875
        "h2852_cr": round(majors["2852"].value_crore, 2),
        "h2853_cr": round(majors["2853"].value_crore, 2),
        "h2875_cr": round(majors["2875"].value_crore, 4),
        "source_volumes": "Vol 2c (Social Services rev), Vol 2d (Economic Services rev), Vol 3a (Capital)",
        "source_pages": (
            f"2205-00-105: Vol2c pp{observed['targets']['2205-00-105']['window_pages']}; "
            f"2851 p{majors['2851'].printed_page}; 2852 p{majors['2852'].printed_page}; "
            f"2853 p{majors['2853'].printed_page}; 2875 p{majors['2875'].printed_page} (Vol2d printed pages)"
        ),
        "source_unit": "thousand_rupees",
        "retrieval_date": date.today().isoformat(),
        "notes": "Library heads via committed Surya OCR (label font-garbled in pdftotext); industry majors code-anchored live from PDF.",
    }
    return row, majors, lib_rev_t, lib_cap_t


def write_rtr_csv(row: dict) -> Path:
    out = OUT_DIR / "rtr_library_vs_capital.csv"
    fields = list(row.keys())
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow(row)
    return out


def write_cag_four_head_csv(row: dict, lib_rev_t: float, lib_cap_t: float) -> Path:
    """Write Rajasthan's BUDGET-BE library heads in the four-head shape (labelled).

    Writes to its own file: ``cag_library_four_head.csv`` is now the national
    CAG-actuals panel owned by ``build_cag_library_national.py`` — this builder
    must never overwrite it."""
    out = OUT_DIR / "rtr_library_four_head_rajasthan_be.csv"
    fields = [
        "state", "fy", "lib_receipts_cr", "lib_rev_exp_cr", "lib_cap_exp_cr",
        "lib_loans_cr", "recovery_ratio", "source_statement", "source_page",
        "source_url", "retrieval_date",
    ]
    lib_rev = round(_thousand_to_crore(lib_rev_t), 4)
    raj = {
        "state": "Rajasthan",
        "fy": RAJ_FY,
        "lib_receipts_cr": "",  # 0202-04-102 not extracted from budget (Vol 2a); needs CAG Stmt 14
        "lib_rev_exp_cr": lib_rev,                       # 2205-00-105 (BE)
        "lib_cap_exp_cr": round(_thousand_to_crore(lib_cap_t), 4),  # 4202-04-105 (BE)
        "lib_loans_cr": 0.0,                             # 6202 (expected nil)
        "recovery_ratio": "",                            # needs receipts
        "source_statement": "Rajasthan Budget BE (Vol 2c/3a) -- NOT CAG actuals",
        "source_page": row["source_pages"],
        "source_url": "local: data/state_budgets/Rajasthan/2026-27",
        "retrieval_date": date.today().isoformat(),
    }
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow(raj)
    return out


def write_fiscal_indicators(row: dict, majors: dict, lib_rev_t: float, lib_cap_t: float, db_path=DEFAULT_DB_PATH):
    ensure_db(db_path)
    doc_id = f"rajasthan_{RAJ_FY.replace('-', '_')}_rtr_library_vs_capital"
    entries = [
        ("Public Libraries revenue (BE)", "2205-00-105", round(_thousand_to_crore(lib_rev_t), 4)),
        ("Public Libraries capital (BE)", "4202-04-105", round(_thousand_to_crore(lib_cap_t), 4)),
        ("Village & Small Industries (BE)", "2851", round(majors["2851"].value_crore, 4)),
        ("Industries (BE)", "2852", round(majors["2852"].value_crore, 4)),
        ("Non-ferrous Mining & Metallurgical Industries (BE)", "2853", round(majors["2853"].value_crore, 4)),
        ("Industries - other (BE)", "2875", round(majors["2875"].value_crore, 4)),
    ]
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM fiscal_indicators WHERE doc_id = ?", (doc_id,))
        for name, head, val in entries:
            conn.execute(
                "INSERT INTO fiscal_indicators (doc_id, indicator_name, major_head, value, unit) "
                "VALUES (?, ?, ?, ?, ?)",
                (doc_id, name, head, val, "Crore"),
            )
        conn.commit()
    finally:
        conn.close()
    return doc_id


def main():
    row, majors, lib_rev_t, lib_cap_t = build_rajasthan_row()
    p1 = write_rtr_csv(row)
    p2 = write_cag_four_head_csv(row, lib_rev_t, lib_cap_t)
    doc_id = write_fiscal_indicators(row, majors, lib_rev_t, lib_cap_t)
    print("RTR row (Rajasthan", RAJ_FY, "BE):")
    for k, v in row.items():
        print(f"  {k}: {v}")
    print("\nwrote:", p1.relative_to(REPO))
    print("wrote:", p2.relative_to(REPO))
    print("fiscal_indicators doc_id:", doc_id)


if __name__ == "__main__":
    main()
