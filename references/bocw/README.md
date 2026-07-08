# BOCW Welfare Board finance — one file per state board

The cess-collected vs spent vs unspent-balance series for the **Building and Other
Construction Workers (BOCW) Welfare Boards** — cess-funded statutory bodies under the
BOCW Act 1996 + BOCW Welfare Cess Act 1996 (a 1% cess on construction cost). The
recurring public-interest finding is a large **unspent balance** against cess collected:
money levied in construction workers' name that never reaches them.

Filed for REQ-0002 (sevent4 → public-finance). sevent4 owns the city interpretation
(worker population, municipal-contract joins, gendered barriers); public-finance owns
this reusable board-finance series. One normalised file per board:
`references/bocw/<code>.json`.

## Schema (`bocw-board-v1`)

Per-year row fields (₹ crore, units explicit in every column name):

- `cess_collected_cr` — cess deposited during the FY
- `grant_released_to_board_cr` — released by the State to the Board that FY (Gujarat-specific layer)
- `closing_balance_with_state_govt_cr` — cess pooled with the State, not yet released
- `board_opening_balance_cr` / `board_closing_balance_cr` — grant balance held by the Board
- `board_welfare_expenditure_cr`, `board_admin_expenditure_cr`, `expenditure_cr` (total)
- `total_unspent_balance_cr` — the headline gap (with-State + with-Board)
- `other_income_cr` — interest/misc (null where not disclosed)
- `active_registrations`, `registered_workers`, `beneficiaries`
- `notes` — provenance / caveats per row

Aggregate/multi-year buckets are marked `"fy_bucket": true`.

## Gujarat — first state (proof city: Ahmedabad)

Source of truth: **CAG Report No. 02 of 2025**, *Performance Audit on Welfare of Building
and Other Construction Workers, Government of Gujarat*, period ended March 2022 (updated
to 2022-23). This is the highest-authority source — CAG specifically audited
cess-collected-vs-spent and idle balances.

Headline (as of March 2023, 2006-07 to 2022-23):

| Measure | ₹ crore | share |
|---|---|---|
| Total cess collected | 4,787.60 | 100% |
| Released to the Board by the State | 2,544.81 | 53% |
| **Lying UNRELEASED with the State Govt** | **2,242.79** | **47%** |
| Actually spent by the Board (welfare 782.03 + admin 26.46) | 808.49 | 17% of collected |
| **Released-but-UNSPENT with the Board** | **1,736.32** | 36% of collected |
| **Total unspent balance** | **3,979.11** | **83%** |

**Gujarat's structural quirk:** the State never constituted the statutory BOC Workers'
Welfare Fund (BOCW Act s.24). With no Fund, cess sits in the general Government Account
and the State releases only partial grants to the Board. So the unspent balance has two
layers — cess withheld by the State (47%) *and* grant unspent by the Board (36%). CAG
flagged both the non-constitution of the Fund and the non-transfer of cess as statutory
violations. Because the pool is in the Government Account, interest accrues to the State,
not the Board, and `other_income_cr` is null.

Governance (as of March 2022): 72% of the Board's regular posts vacant (13 of 18);
42% of DISH inspector posts vacant (10 of 24, incl. 100% of Senior Inspector posts);
Member Secretary held only as additional charge since Oct 2021; State Advisory Committee
not constituted since 2011; 13 of 31 welfare schemes (42%) closed or on hold; Old Age
Pension on hold since May 2019. Active registered workers collapsed from 4,67,682
(Mar 2018) to 1,56,955 (Mar 2022) as renewals failed.

### Verification

- **Aggregates** (4,787.60 collected / 2,242.79 with State / 808.49 spent) meet the
  two-source rule: CAG report (primary) + two press reports of the tabled report
  (The Wire, DevDiscourse) corroborate.
- **Year-wise splits** are single-sourced to the CAG report but internally
  arithmetic-reconciled across CAG Tables 4.2, 6.1, 3.4 and Charts 4.2, 3.2 — every row
  foots to the published totals (checked in-turn 2026-07-08).
- Not disclosed / not extracted: interest income; beneficiaries-by-scheme as per-year
  rows; FY2022-23 active registrations.

Raw source PDFs live under `references/bocw/source/` (gitignored).

## Planned coverage (REQ-0002, 5 states)

| Board | State/UT | sevent4 city | status |
|---|---|---|---|
| Gujarat BOCW Welfare Board | Gujarat | Ahmedabad | **done — CAG Report 02/2025** |
| Karnataka BOCW Welfare Board | Karnataka | Bengaluru | pending |
| Tamil Nadu Construction Workers Welfare Board | Tamil Nadu | Chennai | pending |
| Delhi BOCW Welfare Board | Delhi | Delhi | pending |
| West Bengal BOCW Welfare Board | West Bengal | Kolkata | pending |

Grows one acquisition at a time. Partial coverage is honest — a board-year appears only
when a primary source gives it cleanly. National context: Ministry of Labour told
Parliament ~₹1,12,331 cr cess collected nationally against ~₹64,194 cr spent as of
March 2024 (to be captured per-state as the series extends).
