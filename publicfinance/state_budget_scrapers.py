"""
State budget scrapers adapted from CBGA's state_budgets scrapers.

The CBGA originals are source-specific downloaders. This module keeps that
shape, but adds Python 3 compatibility, dry-runs, metadata indexing, safer
paths, and configurable source URLs.
"""

import argparse
import os
import re
import sys
import urllib3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db, index_budget_doc, make_doc_id, safe_path_name
from scrapping_utils import ScrappingUtils


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FOLDER = PROJECT_ROOT / "data" / "state_budgets"
DB_PATH = DEFAULT_DB_PATH

ASSAM_BUDGET_2017_18_URL = "https://finance.assam.gov.in/documents/budget-2017-18"
TAMIL_NADU_DEMANDS_URL = "https://tnbudget.tn.gov.in/demands.html"
TAMIL_NADU_LEGACY_BASE_URL = "http://www.tnbudget.tn.gov.in/"
KERALA_BUDGET_URL = "https://budget.kerala.gov.in/portal/home"
UP_BUDGET_URL = "https://budget.up.nic.in/"
RAJASTHAN_BUDGET_URL = "https://finance.rajasthan.gov.in/website/StateBudgetAll.aspx"
MP_FINANCE_URL = "https://finance.mp.gov.in/"

ASSAM_2017_18_KNOWN_DOCS = [
    (
        "Budget Speech",
        "Budget Speech (English) 2017-18",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Budget%20Speech%20%28English%29%202017-18.pdf",
    ),
    (
        "Budget Speech",
        "Budget Speech (Assamese) 2017-18",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/BUDGET%20SPEECH%20%28ASSAMESE%29%202017-18.pdf",
    ),
    (
        "Budget Highlights",
        "Budget Highlights 2017-18 Infographic",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Budget%20Highlights%202017-18%20Infographic.pdf",
    ),
    (
        "Budget Highlights",
        "Budget Highlights 2017-18",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Budget%20Highlights%202017-18.pdf",
    ),
    (
        "Revenue Receipt Budget",
        "Revenue_Receipt-Final-2017-18",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Revenue_Receipt-Final-2017-18.pdf",
    ),
    (
        "PRI & ULB",
        "Statement of transfer to Local Bodies (Abstract)",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Statement%20of%20transfer%20to%20Local%20Bodies%20%28Abstract%29.pdf",
    ),
    (
        "PRI & ULB",
        "Detailed Statement to Local Bodies (Details)",
        "https://finance.assam.gov.in/sites/default/files/swf_utility_folder/departments/"
        "agriculture_com_oid_2/menu/document/Detailed%20Statement%20to%20Local%20Bodies%20%20%28Details%29.pdf",
    ),
]

