# public-finance — ROADMAP

_Last updated: 2026-07-08. Branch: main._

---

## Where we are right now

The repo now has two tracks. Track A (acquisition) is the original scope and is still the
least mature. Track B (reference-data + visualization) grew out of Track A's outputs and is
the more publicly mature surface today — it's what's actually deployed and linked to.

### Track A — government document acquisition (scrapers)

**What works**

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
- **Gap:** Only one demand number pulled. Every other ministry is untouched. (Expenditure
  Profile / establishment-strength data is now covered separately — see Track B.)

**Rajasthan** (`state_budget_scrapers.py` — `RajasthanBudgetsScraper`)
- Crawls `finance.rajasthan.gov.in/website/StateBudgetAll.aspx`
- 37 PDFs on volume for 2025-26 — full document set
- **Gap:** One year only. No history pull yet.

**Gujarat** (`finance_gujarat_scraper.py`)
- Rewritten against `finance.gujarat.gov.in`. 531 PDFs pulled across multiple grant
  departments. `finance_gujarat_scraper.py --page budget` covers 2022-23→2026-27; 19 earlier
  years (2021-22 back to 2002-03) and other page types not yet downloaded.

**What's broken or incomplete**

- **Uttar Pradesh**: KrutiDev-encoded PDFs crackable (GSDP captured from Budget Speech), but
  3 of 6 `budget.up.nic.in` document sections (`khand4` Detailed Demand, `SND`, `khand6`) are
  still not in `UP_SOURCE_PAGES`, and only the current year is pulled where sections do work.
- **Tamil Nadu**: scraper written, 0 files downloaded — `tnbudget.tn.gov.in/demands.html` is
  JS-rendered; needs Playwright or equivalent.
- **Kerala**: scraper written, 0 budget files downloaded — `budget.kerala.gov.in` is a dynamic
  portal; `known_sample_documents()` has 4 hardcoded 2025-26 URLs, not yet run.
- **Madhya Pradesh**: explicit placeholder — `finance.mp.gov.in` timed out during scouting.
- **Assam**: state-portal scraper written for 2017-18 only, not run. 5 years of CivicDataLab
  expenditure XLS (2018-19→2022-23) imported separately, not from the state portal.

**No scraper exists**: 29 of 36 states/UTs. No portal scouting done.

**Minimum wages layer** (`publicfinance/min_wage/`): framework built. Kerala implemented (4
Labour Dept gazette PDFs). CLC (central) has 4 VDA notification PDFs. Rajasthan has 1 file.
All other 33 state directories are empty.

### Track B — fiscal reference-data clearinghouse + money-flow visualization

This is what's actually live at the deployed site (built from `references/lmmha/lod/`, served
via GitHub Pages):

- **LMMHA chart-of-accounts browser** (`vocab.html`) — the List of Major and Minor Heads of
  Account published as a 5-star SKOS/RDF Linked Open Data ontology: subject lookup, per-code
  scope notes, correction-slip history, methodology tab. Canonical machine-readable dictionary
  for every tax/expenditure head in the Indian budget.
- **Money-flow Sankey site** (`flow.html`) — one deployed front-end reading a generated
  manifest (`sankey_manifest.json`); a new jurisdiction/view is a JSON file + manifest entry,
  never a new HTML page. Four view types per jurisdiction where built: **sector** (functional
  spend breakdown), **balance** (sources vs. uses / net borrowing), **flow** (Union→State
  inter-tier transfers), **off-budget** (guarantees/SPV borrowing kept off the budget line,
  from CAG SFAR — never summed into the on-budget total). Currently covers **Gujarat**
  (built from its own receipts/demand books, 2018-19→2026-27 depending on view; RBI is a
  cross-check, not the source), **Assam** (RBI-sourced), and **Kerala** (off-budget only —
  KIIFB/KSSPL, sub judice).
- **Reference datasets** (`references/`) — reusable, provenanced fiscal reference layers other
  repos in the org pull from directly, not just inputs to this repo's own analysis: municipal
  chart-of-accounts crosswalks (NMAM/GMAM), Gujarat BOCW welfare-board cess/expenditure series
  (CAG-sourced), a 20-year CPI-Combined deflator, Union Budget establishment-strength
  (Expenditure Profile Statement 22, 12 budget years), and cross-tier LMMHA crosswalks mapping
  Union/State heads into a shared pivot vocabulary.
