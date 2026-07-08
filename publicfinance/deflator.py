"""Nominal-to-real rupee conversion using an all-India consumer price deflator.

The series is FY (April-March) annual averages of the all-India CPI-Combined
General index, base calendar year 2012 = 100, covering FY2005-06 through
FY2024-25 (latest confirmed complete fiscal year):

- 2011-12 onward: published annual averages from RBI, Handbook of Statistics
  on Indian Economy 2023-24, Table 37 (original source NSO/MoSPI); 2024-25
  computed as the average of the 12 official MoSPI monthly indices and
  cross-checked against Economic Survey 2025-26 Statistical Appendix Table 4.3.
- 2005-06 to 2010-11: CPI-Combined does not exist before January 2011, so the
  published CPI-IW General annual averages (base 2001=100, Labour Bureau via
  the same RBI HBS table) are ratio-spliced onto the CPI-Combined series at
  the FY2011-12 overlap (factor 93.3/195).

Full per-year provenance and methodology live next to the data:
references/deflator/cpi_combined_fy2005_06_to_latest.json and
references/deflator/README.md.

Usage:
    from publicfinance.deflator import deflate
    deflate(875, "2005-06", "2024-25")  # Rs 875 cr of 2005-06 in 2024-25 rupees
"""

import json
import re
from pathlib import Path

SERIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "deflator"
    / "cpi_combined_fy2005_06_to_latest.json"
)

_FY_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")

_cache = None


def load_series(path=SERIES_PATH):
    """Return {fiscal_year: index_value} from the provenanced series file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {row["fy"]: float(row["index_value"]) for row in payload["years"]}


def _series():
    global _cache
    if _cache is None:
        _cache = load_series()
    return _cache


def coverage():
    """Return the covered fiscal years, sorted."""
    return sorted(_series())


def index_for(fiscal_year):
    """Return the deflator index (base CY2012=100) for a fiscal year."""
    match = _FY_PATTERN.match(fiscal_year)
    if not match or int(match.group(2)) != (int(match.group(1)) + 1) % 100:
        raise ValueError(
            f"Fiscal year must be 'YYYY-YY' (April-March, e.g. '2023-24'), got {fiscal_year!r}"
        )
    series = _series()
    if fiscal_year not in series:
        years = coverage()
        raise ValueError(
            f"No confirmed deflator value for {fiscal_year}: series covers "
            f"{years[0]} to {years[-1]} (FY2025-26 is incomplete at source and "
            "deliberately excluded rather than estimated)"
        )
    return series[fiscal_year]


def deflate(amount, from_year, to_year):
    """Convert a nominal rupee amount of fiscal year `from_year` into constant
    rupees of fiscal year `to_year`.

    Units pass through unchanged (crore in, crore out). `to_year` earlier than
    `from_year` is valid and deflates backwards.
    """
    return amount * index_for(to_year) / index_for(from_year)
