import pdfplumber
import os
import re
import pandas as pd

PDF_PATH = '../data/rbi/2024/State_Finances_2024/Statements: 2025-26/Statement 1: Major Fiscal Indicators.pdf'

def clean_val(v):
    if not v: return 0.0
    v = v.replace(',', '').replace(' ', '').replace('–', '0').replace('-', '0').strip()
    try:
        return float(v)
    except:
        return 0.0

def generate_leaderboard():
    if not os.path.exists(PDF_PATH):
        print(f"File not found: {PDF_PATH}")
        return
    
    data = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                # Improved regex: optional space after dot, handles "&", spaces, etc.
                match = re.search(r'^(\d+)\.\s*([A-Za-z\s&]+?)\s+([\d\.\-\s]+)$', line)
                if match:
                    state_name = match.group(2).strip()
                    nums_str = match.group(3)
                    
                    # Extract all numbers
                    nums = re.findall(r'-?\d+\.\d+|-', nums_str)
                    
                    if len(nums) >= 3:
                        # Ratios are in the last 3 columns for 23-24, 24-25, 25-26
                        r3 = clean_val(nums[-1])
                        r2 = clean_val(nums[-2])
                        r1 = clean_val(nums[-3])
                        
                        data.append({
                            "State": state_name,
                            "Int/RevExp 23-24": r1,
                            "Int/RevExp 24-25": r2,
                            "Int/RevExp 25-26": r3
                        })

    if not data:
        print("Still couldn't find state data. Check regex.")
        return

    leaderboard = pd.DataFrame(data).drop_duplicates(subset=['State'])
    leaderboard = leaderboard.sort_values(by="Int/RevExp 25-26", ascending=False)
    
    print("\n=== Indian States Fiscal Stress Leaderboard (RBI 2024-25) ===")
    print("Metric: Interest Payment as % of Revenue Expenditure")
    print("-" * 80)
    print(leaderboard.to_string(index=False))

if __name__ == "__main__":
    generate_leaderboard()
