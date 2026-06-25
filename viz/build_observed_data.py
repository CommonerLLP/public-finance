# Generated helper — builds the "observed state reporting" layer for the LMMHA browser.
# DO NOT hand-edit the output (viz/observed.json); rerun this script.
#
# Source: CivicDataLab / openbudgetsindia standardised state expenditure sheets
#   data/civicdatalab/assam/assam_expenditure_<FY>.xlsx   (FY 18-19 .. 22-23)
#
# What it does: for every budget line it forms the LMMHA key major-submajor-minor and
# sums the Budget Estimate for that financial year up to the minor-head level, so the
# figures join directly to the codes in the public browser.
#
# Units: the sheets carry amounts in INR lakh (unit column blank; confirmed by the
# grand-total order-of-magnitude check printed at build time and by matching the prior
# verified 2205-00-105 extract). One source only — illustrative until cross-checked
# against RBI State Finances / the Assam budget volumes (repo data-integrity rule).

import json
from collections import defaultdict
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "data" / "civicdatalab" / "assam"
OUT = REPO / "references" / "lmmha" / "lod" / "observed.json"   # emit into the published deploy dir

# column indices in the CivicDataLab schema (0-based)
MAJOR, SUBMAJOR, MINOR = 22, 26, 30
BE_FY = 55          # budget_estimates_financial_year
FY_COL = 50         # budget_financial_year

FILES = {
    "2018-19": "assam_expenditure_18-19.xlsx",
    "2019-20": "assam_expenditure_19-20.xlsx",
    "2020-21": "assam_expenditure_20-21.xlsx",
    "2021-22": "assam_expenditure_21-22.xlsx",
    "2022-23": "assam_expenditure_22-23.xlsx",
}


def code_of(mh, smh, mn):
    if not mh or mn in (None, ""):
        return None
    smh = str(smh).strip() if smh not in (None, "") else "00"
    return f"{str(mh).strip()}-{smh.zfill(2)}-{str(mn).strip()}"


def main():
    # observed[code][fy] = summed BE
    observed = defaultdict(lambda: defaultdict(float))
    grand = defaultdict(float)

    for fy, fname in FILES.items():
        path = SRC / fname
        if not path.exists():
            print(f"  skip {fname} (missing)")
            continue
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        next(rows)  # header
        n = 0
        for r in rows:
            be = r[BE_FY]
            if not be:
                continue
            code = code_of(r[MAJOR], r[SUBMAJOR], r[MINOR])
            if not code:
                continue
            observed[code][fy] += be
            grand[fy] += be
            n += 1
        wb.close()
        print(f"  {fy}: {n:>6} lines  grand BE = {grand[fy]/100:,.0f} cr  ({grand[fy]:,.0f} lakh)")

    # shape: { code: { state, unit, series: [ {fy, be} ... ] } }
    out = {}
    fy_order = list(FILES.keys())
    for code, series in observed.items():
        out[code] = {
            "state": "Assam",
            "unit": "lakh",
            "series": [{"fy": fy, "be": round(series[fy], 2)} for fy in fy_order if fy in series],
        }

    payload = {
        "meta": {
            "source": "CivicDataLab / openbudgetsindia — Assam state expenditure (BE), 2018-19 to 2022-23",
            "unit": "INR lakh, Budget Estimate (BE), aggregated to minor-head level",
            "states": ["Assam"],
            "caveat": "Single-source; illustrative only until cross-checked against RBI State Finances "
                      "or the Assam budget volumes and logged in memory/verified_facts.md.",
            "codes": len(out),
        },
        "observed": out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.0f} KB)  codes={len(out)}")


if __name__ == "__main__":
    main()
