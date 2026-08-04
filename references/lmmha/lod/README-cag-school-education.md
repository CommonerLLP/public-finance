# CAG school-education head extracts (REQ-0047)

School-education heads from CAG State Finance Accounts Vol-II (audited actuals,
Statements 15/16), extracted by `publicfinance/cag_finance_accounts.py` and
batch-built by `publicfinance/build_cag_school_education.py`. Same acquisition
manifest, same reader and same self-validation as the library panel
(`README-cag-library.md`); only the head set differs.

The five heads (all amounts converted lakh → crore):

| head | column |
|---|---|
| 2202-01 Elementary Education (revenue expenditure) | `elem_rev_cr` |
| 2202-02 Secondary Education (revenue expenditure) | `sec_rev_cr` |
| 2202-80 General (revenue expenditure — the denominator) | `gen_rev_cr` |
| 4202-01-201 Elementary Education (capital outlay) | `elem_cap_cr` |
| 4202-01-202 Secondary Education (capital outlay) | `sec_cap_cr` |

## Files

- `cag_school_education.csv` — one row per state × FY (2021-22 → 2024-25 where
  published). Each head carries `<head>_self_validated` and
  `<head>_source_line` (the raw printed line the figure came from), plus the
  volume's `source_url`.

## How a figure is proved

A read is marked `self_validated` only when the document itself proves it, by
one of two independent tests:

1. **The printed per-cent.** CAG prints an increase/decrease per-cent for the
   row; the current-year value is the one that reproduces it against another
   value on the same row.
2. **The row's own arithmetic** — `State Fund Expenditure + Central Assistance
   = Total`. This is what carries rows whose per-cent is printed as a bare
   integer (`(+)136`), which the decimal-only amount rule cannot see. Assam and
   Uttar Pradesh print this way throughout.

`False` means the figure needs a human eyeball before public citation. A
sub-major total that neither test proves is recorded as **empty, not guessed**:
an unproved pick on those rows is a mis-picked column, not an approximation.

## Caveats

- **2202-01/02/80 are read as printed sub-major totals**, not as a sum of minor
  heads. Each sub-major runs a dozen minor heads over several pages, so the
  printed `Total - 01` line is the only place the sub-major figure exists.
- **Coverage**: Tamil Nadu and Arunachal Pradesh Vol-II are image-only scans and
  Karnataka ships Vol-II in parts — those rows are empty here (the library panel
  carries hand-reads for them; school heads have not been hand-read). Goa,
  Rajasthan and West Bengal are absent from the acquisition manifest — absence
  is a coverage gap, not a nil.
- **Head ≠ scheme.** Finance Accounts give the head. Samagra Shiksha, or any
  State's own school programme, is not separable here; that needs State Demands
  for Grants.
- **A State can book school or library capital outside the obvious head.**
  Verified case (2026-08-04): Karnataka's SASCI children's-libraries capital,
  ₹13,198.00 lakh in FY2023-24, sits under **4515-103 Rural Development**, not
  under 4202. A cross-state comparison built on one head therefore understates
  any State that routes the money elsewhere.

Regenerate: `python -m publicfinance.build_cag_school_education --cag-dir <commoner-probe cag dir> --out references/lmmha/lod/cag_school_education.csv`
