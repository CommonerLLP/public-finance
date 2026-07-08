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

## Chart of Accounts JSON

- `nmam_income_base.json` — the **income side** of the NMAM Chart of Accounts
  (Appendix 2, manual pages 4.16-4.21), extracted directly from the acquired PDF
  text on 2026-07-08. 73 records: all 9 income major heads (110 Tax Revenue · 120
  Assigned Revenues & Compensations · 130 Rental Income · 140 Fees & User Charges ·
  150 Sale & Hire · 160 Revenue Grants · 170 Income from Investments · 171 Interest
  Earned · 180 Other Income) with their mandatory minor heads. Schema fields:
  `code, head_name, parent_code, major_head, function_group, income_or_expense,
  accrual_basis, source, page, notes`. `function_group` is `null` for income heads
  because NMAM keeps FUNCTION as a separate code dimension (see `codification_rule`
  inside the JSON). The **expense** side (major heads 2xx-4xx) is a follow-on.

## REQ-0001 finding — Gujarat `23306` vs NMAM

- **`23306` does NOT exist in NMAM** (0 hits in the manual text). NMAM income codes
  are 3-level (`110`-`180`), never 5-digit. So Gujarat's `23306` is a **state-specific
  detailed head**, not a national NMAM code.
- NMAM's authoritative home for penalty-type revenue income is **minor head `140-20`
  "Penalties and Fines"** (under major head `140` Fees & User Charges). That is the
  nearest NMAM parent concept for Gujarat's `233` penalty group (`23305`/`23306`/`23320`).
- The only place NMAM's national CoA names contractors/suppliers on the income side is
  the illustrative remark under `180-11` "Lapsed Deposits" ("Contractors, Suppliers") —
  that is lapsed deposits, not penalties. NMAM codification para 4.21 also flags a naming
  trap: first-digit **`2`** = *Revenue Expenditure*; Gujarat books `23306` as *income*,
  confirming the AMC 5-digit scheme is the **BPMC/GPMC-Act budget classification, not the
  NMAM accrual chart**.
- Cross-tier crosswalk hints (NMAM ↔ Gujarat 5-digit) are recorded per-record in the
  `notes` fields of `nmam_income_base.json`.
- This base anchors the urban tier of the cross-tier crosswalk in
  `notes/fund_flow_map.md`.
