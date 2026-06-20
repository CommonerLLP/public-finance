import pandas as pd
import os

STMT_1 = '../data/rbi/2024/State_Finances_2024/Statements: 2025-26/Statement 1: Major Fiscal Indicators.xls'

def clean_val(v):
    try:
        if pd.isna(v) or str(v).strip() in ['-', '']: return 0.0
        return float(v)
    except:
        return 0.0

def generate_leaderboard():
    if not os.path.exists(STMT_1):
        print(f"File not found: {STMT_1}")
        return
    
    # Read the file
    df = pd.read_excel(STMT_1, header=None)
    
    # States usually start after row 6
    # Col 1: State Name
    # Col 11: 2023-24 (Accounts) - Interest / Rev Exp (%)
    # Col 12: 2024-25 (RE) - Interest / Rev Exp (%)
    # Col 13: 2025-26 (BE) - Interest / Rev Exp (%)
    
    data = []
    for idx, row in df.iterrows():
        state_name = str(row[1]).strip()
        # Filter for rows that look like states (e.g. "1. Andhra Pradesh")
        if any(char.isdigit() for char in state_name) and '.' in state_name:
            # Clean state name
            clean_name = state_name.split('.', 1)[1].strip()
            
            ratio_23_24 = clean_val(row[11])
            ratio_24_25 = clean_val(row[12])
            ratio_25_26 = clean_val(row[13])
            
            data.append({
                "State": clean_name,
                "Interest/RevExp 23-24 (Accounts)": ratio_23_24,
                "Interest/RevExp 24-25 (RE)": ratio_24_25,
                "Interest/RevExp 25-26 (BE)": ratio_25_26
            })
            
    # Create DataFrame
    leaderboard = pd.DataFrame(data)
    
    # Sort by the most recent estimate (2025-26 BE)
    leaderboard = leaderboard.sort_values(by="Interest/RevExp 25-26 (BE)", ascending=False)
    
    print("\n=== Indian States Fiscal Stress Leaderboard (RBI 2024-25 Publication) ===")
    print("Metric: Interest Payment as % of Revenue Expenditure")
    print("-" * 80)
    print(leaderboard.to_string(index=False))
    
    # Identify high-stress states (> 15% is the usual caution line, > 20% is red)
    high_stress = leaderboard[leaderboard["Interest/RevExp 25-26 (BE)"] > 15.0]
    if not high_stress.empty:
        print("\n[!] WARNING: States with Interest/RevExp > 15% (High Stress):")
        for s in high_stress["State"].tolist():
            print(f"  - {s}")

if __name__ == "__main__":
    generate_leaderboard()
