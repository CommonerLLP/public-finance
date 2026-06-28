# GMAM — Gujarat municipal chart of accounts (urban local body)

This directory tracks the **Gujarat municipal corporation budget/account code**
chart — the 5-digit codes urban local bodies in Gujarat (e.g. Ahmedabad Municipal
Corporation) use in their budget books, such as `23306` = *Penalty Recovered from
Contractors*.

**This is NOT the LMMHA government chart** (`references/lmmha/`, used by the Union
and the States under Article 150) and **NOT the NMAM national 3-level accrual
chart** (`references/nmam/`). Urban local bodies budget on their own state-derived
municipal classification. This reference exists so city repos (e.g. sevent4) can
crosswalk municipal budget-line codes to authoritative head names and apply the
correct department→city consolidation, instead of re-deriving meanings from raw
PDFs. (REQ-0001 in `_org/requests/LEDGER.md`.)

## What's here

- `gmam_revenue_income_23xxx.json` — the **`23xxx` non-tax revenue-income slice**:
  - `231` Interest · `232` Sale of forms/scrap · `233` Penalties/fines/misc
    (incl. `23305` Suppliers and `23306` Contractors — a *pair*).
  - parent group `23` = "Non-tax revenue income"; the department→city roll-up rule;
    the 7-column lakh layout; and the related `18133` octroi-grant edge.

## Provenance & status

- **Source:** Ahmedabad Municipal Corporation Budget 2023-24 (English edition),
  read this turn; corroborated by identical code slots across AMC books 2005-06 →
  2026-27 (sevent4).
- **Authority caveat:** the formal *Gujarat Municipal Accounts Manual / GMFR* is the
  de-jure authority and has **not yet been acquired**. Here the AMC budget book is
  the de-facto code list in use. Names with `name_completion_inferred: true` were
  truncated in the book's column layout and completed by inference — confirm against
  the manual.
- Verified figures/definitions are logged in `memory/verified_facts.md`
  (`GMAM-23306`).

## Next

- Acquire the formal Gujarat Municipal Accounts Manual / GMFR to confirm parent
  heads, accrual basis, and the full code list beyond `23xxx`.
- Extend to expense codes and other revenue groups (taxes `11xxx`–`17xxx`, octroi
  grant `181xx`, revenue grants).
