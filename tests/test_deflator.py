import json

import pytest

from publicfinance.deflator import SERIES_PATH, coverage, deflate, index_for, load_series

REQUIRED_PROVENANCE_FIELDS = [
    "fy",
    "index_value",
    "base_year",
    "source",
    "source_table",
    "source_url",
    "retrieval_date",
    "method_note",
]


def test_series_spans_fy2005_06_to_fy2024_25_with_no_internal_gaps():
    years = coverage()
    assert years[0] == "2005-06"
    assert years[-1] == "2024-25"
    assert len(years) == 20
    starts = [int(fy[:4]) for fy in years]
    assert starts == list(range(2005, 2025))


def test_every_year_carries_full_provenance():
    payload = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
    assert len(payload["years"]) == 20
    for row in payload["years"]:
        for field in REQUIRED_PROVENANCE_FIELDS:
            assert row.get(field), f"{row.get('fy')} missing {field}"


def test_published_anchor_values_match_rbi_hbs_table_37():
    # RBI Handbook of Statistics on Indian Economy 2023-24, Table 37,
    # CPI-Combined annual averages (base CY2012=100).
    assert index_for("2011-12") == 93.3
    assert index_for("2012-13") == 102.5
    assert index_for("2023-24") == 184.1
    # FY2024-25: average of the 12 MoSPI monthly indices, cross-checked
    # against Economic Survey 2025-26 Table 4.3 (193 rounded).
    assert index_for("2024-25") == 192.6


def test_pre_2012_values_equal_cpi_iw_times_documented_splice_factor():
    payload = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
    factor = payload["splice"]["splice_factor"]
    assert factor == round(93.3 / 195, 6)
    pre_2012 = [row for row in payload["years"] if row["fy"] < "2011-12"]
    assert len(pre_2012) == 6
    for row in pre_2012:
        assert row["index_value"] == round(
            row["cpi_iw_general_base2001"] * 93.3 / 195, 2
        )


def test_fy2024_25_average_recomputes_from_stored_monthly_indices():
    payload = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
    row = next(r for r in payload["years"] if r["fy"] == "2024-25")
    months = row["monthly_indices_apr_to_mar"]
    assert len(months) == 12
    assert row["index_value"] == round(sum(months) / 12, 1)


def test_deflate_identity_and_round_trip():
    assert deflate(100.0, "2015-16", "2015-16") == 100.0
    assert deflate(deflate(875.0, "2005-06", "2024-25"), "2024-25", "2005-06") == pytest.approx(875.0)


def test_deflate_forwards_and_backwards():
    # Rs 100 of 2011-12 in 2012-13 rupees: 100 x 102.5 / 93.3
    assert deflate(100.0, "2011-12", "2012-13") == pytest.approx(100 * 102.5 / 93.3)
    assert deflate(100.0, "2012-13", "2011-12") == pytest.approx(100 * 93.3 / 102.5)


def test_uncovered_year_raises_with_coverage_message():
    with pytest.raises(ValueError, match="2005-06 to 2024-25"):
        index_for("2025-26")
    with pytest.raises(ValueError, match="2005-06 to 2024-25"):
        deflate(1.0, "2004-05", "2024-25")


def test_malformed_fiscal_year_raises():
    for bad in ["2015", "2015-2016", "2015-17", "FY2015-16", "2015/16"]:
        with pytest.raises(ValueError, match="YYYY-YY"):
            index_for(bad)


def test_load_series_reads_custom_path(tmp_path):
    path = tmp_path / "series.json"
    path.write_text(json.dumps({"years": [{"fy": "2020-21", "index_value": 155.3}]}))
    assert load_series(path) == {"2020-21": 155.3}
