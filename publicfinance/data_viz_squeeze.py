import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json

def find_project_root():
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent: 
        if (current_path / '.git').exists():
            return current_path
        current_path = current_path.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / 'data' / 'rbi' / '2024' / 'State_Finances_2024' / 'Statements: 2025-26'
RBI_STATEMENT_17_PATH = DATA_DIR / 'Statement 17: Devolution and Transfer of Resources from the Centre.xls'
RBI_STATEMENT_19_PATH = DATA_DIR / 'Statement 19: Total Outstanding Liabilities of State Governments.xls'
RBI_STATEMENT_20_PATH = DATA_DIR / 'Statement 20: Total Outstanding Liabilities - As per cent of GSDP.xls'
OUTPUT_DIR = PROJECT_ROOT / 'screen'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# The 'Fiscal Squeeze' factor: 21.7% of the potential divisible pool is shrunken by cesses/surcharges.
# We estimate the 'Gap' as what the state *lost* relative to what it *got*.
SQUEEZE_FACTOR = 0.217 

def clean_val(v):
    try:
        if pd.isna(v) or str(v).strip() in ['-', '']:
            return 0.0
        return float(str(v).replace(',', ''))
    except (ValueError, TypeError):
        return 0.0

def run_viz():
    df_dev = pd.read_excel(RBI_STATEMENT_17_PATH, header=None, skiprows=6)
    df_abs = pd.read_excel(RBI_STATEMENT_19_PATH, header=None, skiprows=6)
    df_pct = pd.read_excel(RBI_STATEMENT_20_PATH, header=None, skiprows=6)

    # Load local body data
    local_body_path = PROJECT_ROOT / 'local_body_finances.json'
    local_body_map = {}
    if local_body_path.exists():
        with open(local_body_path, 'r') as f:
            local_body_map = json.load(f)

    def extract_state_name(x):
        if isinstance(x, str) and '.' in x:
            return x.split('.', 1)[1].strip()
        return str(x).strip()

    df_dev['State'] = df_dev[1].apply(extract_state_name)
    df_abs['State'] = df_abs[1].apply(extract_state_name)
    df_pct['State'] = df_pct[1].apply(extract_state_name)
    
    df_dev_be = df_dev[['State', 5]].rename(columns={5: 'Actual_Devolution_BE'})
    df_abs_be = df_abs[['State', 20]].rename(columns={20: 'Liabilities_Absolute_BE'})
    df_pct_be = df_pct[['State', 20]].rename(columns={20: 'Liabilities_Percent_BE'})

    merged_df = pd.merge(df_dev_be, df_abs_be, on='State')
    merged_df = pd.merge(merged_df, df_pct_be, on='State').dropna()

    results = []
    for _, row in merged_df.iterrows():
        state = row['State']
        devolution = clean_val(row['Actual_Devolution_BE'])
        liabilities_abs = clean_val(row['Liabilities_Absolute_BE'])
        liabilities_pct = clean_val(row['Liabilities_Percent_BE'])

        if liabilities_abs > 0 and liabilities_pct > 0:
            gsdp = (liabilities_abs / (liabilities_pct / 100))
            gap = devolution * (SQUEEZE_FACTOR / (1 - SQUEEZE_FACTOR))
            
            # Match state name for local body data (case-insensitive).
            # None means the state genuinely did not report under MH-3604 in RBI Appendix II.
            lb_grants = None
            for lb_state, lb_val in local_body_map.items():
                if lb_state.lower() == state.lower():
                    lb_grants = lb_val
                    break

            results.append({
                "State": state,
                "GSDP": gsdp,
                "Devolution": devolution,
                "Gap": gap,
                "SqueezeIntensity": (gap / gsdp) * 100,
                "LocalBodyGrants": lb_grants,
                "LocalBodyIntensity": (lb_grants / gsdp) * 100 if (lb_grants is not None and gsdp > 0) else None,
            })

    df = pd.DataFrame(results).sort_values(by="Gap", ascending=False)
    df = df[~df['State'].isin(['All States and UTs', 'Total'])]

    total_gsdp = df['GSDP'].sum()
    total_gap = df['Gap'].sum()
    total_lb = df['LocalBodyGrants'].sum(skipna=True)
    avg_intensity = (total_gap / total_gsdp) * 100 if total_gsdp > 0 else 0
    
    leaderboard_json = df.to_json(orient='records')
    
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forensic Audit: State & Local Finances</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f2ee; color: #333; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-radius: 12px; }
        h1 { font-family: serif; border-bottom: 3px solid #c00; padding-bottom: 10px; margin-bottom: 10px; font-size: 2.5em; color: #111; }
        .subtitle { font-size: 1.1em; color: #666; margin-bottom: 30px; font-style: italic; }
        
        .tabs { display: flex; border-bottom: 2px solid #eee; margin-bottom: 30px; }
        .tab { padding: 15px 30px; cursor: pointer; font-weight: bold; color: #777; border-bottom: 3px solid transparent; transition: 0.2s; }
        .tab:hover { color: #c00; }
        .tab.active { color: #c00; border-bottom-color: #c00; background: #fff4f4; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .stat-val { font-size: 1.8em; font-weight: bold; color: #111; display: block; }
        .stat-label { font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.1em; color: #777; margin-top: 5px; display: block; }
        .stat-card.highlight { background: #fff4f4; border-color: #ffcccc; }
        .stat-card.highlight .stat-val { color: #c00; }

        .viz-container { margin: 30px 0; display: grid; grid-template-columns: 1fr 1.2fr; gap: 30px; }
        .chart-box { background: #fff; border: 1px solid #ddd; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .chart-box h3 { font-family: serif; margin-top: 0; color: #444; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
        
        .controls { background: #f9f9f9; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #eee; }
        #search-box { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1em; box-sizing: border-box; outline: none; }
        #search-box:focus { border-color: #c00; }
        
        table.leaderboard { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        table.leaderboard th { background: #111; color: #fff; padding: 12px; text-align: right; text-transform: uppercase; font-size: 0.75em; letter-spacing: 0.05em; position: sticky; top: 0; }
        table.leaderboard td { padding: 10px 12px; border-bottom: 1px solid #eee; text-align: right; }
        table.leaderboard th:first-child, table.leaderboard td:first-child { text-align: left; font-weight: bold; color: #111; }
        table.leaderboard tr:hover { background: #f9f9f9; }
        
        .footer { margin-top: 60px; padding-top: 30px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }
        .methodology { background: #fdfdfd; padding: 15px; border-radius: 4px; border-left: 4px solid #c00; margin-top: 20px; font-size: 0.9em; }
        
        @media (max-width: 1000px) { .viz-container, .stats-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Forensic Audit: State & Local Finances</h1>
        <div class="subtitle">Systemic investigation into Fiscal Squeeze and Local Body Support (2025-26 BE)</div>

        <div class="tabs">
            <div class="tab active" id="tab-squeeze" onclick="switchTab('squeeze')">National Fiscal Squeeze</div>
            <div class="tab" id="tab-local" onclick="switchTab('local')">Local Government Support</div>
        </div>

        <div class="controls">
            <input type="text" id="search-box" placeholder="Filter by State..." onkeyup="updateDashboard()">
        </div>

        <!-- Squeeze Tab -->
        <div id="squeeze-content" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-val">₹ {{total_gsdp_formatted}} Cr</span>
                    <span class="stat-label">National Derived GSDP</span>
                </div>
                <div class="stat-card highlight">
                    <span class="stat-val">₹ {{total_gap_formatted}} Cr</span>
                    <span class="stat-label">Total Structural Gap</span>
                </div>
                <div class="stat-card">
                    <span class="stat-val">₹ {{avg_intensity_formatted}}%</span>
                    <span class="stat-label">Avg. Squeeze Intensity</span>
                </div>
            </div>
            
            <div class="viz-container">
                <div class="chart-box">
                    <h3>Structural Gap (₹ Crore)</h3>
                    <div style="height: 350px;"><canvas id="gapChart"></canvas></div>
                </div>
                <div class="chart-box">
                    <h3>Gap vs GSDP Concentration</h3>
                    <div style="height: 350px;"><canvas id="gapScatter"></canvas></div>
                </div>
            </div>

            <h2>Squeeze Audit Registry</h2>
            <div class="table-scroll" style="max-height: 500px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px;">
                <table class="leaderboard" id="squeeze-table">
                    <thead>
                        <tr>
                            <th>State</th>
                            <th>GSDP (Cr)</th>
                            <th>Actual Devolution (Cr)</th>
                            <th>Structural Gap (Cr)</th>
                            <th>Intensity (%)</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <!-- Local Tab -->
        <div id="local-content" class="tab-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-val">₹ {{total_gsdp_formatted}} Cr</span>
                    <span class="stat-label">National Derived GSDP</span>
                </div>
                <div class="stat-card highlight">
                    <span class="stat-val">₹ {{total_lb_formatted}} Cr</span>
                    <span class="stat-label">Total Local Body Transfers</span>
                </div>
                <div class="stat-card">
                    <span class="stat-val">RBI Major Head 3604</span>
                    <span class="stat-label">Data Source</span>
                </div>
            </div>

            <div class="viz-container">
                <div class="chart-box">
                    <h3>Local Body Transfers (₹ Crore)</h3>
                    <div style="height: 350px;"><canvas id="lbChart"></canvas></div>
                </div>
                <div class="chart-box">
                    <h3>Support Intensity (% of GSDP)</h3>
                    <div style="height: 350px;"><canvas id="lbScatter"></canvas></div>
                </div>
            </div>

            <h2>Local Body Support Registry</h2>
            <div class="table-scroll" style="max-height: 500px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px;">
                <table class="leaderboard" id="local-table">
                    <thead>
                        <tr>
                            <th>State</th>
                            <th>GSDP (Cr)</th>
                            <th>Local Body Grants (Cr)</th>
                            <th>Support Intensity (%)</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <div class="methodology">
                <strong>Forensic Audit Methodology:</strong> 
                1. <strong>Structural Gap:</strong> Derived from RBI Statement 17 (Actual Devolution) vs. potential share lost to Union Cesses/Surcharges (est. 21.7%).
                2. <strong>Local Body Support:</strong> Extracted from RBI Appendix II (Major Head 3604: Compensation and Assignments to Local Bodies). 
                Intensity is calculated as a percentage of Derived GSDP.
            </div>
            <p style="margin-top: 20px;">Analysis by <strong>CommonerLLP Systemic Audit Institute</strong>. Data: RBI State Finances 2024-25.</p>
        </div>
    </div>

    <script>
        const auditData = {{leaderboard_json}};
        let charts = {};
        let activeTab = 'squeeze';

        function switchTab(tabId) {
            activeTab = tabId;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            document.getElementById('tab-' + tabId).classList.add('active');
            document.getElementById(tabId + '-content').classList.add('active');
            
            updateDashboard();
            
            // Re-update charts to fix sizing
            Object.values(charts).forEach(c => c.resize());
        }

        function initCharts() {
            const commonOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                let label = ctx.raw.label || ctx.chart.data.labels[ctx.dataIndex];
                                let val = ctx.raw.y || ctx.raw;
                                return label + ': ₹' + val.toLocaleString() + ' Cr';
                            }
                        }
                    }
                }
            };

            charts.gap = new Chart(document.getElementById('gapChart'), {
                type: 'bar',
                data: { labels: [], datasets: [{ label: 'Gap', backgroundColor: '#c00', borderRadius: 4, data: [] }] },
                options: { ...commonOptions, indexAxis: 'y' }
            });

            charts.lb = new Chart(document.getElementById('lbChart'), {
                type: 'bar',
                data: { labels: [], datasets: [{ label: 'LB Grants', backgroundColor: '#004a99', borderRadius: 4, data: [] }] },
                options: { ...commonOptions, indexAxis: 'y' }
            });

            charts.gapScatter = new Chart(document.getElementById('gapScatter'), {
                type: 'scatter',
                data: { datasets: [{ label: 'States', backgroundColor: '#c00', data: [] }] },
                options: { ...commonOptions, scales: { x: { title: { display: true, text: 'GSDP (Cr)' } }, y: { title: { display: true, text: 'Gap (Cr)' } } } }
            });

            charts.lbScatter = new Chart(document.getElementById('lbScatter'), {
                type: 'scatter',
                data: { datasets: [{ label: 'States', backgroundColor: '#004a99', data: [] }] },
                options: { ...commonOptions, scales: { x: { title: { display: true, text: 'GSDP (Cr)' } }, y: { title: { display: true, text: 'Intensity (%)' } } } }
            });
        }

        function updateDashboard() {
            const filter = document.getElementById("search-box").value.toUpperCase();
            const filtered = auditData.filter(d => d.State.toUpperCase().includes(filter));
            
            if (activeTab === 'squeeze') {
                const tbody = document.querySelector("#squeeze-table tbody");
                tbody.innerHTML = "";
                filtered.sort((a,b) => b.Gap - a.Gap).forEach(d => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${d.State}</td>
                        <td>${Math.round(d.GSDP).toLocaleString()}</td>
                        <td>${Math.round(d.Devolution).toLocaleString()}</td>
                        <td>${Math.round(d.Gap).toLocaleString()}</td>
                        <td>${d.SqueezeIntensity.toFixed(2)}%</td>
                    `;
                });

                const topGap = [...filtered].sort((a,b) => b.Gap - a.Gap).slice(0, 15);
                charts.gap.data.labels = topGap.map(d => d.State);
                charts.gap.data.datasets[0].data = topGap.map(d => d.Gap);
                charts.gap.update();

                charts.gapScatter.data.datasets[0].data = filtered.map(d => ({ x: d.GSDP, y: d.Gap, label: d.State }));
                charts.gapScatter.update();
            } else {
                const tbody = document.querySelector("#local-table tbody");
                tbody.innerHTML = "";
                const reported = filtered.filter(d => d.LocalBodyGrants !== null);
                const notReported = filtered.filter(d => d.LocalBodyGrants === null);
                reported.sort((a,b) => b.LocalBodyGrants - a.LocalBodyGrants).concat(notReported)
                    .forEach(d => {
                        const row = tbody.insertRow();
                        const grants = d.LocalBodyGrants !== null ? Math.round(d.LocalBodyGrants).toLocaleString() : '<em style="color:#999">not reported (MH-3604)</em>';
                        const intensity = d.LocalBodyIntensity !== null ? d.LocalBodyIntensity.toFixed(4) + '%' : '—';
                        row.innerHTML = `
                            <td>${d.State}</td>
                            <td>${Math.round(d.GSDP).toLocaleString()}</td>
                            <td>${grants}</td>
                            <td>${intensity}</td>
                        `;
                    });

                const topLB = reported.sort((a,b) => b.LocalBodyGrants - a.LocalBodyGrants).slice(0, 15);
                charts.lb.data.labels = topLB.map(d => d.State);
                charts.lb.data.datasets[0].data = topLB.map(d => d.LocalBodyGrants);
                charts.lb.update();

                charts.lbScatter.data.datasets[0].data = reported.map(d => ({ x: d.GSDP, y: d.LocalBodyIntensity, label: d.State }));
                charts.lbScatter.update();
            }
        }

        window.onload = () => {
            initCharts();
            updateDashboard();
        };
    </script>
</body>
</html>
"""
    
    final_html = html_template.replace("{{leaderboard_json}}", leaderboard_json)
    final_html = final_html.replace("{{total_gsdp_formatted}}", f"{total_gsdp:,.0f}")
    final_html = final_html.replace("{{total_gap_formatted}}", f"{total_gap:,.0f}")
    final_html = final_html.replace("{{total_lb_formatted}}", f"{total_lb:,.0f}")
    final_html = final_html.replace("{{avg_intensity_formatted}}", f"{avg_intensity:.2f}")
    
    with open(OUTPUT_DIR / 'fiscal-squeeze-audit-interactive.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Interactive report generated: {OUTPUT_DIR / 'fiscal-squeeze-audit-interactive.html'}")

if __name__ == "__main__":
    run_viz()
