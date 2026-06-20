"""
Probe each indexed PDF for extractability and tag a parser route.
Enhanced with 'Austerity' and 'Extravagance' markers based on Melinda Cooper's framework.
Supports multiple intelligence providers (Regex, Ollama).

Usage:
  python3 publicfinance/analyze_docs.py --state Rajasthan
  python3 publicfinance/analyze_docs.py --provider ollama --state Rajasthan
"""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pdfplumber

# Explicit .env loading for environment sovereignty
# We look for .env in the parent directory of this script (the project root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    with open(ENV_PATH, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, upsert_probe_result
from llm_providers import get_provider

def classify_route(
    *,
    file_extension: str | None,
    pdftotext_chars_p1: int | None,
    pdfplumber_tables_p1: int | None,
    has_devanagari: bool,
) -> str:
    if file_extension in ("xls", "xlsx", "csv"):
        return "xls"
    if pdftotext_chars_p1 is None:
        return "unknown"
    if has_devanagari:
        return "devanagari_pdf"
    if pdftotext_chars_p1 < 100:
        return "scanned_pdf"
    if pdfplumber_tables_p1 is not None and pdfplumber_tables_p1 >= 2:
        return "table_pdf"
    return "text_pdf"

def probe_pdf(path: Path, provider) -> dict:
    result = {
        "file_size_bytes": None,
        "page_count": None,
        "pdftotext_chars_p1": None,
        "pdftotext_sample": None,
        "pdfplumber_tables_p1": None,
        "has_devanagari": False,
        "parser_route": "unknown",
        "austerity_score": 0,
        "extravagance_score": 0,
        "error": None,
    }
    try:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        result["file_size_bytes"] = path.stat().st_size

        # page count via pdfinfo
        info = subprocess.run(
            ["pdfinfo", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        for line in info.stdout.splitlines():
            if line.startswith("Pages:"):
                result["page_count"] = int(line.split(":")[1].strip())
                break

        # first-page text via pdftotext (Probing 5 pages for better context)
        proc = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "5", str(path), "-"],
            capture_output=True, text=True, timeout=30,
        )
        text = proc.stdout
        result["pdftotext_chars_p1"] = len(text)
        result["pdftotext_sample"] = text[:500]
        result["has_devanagari"] = bool(re.search(r"[ऀ-ॿ]", text))
        
        # Counter-Revolution Audit via Provider (Regex or LLM)
        analysis = provider.analyze_signals(text)
        result["austerity_score"] = analysis.get("austerity_score", 0)
        result["extravagance_score"] = analysis.get("extravagance_score", 0)

        # table count on first page via pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            if pdf.pages:
                result["pdfplumber_tables_p1"] = len(pdf.pages[0].extract_tables())

        result["parser_route"] = classify_route(
            file_extension=path.suffix.lower().lstrip("."),
            pdftotext_chars_p1=result["pdftotext_chars_p1"],
            pdfplumber_tables_p1=result["pdfplumber_tables_p1"],
            has_devanagari=result["has_devanagari"],
        )
    except Exception as exc:
        result["error"] = str(exc)[:300]

    return result

def run(state: str | None, limit: int | None, db_path: Path, provider_type: str) -> None:
    provider = get_provider(provider_type)
    print(f"Using Intelligence Provider: {provider_type}")

    conn = sqlite3.connect(db_path)
    query = "SELECT id, local_path, file_extension, state FROM budget_docs WHERE local_path IS NOT NULL"
    params: list = []
    if state:
        query += " AND (state = ? OR state = ?)"
        params.extend([state, state.replace(" ", "_")])
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print(f"No documents found for state: {state}")
        return

    for doc_id, local_path, file_extension, state_name in rows:
        path = Path(local_path)
        if not path.exists():
            continue

        print(f"  probing: [{state_name}] {path.name} ...", end=" ", flush=True)

        if file_extension in ("xls", "xlsx", "csv"):
            result = {
                "file_size_bytes": path.stat().st_size,
                "page_count": None,
                "pdftotext_chars_p1": None,
                "pdftotext_sample": None,
                "pdfplumber_tables_p1": None,
                "has_devanagari": False,
                "parser_route": "xls",
                "austerity_score": 0,
                "extravagance_score": 0,
                "error": None,
            }
        else:
            result = probe_pdf(path, provider)

        upsert_probe_result(doc_id=doc_id, db_path=db_path, **result)
        scores = f"(A:{result['austerity_score']}, E:{result['extravagance_score']})"
        print(f"{result['parser_route']} {scores}")
        if result['error']:
            print(f"    ERROR: {result['error']}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Probe indexed PDFs for parser routing and Counter-Revolution audit.")
    parser.add_argument("--state", help="Filter by state (e.g. Rajasthan)")
    parser.add_argument("--limit", type=int, help="Max docs to probe")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    parser.add_argument(
        "--provider", 
        default="regex", 
        choices=["regex", "ollama", "openrouter"], 
        help="Intelligence provider"
    )
    args = parser.parse_args()
    run(state=args.state, limit=args.limit, db_path=Path(args.db), provider_type=args.provider)

if __name__ == "__main__":
    main()
