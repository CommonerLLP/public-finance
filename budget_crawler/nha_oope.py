"""Normalize National Health Accounts OOPE/GHE tabular extracts."""

from pathlib import Path

import pandas as pd

NHA_OOPE_COLUMNS = [
    "fiscal_year",
    "ghe_pct_gdp",
    "oope_pct_the",
    "ghe_pct_the",
    "per_capita_ghe_inr",
    "per_capita_oope_inr",
]

SOURCE_COLUMNS = {
    "Year": "fiscal_year",
    "GHE_Pct_GDP": "ghe_pct_gdp",
    "OOPE_Pct_THE": "oope_pct_the",
    "GHE_Pct_THE": "ghe_pct_the",
    "Per_Capita_GHE_INR": "per_capita_ghe_inr",
    "Per_Capita_OOPE_INR": "per_capita_oope_inr",
}


def build_nha_oope_frame(source):
    frame = source.rename(columns=SOURCE_COLUMNS)
    missing = [column for column in NHA_OOPE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing NHA OOPE columns: {', '.join(missing)}")

    frame = frame[NHA_OOPE_COLUMNS].copy()
    for column in NHA_OOPE_COLUMNS[1:]:
        frame[column] = pd.to_numeric(frame[column])
    return frame


def write_nha_oope_csv(source_path, out_path):
    source_path = Path(source_path)
    out_path = Path(out_path)
    frame = build_nha_oope_frame(pd.read_csv(source_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    return out_path
