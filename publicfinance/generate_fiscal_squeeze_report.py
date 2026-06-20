import argparse
import os
import pandas as pd
from pathlib import Path
import html
import subprocess
import sys

# --- Constants ---
def find_project_root():
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent: 
        if (current_path / '.git').exists():
            return current_path
        current_path = current_path.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()

# DATA_DIR points to the 2024 RBI dataset which is the most recent.
DATA_DIR = PROJECT_ROOT / 'data' / 'rbi' / '2024' / 'State_Finances_2024' / 'Statements: 2025-26'
RBI_STATEMENT_19_PATH = DATA_DIR / 'Statement 19: Total Outstanding Liabilities of State Governments.xls'
RBI_STATEMENT_20_PATH = DATA_DIR / 'Statement 20: Total Outstanding Liabilities - As per cent of GSDP.xls'

OUTPUT_DIR = PROJECT_ROOT / 'screen'
OUTPUT_HTML_FILENAME = 'fiscal-squeeze-national.html'

FC_SHRINKAGE_RATE = 0.783
UNION_GTR_TO_GDP_RATIO = 0.12
NOMINAL_DEVOLUTION_RATE = 0.41

def clean_val(v):
    try:
        if pd.isna(v) or str(v).strip() in ['-', '']:
            return 0.0
        return float(str(v).replace(',', ''))
    except (ValueError, TypeError):
        return 0.0

def calculate_squeeze(state_gsdp: float) -> dict:
    if state_gsdp <= 0: return {"missing_share_cr": 0.0}
    union_gtr_estimate = state_gsdp * UNION_GTR_TO_GDP_RATIO
    ideal_share = union_gtr_estimate * NOMINAL_DEVOLUTION_RATE
    actual_share = ideal_share * FC_SHRINKAGE_RATE
    missing_share = ideal_share - actual_share
    return {"missing_share_cr": missing_share}

