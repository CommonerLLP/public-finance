import requests
import os
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class RBIFetcher:
    BASE_URL = "https://www.rbi.org.in/scripts/AnnualPublications.aspx?head=State+Finances+%3a+A+Study+of+Budgets"
    
    def __init__(self, db_path="db/budget_metadata.db", data_dir="data/rbi"):
        self.db_path = db_path
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def fetch_report_page(self, url):
        """Fetches the landing page of a specific year's report."""
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None

    def get_statement_links(self, html):
        """Extracts links to statistical statements (which usually contain the Excel files)."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            if 'Statement' in a.text or 'Appendix Table' in a.text:
                links.append({
                    'title': a.text.strip(),
                    'url': urljoin(self.BASE_URL, a['href'])
                })
        return links

    def download_excel_from_statement(self, statement_url, title):
        """
        Navigates to the statement page and looks for the actual Excel download link.
        Note: RBI often uses javascript:__doPostBack, but direct .xls links sometimes exist 
        in the raw HTML or can be constructed.
        """
        # For now, we log the discovery. Actual downloading of RBI's JS-heavy Excel 
        # links might require a session-based approach or known URL pattern matching.
        print(f"Discovering data at: {title} -> {statement_url}")
        
        # Pattern discovery: Most RBI Excel files follow a predictable rbidocs.rbi.org.in path
        # If we can't find it directly, we'll use a browser-based fetcher for this module.
        pass

    def run(self):
        print("Starting RBI State Finances Fetcher...")
        html = self.fetch_report_page(self.BASE_URL)
        if not html:
            print("Failed to fetch RBI main page.")
            return

        statements = self.get_statement_links(html)
        print(f"Found {len(statements)} data statements.")
        
        # In a real run, we would loop and download. 
        # For this demo, we'll show the top 5 targets.
        for stmt in statements[:10]:
            print(f" - {stmt['title']}")

if __name__ == "__main__":
    fetcher = RBIFetcher()
    fetcher.run()
