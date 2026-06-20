import pdfplumber
import os

PDF_PATH = '../data/gujarat/2026-27/gujarat-budget-at-a-glance-2026-27.pdf'

def extract():
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            
            # Keywords for "Revenue Receipts" and "Interest" in Gujarati
            if "મહેસૂલી" in text and "વ્યાજ" in text:
                print(f"--- MATCH FOUND ON PAGE {i+1} ---")
                print(text)
                
                # Try to get the actual table data
                table = page.extract_table()
                if table:
                    print("\n[Table Data]")
                    for row in table:
                        print(row)
                return True
    return False

if __name__ == "__main__":
    extract()
