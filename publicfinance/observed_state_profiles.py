"""State-specific observed-budget parser memory for LMMHA workflows.

Generated artifacts from this module capture the stable extraction windows,
units, and parsing hints for state budget books so future work can start from
structured parser memory instead of rediscovering page ranges by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from publicfinance.budget_document_profiles import (
    BudgetDocumentProfile,
    PdfWindow,
    document_profiles_for_state,
)

REPO = Path(__file__).resolve().parents[1]
MEMORY_DIR = REPO / "references" / "lmmha" / "lod" / "observed_parser_memory"


@dataclass(frozen=True)
class StateObservedProfile:
    state: str
    fy: str
    layout: str
    currency_unit: str
    parsing_rules: tuple[str, ...]
    documents: tuple[BudgetDocumentProfile, ...]
    windows: tuple[PdfWindow, ...]
    notes: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return f"{self.state.lower()}_{self.fy.replace('-', '_')}"


def _rajasthan_fy_labels(start_year: int = 2013, end_year: int = 2026) -> tuple[str, ...]:
    return tuple(f"{year}-{str(year + 1)[-2:]}" for year in range(start_year, end_year + 1))


RAJASTHAN_FYS = _rajasthan_fy_labels()


def _rajasthan_profile(fy: str, *, split_year: bool = False) -> StateObservedProfile:
    documents = tuple(document_profiles_for_state("Rajasthan", fy))
    layout = "state budget split across vote-on-account and modified-budget phases; pdftotext -layout preserves numeric columns" if split_year else "state budget split across service books; pdftotext -layout preserves numeric columns"
    parsing_rules = (
        "Prefer code hierarchy and page windows over Hindi label matching.",
        "Treat detailed-book sub-major totals as valid anchors when the target code family is isolated under one sub-major.",
        "Keep loan/debt series separate from revenue/capital service heads until minor-head mapping is verified.",
    )
    notes = (
        "Rajasthan FY 2024-25 contains both vote-on-account and modified-budget material; treat it as a split-year profile.",
        "The public-finance parser layer should own these state profiles, not viz scripts.",
    ) if split_year else (
        "Rajasthan budget PDFs are text-bearing; this profile caches extraction windows so future parser work does not have to rediscover them.",
        "The public-finance parser layer should own these state profiles, not viz scripts.",
    )
    if split_year:
        parsing_rules = (
            "Treat Rajasthan FY 2024-25 as a split fiscal year because the election cycle divides vote-on-account and modified-budget material.",
            *parsing_rules,
        )
    return StateObservedProfile(
        state="Rajasthan",
        fy=fy,
        layout=layout,
        currency_unit="lakh",
        parsing_rules=parsing_rules,
        documents=documents,
        windows=tuple(window for document in documents for window in document.windows),
        notes=notes,
    )


RAJASTHAN_PROFILES = {
    fy: _rajasthan_profile(fy, split_year=(fy == "2024-25")) for fy in RAJASTHAN_FYS
}

RAJASTHAN_2013_14 = RAJASTHAN_PROFILES["2013-14"]
RAJASTHAN_2014_15 = RAJASTHAN_PROFILES["2014-15"]
RAJASTHAN_2015_16 = RAJASTHAN_PROFILES["2015-16"]
RAJASTHAN_2016_17 = RAJASTHAN_PROFILES["2016-17"]
RAJASTHAN_2017_18 = RAJASTHAN_PROFILES["2017-18"]
RAJASTHAN_2018_19 = RAJASTHAN_PROFILES["2018-19"]
RAJASTHAN_2019_20 = RAJASTHAN_PROFILES["2019-20"]
RAJASTHAN_2020_21 = RAJASTHAN_PROFILES["2020-21"]
RAJASTHAN_2021_22 = RAJASTHAN_PROFILES["2021-22"]
RAJASTHAN_2022_23 = RAJASTHAN_PROFILES["2022-23"]
RAJASTHAN_2023_24 = RAJASTHAN_PROFILES["2023-24"]
RAJASTHAN_2024_25 = RAJASTHAN_PROFILES["2024-25"]
RAJASTHAN_2025_26 = RAJASTHAN_PROFILES["2025-26"]
RAJASTHAN_2026_27 = RAJASTHAN_PROFILES["2026-27"]

PROFILES = {(profile.state.lower(), profile.fy): profile for profile in RAJASTHAN_PROFILES.values()}


def profile_for(state: str, fy: str) -> StateObservedProfile:
    try:
        return PROFILES[(state.lower(), fy)]
    except KeyError as exc:
        raise KeyError(f"No observed-budget profile for {state} {fy}") from exc


def _extract_window_text(pdf_path: Path, page_start: int, page_end: int) -> str:
    proc = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-f",
            str(page_start),
            "-l",
            str(page_end),
            str(pdf_path),
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return proc.stdout


def _iter_window_rows(profile: StateObservedProfile) -> Iterable[dict[str, object]]:
    for document in profile.documents:
        for window in document.windows:
            yield {
                "state": profile.state,
                "fy": profile.fy,
                "document_type": document.document_type,
                "document_family": document.document_family,
                "document_source": window.source_relpath,
                "page_start": window.page_start,
                "page_end": window.page_end,
                "code_family": window.code_family,
                "target_codes": window.target_codes,
                "unit": window.unit,
                "parser_hint": window.parser_hint,
                "can_extract_be_re": document.can_extract_be_re,
                "can_extract_codes": document.can_extract_codes,
                "can_extract_scheme_info": document.can_extract_scheme_info,
                "window_parser_strategy": document.parser.strategy,
                "window_unit": document.parser.unit,
                "text": _extract_window_text(
                    REPO / window.source_relpath, window.page_start, window.page_end
                ),
            }


def _default_output_path(profile: StateObservedProfile, suffix: str) -> Path:
    return MEMORY_DIR / f"{profile.slug}.{suffix}"


def _write_window_rows_as_jsonl(profile: StateObservedProfile, out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as handle:
        for row in _iter_window_rows(profile):
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def _write_window_rows_as_csv(profile: StateObservedProfile, out_path: Path) -> None:
    rows = list(_iter_window_rows(profile))
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return

    fieldnames = tuple(sorted({key for row in rows for key in row}))
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cleaned = dict(row)
            cleaned["target_codes"] = json.dumps(cleaned["target_codes"], ensure_ascii=False)
            writer.writerow(cleaned)


def materialize_parser_memory(
    profile: StateObservedProfile,
    *,
    refresh: bool = False,
    out_path: Path | None = None,
    out_jsonl_path: Path | None = None,
    out_csv_path: Path | None = None,
) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    destination = out_path or (MEMORY_DIR / f"{profile.slug}.json")
    if destination.exists() and not refresh:
        return destination

    windows = []
    for window in profile.windows:
        pdf_path = REPO / window.source_relpath
        windows.append(
            {
                **asdict(window),
                "text": _extract_window_text(pdf_path, window.page_start, window.page_end),
            }
        )

    payload = {
        "generated_by": "publicfinance/observed_state_profiles.py",
        "do_not_hand_edit": True,
        "profile": {
            "state": profile.state,
            "fy": profile.fy,
            "layout": profile.layout,
            "currency_unit": profile.currency_unit,
            "parsing_rules": list(profile.parsing_rules),
            "notes": list(profile.notes),
        },
        "documents": [asdict(document) for document in profile.documents],
        "windows": windows,
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if out_jsonl_path is not None:
        _write_window_rows_as_jsonl(profile, out_jsonl_path)
    if out_csv_path is not None:
        _write_window_rows_as_csv(profile, out_csv_path)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize observed-budget parser memory for a state profile.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--fy", required=True)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--jsonl", action="store_true", help="Write window-level rows to .jsonl")
    parser.add_argument(
        "--jsonl-path",
        default=None,
        help="Output path for JSONL rows (defaults to <state>_<fy>.jsonl)",
    )
    parser.add_argument("--csv", action="store_true", help="Write window-level rows to .csv")
    parser.add_argument(
        "--csv-path",
        default=None,
        help="Output path for CSV rows (defaults to <state>_<fy>.csv)",
    )
    args = parser.parse_args()

    profile = profile_for(args.state, args.fy)
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else (_default_output_path(profile, "jsonl") if args.jsonl else None)
    csv_path = Path(args.csv_path) if args.csv_path else (_default_output_path(profile, "csv") if args.csv else None)

    path = materialize_parser_memory(
        profile,
        refresh=args.refresh,
        out_jsonl_path=jsonl_path,
        out_csv_path=csv_path,
    )
    print(path.relative_to(REPO))


if __name__ == "__main__":
    main()
