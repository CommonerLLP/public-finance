# public-finance

The Union and state budgets are the arithmetic of who gets what from the political equality the Constitution promised in 1950. That arithmetic is scattered across dozens of Finance Ministry portals, state finance department websites, and RBI publications — in PDFs, XLS files, and JavaScript-rendered pages designed, at best, for the occasional audit and not for longitudinal research.

---

## Foundational Acknowledgement: The OBI Gold Standard

This project stands on the shoulders of **Open Budgets India (OBI)**, the foundational infrastructure built by the **Centre for Budget and Governance Accountability (CBGA)** and **CivicDataLab (CDL)**. 

For over a decade, OBI has defined the gold standard for budget transparency in India, transforming inaccessible government documents into a public data common. This `public-finance` is not an independent invention; it is a **forensic extension** of their work. We use the CBGA scrapers and parsers as our primary reference architecture, and our primary goal is to ensure the continuity and graceful reproduction of the OBI vision for the 2024-25 fiscal year and beyond.

We acknowledge our deep technical and intellectual debt to the CBGA and CDL teams whose labor made Indian fiscal accountability machine-readable.

---

## What this is for

Budget data in India is used primarily by the institutions that produce it. This project exists for the constituencies the data is *about* — researchers documenting under-provisioning in welfare programmes, journalists tracing allocation cuts across fiscal years, law collectives building evidence on constitutional welfare obligations, movements that need a number that holds up under scrutiny.

The analytical frame is accountability, not audit. The question every scraper is built to answer is not "how much was spent" but "how does the allocation pattern change across years, across states, across welfare heads" — and what does the pattern reveal about which demands the State absorbs versus which it deflects.

---

## What works

| Source | Script | Coverage | Output |
|---|---|---|---|
| RBI State Finances | `rbi_budgets_scraper.py` | 5 years (2021–2025 publications), all appendices, all-India | PDF + XLS in `data/rbi/` |
| Union Budget SBE | `union_budget_scraper.py` | 7 years (2020-21 to 2026-27), Demand No. 101 (MWCD) | XLS in `data/union_budget/` |
| Rajasthan | `state_budget_scrapers.py` | 2025-26, full document set | PDF in `data/state_budgets/Rajasthan/` |

## What is partially working

| Source | Script | Issue |
|---|---|---|
| Uttar Pradesh | `state_budget_scrapers.py` | 3 of 6 document sections only; current year only — `khand4` (Detailed Demand for Grants), `SND`, `khand6` not yet scraped; no history pull |
| Gujarat | `gujarat_scraper.py` | Wrong source — CMO press PDFs, not Finance Dept grant data; `finance.gujarat.gov.in` untouched |
| Kerala | `state_budget_scrapers.py` | Dynamic portal; `--known-sample` mode works for 4 documents |
| Assam | `state_budget_scrapers.py` | Written for 2017-18 only; not run |

## What is not working

| Source | Issue |
|---|---|
| Tamil Nadu | JS-rendered portal; static XPATH fails silently; needs Playwright |
| Madhya Pradesh | `finance.mp.gov.in` timed out during scouting; placeholder only |
| 29 other states/UTs | No scraper exists |

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python publicfinance/db_init.py
```

### RBI State Finances

```bash
# Preview without downloading
python publicfinance/rbi_budgets_scraper.py --dry-run

# Download current publication
python publicfinance/rbi_budgets_scraper.py

# Download a specific archived year
python publicfinance/rbi_budgets_scraper.py --url <url> --fiscal-year 2023-24
```

### Union Budget Demand for Grants

```bash
# Download all archive years for a demand number
python publicfinance/union_budget_scraper.py --demand 101 --out data/union_budget

# Dry run
python publicfinance/union_budget_scraper.py --demand 101 --dry-run
```

### State budget scrapers

```bash
# Rajasthan 2025-26 (works)
python publicfinance/state_budget_scrapers.py rajasthan --fiscal-year 2025-26

# Uttar Pradesh 2026-27 (partial)
python publicfinance/state_budget_scrapers.py uttar-pradesh --fiscal-year 2026-27

# Kerala known sample (4 documents)
python publicfinance/state_budget_scrapers.py kerala --fiscal-year 2025-26 --known-sample

# Dry-run any state before downloading
python publicfinance/state_budget_scrapers.py <state> --fiscal-year <year> --dry-run
```

Available state choices: `assam`, `tamil-nadu`, `kerala`, `uttar-pradesh`, `rajasthan`, `madhya-pradesh`

---

## Data layout

```
data/                         # gitignored — lives on external volume or local disk
  rbi/                        # RBI State Finances publications
  union_budget/               # Union Budget SBE XLS files
  state_budgets/              # State Finance Dept documents
  min_wage/                   # State Labour Dept minimum wage schedules
db/
  budget_metadata.db          # SQLite index of all downloaded documents (gitignored)
```

Financial year is Apr–Mar, recorded as `YYYY-YY` (e.g. `2023-24`). All output column names carry explicit units (`expenditure_cr`, not `expenditure`).

---

## Standards

- **RBI "State Finances: A Study of Budgets"** is the reference for cross-state fiscal time-series. When RBI figures conflict with a state portal figure, the discrepancy is flagged, not silently resolved.
- Every scraper is safe to re-run: file existence is checked before fetching; skips are logged.
- Per-host sleep between requests. Government portals are not load-test targets.
- No Java dependency. PDF parsing uses `pdfplumber`.

---

## Notes

- `cbga_parsers/` and `cbga_scrapers/` are upstream CBGA reference clones kept locally. They are gitignored and not vendored.
- Never commit `data/`, `db/`, or `notes/` — they are gitignored for a reason.
- See [ROADMAP.md](ROADMAP.md) for version milestones, known gaps, and the path to 1.0.0.
- See [CHANGELOG.md](CHANGELOG.md) for per-release notes.
