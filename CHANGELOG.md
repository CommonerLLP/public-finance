# CHANGELOG

All notable changes to this project will be documented here.
Format: [Semantic Versioning](https://semver.org). `Unreleased` tracks work since the last tag.

---

## [Unreleased]

---

## [0.1.0] — 2026-05-20 — Initial public release

First public release. Infrastructure is stable. Three sources work reliably end-to-end.
State coverage is early — 1 of 36 states fully scraped, 4 partially, 31 untouched.

### Working

- **RBI State Finances scraper** (`rbi_budgets_scraper.py`) — crawls
  `rbi.org.in` annual publication pages; downloads PDF + XLS appendices;
  indexes to SQLite. 5 publication years (2021–2025) verified on disk.
- **Union Budget SBE scraper** (`union_budget_scraper.py`) — downloads
  Demand for Grants XLS from `indiabudget.gov.in`; parses scheme-level
  BE/RE/Actuals rows. 7 years (2020-21 to 2026-27), Demand No. 101.
- **Rajasthan state budget scraper** — 37 PDFs, 2025-26, full document set.
- **Metadata DB** (`db_init.py`, `metadata.py`) — SQLite index with
  dedup, fiscal-year labelling, and extension normalisation.
- **Scraping base** (`scrapping_utils.py`) — shared HTTP layer with
  per-host sleep, retries, SSL bypass for gov portals, lxml DOM helpers.
- **Union Budget SBE parser** (`union_budget_scraper.parse_demand_xls`) —
  extracts scheme-level allocation rows from SBE XLS files.
- **ICDS fiscal pipeline** — `icds_timeseries.py`, `dfg_projection_extractor.py`,
  `icds_inflation_table.py`; 5-year BE/RE/Actuals for Saksham Anganwadi +
  POSHAN 2.0; Finance Ministry vs. MWCD projection gap documented.
- **Minimum wage scraper framework** (`publicfinance/min_wage/`) — base
  classes, state registry, CLI. Kerala implemented and verified.

### Partial / known issues

- **Uttar Pradesh** — scraper covers 3 of 6 document sections; no history pull.
  `khand4` (Detailed Demand for Grants), `SND`, `khand6` not yet in scope.
- **Gujarat** — `gujarat_scraper.py` targets wrong source (CMO press PDFs,
  not Finance Dept). No grant-level data. Rewrite planned for 0.2.0.
- **Kerala** — scraper written; dynamic portal means `discover_documents`
  returns 0. `--known-sample` mode works for 4 documents.
- **Assam** — scraper targets 2017-18 only; not run. CivicDataLab
  expenditure XLS (2018-19 to 2022-23) imported separately.

### Not working

- **Tamil Nadu** — `tnbudget.tn.gov.in` is JS-rendered; static XPATH
  fails silently. Requires Playwright. Planned for 0.2.0.
- **Madhya Pradesh** — `finance.mp.gov.in` timed out during scouting.
  Placeholder class returns empty list.
- **29 other states/UTs** — no scraper exists.

---

_See [ROADMAP.md](ROADMAP.md) for the path to 1.0.0._
