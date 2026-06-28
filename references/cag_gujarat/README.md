# CAG Gujarat — State Finances Audit Report (off-budget & guarantees slice)

The authoritative source for Gujarat's **off-budget borrowing, contingent
liabilities (guarantees), and PSU/SPV exposure** — the part of state finance that
sits *outside* the LMMHA budget chart by design.

## Why this is here

The flow graph's `borrow.market_state` edge is **on-budget only** (the gross
fiscal deficit residual). Off-budget borrowing, state guarantees of PSU/SPV debt,
and back-to-back loans excluded from state debt by GoI fiat are invisible to the
budget — and therefore to that edge. The CAG State Finances Audit Report (SFAR) is
the audit gold-standard for these, drawn from Statement No. 20 of the Finance
Accounts. This slice extracts the FY 2022-23 figures.

## Provenance — three years acquired

| FY | Report | SHA-256 | Pages | Text |
|---|---|---|---|---|
| 2022-23 | No. 1 of 2024 | `f80bc30f…6d7cb0` | 266 | scanned → OCR (ocrmypdf/tesseract) |
| 2023-24 | No. 1 of 2025 | `f55cbd1b…b1b73a` | 200 | born-digital |
| 2024-25 | No. 2 of 2026 | `fe643892…f8a23cd` | 230 | born-digital |

Full URLs + the verbatim hashes are in the normalised slice `../offbudget/gujarat.json`
(`sources`). All three confirmed **Government of Gujarat** by title page. Source
PDFs + OCR outputs live in `source/` (gitignored); only this README and the JSON
slice are tracked.

## Acquisition lesson (logged)

The first PDF found via web search (`SFAR_22-23_Approved_Bond_Coloured...pdf`) was
**Karnataka**, not Gujarat — the filename was not state-tagged and a search engine
asserted it was Gujarat. Caught by reading the title page before trusting it
(*found is not acquired*). The correct Gujarat PDF was taken from the CAG Gujarat
detail page (`details/120434`), then OCR'd and confirmed (587 "Gujarat" mentions).

## Headline figures (INR crore) — see the JSON for the full slice

- **Outstanding guarantees (close of year):** ₹1,473 (2022-23) → ₹1,463 (2023-24)
  → ₹1,421 (2024-25); ceiling ₹20,000 (Gujarat State Guarantees Act 1963);
  0.74% → 0.66% → 0.65% of revenue receipts. Falling trend from ₹4,699 cr (2018-19).
  Stable top exposure all three years: GUVNL (power PSU) ₹345 cr, **Vadodara
  Municipal Corporation** ₹273 cr, Gujarat Water Supply & Sewerage Board ₹222 cr.
- **Off-budget borrowing:** the State *claims* none, every year (a narrow
  self-report). The **2024-25 SFAR §3.1** names the mechanism anyway — borrowing
  routed through SPSUs to bypass the XV-FC 3%-of-GSDP Net Borrowing Ceiling, with
  GoI now *reducing* a state's ceiling by the extent of off-budget borrowing.
  Plus the GST back-to-back device (₹9,222 cr FY21, ₹13,040 cr FY22) excluded from
  state debt by GoI fiat, and §3.2 undischarged liabilities (₹70.76 cr unpaid
  deposit interest, cess/NPS short-transfers).
- **PSU channel (on-budget support, 2022-23):** power-sector SPSU support rose
  ₹5,263 → ₹14,614 cr; non-power ₹3,418 → ₹9,208 cr.

## Cross-check status

CAG is the **primary** (ex Finance Accounts Statement 20). RBI *State Finances: A
Study of Budgets* guarantees statement is the **pending** second source (repo
two-source rule).
