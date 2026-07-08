# All-India consumer price deflator (FY2005-06 to FY2024-25)

`cpi_combined_fy2005_06_to_latest.json` is a reusable annual-average price
index for converting nominal rupee figures between Indian fiscal years
(April-March). Consume it through `publicfinance.deflator`:

```python
from publicfinance.deflator import deflate

deflate(875, "2005-06", "2024-25")   # -> ~3011 (Rs cr, constant 2024-25 rupees)
```

Units pass through unchanged (crore in, crore out).

## What the index is

**Base: all-India CPI-Combined (Rural+Urban) General index, calendar year
2012 = 100.** Each value is the fiscal-year annual average ("average of
months", the same construction RBI publishes).

| Segment | Source series | How |
|---|---|---|
| FY2011-12 to FY2023-24 | CPI-Combined, base 2012=100 | Published annual averages, RBI *Handbook of Statistics on Indian Economy 2023-24*, Table 37 (original source NSO/MoSPI). 2011-12 and 2012-13 are NSO's official back-cast/linked values (the CPI Rural/Urban/Combined series begins January 2011). |
| FY2024-25 | CPI-Combined, base 2012=100 | Average of the 12 official monthly indices (MoSPI CPI data API); cross-checked against Economic Survey 2025-26 Statistical Appendix Table 4.3 (193, rounded). |
| FY2005-06 to FY2010-11 | CPI-IW General, base 2001=100 (Labour Bureau) | **CPI-Combined does not exist before January 2011.** The published CPI-IW annual averages are ratio-spliced onto the CPI-Combined series at the FY2011-12 overlap: `index = CPI-IW x (93.3 / 195)`, both overlap values from the same RBI HBS Table 37. |

The FY2005-06 CPI-IW value (117) is itself a linked value published by
RBI/Labour Bureau: the base-2001 CPI-IW series starts January 2006, and
2005-06 is derived from the base-1982 annual average (542) using the official
linking factor 4.63 (RBI HBS 2023-24, Table 37, Note 2; identical note in
Economic Survey 2016-17 Statistical Appendix Table 5.3).

## Citing this on a public page

> Real values computed with an all-India CPI-Combined deflator (base
> 2012=100), fiscal-year annual averages from RBI, Handbook of Statistics on
> Indian Economy 2023-24, Table 37 (NSO/MoSPI data); years before 2011-12 use
> the CPI-IW (base 2001=100, Labour Bureau) annual averages ratio-linked to
> CPI-Combined at the 2011-12 overlap.

## Verification status

Every value is cross-checked against at least two independent official
publications (per-year provenance in the JSON):

- RBI, Handbook of Statistics on Indian Economy 2023-24, Table 37, p. 71
  (retrieved 2026-07-08).
- Economic Survey 2016-17, Statistical Appendix Table 5.3, pp. A76-A77
  (indiabudget.gov.in) - confirms all CPI-IW values used for pre-2012.
- Economic Survey 2025-26, Statistical Appendix Table 4.3, pp. 88-89
  (indiabudget.gov.in) - confirms CPI-Combined averages through 2024-25.
- MoSPI CPI data API (base 2012, All India, Combined, General, monthly) -
  FY averages recomputed from the official monthly indices match the RBI
  published values to one decimal for every year 2011-12 to 2023-24.

Source documents are archived locally in `data/deflator_sources/` (gitignored).

## Known gaps - do not interpolate

- **FY2025-26** is excluded: the base-2012 series ends December 2025 (CPI was
  re-based to 2024=100 from January 2026), so no complete April-March year
  exists yet. Extend the series only with published values.
- Years before FY2005-06 are out of scope for this file.

## Updating for a new fiscal year

Append a new object to `years` in the JSON with all provenance fields
(`fy, index_value, base_year, source, source_table, source_url,
retrieval_date, method_note`), sourced from the next RBI HBS edition or the
official monthly indices (note the 2024=100 re-base: a published linking
factor to base 2012 will be needed from FY2025-26 onward). Run
`tests/test_deflator.py` after any change.
