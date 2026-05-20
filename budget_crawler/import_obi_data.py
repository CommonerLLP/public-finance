"""
Importer for historical OBI/CBGA timeseries CSV data.
Normalizes data into the CommonerLLP scheme_allocations table.
"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, upsert_scheme_allocation, get_canonical

def import_icds_timeseries(csv_path, db_path=DEFAULT_DB_PATH):
    print(f"Importing OBI/CBGA ICDS Timeseries from: {csv_path}")
    count = 0
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scheme_name = row["scheme"]
            canonical = get_canonical(scheme_name, db_path=db_path) or "icds_anganwadi_services"
            
            upsert_scheme_allocation(
                doc_id="obi_icds_historical_timeseries",
                level="central",
                state="central",
                fiscal_year=row["fiscal_year"],
                demand_no="101",
                scheme_name=scheme_name,
                scheme_canonical=canonical,
                col_type=row["col_type"],
                revenue_cr=float(row["revenue_cr"]),
                capital_cr=float(row["capital_cr"]),
                total_cr=float(row["total_cr"]),
                db_path=db_path,
            )
            count += 1
    print(f"  Successfully imported {count} historical records.")

if __name__ == "__main__":
    csv_input = "/Volumes/m1-storage/fiddlewiddle/budget-crawler/data/icds_budget_timeseries.csv"
    import_icds_timeseries(csv_input)
