# Rajasthan Observed-Dataset Onboarding for `public-finance`

## 1) Scope and ownership

This repo’s role:
- `public-finance` owns **budget parsing and interpretation** (LMMHA codes, observed-series assembly, derived fiscal layers).
- `commoner-probe` owns collection/provenance orchestration.

So if you are implementing Rajasthan parsing for observed budget series, this repo is the right place.

## 2) What already exists and should be reused

Use existing scripts and conventions first; avoid creating a new stack.

- `viz/build_observed_data.py`  
  Existing Assam builder that already emits `references/lmmha/lod/observed.json`.
  Target behavior:
  - reads tabular expenditure source,
  - aggregates by `major-submajor-minor` code,
  - writes standardized values in `INR lakh`.

- `publicfinance/extract_fiscal_data.py`  
  Useful for indicator extraction and legacy budget text utilities, but not directly equivalent to the Assam observed pipeline.

- `publicfinance/state_budget_scrapers.py` + other scrapers  
  Useful only for acquisition/ingestion workflows, not the cross-format observed-layer shape.

- `publicfinance/lmmha_*` modules and related tests (`tests/test_lmmha_pipeline.py`)  
  Keep code conventions for code normalization and sub-major/minor identity.

## 3) Current Rajasthan corpus available on disk

Assumption for implementation: data is already present locally; do not fetch again.

- `data/state_budgets/Rajasthan/2025-26/State Budget/`
- Relevant files observed:
  - `Volume 2a _ Revenue Receipts Volume.pdf`
  - `Volume 2c _ Revenue Expenditure-Social Services.pdf`
  - `Volume 3a _ Capital Expenditure.pdf`
  - `Volume 3b _ Public Debt, Loan, Public Account Volume.pdf`

### PDF extraction characteristics

- PDFs are text-bearing and `pdftotext -layout` can extract numeric rows.
- Font mix includes legacy `DevLys-010` + `Arial Unicode MS` (Hindi text often non-clean Unicode).
- Extract based on **codes + structure**, not Hindi label matching.

## 4) Immediate implementation target

Do not block the whole cross-code pipeline on broad OCR-style parsing.

Start with a narrow Rajasthan parser extension that mirrors the existing Assam observed contract:
1. Parse the tables for targeted lines/codes.
2. Normalize to LMMHA key (same major-submajor-minor format as Assam).
3. Convert units consistently to `lakh`.
4. Emit the same `observed.json` shape used by downstream visualizations.

Recommended initial code family for minimum-risk compatibility:
- `2205-00-105`
- `4202-04-105`
- `0202-04-102` (confirm presence in the receipts file before finalizing)
- `6202-04-105` (if present in debt/public account parsing)

## 5) Suggested parser strategy in this repo

### Phase A (recommended first pass)
1. Add a Rajasthan adapter function in `viz/build_observed_data.py` (or a small module imported by it).
2. Parse only verified code-family rows from:
   - Revenue Expenditure PDF for 2205/0202 family.
   - Capital Expenditure PDF for 4202 family.
   - Debt/Loan PDF for 6202 family if available.
3. Use explicit page windows for first pass (for 2025-26 file structure) so extraction is deterministic.
4. Append/merge Rajasthan state series into the observed payload.

### Phase B (standardization hardening)
- Add a generic parser utility to avoid hardcoded logic.
- Add fixtures for extracted snippets (not full scanned pages).
- Expand to additional codes only when regex rules are stable.

## 6) Recommended data normalization

### Units
- Rajasthan totals from current source tables appear in “thousand rupees” form.
- Standardize to `lakh` for compatibility with current Assam output:
  - `value_in_lakh = parse_amount(raw_amount) / 10`

### Code identity rules
- Keep exact `major-submajor-minor` identity, including sub-major context.
- Never collapse by 3-digit strings or major-only prefixes.
- Prefer strict code boundary matching to avoid cross-submajor contamination (`4202-02-105` vs `4202-04-105`).

## 7) Where to write

- Primary output (existing contract):  
  `references/lmmha/lod/observed.json`

- If an intermediate format helps validation, keep it internal (same scope) as plain JSON/CSV before final merge.

## 8) Commands that are useful during implementation

```bash
pdftotext -layout -f 96 -l 97 "data/state_budgets/Rajasthan/2025-26/State Budget/Volume 2c _ Revenue Expenditure-Social Services.pdf" -
pdftotext -layout -f 35 -l 40 "data/state_budgets/Rajasthan/2025-26/State Budget/Volume 3a _ Capital Expenditure.pdf" -
```

Adjust page windows after validating the target layout.

## 9) Pitfalls to avoid

- Don’t infer Hindi labels from noisy OCR-like text.
- Don’t rearchitect into a new scraping/ingestion stack for this task.
- Don’t mix legacy parser contracts with LMMHA observed contract without explicit migration.
- Don’t assume all major codes exist in every volume; confirm before adding hardcoded output.

## 10) Suggested continuation checkpoints

1. First pass parser for targeted Rajasthan library codes in 2025-26.
2. Confirm cross-code series are merged with existing Assam output.
3. Decide whether to refactor to a multi-state schema (`series_by_state`) if downstream consumers need simultaneous per-code multi-state data.
4. Add state-level metadata (`caveat` + source + unit conversion note) in payload.

