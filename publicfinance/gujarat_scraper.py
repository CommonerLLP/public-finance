import argparse
import os
import re
from obi_utils import OBIUtils
from lxml import etree

class GujaratBudgetsScraper(OBIUtils):
    """
    Scraper for Gujarat Budget Data, built on the OBI/CBGA scraper template.
    Replicates the folder-recursive logic from assam_budgets_scraper.py.
    """
    
    # Standard OBI-style XPaths for Liferay-based government portals
    DOC_LINKS_XPATH = '//a[contains(@class, "document-link") or contains(@href, ".pdf")]'
    
    def __init__(self, out_dir="data/gujarat"):
        super().__init__()
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def scrape_budget_year(self, url, year, rename=True):
        """
        Main entry point for a specific budget year.
        """
        print(f"Scraping Gujarat Budget for Year: {year}")
        year_dir = os.path.join(self.out_dir, year)
        self.get_files_from_url(url, year_dir, rename)

    def get_files_from_url(self, url, out_dir, rename):
        """
        Downloads budget files and saves in same folder hierarchy as web.
        Ported from OBI's AssamBudgetsScraper.
        """
        dom_tree = self.get_page_dom(url)
        if dom_tree is None:
            print(f"Could not load DOM for {url}")
            return

        links = dom_tree.xpath(self.DOC_LINKS_XPATH)
        print(f"Found {len(links)} possible links in {url}")

        for link in links:
            link_name = "".join(link.xpath(".//text()")).strip()
            href = link.xpath("@href")[0]
            
            # Identify if it's a direct PDF or a sub-folder
            if href.lower().endswith('.pdf'):
                file_path = os.path.join(out_dir, link_name if link_name.endswith('.pdf') else f"{link_name}.pdf")
                print(f"  Downloading: {link_name}")
                self.fetch_and_save_file(href, file_path)
            elif "folder" in href.lower() or "browse" in href.lower():
                # Recursive folder traversal
                sub_dir = os.path.join(out_dir, link_name)
                print(f"  Descending into folder: {link_name}")
                self.get_files_from_url(href, sub_dir, rename)

if __name__ == "__main__":
    # Example usage for 2026-27 (if we had the live URL)
    # We will pass known working URLs to this script.
    scraper = GujaratBudgetsScraper()
    # Testing with a known stable OBI link if government portal is down
    scraper.scrape_budget_year("https://openbudgetsindia.org/dataset/gujarat-budget-2024-25", "2024-25")
