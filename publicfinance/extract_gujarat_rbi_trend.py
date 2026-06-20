import pandas as pd
import os
import glob

# Paths
RBI_DIR = '../data/rbi/2024/State_Finances_2024/Statements: 2025-26'
STMT_13 = os.path.join(RBI_DIR, 'Statement 13: Interest Payments.xls')
STMT_33 = os.path.join(RBI_DIR, 'Statement 33: Revenue Receipts of State Governments and Uts.xls')

def clean_value(val):
    try:
        if pd.isna(val) or val == '-':
            return 0.0
        if isinstance(val, str):
            val = val.replace(',', '').strip()
        return float(val)
    except:
        return 0.0

def extract_state_data(file_path, state_name):
    print(f"Processing {os.path.basename(file_path)}...")
    # Read the excel, skipping header rows (usually first 3-5 rows in RBI files)
    df = pd.read_excel(file_path, header=None)
    
    # Find the row for the state
    state_row = None
    for idx, row in df.iterrows():
        # Check if the state name is in any column of the row
        row_str = " ".join([str(c) for c in row.values])
        if state_name.lower() in row_str.lower():
            state_row = row
            break
            
    if state_row is None:
        print(f"Could not find {state_name} in {file_path}")
        return None
    
    # Extract years (usually columns 2, 3, 4, 5 etc.)
    # In Statement 13 (2024 pub):
    # Col 2: 2022-23 (Actuals)
    # Col 3: 2023-24 (BE)
    # Col 4: 2023-24 (RE)
    # Col 5: 2024-25 (BE)
    
    # We'll return the raw values for now
    return state_row.values

def main():
    state = "Gujarat"
    interest_data = extract_state_data(STMT_13, state)
    revenue_data = extract_state_data(STMT_33, state)
    
    if interest_data is not None and revenue_data is not None:
        print(f"\n--- {state} Fiscal Trend (RBI 2024 Publication) ---")
        
        # Mapping for 2024 publication columns (approximate, needs manual check of header row)
        # 2: 2022-23 (Actuals)
        # 3: 2023-24 (BE)
        # 4: 2023-24 (RE)
        # 5: 2024-25 (BE)
        
        years = ["2022-23 (Actuals)", "2023-24 (BE)", "2023-24 (RE)", "2024-25 (BE)"]
        
        results = []
        for i, year in enumerate(years):
            int_val = clean_value(interest_data[i+2])
            rev_val = clean_value(revenue_data[i+2])
            ratio = (int_val / rev_val * 100) if rev_val > 0 else 0
            results.append({
                "Year": year,
                "Interest Payments (Cr)": int_val,
                "Revenue Receipts (Cr)": rev_val,
                "Ratio (%)": round(ratio, 2)
            })
            
        print(pd.DataFrame(results).to_string(index=False))

if __name__ == "__main__":
    main()
