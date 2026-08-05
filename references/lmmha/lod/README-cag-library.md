# CAG public-library four-head extracts (REQ-0003)

Public-library heads from CAG State Finance Accounts Vol-II (audited actuals,
Statements 15/16), extracted by `publicfinance/cag_finance_accounts.py` and
batch-built by `publicfinance/build_cag_library_national.py`.

The four heads (all amounts converted lakh → crore):

| head | column |
|---|---|
| 0202-04-102 Public Libraries (receipts) | `lib_receipts_cr` |
| 2205-00-105 Public Libraries (revenue expenditure) | `lib_rev_exp_cr` |
| 4202-04-105 Public Libraries (capital expenditure) | `lib_cap_exp_cr` |
| 6202-04-105 Public Libraries (loans) | `lib_loans_cr` |

Plus one head that is **not** a library head:

| head | column |
|---|---|
| 2205-00-198 Assistance to Gram Panchayats (revenue expenditure) | `gp_assist_cr` |
| 2205-00-196 Assistance to Zilla Parishads / District Level Panchayats | `zp_assist_cr` |

It is read because it is the route a State can use to fund village libraries
outside head 105. **It is not library spending by definition** — it is the
Art-and-Culture transfer to gram panchayats, whatever the State puts in it. Do
not add it to `lib_rev_exp_cr` without checking that State's own budget
documents first.

Karnataka 2023-24 is the case that put it here. Its entire 2205-198 provision is
a single scheme, "Gram Panchayat Libraries & Information Centre"
(`2205-00-198-1-02`, Demand 07 Rural Development and Panchayat Raj), so head 105
₹80.39 cr and head 198 ₹80.30 cr are both library money and sit adjacent in
Statement 15, within 0.1 per cent of each other. Reading 105 alone halves the
State's library spending; mistaking one for the other is easier still. The
The sibling head 2205-00-196 is read on the same terms — the same transfer one
tier up, to the district panchayat instead of the village one.

Across the 72 state-years in the panel, **only Karnataka uses either head under
2205**. For 2021-22 it reports all three: 105 ₹71.20 cr, 196 ₹2.65 cr, 198
₹72.51 cr — ₹146.36 cr against the ₹71.20 cr a single-head reading records.
Other States are empty because the heads are absent from their books, not
because the reader missed them: 2205's minor-head list was enumerated for
Kerala, Madhya Pradesh and Uttar Pradesh and none carries 196 or 198.

## Files

- `cag_library_four_head.csv` — the multi-year panel (2021-22 → 2024-25 where
  published), one row per state × FY, auto-extracted. `rev_self_validated` /
  `cap_self_validated` mark reads proved against the document's own printed
  increase/decrease per-cent column; `False` means the figure needs a human
  eyeball before public citation. Empty rows mean the volume could not be
  auto-read (scanned image or multi-part layout).
- `cag_library_national_2023-24_clean.csv` — the curated single-year national
  table for FY 2023-24: auto rows hand-verified, plus hand-read values for the
  three volumes automation cannot read (Tamil Nadu and Arunachal Pradesh are
  image-only scans; Karnataka ships Vol-II in parts). Provenance is labelled
  per row.

## Caveats

- Coverage: states absent from the panel (e.g. Goa, Rajasthan, West Bengal)
  had no Vol-II in the acquisition manifest at build time — absence is a
  coverage gap, not a nil.
- Capital figures repeated identically across adjacent years carry
  `cap_self_validated=False` and need review before citation.
- The earlier single Rajasthan Budget-Estimate row this file once held (BE,
  not CAG actuals) is preserved in git history and superseded by
  `rtr_library_vs_capital.csv`.

Regenerate: `python -m publicfinance.build_cag_library_national --cag-dir <commoner-probe cag dir> --out references/lmmha/lod/cag_library_four_head.csv`
