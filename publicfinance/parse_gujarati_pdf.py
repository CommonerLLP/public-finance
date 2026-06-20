import pdfplumber
import os

PDF_PATH = '../data/gujarat/2026-27/gujarat-budget-at-a-glance-2026-27.pdf'

def find_gujarati_summary():
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            
            # "Budget at a Glance" in Gujarati
            if "એક નજરે" in text or "મહેસૂલી" in text:
                print(f"--- Potential Table on Page {i+1} ---")
                print(text)
                # Try to extract table properly
                table = page.extract_table()
                if table:
                    print("\n[Table Extracted]")
                    for row in table[:10]:
                        print(row)
                return

if __name__ == "__main__":
    find_gujarati_summary()
