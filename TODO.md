# Current

- [ ] **Ship the pages migration (data.commonerllp.org → github.io/public-finance/data):** staged on branch `chore/pages-move-to-github-io` (worktree `scratchpad/pf-pages-move`; durable patch `notes/patches/pages-move-to-github-io.patch`). Needs Aakash: (a) "ship it" (commit→push→PR→merge→detach domain via Pages API), (b) Cloudflare API token location (keychain service / env var / file) for the proxied-CNAME + 301 redirect rule; else 2-min dashboard steps in `notes/HANDOFF.md`. Sequence: merge→verify 200→detach→301. Also: TCC grant for `/Volumes/m1-storage` so `data/` is readable again.

- [ ] **[REQ-0003 ← theright2read] CAG 4-head batch blocked on network egress:** `cag.gov.in` is geo-fenced/unreachable from local sessions; the spec's seed values were NOT re-verified and must not be cited yet. Needs a fetch path with India-based network egress (internal ops detail — ask Aakash which resource to use) rather than local network. Extraction primitive `publicfinance/account_code_extract.py` is built + unit-tested (synthetic rows only) — run it against the real UP/Gujarat/Kerala/AP CAG Finance Accounts Vol-II PDFs once fetched. Rajasthan slice (original ask, `2852/2853/2875`) is DONE — see Archive.
- [ ] **[REQ-0002 ← sevent4] BOCW welfare-board finance — Gujarat done, 4 states remain:** Karnataka, Tamil Nadu, Delhi, West Bengal BOCW boards, same cess/expenditure/balance series as Gujarat (`references/bocw/gujarat.json` is the template; CAG performance-audit reports were the highest-authority source for Gujarat — check those first per state). Note: CAG report downloads for these states will hit the same `cag.gov.in` geo-fence — same India-egress need as REQ-0003 above.
- [ ] **[REQ-0001 ← sevent4] De-jure Gujarat municipal accounts manual (GMFB) still not locatable online:** GMFB site has no public CoA download. Follow-on: CAG "Manual of Instructions for Audit of Local Bodies, Gujarat" (cag.gov.in — same geo-fence issue as above), the GPMC Act 1949 (indiacode.nic.in), or a direct GMFB request/RTI. Until then `23306`'s parent head is confirmed de-facto only (AMC books), not de-jure — see Archive for the NMAM finding.
- [ ] **Backflow to commoner-probe:** Expenditure Profile Statement 22 fetch (REQ-0015, delivered — see Archive) is not yet covered by `commoner_probe/budget/probe.py` (only SBE demand-for-grants XLS is). Add an `expenditure-profile` source family using the URL map in `references/expenditure_profile/README.md` (incl. the pre-2019 combined-vol1.pdf fallback years).