- **Verified-facts ledger** (local, not published raw) — 67 rows, each two-source-verified
  before being treated as citable; 4 currently flagged single-source and not yet hardened.
- **Test coverage**: 62 tests across `tests/` and `publicfinance/` (`pytest --collect-only`,
  verified 2026-07-08 — not carried forward from a prior self-report).

**Known gaps in Track B:**
- Off-budget figures are CAG-sourced and internally cross-reconciled, but the RBI guarantees
  statement (the two-source rule's second source) hasn't been pulled yet — off-budget figures
  aren't in the verified-facts ledger as publicly citable.
- Money-flow (sector/balance/flow) aggregates are indicative, not line-verified, pending the
  same two-source gate.
- A CAG report-download source is unreachable from the network this repo's sessions currently
  run on — this blocks extending the off-budget/municipal-CoA reference layers to any
  additional state until a different network path is available.
- Only 3 of 36 states/UTs have a money-flow view built.

---

## Version ladder

### `0.1.0` — released 2026-05-20
First public release. Track A infrastructure solid, three acquisition sources working
end-to-end. State coverage: 1 of 36 fully scraped. (Track B did not exist yet.)

### `0.2.0` — in progress, Track A mostly unchanged; Track B is what actually shipped
The original `0.2.0` scraper-coverage targets are still mostly open:

- [ ] UP: add `khand4`, `SND`, `khand6` to `UP_SOURCE_PAGES`; pull all years not just current
- [x] Gujarat: rewrite against `finance.gujarat.gov.in`; discard `gujarat_scraper.py`
- [ ] Gujarat: pull remaining 19 years (2021-22→2002-03) and other page types
- [ ] TN: Playwright-based scraper for `tnbudget.tn.gov.in`
- [ ] Kerala: run known-sample + resolve dynamic portal
- [ ] Rajasthan: pull historical years (portal has multi-year archive)
- [ ] RBI: add fiscal-year mapping layer so publication years resolve to fiscal years
- [ ] Union Budget: pull at least 5 more demand numbers (Health, Education, Rural Dev, Agriculture, Finance)
- [ ] Min wages: implement 4–5 more states beyond Kerala

What actually shipped in this cycle instead was Track B, unplanned in the original ladder:
LMMHA LOD site, generic Sankey money-flow layer (3 jurisdictions, 4 view types), off-budget
layer from CAG SFAR, municipal chart-of-accounts crosswalks, BOCW welfare-board finance, CPI
deflator, Expenditure Profile establishment-strength. None of this required Track A coverage
to grow — it came from parsing primary documents directly per jurisdiction. Track A and Track
B are decoupled; a state can get a Track B reference dataset without a Track A scraper existing
for it.

### `0.5.0` — mid-term
Coverage across major states; structured output layer; Track B extended.

- [ ] 15+ state scrapers working with history (Track A)
- [ ] Extraction layer: PDF → structured table for Demand for Grants (pdfplumber-based)
- [ ] Unified CSV output schema: `state`, `fiscal_year`, `head_of_account`, `col_type`, `amount_cr`
- [ ] Min wages for all major states (at minimum: TN, KA, MH, WB, MP, RJ, UP, AP, TG)
- [ ] CI: scheduled weekly crawl check to catch portal breakage early
- [ ] Money-flow Sankey: wire 5+ more states via the `viz/sankey/adapters/` pattern
- [ ] Off-budget layer: a third jurisdiction beyond Gujarat/Kerala
- [ ] Two-source verification: RBI guarantees cross-check clears the off-budget and money-flow
      figures currently indicative-only, moving them into the verified-facts ledger

### `1.0.0` — mission
Automated, reproducible acquisition of Indian public finance data — Union Government and all
major states — with structured output (CSV + SQLite) that any researcher can clone, run, and
trust, plus a public reference-data and visualization layer other researchers and repos can
build on directly.

Definition of done:
- Union Budget: all major demand numbers, 10+ years
- RBI State Finances: all available years, fiscal-year mapped
- States: 25+ scrapers working with 5+ years of history each
- Extraction: PDFs parsed to structured rows for at least demand-summary level
- Min wages: all 36 states/UTs
- Money-flow Sankey + off-budget layer: at least 10 states/UTs, each two-source verified
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
- Now that Track B has its own momentum independent of Track A coverage, should the version
  ladder track them separately (e.g. a Track-B-specific gate for "N jurisdictions, M view
  types, two-source verified") rather than folding both into one number?
