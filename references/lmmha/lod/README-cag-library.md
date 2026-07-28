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
