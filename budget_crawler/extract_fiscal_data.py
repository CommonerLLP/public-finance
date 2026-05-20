"""
Extract structured fiscal data from Rajasthan and Uttar Pradesh budget volumes.
Normalizes units to Crores and writes to the fiscal_indicators table.
Supports legacy font transliteration for Hindi documents.
"""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db
from llm_providers import krutidev_to_unicode

def normalize_to_crore(value_str, unit):
    """Converts a value string to a float in Crores."""
    if not value_str or value_str.strip() in ("", "..", "-", "NA"):
        return 0.0
    
    # Remove commas and clean numeric string
    clean_val = re.sub(r"[^\d\.-]", "", value_str.replace(",", ""))
    try:
        val = float(clean_val)
    except ValueError:
        return 0.0

    if "lakh" in unit.lower() or "लख" in unit:
        return val / 100.0
    if "thousand" in unit.lower() or "हजkj" in unit:
        return val / 10000.0
    return val

def upsert_fiscal_indicator(db_path, doc_id, indicator_name, value, unit, major_head=None):
    """Writes a single fiscal indicator to the database."""
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO fiscal_indicators (doc_id, indicator_name, major_head, value, unit)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, indicator_name, major_head, value, unit),
        )
        conn.commit()
    finally:
        conn.close()

def extract_from_pdf(pdf_path, state, year, db_path):
    print(f"Extracting from: {pdf_path.name}")
    
    # Generate doc_id from path/state/year if not provided
    doc_id = f"{state.lower()}_{year.replace('-', '_')}_{pdf_path.stem.lower()}"
    
    results = []
    
    # Use pdftotext -layout to preserve column alignment
    proc = subprocess.run(
        ["pdftotext", "-layout", "-f", "1", "-l", "50", str(pdf_path), "-"],
        capture_output=True, text=True, timeout=60
    )
    
    raw_text = proc.stdout
    # Transliterate for robust semantic matching
    clean_text = krutidev_to_unicode(raw_text)
    
    # Semantic extraction from prose (Multi-line safe)
    # Look for GSDP (जीएसडीपी) followed by a number and "लाख करोड़" (Lakh Crore)
    match_gsdp = re.search(r"(जीएसडीपी)\s+([\d\.-]+)\s+लाख\s+करोड़", clean_text, re.MULTILINE)
    if match_gsdp:
        indicator, val = match_gsdp.groups()
        # Handle decimal dash used in some legacy encodings
        clean_val = val.replace("-", ".")
        curr_val = float(clean_val) * 100000 # Convert Lakh Crore to Crore
        upsert_fiscal_indicator(db_path, doc_id, "GSDP (Hindi/Unicode)", curr_val, "Crore")
        print(f"  SAVED Transliterated: GSDP: {clean_val} Lakh Crore -> {curr_val} Cr")
        results.append("जीएसडीपी")

    lines = clean_text.splitlines()
    for line in lines:
        # Match lines with a label followed by 2-3 columns of numbers
        match = re.search(r"^(.*?)\s{2,}([\d,\.-]+)\s{2,}([\d,\.-]+)", line.strip())
        
        if match:
            indicator, v1, v2 = match.groups()
            if re.match(r"^\d+$", indicator.strip()):
                continue
                
            unit = "Crore" if "cr" in indicator.lower() or "करोड़" in indicator.lower() else "Lakh"
            
            curr_val = normalize_to_crore(v2, unit)
            
            upsert_fiscal_indicator(
                db_path=db_path,
                doc_id=doc_id,
                indicator_name=indicator.strip(),
                value=curr_val,
                unit="Crore", # We normalize everything to Crore
            )
            
            print(f"  SAVED: {indicator.strip()[:45]}: {curr_val} Cr")
            results.append(indicator.strip())

    return results

def main():
    parser = argparse.ArgumentParser(description="Extract fiscal tables from budget PDFs.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--state", default="Rajasthan")
    parser.add_argument("--year", default="2025-26")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    
    extract_from_pdf(Path(args.pdf), args.state, args.year, Path(args.db))

if __name__ == "__main__":
    main()
