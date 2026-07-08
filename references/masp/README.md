# MASP — Model Accounting System for Panchayats (rural local body)

The **Model Accounting System for Panchayati Raj Institutions (MASP)** is the chart
of accounts for **rural** local bodies — issued by the C&AG with the Ministry of
Panchayati Raj on the recommendation of the Eleventh Finance Commission, prescribed
in its current form in **2009**, and operationalised through **PRIASoft / eGramSwaraj**
(NIC + MoPR) across all three PRI tiers (Zilla / Block / Gram Panchayat).

## Where it sits among the four charts

- **Basis:** cash, single-entry — like the LMMHA government chart
  (`references/lmmha/`), and **unlike** the accrual NMAM/urban chart
  (`references/nmam/`, `references/gmam/`).
- **Structure:** accounts in two parts — Part I (Panchayat Fund receipts/expenditure),
  Part II (Provident Funds, Loans, Deposits, Advances) — classified in **four tiers:
  Major Head → Minor Head → Sub-Head → Object Head**, plus a separate **list of Codes
  for Functions, Programmes & Activities** and **standardised Object heads**.
- **Alignment caveat (verified this turn):** MASP is cash like the LMMHA, but it does
  **not** reuse the LMMHA's functional major-head codes (e.g. `2515` Rural
  Development). A quick scan of the C&AG PRI manual found its own
  Function/Programme/Activity codification, not the LMMHA majors. So rural is closer
  to government in *basis*, not in *codes*. (Earlier draft of `fund_flow_map.md`
  over-stated the alignment; corrected.)

## Provenance — what's acquired

- `source/cag_pri_manual.pdf` — **Manual of Instructions for Audit of Panchayati Raj
  Institutions**, C&AG (gitignored — local only).
  - Source URL: https://cag.gov.in/uploads/media/PRI-Manual-20201127173825.pdf
  - Retrieved 2026-06-27 · 2,457,432 bytes · SHA-256
    `45fd0c4836ead3bd8dda5aa247899cd0a308d5c6b76cc917fe801b9a0a2330e2` · 236 pages.
  - Carries the accounting classification (list of Codes for Functions/Programmes/
    Activities, standardised Object heads, major-headwise budget format).
- Logged in `memory/verified_facts.md` (`MASP-ACQ-001`).

## Status / next

- This is the **C&AG audit manual** for PRIs, which embeds the classification. The
  standalone **MoPR "Model Accounting System — List of Codes"** (the 8 prescribed
  formats + full code list) lives on the MoPR / eGramSwaraj portal and is the ideal
  next acquisition for a complete rural chart.
- Completes the four-tier set (LMMHA · NMAM/GMAM · MASP) at the *structure* level,
  enough to design the crosswalk schema once against all four.
