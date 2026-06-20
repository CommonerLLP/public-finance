import pandas as pd
import os

# Paths
BASE_DIR = '../data/rbi/2024/State_Finances_2024'
REV_REC_FILE = os.path.join(BASE_DIR, 'Appendices I to IV: 2025-26 Appendix I: Revenue Receipts of States and Union Territories with Legislature', 'States: Chhattisgarh, Goa, Gujarat, Haryana.xls')
REV_EXP_FILE = os.path.join(BASE_DIR, 'Appendix II: Revenue Expenditure of States and Union Territories with Legislature', 'States: Chhattisgarh, Goa, Gujarat, Haryana.xls')

def clean_value(val):
    try:
        if pd.isna(val) or val == '-':
            return 0.0
        if isinstance(val, str):
            val = val.replace(',', '').replace(' ', '').strip()
        return float(val)
    except:
        return 0.0

def get_gujarat_data():
    # 1. Get Revenue Receipts
    df_rec = pd.read_excel(REV_REC_FILE, header=None)
    # Total Revenue Receipts row
    rec_row = None
    for idx, row in df_rec.iterrows():
        if 'Total Revenue Receipts' in str(row.values) and 'Gujarat' in str(df_rec.iloc[max(0, idx-50):idx+1].values):
            # This logic is a bit brittle, let's find the "Gujarat" section first
            pass
    
    # Simpler: find the row where Col 1 is 'Gujarat' or contains it
    # These files are structured with multiple states. We need to find the Gujarat block.
    
    # 2. Get Interest Payments from Revenue Expenditure file
    df_exp = pd.read_excel(REV_EXP_FILE, header=None)
    
    # Columns for 2024 publication:
    # Col 2: 2023-24 (Accounts) -> i.e. 2022-23 Actuals? No, 2023-24 Accounts is 2023-24 Actuals.
    # Usually: 2022-23 (Accounts), 2023-24 (BE), 2023-24 (RE), 2024-25 (BE)
    
    # Let's print the first 50 rows of both to see the structure
    print("--- Revenue Receipts (Gujarat Section) ---")
    # Find row with 'Gujarat'
    guj_idx = df_rec[df_rec.apply(lambda r: 'Gujarat' in str(r.values), axis=1)].index[0]
    print(df_rec.iloc[guj_idx:guj_idx+30, 0:6].to_string())
    
    print("\n--- Revenue Expenditure (Gujarat Section) ---")
    guj_idx_exp = df_exp[df_exp.apply(lambda r: 'Gujarat' in str(r.values), axis=1)].index[0]
    print(df_exp.iloc[guj_idx_exp:guj_idx_exp+30, 0:6].to_string())

if __name__ == "__main__":
    get_gujarat_data()
