import pandas as pd

from budget_crawler.nha_oope import NHA_OOPE_COLUMNS, build_nha_oope_frame, write_nha_oope_csv


def test_build_nha_oope_frame_has_normalized_columns_and_units():
    source = pd.DataFrame(
        [
            {
                "Year": "2021-22",
                "GHE_Pct_GDP": 1.1,
                "OOPE_Pct_THE": 2.2,
                "GHE_Pct_THE": 3.3,
                "Per_Capita_GHE_INR": 1100,
                "Per_Capita_OOPE_INR": 2200,
            },
            {
                "Year": "2022-23",
                "GHE_Pct_GDP": 4.4,
                "OOPE_Pct_THE": 5.5,
                "GHE_Pct_THE": 6.6,
                "Per_Capita_GHE_INR": 3300,
                "Per_Capita_OOPE_INR": 4400,
            },
        ]
    )

    frame = build_nha_oope_frame(source)

    assert list(frame.columns) == NHA_OOPE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "fiscal_year"] == "2021-22"
    assert frame.loc[1, "fiscal_year"] == "2022-23"
    assert frame["ghe_pct_gdp"].dtype.kind == "f"
    assert frame["per_capita_oope_inr"].dtype.kind in {"i", "u"}


def test_write_nha_oope_csv_writes_expected_file(tmp_path):
    source_path = tmp_path / "source.csv"
    out_path = tmp_path / "nha_oope_timeseries.csv"
    pd.DataFrame(
        [
            {
                "Year": "2022-23",
                "GHE_Pct_GDP": 4.4,
                "OOPE_Pct_THE": 5.5,
                "GHE_Pct_THE": 6.6,
                "Per_Capita_GHE_INR": 3300,
                "Per_Capita_OOPE_INR": 4400,
            }
        ]
    ).to_csv(source_path, index=False)

    returned = write_nha_oope_csv(source_path, out_path)

    assert returned == out_path
    written = pd.read_csv(out_path)
    assert list(written.columns) == NHA_OOPE_COLUMNS
    assert written.loc[written["fiscal_year"] == "2022-23", "oope_pct_the"].item() == 5.5
