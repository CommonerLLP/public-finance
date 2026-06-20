import pdfplumber
import os
import pandas as pd
import re

PDF_PATH = '../data/gujarat/2026-27/gujarat-budget-at-a-glance-2026-27.pdf'

def extract_budget_summary(pdf_path):
    print(f"Analyzing {pdf_path}...")
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages[:10]: # Check first 10 pages for summary table
            text = page.extract_text()
            all_text += text + "\n"
            
            # Look for tables on the page
            tables = page.extract_tables()
            for table in tables:
                # Convert to df for easier searching
                df = pd.DataFrame(table)
                # Check if "Revenue Receipts" or "Interest Payments" is in any cell
                table_str = df.to_string().lower()
                if "revenue receipts" in table_str or "interest" in table_str:
                    print(f"Found potential budget summary table on page {page.page_number}")
                    # Clean and print the table
                    print(df.to_string())
                    return df
    
    print("Could not find a summary table in the first 10 pages.")
    return None

if __name__ == "__main__":
    if os.path.exists(PDF_PATH):
        extract_budget_summary(PDF_PATH)
    else:
        print(f"File not found: {PDF_PATH}")
