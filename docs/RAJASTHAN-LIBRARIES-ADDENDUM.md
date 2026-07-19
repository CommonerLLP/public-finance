# Rajasthan public libraries addendum

Generated from the Rajasthan observed extraction layer on 2026-06-26.

This addendum covers Rajasthan budget reporting for public libraries in the
state budget books currently parsed by `public-finance`.

## Scope

Target codes:

| Code | Budget side | Rajasthan label observed |
|---|---|---|
| `2205-00-105` | Revenue expenditure | `सार्वजनिक पुस्तकालय` |
| `4202-04-105` | Capital expenditure | `सार्वजनिक पुस्तकालय` under `04-कला तथा संस्कृति` |

Important code rule:

`4202-104-105` is not the public-library code path. In Rajasthan `4202-04-104`
is Archives. Public libraries are under `4202-04-105`.

Unit rule:

Rajasthan tables are printed in `रूपये सहस्र में` - thousand rupees. The
observed JSON therefore uses `selected_amount_thousand_rupees`; crore values
below are computed as:

```text
crore = selected_amount_thousand_rupees / 10000
```

## Current parser-confirmed series

Source artifact:

`references/lmmha/lod/rajasthan_observed_time_series.json`

Only `surya_ocr_summary` rows are treated as observed values. Broad
`pdftotext` fallbacks such as major-head totals are blocked from final output.

| FY | Revenue `2205-00-105` crore | Capital `4202-04-105` crore | Total crore | Status |
|---|---:|---:|---:|---|
| 2013-14 | 7.9923 | 14.0000 | 21.9923 | revenue + capital found |
| 2014-15 | 9.8209 | 1.0020 | 10.8229 | revenue + capital found |
| 2015-16 | 9.7592 |  |  | capital missing |
| 2016-17 | 10.0553 |  |  | capital missing |
| 2017-18 |  |  |  | revenue + capital missing |
| 2018-19 | 12.6554 |  |  | capital missing |
| 2019-20 | 12.4160 |  |  | capital missing |
| 2020-21 | 13.6910 | 0.0001 | 13.6911 | revenue + capital found |
| 2021-22 | 13.3997 | 0.0001 | 13.3998 | revenue + capital found |
| 2022-23 | 12.4052 | 0.0001 | 12.4053 | revenue + capital found |
| 2023-24 | 18.8168 | 8.0000 | 26.8168 | revenue + capital found |
| 2024-25 | 18.2822 | 4.0570 | 22.3392 | revenue + capital found; modified-budget year |
| 2025-26 | 18.1620 | 2.4991 | 20.6611 | revenue + capital found |
| 2026-27 | 16.8010 | 2.4000 | 19.2010 | revenue + capital found |

## First-pass reading

Revenue public-library expenditure roughly doubles in nominal terms from
`7.9923 crore` in `2013-14` to `16.8010 crore` in `2026-27`. This is not a
real-terms doubling once inflation is considered; the allocation is better read
as broadly stagnant with a late spike.

The revenue series rises gradually through the 2010s, reaches a higher plateau
around `2023-24`, and then declines:

| FY | Revenue crore |
|---|---:|
| 2023-24 | 18.8168 |
| 2024-25 | 18.2822 |
| 2025-26 | 18.1620 |
| 2026-27 | 16.8010 |

Capital expenditure is uneven. The currently observed pattern is:

| Period | Pattern |
|---|---|
| `2013-14` | High capital provision: `14.0000 crore` |
| `2014-15` | Drops to `1.0020 crore` |
| `2020-21` to `2022-23` | Token provision of `0.0001 crore` each year |
| `2023-24` | Capital jump to `8.0000 crore` |
| `2024-25` to `2026-27` | Capital tapers from `4.0570 crore` to `2.4000 crore` |

## Reliability status

This is parser-confirmed, not yet publication-verified.

What is strong:

- Rows are extracted from page-specific Surya OCR artifacts.
- Final observed values require `surya_ocr_summary` status.
- The parser now blocks unsafe `line_hint` and `submajor_total` fallbacks.
- Unit labeling is corrected to thousand rupees.

What remains incomplete:

- Revenue `2017-18` is still missing.
- Capital `2015-16`, `2016-17`, `2017-18`, `2018-19`, and `2019-20` are still
  missing.
- Inflation adjustment should be redone with a logged CPI source before public
  citation.
- Figures should be cross-checked against the rendered PDF pages before any
  public claim.

## Methodological caveat: Rajasthan 2024-25

Treat `2024-25` as a split-year / modified-budget year. Rajasthan had a state
election in 2023, and the `2024-25` budget material includes modified-budget
context. Longitudinal interpretation should not silently treat `2024-25` as a
normal same-government budget year.

## Analytical use

This addendum supports the public-finance research question on whether states
report public-library expenditure under standard LMMHA codes.

For Rajasthan, current evidence shows:

- Revenue public-library expenditure is reported under `2205-00-105`.
- Capital public-library expenditure is reported under `4202-04-105`.
- Rajasthan does not appear to be hiding public libraries outside the standard
  public-library minor head for the observed rows; the harder problem is
  extraction reliability across older budget PDFs.

Next step:

Finish the missing-year page repair, then compare Rajasthan against Assam and
other states for standard-code compliance and real-terms allocation trends.
