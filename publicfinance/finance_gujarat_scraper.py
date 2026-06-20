"""
Gujarat Finance Department budget scraper.

Source: financedepartment.gujarat.gov.in
Mechanism: ASP.NET WebForms postback — year dropdown triggers a server-side
round-trip that returns a table of PDF links. No REST API.

Coverage: 2002-03 through 2026-27 (24 fiscal years, ~1,500 PDFs on Budget
page alone). Four page types: Budget, Modified Budget, Budget in Brief,
Budget Speech.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db, index_budget_doc, make_doc_id, safe_path_name
from scrapping_utils import ScrappingUtils

BASE_URL = "https://financedepartment.gujarat.gov.in/"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "gujarat" / "finance_dept"

PAGES = {
    "budget": "Budget.html",
    "modified_budget": "modified-Budget.html",
    "budget_in_brief": "Budget-in-brief.html",
    "budget_speech": "Budget-speech.html",
}

# Dropdown value → fiscal year label.  The values are non-sequential;
# they must be hardcoded from the portal's <option> tags.
YEAR_MAP = {
    "2027": "2026-27", "2026": "2025-26", "1026": "2024-25",
    "24": "2023-24", "23": "2022-23", "22": "2021-22",
    "21": "2020-21", "20": "2019-20", "19": "2018-19",
    "18": "2017-18", "17": "2016-17", "16": "2015-16",
    "15": "2014-15", "1": "2013-14", "2": "2012-13",
    "3": "2011-12", "4": "2010-11", "5": "2009-10",
    "6": "2008-09", "7": "2007-08", "8": "2006-07",
    "10": "2004-05", "11": "2003-04", "12": "2002-03",
}

FISCAL_YEAR_TO_VAL = {v: k for k, v in YEAR_MAP.items()}

SLEEP_BETWEEN_YEARS = 2
SLEEP_BETWEEN_DOWNLOADS = 1


class FinanceGujaratScraper(ScrappingUtils):

    def __init__(self, db_path=DEFAULT_DB_PATH):
        super().__init__(request_timeout=20, file_timeout=120)
        self.db_path = db_path
        ensure_db(self.db_path)

    # ------------------------------------------------------------------
    # ASP.NET postback helpers
    # ------------------------------------------------------------------

    def _init_page(self, page_url):
        """GET the page to establish a session and extract ViewState."""
        r = self.session.get(page_url, timeout=self.request_timeout)
        r.raise_for_status()
        vs = re.search(r'__VIEWSTATE" value="(.*?)"', r.text)
        gen = re.search(r'__VIEWSTATEGENERATOR" value="(.*?)"', r.text)
        if not vs or not gen:
            raise RuntimeError(f"Could not extract ViewState from {page_url}")
        return vs.group(1), gen.group(1)

    def _postback_year(self, page_url, viewstate, generator, year_val):
        """POST the year dropdown selection and return the response HTML."""
        r = self.session.post(page_url, data={
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": generator,
            "__VIEWSTATEENCRYPTED": "",
            "__EVENTTARGET": "ctl08$ddlyear",
            "__EVENTARGUMENT": "",
            "ctl08$ddlyear": year_val,
        }, timeout=self.request_timeout)
        r.raise_for_status()
        new_vs = re.search(r'__VIEWSTATE" value="(.*?)"', r.text)
        new_gen = re.search(r'__VIEWSTATEGENERATOR" value="(.*?)"', r.text)
        vs = new_vs.group(1) if new_vs else viewstate
        gen = new_gen.group(1) if new_gen else generator
        return r.text, vs, gen

    # ------------------------------------------------------------------
    # Parse document table from postback response
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_document_table(html):
        """Extract (title, lang, relative_pdf_path) tuples from the response."""
        docs = []
        rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL)
        current_section = ""
        for row in rows:
            section_m = re.search(r"class='head-text1'[^>]*>(.*?)</th>", row)
            if section_m:
                current_section = re.sub(r"<[^>]+>", "", section_m.group(1)).strip()
                continue
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(tds) < 2:
                continue
            title = re.sub(r"<[^>]+>", "", tds[0]).strip()
            if not title:
                continue
            for i, lang in [(1, "en"), (2, "gu")]:
                if i >= len(tds):
                    continue
                href_m = re.search(r"href='([^']+\.pdf)'", tds[i])
                if href_m:
                    docs.append({
                        "title": title,
                        "section": current_section,
                        "lang": lang,
                        "pdf_path": href_m.group(1),
                    })
        return docs

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def scrape_page_type(self, page_key, years=None, dry_run=False):
        """Scrape one page type (budget / modified_budget / etc.) for given years."""
        page_file = PAGES[page_key]
        page_url = BASE_URL + page_file
        print(f"\n{'=' * 60}")
        print(f"Page: {page_key} ({page_url})")
        print(f"{'=' * 60}")

        viewstate, generator = self._init_page(page_url)

        if years is None:
            year_pairs = list(YEAR_MAP.items())
        else:
            year_pairs = []
            for fy in years:
                val = FISCAL_YEAR_TO_VAL.get(fy)
                if val is None:
                    print(f"  WARNING: unknown fiscal year {fy}, skipping")
                    continue
                year_pairs.append((val, fy))

        results = []
        for year_val, fiscal_year in year_pairs:
            print(f"\n--- {fiscal_year} ---")
            html, viewstate, generator = self._postback_year(
                page_url, viewstate, generator, year_val
            )
            docs = self._parse_document_table(html)
            print(f"  {len(docs)} documents found")

            year_dir = DATA_DIR / fiscal_year / page_key
            year_dir.mkdir(parents=True, exist_ok=True)

            for doc in docs:
                pdf_url = BASE_URL + doc["pdf_path"]
                filename = safe_path_name(f"{doc['title']}_{doc['lang']}") + ".pdf"
                local_path = year_dir / filename

                if local_path.exists() and local_path.stat().st_size > 1000:
                    print(f"  [SKIP] {filename}")
                    status = "skipped"
                elif dry_run:
                    print(f"  [DRY]  {filename}  ←  {pdf_url}")
                    status = "dry_run"
                else:
                    ok = self.fetch_and_save_file(pdf_url, str(local_path))
                    if ok:
                        size_kb = local_path.stat().st_size // 1024
                        print(f"  [OK]   {filename} ({size_kb} KB)")
                        status = "downloaded"
                    else:
                        print(f"  [FAIL] {filename}")
                        status = "failed"
                    time.sleep(SLEEP_BETWEEN_DOWNLOADS)

                doc_id = make_doc_id(
                    "gujarat", fiscal_year, page_key,
                    doc["title"], doc["lang"],
                )
                if status in ("downloaded", "skipped"):
                    index_budget_doc(
                        doc_id=doc_id,
                        state="Gujarat",
                        fiscal_year=fiscal_year,
                        document_type=f"{page_key}/{doc['section']}/{doc['title']}",
                        estimate_type="BE" if page_key == "budget" else page_key,
                        source_url=pdf_url,
                        local_path=str(local_path),
                        file_extension="pdf",
                        db_path=self.db_path,
                    )

                results.append({
                    "fiscal_year": fiscal_year,
                    "page": page_key,
                    "title": doc["title"],
                    "lang": doc["lang"],
                    "url": pdf_url,
                    "status": status,
                })

            time.sleep(SLEEP_BETWEEN_YEARS)

        return results

    def scrape_all(self, years=None, dry_run=False):
        """Scrape all four page types."""
        all_results = []
        for page_key in PAGES:
            all_results.extend(
                self.scrape_page_type(page_key, years=years, dry_run=dry_run)
            )
        return all_results

    def manifest(self, years=None):
        """Dry-run that prints a JSON manifest of all available documents."""
        page_url = BASE_URL + "Budget.html"
        viewstate, generator = self._init_page(page_url)

        inventory = {}
        year_pairs = list(YEAR_MAP.items()) if years is None else [
            (FISCAL_YEAR_TO_VAL[fy], fy) for fy in years if fy in FISCAL_YEAR_TO_VAL
        ]
        for year_val, fiscal_year in year_pairs:
            html, viewstate, generator = self._postback_year(
                page_url, viewstate, generator, year_val
            )
            docs = self._parse_document_table(html)
            inventory[fiscal_year] = {
                "total": len(docs),
                "en": len([d for d in docs if d["lang"] == "en"]),
                "gu": len([d for d in docs if d["lang"] == "gu"]),
            }
            time.sleep(0.5)
        return inventory


def _parse_years(arg):
    if not arg:
        return None
    return [y.strip() for y in arg.split(",")]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Gujarat Finance Department budget PDFs"
    )
    parser.add_argument(
        "--years", type=str, default=None,
        help="Comma-separated fiscal years, e.g. '2026-27,2025-26'. Default: all."
    )
    parser.add_argument(
        "--page", type=str, default=None, choices=list(PAGES.keys()),
        help="Scrape only this page type. Default: all four."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List documents without downloading."
    )
    parser.add_argument(
        "--manifest", action="store_true",
        help="Print year-by-year document counts as JSON (Budget page only)."
    )
    args = parser.parse_args()
    years = _parse_years(args.years)

    scraper = FinanceGujaratScraper()

    if args.manifest:
        inv = scraper.manifest(years=years)
        print(json.dumps(inv, indent=2))
        return

    if args.page:
        results = scraper.scrape_page_type(args.page, years=years, dry_run=args.dry_run)
    else:
        results = scraper.scrape_all(years=years, dry_run=args.dry_run)

    downloaded = sum(1 for r in results if r["status"] == "downloaded")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n{'=' * 60}")
    print(f"Done. {downloaded} downloaded, {skipped} skipped, {failed} failed.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
