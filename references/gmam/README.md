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

## Gujarat manual — acquisition attempt (2026-07-08)

The formal, de-jure Gujarat Municipal Accounts Manual / GMFR code list **could not be
located online** on 2026-07-08. Checked:

- **Gujarat Municipal Finance Board** (https://gmfb.in/) — the nodal agency for the
  accrual double-entry rollout. Its site carries **no downloadable manual / chart of
  accounts** (only an RTI PDF). GMFB tenders confirm the accrual system covers 159
  Gujarat municipalities but do not publish the code list.
- Web/search for a Gujarat manual PDF returned only **peer-state NMAM-derived manuals**
  (Karnataka `KMAM-Vol-1`, Chhattisgarh, Odisha, Tamil Nadu, Maharashtra Municipal
  Account Code 2010) — useful structural analogues, not the Gujarat text.
- Gujarat-specific primary-source **leads for the follow-on** (not yet mined):
  - C&AG *Manual of Instructions for Audit of Local Bodies, Gujarat 2023-24*
    (`cag.gov.in/uploads/office_mannual/LB-Manual-064c8fa62129925-23318514.pdf`).
  - Gujarat Provincial Municipal Corporations (GPMC) Act 1949
    (`indiacode.nic.in/bitstream/123456789/4653/1/gpmcact.pdf`) — the statutory budget-head basis.

**Status of `23306`:** its name ("Penalty Recovered from Contractors") is confirmed
**de-facto** from AMC budget books (20-year slot stability); it is **not yet confirmed
against a de-jure manual**, because NMAM does not contain it and the Gujarat manual is
not online. See `../nmam/README.md` for the NMAM crosswalk (nearest concept: NMAM
`140-20` Penalties and Fines). This gap is the honest open item, not a resolved fact.

## Next

- Acquire the formal Gujarat Municipal Accounts Manual / GMFR (try GMFB directly / RTI,
  or the CAG LB-audit and GPMC-Act leads above) to confirm parent heads, accrual basis,
  and the full code list beyond `23xxx`.
- Extend to expense codes and other revenue groups (taxes `11xxx`–`17xxx`, octroi
  grant `181xx`, revenue grants).
