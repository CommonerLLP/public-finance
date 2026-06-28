# NMAM — National Municipal Accounts Manual (urban local body, national base)

The **National Municipal Accounts Manual** is the Government of India model chart of
accounts for urban local bodies — issued by the Ministry of Urban Development (now
MoHUA) with the Office of the C&AG, 2004. States "may develop state-level manuals
based on this" (e.g. Gujarat → `references/gmam/`), so adoption is partial and
divergent.

**It is a different paradigm from the LMMHA** (`references/lmmha/`): NMAM is
**accrual, double-entry**, with a **3-level code** (Major Head → Minor Head →
Detailed Head, e.g. `140-20-(a)` = Fees & User Charges → Penalties & Fines).
The LMMHA is cash, single-entry. That is why a 5-digit Gujarat municipal code like
`23306` has **no equivalent in NMAM** and zero hits in the national manual — the
state assigns its own codes within (or beside) the NMAM structure.

NMAM income major heads: `110` Tax Revenue · `120` Assigned Revenues &
Compensation · `130` Rental Income · `140` Fees & User Charges · `150` Sale & Hire
Charges · `160` Revenue Grants/Contributions/Subsidies · `171` Interest Earned ·
`180` Other Income.

## Provenance

- **File:** `source/nmam_goi_2004.pdf` (gitignored — large binary, local only).
- **Source URL:** https://sfcassam.nic.in/13thFC/13thFC-ManualGOIULB.pdf
  (Assam State Finance Commission 13th-FC mirror of the GoI manual; `.nic.in` host).
- **Retrieved:** 2026-06-27.
- **Size / hash:** 9,181,248 bytes · SHA-256
  `9fbd3fde6d893911447df052328eac681b5c86a8f978907fd7f91c78a7def847`.
- **Pages:** 722 (A4); PDF created Jan 2005 (consistent with the Nov 2004 manual).
- Logged in `memory/verified_facts.md` (`NMAM-ACQ-001`).

## Status / next

- Acquired + text-extracted (`source/nmam_goi_2004.txt`). The structured **Chart of
  Accounts JSON** (income + expense heads from Chapter 4 / Appendix 2) is a
  follow-on extraction, not yet built.
- This base anchors the urban tier of the cross-tier crosswalk in
  `notes/fund_flow_map.md`.