def generate_national_report():
    if not RBI_STATEMENT_19_PATH.exists() or not RBI_STATEMENT_20_PATH.exists():
        print(f"ERROR: RBI data files not found.")
        print(f"- Checked for: {RBI_STATEMENT_19_PATH}")
        print(f"- Checked for: {RBI_STATEMENT_20_PATH}")
        return

    try:
        # header=None ensures we keep control of column indexing
        df_abs = pd.read_excel(RBI_STATEMENT_19_PATH, header=None, skiprows=6)
        df_pct = pd.read_excel(RBI_STATEMENT_20_PATH, header=None, skiprows=6)
    except Exception as e:
        print(f"ERROR: Could not read Excel files: {e}")
        return

    # Prepare dataframes
    def extract_state_name(x):
        if isinstance(x, str) and '.' in x:
            return x.split('.', 1)[1].strip()
        return str(x).strip()

    df_abs['State'] = df_abs[1].apply(extract_state_name)
    df_pct['State'] = df_pct[1].apply(extract_state_name)
    
    # Column 20 is '2026 (BE)' in both files
    df_abs_be = df_abs[['State', 20]].rename(columns={20: 'Liabilities_Absolute_BE'})
    df_pct_be = df_pct[['State', 20]].rename(columns={20: 'Liabilities_Percent_BE'})

    merged_df = pd.merge(df_abs_be, df_pct_be, on='State').dropna()

    results = []
    for _, row in merged_df.iterrows():
        liabilities_abs = clean_val(row['Liabilities_Absolute_BE'])
        liabilities_pct = clean_val(row['Liabilities_Percent_BE'])

        if liabilities_abs > 0 and liabilities_pct > 0:
            gsdp = (liabilities_abs / (liabilities_pct / 100))
            squeeze_data = calculate_squeeze(gsdp)
            results.append({
                "State": row['State'],
                "Derived GSDP (Cr)": gsdp,
                "Structural Gap (Cr)": squeeze_data["missing_share_cr"]
            })

    if not results:
        print("No state data could be processed.")
        return

    leaderboard_df = pd.DataFrame(results)
    leaderboard_df = leaderboard_df.sort_values(by="Structural Gap (Cr)", ascending=False)

    # --- HTML Generation ---
    leaderboard_html_table = leaderboard_df.to_html(
        index=False,
        formatters={
            'Derived GSDP (Cr)': '{:,.0f}'.format,
            'Structural Gap (Cr)': '{:,.0f}'.format
        },
        classes='leaderboard'
    )

    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>National Fiscal Squeeze Audit</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eae8e3; color: #111; margin: 0; padding: 40px; line-height: 1.5; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-radius: 8px; }
        h1 { font-family: serif; border-bottom: 2px solid #c00; padding-bottom: 10px; margin-bottom: 30px; font-size: 2.5em; }
        h2 { font-family: serif; margin-top: 50px; border-left: 4px solid #c00; padding-left: 15px; }
        .grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 40px; margin-top: 30px; }
        .chart-container { background: #f9f9f7; padding: 20px; border-radius: 4px; border: 1px solid #ddd; }
        .bar-group { margin-bottom: 25px; }
        .bar-label { font-weight: bold; font-size: 0.9em; margin-bottom: 5px; display: flex; justify-content: space-between; }
        .bar-outer { background: #ddd; height: 30px; border-radius: 2px; position: relative; overflow: hidden; }
        .bar-inner { background: #004a99; height: 100%; display: flex; align-items: center; padding-left: 10px; color: white; font-size: 0.8em; font-weight: bold; }
        .bar-gap { background: #c00; height: 100%; position: absolute; top: 0; right: 0; display: flex; align-items: center; padding-right: 10px; color: white; font-size: 0.8em; font-weight: bold; justify-content: flex-end; }
        .stat-box { background: #fff4f4; border: 1px solid #ffcccc; padding: 20px; border-radius: 4px; margin-top: 20px; }
        .stat-val { font-size: 2em; font-weight: bold; color: #c00; }
        .stat-label { font-size: 0.9em; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
        table.leaderboard { width: 100%; border-collapse: collapse; margin-top: 30px; }
        table.leaderboard th, table.leaderboard td { padding: 12px; border-bottom: 1px solid #eee; text-align: right; }
        table.leaderboard th:first-child, table.leaderboard td:first-child { text-align: left; }
        table.leaderboard th { background: #f5f5f5; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>National Fiscal Squeeze Audit</h1>
        <p>An audit of the structural gap created by the erosion of the divisible pool.</p>
        <p>Source: RBI 'State Finances 2024' (Statements 19 & 20) | Analysis based on 16th FC Report (Para 7.35)</p>

        <h2>1. The National Macro Squeeze (The Shrinking Pie)</h2>
        <div class="grid">
            <div class="chart-container">
                <div class="bar-group">
                    <div class="bar-label"><span>FC-13 (2010-15)</span> <span>89.2% Shareable</span></div>
                    <div class="bar-outer"><div class="bar-inner" style="width: 89.2%;">Divisible Pool</div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>FC-14 (2015-20)</span> <span>82.1% Shareable</span></div>
                    <div class="bar-outer"><div class="bar-inner" style="width: 82.1%;">Divisible Pool</div></div>
                </div>
                <div class="bar-group" style="border: 2px dashed #c00; padding: 5px; margin: -7px;">
                    <div class="bar-label"><span>FC-15 (Current)</span> <span>78.3% Shareable</span></div>
                    <div class="bar-outer"><div class="bar-inner" style="width: 78.3%;">Divisible Pool</div></div>
                    <div class="bar-gap" style="width: 21.7%;">The Union's Withheld Portion</div>
                </div>
            </div>
            <div>
                <p>The Union's increasing reliance on Cesses and Surcharges has shrunken the resources states can draw from.</p>
                <div class="stat-box">
                    <div class="stat-label">Effective Devolution Rate (FC-15)</div>
                    <div class="stat-val">32.1%</div>
                    <p style="font-size: 0.85em; margin-top: 10px; color: #444;">Nominal 41% share applied to the shrunken divisible pool (78.3% of GTR).</p>
                </div>
            </div>
        </div>

        <h2>2. State-Level Structural Gap</h2>
        <p>States ranked by the absolute "Structural Gap" – estimated конституционно-mandated devolution withheld annually.</p>

        {{leaderboard_html}}

        <p style="margin-top: 40px; font-size: 0.8em; color: #888; border-top: 1px solid #eee; padding-top: 20px;">
            Methodology: Derived GSDP for 2025-26 (BE) from RBI Statements 19 & 20. Calculated 'Ideal Share' (41% of GTR, where GTR is 12% of GSDP) and 'Actual Share' (41% of shrunken divisible pool at 78.3% of GTR).
        </p>
    </div>
</body>
</html>
"""
    final_html = template.replace("{{leaderboard_html}}", leaderboard_html_table)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_file_path = OUTPUT_DIR / OUTPUT_HTML_FILENAME

    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Successfully generated HTML report: {html_file_path}")

    # Serving instructions
    print(f"\nTo view the visualization, run:")
    print(f"python3 -m http.server 8000 --directory {OUTPUT_DIR}")
    print(f"Then open: http://localhost:8000/{OUTPUT_HTML_FILENAME}")

def main():
    parser = argparse.ArgumentParser(description="Generate a 'Fiscal Squeeze' audit visualization.")
    parser.parse_args()
    generate_national_report()

if __name__ == "__main__":
    main()