TAMIL_NADU_2025_26_KNOWN_DOCS = [
    ("Budget at a Glance", "Budget at a Glance 2025-2026 English", "https://www.tnbudget.tn.gov.in/tnweb_files/CB%202025_2026_English.pdf"),
    ("Detailed Demand List 2025-2026", "01.STATE LEGISLATURE", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/d01.pdf"),
    ("Detailed Demand List 2025-2026", "02.GOVERNOR AND COUNCIL OF MINISTERS", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/d02.pdf"),
    ("Detailed Demand List 2025-2026", "03.ADMINISTRATION OF JUSTICE", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/d03.pdf"),
    ("Detailed Demand List 2025-2026", "04.ADI-DRAVIDAR AND TRIBAL WELFARE DEPARTMENT", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/d04.pdf"),
    ("Detailed Demand List 2025-2026", "05.AGRICULTURE AND FARMER'S WELFARE DEPARTMENT", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/d05.pdf"),
    ("Other Budget Publications", "Annual Financial Statement", "https://www.tnbudget.tn.gov.in/tnweb_files/demands/61%20Annual_Financial_statements.pdf"),
    ("Other Budget Publications", "An Introduction to Budget", "https://www.tnbudget.tn.gov.in/tnweb_files/Introduction%20to%20Budget_PDF%20format.pdf"),
]

KERALA_2025_26_KNOWN_DOCS = [
    ("Budget Documents", "Budget Speech", "https://www.budget.kerala.gov.in/keralabudgetdoc/2025_26/BudgetSpeech_Eng.pdf"),
    ("Budget Documents", "Budget in Brief", "https://www.budget.kerala.gov.in/keralabudgetdoc/2025_26/BudgetBrief.pdf"),
    ("Budget Documents", "Annual Financial Statement", "https://www.budget.kerala.gov.in/keralabudgetdoc/2025_26/AFS.pdf"),
    ("Budget Documents", "Summary Documents of plan", "https://www.budget.kerala.gov.in/keralabudgetdoc/2025_26/SummaryDocument.pdf"),
]

UP_SOURCE_PAGES = {
    "Budget Speech": "https://budget.up.nic.in/budgetspeech.html",
    "Annual Financial Statement": "https://budget.up.nic.in/khand2part1.html",
    "Memorandum On Grant Wise Demand": "https://budget.up.nic.in/khand2part2.html",
}


@dataclass
class StateBudgetDocument:
    state: str
    fiscal_year: str
    document_type: str
    source_url: str
    local_path: Path
    collection_url: str
    section: str | None = None

    @property
    def extension(self):
        suffix = self.local_path.suffix.lower().lstrip(".")
        return suffix or _extension_from_url(self.source_url)

    @property
    def doc_id(self):
        return make_doc_id(
            self.state,
            self.fiscal_year,
            self.section,
            self.document_type,
            self.extension,
        )


class StateBudgetScraper(ScrappingUtils):
    state = None

    def __init__(self, out_folder=OUT_FOLDER, db_path=DB_PATH):
        super().__init__(max_retries=1, request_timeout=12, file_timeout=12, verify_ssl=False)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.out_folder = Path(out_folder)
        self.db_path = Path(db_path)
        self.out_folder.mkdir(parents=True, exist_ok=True)
        ensure_db(self.db_path)

    def crawl(self, url, fiscal_year, dry_run=False, force=False, limit=None):
        documents = self.discover_documents(url=url, fiscal_year=fiscal_year)
        if limit is not None:
            documents = documents[:limit]

        return self._crawl_documents(documents, dry_run=dry_run, force=force)

    def crawl_known_sample(self, fiscal_year, dry_run=False, force=False, limit=None):
        documents = self.known_sample_documents(fiscal_year=fiscal_year)
        if limit is not None:
            documents = documents[:limit]
        return self._crawl_documents(documents, dry_run=dry_run, force=force)

    def known_sample_documents(self, fiscal_year):
        return []

    def _crawl_documents(self, documents, dry_run=False, force=False):
        saved = 0
        skipped = 0
        failed = 0

        for document in documents:
            if dry_run:
                print(
                    f"{document.state} | {document.fiscal_year} | "
                    f"{document.extension.upper()} | {document.section or '-'} | "
                    f"{document.document_type} | {document.source_url}"
                )
                continue

            if document.local_path.exists() and document.local_path.stat().st_size > 0 and not force:
                skipped += 1
                self._index(document)
                continue

            if self.fetch_and_save_file(document.source_url, str(document.local_path)):
                saved += 1
                self._index(document)
            else:
                failed += 1

        if dry_run:
            print(f"\nDiscovered {len(documents)} {self.state} documents.")
        else:
            print(
                f"{self.state} crawl complete. "
                f"Saved {saved}; skipped {skipped}; failed {failed}; discovered {len(documents)}."
            )
        return documents

    def _index(self, document):
        index_budget_doc(
            doc_id=document.doc_id,
            state=document.state,
            fiscal_year=document.fiscal_year,
            document_type=document.document_type,
            estimate_type=None,
            source_url=document.source_url,
            local_path=document.local_path,
            file_extension=document.extension,
            db_path=self.db_path,
        )

    def _local_path(self, fiscal_year, section, title, url):
        extension = _extension_from_url(url)
        name = safe_path_name(title)
        if extension and not name.lower().endswith(f".{extension}"):
            name = f"{name}.{extension}"
        parts = [self.out_folder, safe_path_name(self.state), fiscal_year]
        if section:
            parts.append(safe_path_name(section))
        return Path(*parts) / name


class AssamBudgetsScraper(StateBudgetScraper):
    """Downloader for Assam Finance document collection pages."""

    state = "Assam"
    LISTING_LINK_XPATHS = (
        "//h1[contains(normalize-space(), 'Budget')]/following::a[contains(@href, '/documents-detail/')][position() <= 40]",
        "//a[contains(@href, '/documents-detail/')]",
    )
    PDF_LINK_XPATH = "//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf')]"
    NEXT_LINK_XPATH = "//a[contains(., 'next') or contains(., 'last')]/@href"

    def discover_documents(self, url=ASSAM_BUDGET_2017_18_URL, fiscal_year="2017-18"):
        documents = []
        seen_detail_urls = set()

        for listing_url, dom in self._listing_pages(url):
            for link in self._detail_links(dom, listing_url):
                detail_url, section = link
                if detail_url in seen_detail_urls:
                    continue
                seen_detail_urls.add(detail_url)
                documents.extend(self._documents_from_detail(detail_url, fiscal_year, section))

        return documents

    def known_sample_documents(self, fiscal_year="2017-18"):
        return [
            StateBudgetDocument(
                state=self.state,
                fiscal_year=fiscal_year,
                document_type=title,
                source_url=source_url,
                local_path=self._local_path(fiscal_year, section, title, source_url),
                collection_url=ASSAM_BUDGET_2017_18_URL,
                section=section,
            )
            for section, title, source_url in ASSAM_2017_18_KNOWN_DOCS
        ]

    def _listing_pages(self, url):
        dom = self.get_page_dom(url)
        if dom is None:
            return
        yield url, dom
        for next_href in dom.xpath(self.NEXT_LINK_XPATH):
            next_url = urljoin(url, next_href)
            if next_url != url:
                next_dom = self.get_page_dom(next_url)
                if next_dom is not None:
                    yield next_url, next_dom

    def _detail_links(self, dom, listing_url):
        links = []
        for xpath in self.LISTING_LINK_XPATHS:
            links = dom.xpath(xpath)
            if links:
                break

        for element in links:
            hrefs = element.xpath("./@href")
            if not hrefs:
                continue
            title = self.get_text_from_element(element)
            if not title:
                continue
            yield urljoin(listing_url, hrefs[0]), title

    def _documents_from_detail(self, detail_url, fiscal_year, section):
        dom = self.get_page_dom(detail_url)
        if dom is None:
            return []

        documents = []
        for element in dom.xpath(self.PDF_LINK_XPATH):
            hrefs = element.xpath("./@href")
            if not hrefs:
                continue
            title = self.get_text_from_element(element) or section
            pdf_url = urljoin(detail_url, hrefs[0])
            documents.append(
                StateBudgetDocument(
                    state=self.state,
                    fiscal_year=fiscal_year,
                    document_type=title,
                    source_url=pdf_url,
                    local_path=self._local_path(fiscal_year, section, title, pdf_url),
                    collection_url=detail_url,
                    section=section,
                )
            )
        return documents


class TamilNaduBudgetsScraper(StateBudgetScraper):
    """Downloader for Tamil Nadu budget demand/publication pages."""

    state = "Tamil_Nadu"
    DOCUMENT_LINK_XPATH = (
        "//a[contains(translate(@href, 'PDFXLS', 'pdfxls'), '.pdf') "
        "or contains(translate(@href, 'PDFXLS', 'pdfxls'), '.xls')]"
    )

    def discover_documents(self, url=TAMIL_NADU_DEMANDS_URL, fiscal_year="2025-26"):
        dom = self.get_page_dom(url)
        if dom is None:
            return []

        documents = []
        for element in dom.xpath(self.DOCUMENT_LINK_XPATH):
            hrefs = element.xpath("./@href")
            if not hrefs:
                continue
            source_url = urljoin(url, hrefs[0])
            title = self.get_text_from_element(element) or Path(urlparse(source_url).path).stem
            section = self._section_for_link(element)
            documents.append(
                StateBudgetDocument(
                    state=self.state,
                    fiscal_year=fiscal_year,
                    document_type=title,
                    source_url=source_url,
                    local_path=self._local_path(fiscal_year, section, title, source_url),
                    collection_url=url,
                    section=section,
                )
            )
        return documents

    def known_sample_documents(self, fiscal_year="2025-26"):
        return [
            StateBudgetDocument(
                state=self.state,
                fiscal_year=fiscal_year,
                document_type=title,
                source_url=source_url,
                local_path=self._local_path(fiscal_year, section, title, source_url),
                collection_url=TAMIL_NADU_DEMANDS_URL,
                section=section,
            )
            for section, title, source_url in TAMIL_NADU_2025_26_KNOWN_DOCS
        ]

    def discover_legacy_documents(self, url, fiscal_year):
        """Best-effort port of CBGA's older JS/menu-driven Tamil Nadu scraper."""
        documents = []
        documents.extend(self._legacy_demand_documents(url, fiscal_year))
        documents.extend(self._legacy_menu_documents(url, fiscal_year))
        return documents

    def _legacy_demand_documents(self, base_url, fiscal_year):
        demand_url = urljoin(base_url.rstrip("/") + "/", "demands/Demand_head.htm")
        dom = self.get_page_dom(demand_url)
        if dom is None:
            return []

        documents = []
        for element in dom.xpath("//td//a[@href]"):
            title = self.get_text_from_element(element)
            href = element.xpath("./@href")[0]
            source_url = urljoin(demand_url, href)
            if not title or ".pdf" not in source_url.lower():
                continue
            title = title.split(". ", 1)[-1].strip().title()
            documents.append(
                StateBudgetDocument(
                    state=self.state,
                    fiscal_year=fiscal_year,
                    document_type=title,
                    source_url=source_url,
                    local_path=self._local_path(fiscal_year, "Demands for Grant", title, source_url),
                    collection_url=demand_url,
                    section="Demands for Grant",
                )
            )
        return documents

    def _legacy_menu_documents(self, base_url, fiscal_year):
        menu_url = urljoin(base_url.rstrip("/") + "/", "spi_files/spi_array.js")
        page_text = self.fetch_page(menu_url)
        if not page_text:
            return []

        menu_list = re.compile(r"menu\d+=").split(page_text)[1:]
        menu_headers = []
        documents = []
        for menu_index, menu_str in enumerate(menu_list):
            file_rows = menu_str.split("]")[0].splitlines()[2:]
            if menu_index == 0:
                for file_str in file_rows:
                    parts = _csvish_js_parts(file_str)
                    if len(parts) > 2 and "&nbsp;" in parts[0]:
                        menu_headers.append(parts[0].split("&nbsp;")[0])
                continue

            section = menu_headers[menu_index - 1] if menu_index - 1 < len(menu_headers) else "Budget Publications"
            for file_str in file_rows:
                parts = _csvish_js_parts(file_str)
                if len(parts) < 2:
                    continue
                title = parts[0].strip()
                source_url = urljoin(base_url, parts[1].strip())
                if not title or ".pdf" not in source_url.lower():
                    continue
                documents.append(
                    StateBudgetDocument(
                        state=self.state,
                        fiscal_year=fiscal_year,
                        document_type=title,
                        source_url=source_url,
                        local_path=self._local_path(fiscal_year, section, title, source_url),
                        collection_url=menu_url,
                        section=section,
                    )
                )
        return documents

    def crawl_legacy(self, url=TAMIL_NADU_LEGACY_BASE_URL, fiscal_year="2017-18", dry_run=False, force=False, limit=None):
        documents = self.discover_legacy_documents(url=url, fiscal_year=fiscal_year)
        if limit is not None:
            documents = documents[:limit]
        return self._crawl_documents(documents, dry_run=dry_run, force=force)

    def _crawl_documents(self, documents, dry_run=False, force=False):
        saved = skipped = failed = 0
        for document in documents:
            if dry_run:
                print(
                    f"{document.state} | {document.fiscal_year} | "
                    f"{document.extension.upper()} | {document.section or '-'} | "
                    f"{document.document_type} | {document.source_url}"
                )
                continue
            if document.local_path.exists() and document.local_path.stat().st_size > 0 and not force:
                skipped += 1
                self._index(document)
                continue
            if self.fetch_and_save_file(document.source_url, str(document.local_path)):
                saved += 1
                self._index(document)
            else:
                failed += 1
        if dry_run:
            print(f"\nDiscovered {len(documents)} {self.state} documents.")
        else:
            print(
                f"{self.state} crawl complete. "
                f"Saved {saved}; skipped {skipped}; failed {failed}; discovered {len(documents)}."
            )
        return documents

    def _section_for_link(self, element):
        headings = element.xpath("preceding::*[self::h1 or self::h2 or self::h3 or self::h4][1]//text()")
        if headings:
            return re.sub(r"\s+", " ", " ".join(headings)).strip()
        return "Budget Publications"


class KeralaBudgetsScraper(StateBudgetScraper):
    state = "Kerala"

    def discover_documents(self, url=KERALA_BUDGET_URL, fiscal_year="2025-26"):
        dom = self.get_page_dom(url)
        if dom is None:
            return []
        documents = []
        for element in dom.xpath("//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf')]"):
            document = self._document_from_link(element, url, fiscal_year)
            if document is not None:
                documents.append(document)
        return documents

    def known_sample_documents(self, fiscal_year="2025-26"):
        return [
            StateBudgetDocument(
                state=self.state,
                fiscal_year=fiscal_year,
                document_type=title,
                source_url=source_url,
                local_path=self._local_path(fiscal_year, section, title, source_url),
                collection_url=KERALA_BUDGET_URL,
                section=section,
            )
            for section, title, source_url in KERALA_2025_26_KNOWN_DOCS
        ]

    def _document_from_link(self, element, collection_url, fiscal_year):
        hrefs = element.xpath("./@href")
        if not hrefs:
            return None
        title = self.get_text_from_element(element) or Path(urlparse(hrefs[0]).path).stem
        source_url = urljoin(collection_url, hrefs[0])
        section = "Budget Documents"
        return StateBudgetDocument(
            state=self.state,
            fiscal_year=fiscal_year,
            document_type=title,
            source_url=source_url,
            local_path=self._local_path(fiscal_year, section, title, source_url),
            collection_url=collection_url,
            section=section,
        )


class UttarPradeshBudgetsScraper(StateBudgetScraper):
    state = "Uttar_Pradesh"

    def discover_documents(self, url=UP_BUDGET_URL, fiscal_year="2026-27"):
        documents = []
        year_variants = _fiscal_year_variants(fiscal_year)
        for section, page_url in UP_SOURCE_PAGES.items():
            dom = self.get_page_dom(page_url)
            if dom is None:
                continue
            for element in dom.xpath("//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf')]"):
                title = self.get_text_from_element(element).lstrip("!").strip()
                href = element.xpath("./@href")[0]
                haystack = f"{href} {title}"
                if not any(variant in haystack for variant in year_variants):
                    continue
                source_url = urljoin(page_url, href)
                documents.append(
                    StateBudgetDocument(
                        state=self.state,
                        fiscal_year=fiscal_year,
                        document_type=title or section,
                        source_url=source_url,
                        local_path=self._local_path(fiscal_year, section, title or section, source_url),
                        collection_url=page_url,
                        section=section,
                    )
                )
        return documents


class RajasthanBudgetsScraper(StateBudgetScraper):
    state = "Rajasthan"

    def discover_documents(self, url=RAJASTHAN_BUDGET_URL, fiscal_year="2025-26"):
        dom = self.get_page_dom(url)
        if dom is None:
            return []

        year_variants = _fiscal_year_variants(fiscal_year)
        documents = []
        for element in dom.xpath("//a[contains(@href, '/docs/budget/statebudget/') and contains(translate(@href, 'PDF', 'pdf'), '.pdf')]"):
            href = element.xpath("./@href")[0]
            title = self.get_text_from_element(element) or Path(urlparse(href).path).stem
            if not any(f"/{variant}/" in href for variant in year_variants):
                continue
            source_url = urljoin(url, href)
            documents.append(
                StateBudgetDocument(
                    state=self.state,
                    fiscal_year=fiscal_year,
                    document_type=title,
                    source_url=source_url,
                    local_path=self._local_path(fiscal_year, "State Budget", title, source_url),
                    collection_url=url,
                    section="State Budget",
                )
            )
        return documents


class MadhyaPradeshBudgetsScraper(StateBudgetScraper):
    state = "Madhya_Pradesh"

    def discover_documents(self, url=MP_FINANCE_URL, fiscal_year="2025-26"):
        # The official finance site timed out during scouting. Keep this class
        # as an explicit placeholder so MP is tracked without using unofficial
        # mirrors as source material.
        dom = self.get_page_dom(url)
        if dom is None:
            return []
        return []


def _extension_from_url(url):
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix or "pdf"


def _fiscal_year_variants(fiscal_year):
    variants = {fiscal_year, fiscal_year.replace("-", "_")}
    match = re.fullmatch(r"(20\d{2})-(\d{2})", fiscal_year)
    if match:
        start, end = match.groups()
        long_year = f"{start}-20{end}"
        variants.update({long_year, long_year.replace("-", "_")})
    return variants


def _csvish_js_parts(value):
    return [
        part.strip().strip('"').strip("'")
        for part in value.strip().rstrip(",").split(",")
        if part.strip()
    ]


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl state budget documents adapted from CBGA scrapers.")
    parser.add_argument(
        "state",
        choices=["assam", "tamil-nadu", "kerala", "uttar-pradesh", "rajasthan", "madhya-pradesh"],
        help="State scraper to run.",
    )
    parser.add_argument("--url", help="Collection URL to crawl.")
    parser.add_argument("--fiscal-year", required=True, help="Fiscal year label, e.g. 2017-18 or 2025-26.")
    parser.add_argument("--out-dir", default=str(OUT_FOLDER), help="Output directory for downloaded files.")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite metadata database path.")
    parser.add_argument("--dry-run", action="store_true", help="List discovered documents without downloading.")
    parser.add_argument("--force", action="store_true", help="Re-download files that already exist.")
    parser.add_argument("--limit", type=int, help="Limit documents downloaded/listed for reproduction tests.")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use the legacy Tamil Nadu CBGA menu/demand scraper path.",
    )
    parser.add_argument(
        "--known-sample",
        action="store_true",
        help="Use a small documented source sample when the live government listing is unreachable.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper_classes = {
        "assam": AssamBudgetsScraper,
        "tamil-nadu": TamilNaduBudgetsScraper,
        "kerala": KeralaBudgetsScraper,
        "uttar-pradesh": UttarPradeshBudgetsScraper,
        "rajasthan": RajasthanBudgetsScraper,
        "madhya-pradesh": MadhyaPradeshBudgetsScraper,
    }
    scraper = scraper_classes[args.state](out_folder=args.out_dir, db_path=args.db)

    if args.known_sample:
        scraper.crawl_known_sample(
            fiscal_year=args.fiscal_year,
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
        )
    elif args.state == "assam":
        if args.known_sample:
            scraper.crawl_known_sample(
                fiscal_year=args.fiscal_year,
                dry_run=args.dry_run,
                force=args.force,
                limit=args.limit,
            )
        else:
            scraper.crawl(
                url=args.url or ASSAM_BUDGET_2017_18_URL,
                fiscal_year=args.fiscal_year,
                dry_run=args.dry_run,
                force=args.force,
                limit=args.limit,
            )
    elif args.state == "tamil-nadu":
        if args.legacy:
            scraper.crawl_legacy(
                url=args.url or TAMIL_NADU_LEGACY_BASE_URL,
                fiscal_year=args.fiscal_year,
                dry_run=args.dry_run,
                force=args.force,
                limit=args.limit,
            )
        else:
            scraper.crawl(
                url=args.url or TAMIL_NADU_DEMANDS_URL,
                fiscal_year=args.fiscal_year,
                dry_run=args.dry_run,
                force=args.force,
                limit=args.limit,
            )
    else:
        default_urls = {
            "kerala": KERALA_BUDGET_URL,
            "uttar-pradesh": UP_BUDGET_URL,
            "rajasthan": RAJASTHAN_BUDGET_URL,
            "madhya-pradesh": MP_FINANCE_URL,
        }
        scraper.crawl(
            url=args.url or default_urls[args.state],
            fiscal_year=args.fiscal_year,
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
        )
