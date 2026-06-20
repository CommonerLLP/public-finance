import requests
import os
import sqlite3
import pandas as pd
from datetime import datetime

class RBIBulkDownloader:
    """
    Downloads and indexes standardized state finance data from the RBI.
    Focuses on the time-series Excel data which is easier to parse than individual state PDFs.
    """
    
    # These are known IDs for critical fiscal statements in the RBI DBIE / Publications portal
    # We will expand this manifest as we discover more IDs.
    MANIFEST = {
        "23710": "Major_Fiscal_Indicators",
        "23711": "Revenue_Deficit_Surplus",
        "23712": "Gross_Fiscal_Deficit",
        "23722": "Interest_Payments",
        "23742": "Revenue_Receipts",
        "23743": "Revenue_Expenditure",
        "23744": "Development_Expenditure_Select_Indicators"
    }

    def __init__(self, db_path="db/budget_metadata.db", data_dir="data/rbi"):
        self.db_path = db_path
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def download_statement(self, stmt_id, title):
        """
        Downloads a specific statement by ID.
        RBI Publications often allow direct access via this pattern.
        """
        # Note: In a production environment, we'd handle the session and potential JS redirects.
        # This URL pattern is a common shortcut for RBI statistical publications.
        url = f"https://rbidocs.rbi.org.in/rdocs/Publications/Xls/{stmt_id}.XLS"
        target_path = os.path.join(self.data_dir, f"{stmt_id}_{title}.xls")
        
        print(f"Downloading {title} (ID: {stmt_id})...")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                with open(target_path, 'wb') as f:
                    f.write(response.content)
                self.index_file(stmt_id, title, target_path, url)
                return True
            else:
                print(f"  Failed to download {stmt_id}. Status: {response.status_code}")
        except Exception as e:
            print(f"  Error downloading {stmt_id}: {str(e)}")
        return False

    def index_file(self, stmt_id, title, path, url):
        """Adds the downloaded file to the metadata database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # We use 'All States' as the state for RBI consolidated reports
        cursor.execute('''
            INSERT OR REPLACE INTO budget_docs (
                id, state, fiscal_year, document_type, source_url, local_path, last_crawled
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            stmt_id, "All_States", "2019-2026", title, url, path, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

    def run(self):
        print("Starting RBI Bulk Download...")
        results = []
        for stmt_id, title in self.MANIFEST.items():
            success = self.download_statement(stmt_id, title)
            results.append(success)
        
        success_count = sum(results)
        print(f"Bulk download complete. {success_count}/{len(self.MANIFEST)} files downloaded.")

if __name__ == "__main__":
    downloader = RBIBulkDownloader()
    downloader.run()
