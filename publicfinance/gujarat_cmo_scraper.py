"""
CMO Gujarat ebook scraper - extracts direct PDF links from each ebook page
and downloads them. Uses the pattern discovered on the 2026-27 page.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, ensure_db, index_budget_doc, make_doc_id
from scrapping_utils import ScrappingUtils

# All budget-related ebook slugs found on cmogujarat.gov.in/en/ebooks
EBOOK_SLUGS = {
    "2026-27": [
        "gujarat-budget-2026-27",
        "gujarat-budget-at-a-glance-2026-27",
    ],
    "2025-26": [
        "gujarat-budget-2025-26-circular",
        "gujarat-budget-2025-2026-special-edition-circular",
        "gujarat-budget-growth-empowerment-mar-2025-ebook",
        "gujarat-april-2025-budget-visit-lakhpati-didi-nfsu",
    ],
    "2024-25": [
        "gujarat-budget-2024-2025-circular",
    ],
    "2023-24": [
        "gujarat-budget-2023-24-presented-by-shri-kanubhai-desai",
        "gujarat-budget-2023-24-progress-report-ebooks",
        "panchamrut-of-amritkaal-budget-gujarat-budget-2023-24",
        "gujarat-roadmap-2047-annual-budget-3-lakh-crores",
    ],
    "2022-23": [
        "gujarat-budget-2022-23-presented-by-shri-kanubhai-desai",
        "gujarat-budget-2022-23-state-landmark-budget",
        "historic-and-people-friendly-budget-2022-23-ebooks",
    ],
}

BASE_URL = "https://cmogujarat.gov.in/en/ebooks/"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'gujarat')
DB_PATH = DEFAULT_DB_PATH

# Pattern that matches direct PDF links on CMO Gujarat pages
PDF_XPATH = "//a[contains(@href, '.pdf')]/@href"


class CMOGujaratScraper(ScrappingUtils):

    def __init__(self):
        super().__init__()
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        ensure_db(DB_PATH)

    def _index(self, doc_id, year, slug, url, path):
        index_budget_doc(
            doc_id=make_doc_id("gujarat", year, doc_id),
            state='Gujarat',
            fiscal_year=year,
            document_type=slug,
            estimate_type='BE',
            source_url=url,
            local_path=path,
            file_extension='pdf',
            db_path=DB_PATH,
        )

    def scrape_ebook_page(self, slug, year):
        """Fetches the ebook landing page and extracts the direct PDF link."""
        page_url = BASE_URL + slug
        print(f"  Fetching: {page_url}")
        dom = self.get_page_dom(page_url)
        if dom is None:
            print(f"  ERROR: Could not load {page_url}")
            return None

        pdf_links = dom.xpath(PDF_XPATH)
        if not pdf_links:
            print(f"  No PDF links found on {page_url}")
            return None

        # Pick the first .pdf href that looks like a direct file (not a flip viewer)
        for link in pdf_links:
            if '/sites/default/files/' in link or link.endswith('.pdf'):
                # Make absolute if relative
                if link.startswith('/'):
                    link = 'https://cmogujarat.gov.in' + link
                return link

        return None

    def download_all(self):
        results = []
        for year, slugs in EBOOK_SLUGS.items():
            year_dir = os.path.join(DATA_DIR, year)
            os.makedirs(year_dir, exist_ok=True)
            print(f"\n=== Gujarat {year} ===")

            for slug in slugs:
                pdf_url = self.scrape_ebook_page(slug, year)
                if not pdf_url:
                    continue

                filename = slug + ".pdf"
                local_path = os.path.join(year_dir, filename)

                # Skip if already downloaded
                if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                    print(f"  Already exists: {filename}")
                    self._index(slug, year, slug, pdf_url, local_path)
                    results.append((year, slug, 'skipped'))
                    continue

                success = self.fetch_and_save_file(pdf_url, local_path)
                if success:
                    size_kb = os.path.getsize(local_path) // 1024
                    print(f"  Downloaded ({size_kb}KB): {filename}")
                    self._index(slug, year, slug, pdf_url, local_path)
                    results.append((year, slug, 'downloaded'))
                else:
                    results.append((year, slug, 'failed'))

        print(f"\n=== Summary ===")
        for year, slug, status in results:
            print(f"  [{status.upper()}] {year}: {slug}")
        return results

    def reindex_existing(self):
        """Index already-downloaded CMO ebook PDFs using the known CMS URL pattern."""
        results = []
        for year, slugs in EBOOK_SLUGS.items():
            for slug in slugs:
                local_path = os.path.join(DATA_DIR, year, slug + ".pdf")
                if not os.path.exists(local_path):
                    continue
                source_url = self._known_source_url(slug, year)
                self._index(slug, year, slug, source_url, local_path)
                results.append((year, slug, local_path))
        return results

    def _known_source_url(self, slug, year):
        known_urls = {
            "gujarat-budget-2024-2025-circular": (
                "https://cmogujarat.gov.in/sites/default/files/2024-09/"
                "gujarat-budget-2024-25-presented-by-shri-kanubhai-desai.pdf"
            ),
        }
        if slug in known_urls:
            return known_urls[slug]

        upload_months = {
            "2022-23": "2024-09",
            "2023-24": "2024-09",
            "2024-25": "2024-09",
            "2025-26": "2025-02",
            "2026-27": "2026-02",
        }
        month = upload_months.get(year)
        if slug == "gujarat-budget-2025-2026-special-edition-circular":
            month = "2025-04"
        if slug in {
            "gujarat-budget-growth-empowerment-mar-2025-ebook",
            "gujarat-april-2025-budget-visit-lakhpati-didi-nfsu",
        }:
            month = "2025-07"
        return f"https://cmogujarat.gov.in/sites/default/files/{month}/{slug}.pdf"


if __name__ == "__main__":
    scraper = CMOGujaratScraper()
    scraper.download_all()
