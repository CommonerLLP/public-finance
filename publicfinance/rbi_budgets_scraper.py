"""
Crawler for RBI's "State Finances: A Study of Budgets" publication pages.

The RBI landing page points to the latest publication. Historical publications
can be crawled by passing their specific URL with --url.
"""

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db, index_budget_doc, make_doc_id, safe_path_name
from scrapping_utils import ScrappingUtils


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FOLDER = PROJECT_ROOT / "data" / "rbi"
DB_PATH = DEFAULT_DB_PATH

RBI_STATE_FINANCES_URL = (
    "https://www.rbi.org.in/scripts/AnnualPublications.aspx"
    "?head=State+Finances+%3a+A+Study+of+Budgets"
)

TABLE_ROWS_XPATH = "//table[@class='tablebg']/tr"
HEADER_XPATH = "./td[@class='tableheader']//text()"
TITLE_XPATH = "./td[@style]//text()"
XLS_LINK_XPATH = "./td[2]/a[@target]/@href"
PDF_LINK_XPATH = "./td[3]/a[@target]/@href"
PAGE_TITLE_XPATH = "//h2[@class='page_title']/text()"


@dataclass
class RBIDocument:
    title: str
    section: str
    fiscal_year: str
    extension: str
    url: str
    local_path: Path

    @property
    def doc_id(self):
        return make_doc_id("rbi", self.fiscal_year, self.section, self.title, self.extension)


class RBIBudgetScraper(ScrappingUtils):
    def __init__(self, out_folder=OUT_FOLDER, db_path=DB_PATH):
        super().__init__()
        self.out_folder = Path(out_folder)
        self.db_path = Path(db_path)
        self.out_folder.mkdir(parents=True, exist_ok=True)
        ensure_db(self.db_path)

    def discover_documents(self, url=RBI_STATE_FINANCES_URL, fiscal_year=None):
        page_dom = self.get_page_dom(url)
        if page_dom is None:
            logger.error("Could not load page: %s", url)
            return []

        page_title = self._page_title(page_dom)
        fiscal_year = fiscal_year or self._infer_fiscal_year(page_dom) or str(date.today().year)
        report_dir = self.out_folder / fiscal_year / safe_path_name(page_title)
        current_section = "Publication"
        documents = []

        for node in page_dom.xpath(TABLE_ROWS_XPATH):
            section = self.get_text_from_element(node, xpath=HEADER_XPATH)
            if section:
                current_section = section
                continue

            title = self.get_text_from_element(node, xpath=TITLE_XPATH)
            if not title:
                continue

            for extension, link_xpath in (("xls", XLS_LINK_XPATH), ("pdf", PDF_LINK_XPATH)):
                links = node.xpath(link_xpath)
                if not links:
                    continue
                doc_url = urljoin(url, links[0]).replace("http://", "https://")
                local_path = self._local_path(
                    report_dir=report_dir,
                    section=current_section,
                    title=title,
                    extension=self._extension_from_url(doc_url, extension),
                )
                documents.append(
                    RBIDocument(
                        title=title,
                        section=current_section,
                        fiscal_year=fiscal_year,
                        extension=local_path.suffix.lstrip("."),
                        url=doc_url,
                        local_path=local_path,
                    )
                )

        return documents

    def crawl(self, url=RBI_STATE_FINANCES_URL, fiscal_year=None, dry_run=False, force=False):
        documents = self.discover_documents(url=url, fiscal_year=fiscal_year)
        saved = 0
        skipped = 0

        for document in documents:
            if dry_run:
                print(f"{document.fiscal_year} | {document.extension.upper()} | {document.section} | {document.title}")
                continue

            if document.local_path.exists() and document.local_path.stat().st_size > 0 and not force:
                skipped += 1
                self._index_document(document)
                continue

            if self.fetch_and_save_file(document.url, str(document.local_path)):
                saved += 1
                self._index_document(document)

        if dry_run:
            print(f"\nDiscovered {len(documents)} RBI documents.")
        else:
            print(f"RBI crawl complete. Saved {saved}; skipped {skipped}; discovered {len(documents)}.")
        return documents

    def _index_document(self, document):
        index_budget_doc(
            doc_id=document.doc_id,
            state="All_States_RBI",
            fiscal_year=document.fiscal_year,
            document_type=document.title,
            estimate_type=None,
            source_url=document.url,
            local_path=document.local_path,
            file_extension=document.extension,
            db_path=self.db_path,
        )

    def _page_title(self, page_dom):
        title_nodes = page_dom.xpath(PAGE_TITLE_XPATH)
        return title_nodes[0].strip() if title_nodes else "State Finances"

    def _infer_fiscal_year(self, page_dom):
        page_text = " ".join(page_dom.xpath("//text()"))
        matches = re.findall(r"\b(20\d{2}-\d{2})\b", page_text)
        return matches[0] if matches else None

    def _local_path(self, *, report_dir, section, title, extension):
        return report_dir / safe_path_name(section) / f"{safe_path_name(title)}.{extension}"

    def _extension_from_url(self, url, fallback):
        suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
        return suffix or fallback


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl RBI State Finances budget documents.")
    parser.add_argument("--url", default=RBI_STATE_FINANCES_URL, help="RBI publication page URL to crawl.")
    parser.add_argument(
        "--fiscal-year",
        help="Override the fiscal year folder/index value. By default it is inferred from the page.",
    )
    parser.add_argument("--out-dir", default=str(OUT_FOLDER), help="Output directory for downloaded files.")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite metadata database path.")
    parser.add_argument("--dry-run", action="store_true", help="List discovered documents without downloading.")
    parser.add_argument("--force", action="store_true", help="Re-download files that already exist.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper = RBIBudgetScraper(out_folder=args.out_dir, db_path=args.db)
    scraper.crawl(
        url=args.url,
        fiscal_year=args.fiscal_year,
        dry_run=args.dry_run,
        force=args.force,
    )
