# TODO — public-finance

---

# Current

- [ ] UP scraper: add `khand4`, `SND`, `khand6` to `UP_SOURCE_PAGES`; remove year-filter to pull full history
- [ ] Gujarat remaining 19 years download: run `finance_gujarat_scraper.py --page budget --years "2021-22,...,2002-03"` then other page types
- [ ] Delete old `gujarat_scraper.py` (OBI-based, replaced by `finance_gujarat_scraper.py`)
- [ ] ICDS DDG data quality: verify 2021-22 zero-cut anomaly and 2020-21 pdfplumber artifact vs. Reports 326 and 314
- [ ] ICDS case study §3 correction: "every year" → "every POSHAN-era year with reliable data (2018-19, 2020-21, 2022-23, 2025-26)"
- [ ] Min wages: stage `publicfinance/min_wage/` for v0.2.0; implement TN, KA, MH

---

# Future

- [ ] Rajasthan history pull (portal has multi-year archive)
- [ ] RBI fiscal-year mapping layer (publication year → fiscal year)
- [ ] Union Budget demand breadth: Health, Education, Rural Dev, Agriculture, Finance (minimum 5 more)
- [ ] Kerala portal: resolve dynamic portal; run `--known-sample` as interim
- [ ] Tamil Nadu: Playwright-based scraper for `tnbudget.tn.gov.in`
- [ ] `publicfinance/case_status/` module: eCourts + SC portal case-number → verified status CSV

- [ ] ICDS CPI deflation: ₹8/day (Oct 2017) → 2026 rupees using CPI food index
- [ ] ICDS state-level layer: MH + WB budget portals (portal URLs not yet identified)
- [ ] ICDS RS Health committee PDF text: 174 PDFs in `data/icds_sansad_committees/pdfs/rs/health_*.pdf`
- [ ] sansad-semantic-crawler regex v2 implementation (notes in `sansad-semantic-crawler/notes/regex_v2_icds_audit.md`)
- [ ] CPR Accountability Initiative: budget briefs + PAISA reports (Playwright needed for JS-rendered pages)

---

# Archive

- [x] 2026-06-20 — Finalized 'Prose of Austerity' White Paper op-ed.
- [x] 2026-06-20 — Extracted UP and Punjab library minor head codes for theright2read.
- [x] 2026-05-20 — v0.1.0 tagged and pushed to CommonerLLP/public-finance on GitHub
- [x] 2026-05-20 — README rewritten with mission framing
- [x] 2026-05-20 — ROADMAP.md and CHANGELOG.md created
- [x] 2026-05-20 — `union_budget_scraper.py`, `metadata.py`, `llm_providers.py` (OpenRouter added), `tests/test_scheme_pipeline.py` committed
- [x] 2026-05-16 — AWW litigation map built (`notes/aww_litigation_map.html`)
- [x] 2026-05-16 — Min wage scraper framework created (`publicfinance/min_wage/`); Kerala test case complete
- [x] 2026-05-16 — State-wise AWW/AWH honorarium data (PIB 2003433, RS Q.627)
- [x] 2026-05-16 — ICDS-015 superseded; ICDS-018/019/020/021 verified and logged
- [x] 2026-05-15 — DDG projection extractor (`dfg_projection_extractor.py`); ATR linkage (17 MWCD DFG→ATR pairs)
- [x] 2026-05-15 — Q&A corpus refresh (2,576 records classified); discourse time-series complete
- [x] 2026-05-14 — ICDS three-modes analysis complete (`notes/icds_case_study.md`)
- [x] 2026-05-10 — Initial infrastructure: RBI scraper, Rajasthan scraper, metadata DB
