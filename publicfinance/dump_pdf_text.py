import pdfplumber

with pdfplumber.open('../data/gujarat/2026-27/gujarat-budget-at-a-glance-2026-27.pdf') as pdf:
    for i in range(min(5, len(pdf.pages))):
        print(f"--- PAGE {i} ---")
        print(pdf.pages[i].extract_text())
