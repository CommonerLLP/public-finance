# public-finance — ROADMAP

_Last updated: 2026-05-20. Branch: feat/icds-pipeline._

---

## Where we are right now

### What works

**RBI State Finances** (`rbi_budgets_scraper.py`)
- Crawls `rbi.org.in/scripts/AnnualPublications.aspx` — the "State Finances: A Study of Budgets" publication page
- 5 publication years on volume: 2021, 2022, 2023, 2024, 2025
- 742 files (PDF + XLS) — all four appendices: Revenue Receipts, Revenue Expenditure, Capital Receipts, Capital Expenditure
- All-India coverage within each year
- **Pending fix:** folder labels are publication years, not fiscal years — needs a mapping layer before time-series use

**Union Budget SBE** (`union_budget_scraper.py`)
- Crawls `indiabudget.gov.in` Demand for Grants XLS files
- 7 years on volume: 2020-21 through 2026-27 — Demand No. 101 (MWCD/Anganwadi) only
- Parser (`parse_demand_xls`) extracts scheme-level BE/RE/Actuals rows
- **Gap:** Only one demand number pulled. Every other ministry is untouched.

**Rajasthan** (`state_budget_scrapers.py` — `RajasthanBudgetsScraper`)
- Crawls `finance.rajasthan.gov.in/website/StateBudgetAll.aspx`
- 37 PDFs on volume for 2025-26 — full document set
- **Gap:** One year only. No history pull yet.

---

### What's broken or incomplete

**Uttar Pradesh** (`UttarPradeshBudgetsScraper`)
- ✓ **Breakthrough (2026-05-20):** Cracked KrutiDev encoding; captured **₹30.25 Lakh Crore GSDP** from Budget Speech.
- ✓ **Intelligence:** Successfully ran Open-Model audit (A:2, E:6) via Llama-3.
- **Gap:** Still missing `khand4` (Detailed Demand), `SND`, `khand6`.

**Rajasthan** (`RajasthanBudgetsScraper`)
- ✓ **Breakthrough (2026-05-20):** Captured **88 fiscal indicators** (GSDP, PCI) from Economic Review.
- ✓ **Intelligence:** Successfully ran Open-Model audit (A:6, E:4) via Llama-3.
- **Gap:** History pull pending.

`budget.up.nic.in` has 6 document sections across ~10 years each:

| Section | What it is | Years available | Pulled? |
|---|---|---|---|
| `budgetspeech` | Budget Speech | 27 PDFs | ✓ (2026-27 only) |
| `khand2part1` | Annual Financial Statement | 11 PDFs | ✓ (2026-27 only) |
| `khand2part2` | Grant Memorandum | 10 PDFs | ✓ (2026-27 only) |
| `khand4` | **Detailed Demand for Grants** | 10 PDFs | ✗ not in scraper |
| `SND` | Statement of New Demands | 10 PDFs | ✗ not in scraper |
| `khand6` | — | 6 PDFs | ✗ not in scraper |

Fix: add the 3 missing sections to `UP_SOURCE_PAGES`; remove the year-filter and pull all years from each page.

**Gujarat** (`finance_gujarat_scraper.py`)

✓ **Breakthrough:** Rewrote against `finance.gujarat.gov.in`. Successfully pulled 531 PDFs across multiple grant departments. Obsolete `gujarat_scraper.py` discarded.

**Tamil Nadu** (`TamilNaduBudgetsScraper`)

Scraper written, 0 files downloaded. `tnbudget.tn.gov.in/demands.html` is JS-rendered — the static XPATH finds nothing. Legacy menu-based path (`spi_array.js`) may work for older years but the current portal requires Playwright or equivalent.

**Kerala** (`KeralaBudgetsScraper`)

Scraper written, 0 budget files. `budget.kerala.gov.in/portal/home` is a dynamic portal. `known_sample_documents()` has 4 hardcoded 2025-26 URLs that would work if run — but haven't been executed.

**Madhya Pradesh** (`MadhyaPradeshBudgetsScraper`)

Explicit placeholder. `finance.mp.gov.in` timed out during scouting. `discover_documents()` returns an empty list by design.

**Assam** (`AssamBudgetsScraper`)

Scraper written for 2017-18 only. Not run. 5 years of CivicDataLab expenditure XLS (2018-19 to 2022-23) imported separately into `data/civicdatalab/assam/` — not from the state portal.

---

### No scraper exists

29 of 36 states/UTs. No portal scouting done.

---

### Minimum wages layer (`publicfinance/min_wage/`)

Scraper framework built. Kerala implemented (4 Labour Dept gazette PDFs). CLC (central) has 4 VDA notification PDFs. Rajasthan has 1 file. All other 33 state directories are empty.

---

## Version ladder

### `0.1.0` — released 2026-05-20
First public release. Infrastructure solid. Three sources working end-to-end.
State coverage: 1 of 36 fully scraped.

### `0.2.0` — next cycle
Fix what is broken. Add history to what works. Target: 6–8 functioning state scrapers.

- [ ] UP: add `khand4`, `SND`, `khand6` to `UP_SOURCE_PAGES`; pull all years not just current
- [x] Gujarat: rewrite against `finance.gujarat.gov.in`; discard `gujarat_scraper.py`
- [ ] TN: Playwright-based scraper for `tnbudget.tn.gov.in`
- [ ] Kerala: run known-sample + resolve dynamic portal
- [ ] Rajasthan: pull historical years (portal has multi-year archive)
- [ ] RBI: add fiscal-year mapping layer so publication years resolve to fiscal years
- [ ] Union Budget: pull at least 5 more demand numbers (Health, Education, Rural Dev, Agriculture, Finance)
- [ ] Min wages: implement 4–5 more states beyond Kerala

### `0.5.0` — mid-term
Coverage across major states. Structured output layer.

- [ ] 15+ state scrapers working with history
- [ ] Extraction layer: PDF → structured table for Demand for Grants (pdfplumber-based)
- [ ] Unified CSV output schema: `state`, `fiscal_year`, `head_of_account`, `col_type`, `amount_cr`
- [ ] Min wages for all major states (at minimum: TN, KA, MH, WB, MP, RJ, UP, AP, TG)
- [ ] CI: scheduled weekly crawl check to catch portal breakage early

### `1.0.0` — mission
Automated, reproducible acquisition of Indian public finance data — Union Government and all major states — with structured output (CSV + SQLite) that any researcher can clone, run, and trust.

**Linked Open Data (5-Star):** Serve the official List of Major and Minor Heads of Account (LMMHA) as a fully machine-readable SKOS/RDF ontology on GitHub Pages to act as the central semantic dictionary for Indian finance.

Definition of done:
- Union Budget: all major demand numbers, 10+ years
- RBI State Finances: all available years, fiscal-year mapped
- States: 25+ scrapers working with 5+ years of history each
- Extraction: PDFs parsed to structured rows for at least demand-summary level
- Min wages: all 36 states/UTs
- Output: a single `make data` command produces a verified, dated dataset
- Docs: every scraper documents its source URL, known breakage modes, and last-verified date

---

## Open questions for the 1.0.0 brainstorm

- Is RBI sufficient for cross-state fiscal time-series, or do we need state portal data too?
- Do we need grant-level PDFs, or extracted CSVs, or both?
- What's the minimum history depth — 5 years? 10?
- Delivery format: SQLite DB, CSV, Parquet, or all three?
- Who is the primary user — our own analysis pipelines only, or publishable as a public dataset?
- Licensing: what licence do we put on the code vs. the data?