- [ ] **Verification gate (BINDING before citing any figure publicly):** log the **Gujarat money-flow** aggregates (own tax/non-tax/devolution/grants/net-borrowing, 2024-25 BE) to `verified_facts.md` with two sources (Gujarat receipts book + RBI), then mark verified. Same for Assam observed and Rajasthan public-library.
- [ ] **Older Gujarat receipts books → balance/flow back to 2018-19:** balance/flow now build for all 5 receipts-years on disk (2022-23→2026-27; the lakh-vs-crore unit bug is fixed). Pre-2022-23 receipts books are NOT on disk — fetch from the Gujarat finance portal to extend balance/flow earlier (sector already 9yr; off-budget 6yr).
- [ ] **RBI guarantees cross-check (off-budget two-source gate):** off-budget/guarantee figures are CAG-only in `verified_facts.md`; pull RBI "State Finances: A Study of Budgets" guarantee statements as the second source before public citation.
- [ ] **Push `feat/municipal-coa-nmam` + open PR:** 6 local commits (municipal CoA → crosswalk → flow graph → overlay → modular off-budget view + flow FY-switching + receipts fix → Gujarat off-budget back-catalogue). Awaiting Aakash's explicit "push". Do NOT bundle the inherited Rajasthan dirt.
- [ ] **Third off-budget jurisdiction:** pipeline is file-driven — drop `references/offbudget/<code>.json` (from that state's CAG SFAR) + `build_sankey_manifest`. Gujarat + Kerala done.
- [ ] **Rajasthan public libraries verification gate:** finish source-page/second-source verification for parser-confirmed `2205-00-105` and `4202-04-105` values before public citation.
- [ ] **Rajasthan missing-year repair:** recover revenue `2017-18`; recover capital `2015-16`, `2016-17`, `2017-18`, `2018-19`, `2019-20`.
- [ ] **Rajasthan staged PRs:** split the dirty `feat/rajasthan-observed-layer` surface into review slices (parser/tests → generated JSON → Surya artifacts → addendum docs).
- [ ] **Pre-2018 Gujarat OCR pilot:** deploy the Surya/Rajasthan extractor to ONE scanned older year (twenty27 left 15 empty stubs) to prove generalization before backfilling.
- [ ] **Wire more states into the generic Sankey:** TN/KA/MH/MP via the `viz/sankey/adapters/` pattern (one adapter per source).
- [ ] **GFR 2017 PDF parsing:** Acquire the General Financial Rules 2017 PDF and parse its structural rules into the LMMHA spatial parser.
- [ ] **Fiscal-federal map: cross-check top-6 specimens** (TN/KA/MH/MP/Assam/Gujarat) vs RBI State Finances / state Budgets; log both sources → `verified_facts.md`. (Map: `notes/fiscal_federal_extraction_map.md`.)
- [ ] **Pull primary-doc text:** BBMP appendix d5 (slab tables, ₹26,352cr capex); MH Cabinet excise order; MP borrowing/FRBM line.
- [ ] **RTI:** Karnataka state-BCG contract/GO; TN-BCG & Telangana Rising 2047 scopes/fees; West investment-promotion consultancies.
- [ ] **Decide deliverable:** (a) op-ed pillar / (b) cross-state table + harden top-6 / (c) Karnataka deep-dive. Gujarat "manufactured prudence" = 2nd blade for Debt-vs-Death op-ed.
- [ ] UP scraper: add `khand4`, `SND`, `khand6` to `UP_SOURCE_PAGES`; remove year-filter to pull full history
- [ ] Gujarat remaining 19 years download: run `finance_gujarat_scraper.py --page budget --years "2021-22,...,2002-03"` then other page types
- [ ] ICDS DDG data quality: verify 2021-22 zero-cut anomaly and 2020-21 pdfplumber artifact vs. Reports 326 and 314
- [ ] ICDS case study §3 correction: "every year" → "every POSHAN-era year with reliable data (2018-19, 2020-21, 2022-23, 2025-26)"
- [ ] Min wages: stage `publicfinance/min_wage/` for v0.2.0; implement TN, KA, MH

---

# Future

- [ ] Rajasthan observed layer PR staging: split parser/tests, generated JSON, Surya OCR artifacts, and addendum docs into reviewable slices.
- [ ] Rajasthan broader-code expansion beyond public libraries: receipts, loans, and full LMMHA service coverage.
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

- [x] 2026-07-08 — **Delivered 5 cross-repo REQs in parallel (uncommitted, working tree only):**
  - **REQ-0001** (sevent4, municipal CoA) — `references/nmam/nmam_income_base.json` (73-record NMAM income CoA). Finding: `23306` does not exist in NMAM (Gujarat-specific 5-digit code, nearest NMAM concept `140-20` Penalties and Fines); de-jure Gujarat manual still not locatable online.
  - **REQ-0002** (sevent4, BOCW finance) — `references/bocw/gujarat.json`, sourced to CAG Report 02/2025: ₹4,787.60cr cess collected 2006-07→2022-23, 83% (₹3,979.11cr) unspent.
  - **REQ-0003** (theright2read, RTR library heads) — Rajasthan slice complete (`references/lmmha/lod/rtr_library_vs_capital.csv`, libraries ₹16.80cr vs capital ₹378.70cr BE FY2026-27) — first non-Gujarat complete pair. CAG 4-head batch extension blocked on `cag.gov.in` egress; extractor built+tested, not run against real PDFs yet.
  - **REQ-0011** (sevent4, CPI deflator) — `publicfinance/deflator.py` + `references/deflator/cpi_combined_fy2005_06_to_latest.json`, 20/20 years real-sourced (RBI HBS + MoSPI + Economic Survey), 10/10 tests pass.
  - **REQ-0015** (governingclaste, Expenditure Profile) — `references/expenditure_profile/establishment_strength_all_years.csv`, 1,099 rows across 12 budget years (2015-16→2026-27), all grand-totals cross-checked.
  - All 5 delivered via parallel Opus/Fable-5 agents; ledger rows + `memory/verified_facts.md` reconciled same session. Nothing committed/pushed — awaiting Aakash's review + explicit commit/push permission.
- [x] 2026-06-29 — **Modular off-budget Sankey view + Centre→State flow FY-switching + receipts unit fix** (commits `23c137c`, `5738c70`, local on `feat/municipal-coa-nmam`, NOT pushed). New deployed `flow.html` toggles: "flow" (Union→State inter-tier) and "offbudget" (guarantees/off-budget). Pipeline file-driven + manifest GENERATED (`build_sankey_manifest.py`) → scales to all states/UTs/Union × years. Fixed Gujarat receipts lakh-vs-crore unit bug → balance/flow now 5yr (2022-23→2026-27). Acquired CAG SFARs: Gujarat off-budget 6yr (2018-19,2020-21→2024-25; guarantees ₹4,699→₹1,421 cr; SSNNL→GUVNL/Vadodara shift) + Kerala 2023-24 (KIIFB+KSSPL ₹32,942 cr undisclosed, sub judice — proved modularity, zero code change). Fixed flow-graph 3601→3604. 3 new tests; all 7 pass.
- [x] 2026-06-26 — **Shipped Gujarat money-flow + generic Sankey (PR #23, `650f9ce`, merged+deployed).** Refactored Assam-hardcoded builders into ports/adapters (`viz/sankey/`); Assam reproduces byte-identical. Gujarat built entirely from its own books (Demands for Grants + Receipt under Consolidated Fund), no RBI in pipeline. State+Year picker, per-state Cooper dual-mandate, XSS-hardened, core unit tests. From Centre ₹61,893 cr (24%); net borrowing ₹24,622 cr (indicative, not yet verified).
- [x] 2026-06-26 — **Merged LMMHA public-history website (PR #22).** Reconciled duplicate website dirt off the Rajasthan branch; deleted 15 stray root scratch PNGs; pruned merged branches local+remote.
- [x] 2026-06-26 — Pushed clean website-only branch `feat/lmmha-public-history` (`574734e`): public 1987 Sansad Library history, constitutional-finance frame, external-link cues/new-tab behavior, and timeline correction filters for insertions/renames/deletions. Local 1987 archival PDF stayed untracked.
- [x] 2026-06-26 — Built Rajasthan public-library observed addendum: Surya-backed parser for `2205-00-105` revenue and `4202-04-105` capital, regenerated 2013-14→2026-27 JSONs, added `docs/RAJASTHAN-LIBRARIES-ADDENDUM.md`; still parser-confirmed, not publication-verified.
- [x] 2026-06-25 — Shipped public LMMHA chart-of-accounts browser to data.commonerllp.org root (PR #16); subject lookup, per-code scope notes, correction-slip history, methodology tab. Replaced PyLODE dump (→ /vocab.html).
- [x] 2026-06-25 — Built Assam observed-reporting layer (CivicDataLab BE by LMMHA code) and money-flow Sankey: two-sided RBI sources→uses (net borrowing = GFD) + detailed functional sectors + Cooper dual-mandate reading (PR #17).
- [x] 2026-06-25 — Verified + logged RBI Assam fiscal figures (ASM-RBI-001..004): 63% Centre-funded; net borrowing ₹20,790 cr; cross-source sector reconciliation.
- [x] 2026-06-25 — Mobile-responsive pass (PR #18); GitHub Actions Node-24 bump (PR #19); anchor jump-nav + back-to-top + shareable hash links (PR #20). All merged, deployed, live.
- [x] 2026-06-25 — Read + memorized Rathin Roy "Changing Fiscal Dynamics" (Seminar 717) ↔ Ambedkar fiscal federalism; org synthesis §10.
- [x] 2026-06-25 — Fixed LMMHA Major/Sub-Major/Minor code identity and pushed PR #16 branch `fix/lmmha-submajor-keys`.
- [x] 2026-06-25 — Added LMMHA correction-slip timeline export, 2001 scope-note extraction, and cleaned public correction-slip labels.
- [x] 2026-06-24 — Rebuilt LMMHA PDF parser with precise spatial X-coordinates, generated clean JSON and fixed PyLODE vocpub profile HTML rendering bugs.
- [x] 2026-06-24 — Created 5-Star Semantic Web Linked Open Data (LOD) pipeline for LMMHA (`publicfinance/lmmha_skos_exporter.py`).
- [x] 2026-06-24 — Set up `.github/workflows/publish_lod.yml` to publish LMMHA ontology to GitHub Pages.
- [x] 2026-06-24 — Deleted obsolete `gujarat_scraper.py` and updated README/ROADMAP for `finance_gujarat_scraper.py`.
- [x] 2026-06-20 — Built fiscal-federal extraction map across ~19 states (`notes/fiscal_federal_extraction_map.md`).
- [x] 2026-06-20 — Acquired Karnataka RMC excise draft + BCG↔BBMP report (5 deliverables, RTI/OpenCity).
- [x] 2026-06-20 — Fixed partial-recall MCP -32000 (pymupdf dependency drift).
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
