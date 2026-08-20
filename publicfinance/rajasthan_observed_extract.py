"""Extract Rajasthan observed LMMHA rows from parser-memory windows.

The extractor is intentionally conservative: it reports whether a match was
found exactly, by sub-major total, or not at all, and it captures the raw
amounts for manual review.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup

from publicfinance import observed_state_profiles as state_profiles


REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_relative(path: Path | str) -> str:
    """A path as this repo records it: relative to the repo root.

    Emitted records are tracked and public. An absolute path names the machine
    that produced them, which the org leak check forbids and which makes the
    record unreadable on any other machine. A path outside the repo is returned
    unchanged, because silently truncating it would be worse than showing it.

    The comparison is lexical, and deliberately so. ``resolve()`` follows
    symlinks, and ``data/`` here is a symlink to an external volume, so a
    resolved path lands outside the repo root, fails the relative test, and is
    emitted absolute — re-introducing the leak and adding the volume name to it.
    """
    path = Path(path)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


TARGETS = (
    "2202-00-105",
    "2205-00-105",
    "4202-04-105",
)
TARGET_VARIANTS = {
    "2202-00-105": ("2202-00-105",),
    "2205-00-105": ("2205-00-105",),
    "4202-04-105": ("4202-04-105",),
}
OUT_DIR = REPO_ROOT / "references" / "lmmha" / "lod"


DEVANAGARI_TO_ASCII = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}


_NON_DIGIT_NORMALIZER = re.compile(r"[^0-9,\-\.()\s\w]", re.UNICODE)
_CODE_TOKEN = re.compile(r"(?:\d{4}(?:[-\s–—-]\d{2})?(?:[-\s–—-]\d{3})?)")
_FULL_CODE_RE = re.compile(r"^(\d{4})[-\s–—-](\d{2})[-\s–—-](\d{3})$")
_SUBMAJOR_RE = re.compile(r"^\(?([0-9]{2})\)?$")
_HEADER_RE = re.compile(r"^\d{4}$")
_AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{2,3})+")
_PLAIN_AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?")
_TOTAL_MARKER = re.compile(r"योग|total|Total|grand", re.IGNORECASE)
_CODE_RE = re.compile(r"\b(?P<major>22\d{2}|42\d{2})[^0-9]{0,6}(?P<sub>\d{2})[^0-9]{0,6}(?P<minor>\d{3})\b")
_MAJOR_TOTAL_MARKER_RE = re.compile(r"[-–—]\s*[^0-9]{0,12}(?P<major>22\d{2}|42\d{2})\s*[-–—]")
_SUBMAJOR_HEADING_RE = re.compile(
    r"^\s*(?:\(\s*(?P<sub_a>[0-9]{1,2})\s*\)|(?P<sub_b>[0-9]{1,2}))\s*[-–—]\s*[\u0900-\u097F]"
)
_TITLE_KEYWORD_RE = re.compile(r"पुस्तकालय|public libraries|sarvajanik\s+pustakalay|पत्र\s+पत्रिका", re.IGNORECASE)
_PUBLIC_LIBRARY_KEYWORD_RE = re.compile(r"sarvajanik\s+pustakalay|public libraries|sarvajanik\s+library", re.IGNORECASE)
_CAPITAL_LIBRARY_KEYWORD_RE = re.compile(r"स\s*वज\s*क\s*तक|पुस्तकालय|sarvajanik\s+pustakalay", re.IGNORECASE)
_SURYA_PUBLIC_LIBRARY_LABEL_RE = re.compile(
    r"सार्वजनिक\s+पुस्तकालय|सारजनिक\s+पुस्तकालय|sarvajanik\s+pustakalay|public libraries",
    re.IGNORECASE,
)
_SURYA_MINOR_105_TOTAL_RE = re.compile(
    r"लघु\s*शीर्ष\s*[-–—]?\s*105\s*योग|minor\s+head\s*[-–—]?\s*105\s*total",
    re.IGNORECASE,
)
_SCHOOL_LIBRARY_KEYWORD_RE = re.compile(
    r"(?:school|university|vidyalay|vishvavidyalay|shiksha)[^\n]{0,30}(?:library|pustakalay)",
    re.IGNORECASE,
)
_LIBRARY_ROW_HINT_RE = re.compile(
    r"(?:\b31\b|(?:\(?\s*)105(?:\s*\)?))\s*[-–—]\s*.*पुस्तकालय",
    re.IGNORECASE,
)
_LIBRARY_ROW_NUMBER_RE = re.compile(r"\b31\s*[-–—]")
_TITLELESS_LIBRARY_FALLBACK_RE = re.compile(r"(?:\b31\b\s*[-–—])|(?:\(?\s*105\s*\)?\s*[-–—])", re.IGNORECASE)
_SURYA_SUMMARY_MAJORS = {"2205": "2205-00-105", "4202": "4202-04-105"}
_MATCH_PRIORITY = {
    "not_found": 0,
    "extraction_error": 0,
    "submajor_total": 1,
    "line_hint_fuzzy": 2,
    "line_hint": 2,
    "line_hint_keyword": 3,
    "surya_ocr_summary": 4,
    "exact_code": 5,
}
_FINAL_OBSERVED_STATUSES = {"surya_ocr_summary", "exact_code"}


def _normalize_to_plain_ascii(text: str) -> str:
    out = []
    for ch in text:
        if ch in DEVANAGARI_TO_ASCII:
            out.append(DEVANAGARI_TO_ASCII[ch])
        else:
            out.append(ch)
    text = "".join(out).replace("−", "-").replace("–", "-").replace("—", "-")
    return text


def _infer_library_target(current_major: str | None, targets: dict[str, dict[str, str]]) -> str | None:
    if current_major is None:
        return None
    candidates = [
        code for code, meta in targets.items() if meta["major"] == current_major and meta["minor"] == "105"
    ]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _is_library_row(normalized: str, current_major: str | None) -> bool:
    if current_major not in {"2202", "2205", "4202"}:
        return False
    if _TITLE_KEYWORD_RE.search(normalized):
        return True
    if _LIBRARY_ROW_HINT_RE.search(normalized):
        return True
    if _LIBRARY_ROW_NUMBER_RE.search(normalized):
        return True
    return bool(re.search(r"\b105\b", normalized))


def _infer_library_target_from_keyword(
    normalized: str,
    current_major: str | None,
    targets: dict[str, dict[str, str]],
) -> str | None:
    if _SCHOOL_LIBRARY_KEYWORD_RE.search(normalized):
        return "2202-00-105" if "2202-00-105" in targets else None
    if current_major == "4202" and _CAPITAL_LIBRARY_KEYWORD_RE.search(normalized):
        return "4202-04-105" if "4202-04-105" in targets else None
    if _TITLE_KEYWORD_RE.search(normalized) or _PUBLIC_LIBRARY_KEYWORD_RE.search(normalized):
        return "2205-00-105" if "2205-00-105" in targets else None
    return None


def _extract_amount_candidates(text: str, *, strict_only: bool = False) -> list[float]:
    amounts = [amount_to_float(raw) for raw in _AMOUNT_RE.findall(text)]
    amounts = [amount for amount in amounts if amount is not None]
    if amounts or strict_only:
        return amounts

    fallback = []
    for match in _PLAIN_AMOUNT_RE.finditer(text):
        raw = match.group(0)
        start, end = match.span()
        left = text[start - 1] if start > 0 else ""
        right = text[end] if end < len(text) else ""
        if left in {",", "-", "–", "—", "−"} or right in {",", "-", "–", "—", "−"}:
            continue
        amount = amount_to_float(raw)
        if amount is not None:
            fallback.append(amount)
    return fallback


@dataclass
class ExtractMatch:
    code: str
    match_type: str
    raw_line: str
    amount_candidates: list[float]
    selected_amount: float | None


def normalize_text(text: str) -> str:
    out = []
    for ch in text:
        if ord(ch) >= 128:
            out.append(ch)
        else:
            out.append(ch)
    text = "".join(out)
    return _normalize_to_plain_ascii(text)


def amount_to_float(token: str) -> float | None:
    token = token.replace("\u200c", "")
    if token in {"..", "", "-", "—", "–"}:
        return None
    token = token.replace(",", "")
    if not token.replace(".", "", 1).isdigit():
        return None
    try:
        return float(token)
    except ValueError:
        return None


def parse_target_line(
    line: str,
    current_major: str | None,
    current_submajor: str | None,
    targets: dict[str, dict[str, str]],
    canonical_map: dict[str, str],
) -> tuple[ExtractMatch | None, str | None, str | None]:
    raw_line = line.rstrip("\n")
    normalized = normalize_text(raw_line)
    # preserve only tokens where OCR has turned code separators into simple punctuation
    tokens = re.split(r"\s+", _NON_DIGIT_NORMALIZER.sub(" ", normalized).strip())
    if not tokens:
        return None, current_major, current_submajor

    # exact code with OCR-friendly separators, e.g. 4202-04-105 / 4202 04 105.
    for match in _CODE_RE.finditer(normalized):
        major = match.group("major")
        if major not in {meta["major"] for meta in targets.values()}:
            continue
        target_full = f"{match.group('major')}-{match.group('sub')}-{match.group('minor')}"
        current_major = major
        if target_full in canonical_map:
            amounts = _extract_amount_candidates(normalized, strict_only=True)
            return (
                ExtractMatch(
                    code=target_full,
                    match_type="exact_code",
                    raw_line=raw_line,
                    amount_candidates=amounts,
                    selected_amount=amounts[-1] if amounts else None,
                ),
                current_major,
                current_submajor,
            )

    keyword_target = _infer_library_target_from_keyword(normalized, current_major, targets)
    if keyword_target is not None:
        amounts = _extract_amount_candidates(normalized)
        if amounts:
            return (
                ExtractMatch(
                    code=keyword_target,
                    match_type="line_hint_keyword",
                    raw_line=raw_line,
                    amount_candidates=amounts,
                    selected_amount=amounts[-1],
                ),
                current_major,
                current_submajor,
            )

    # Some Rajasthan OCR lines drop target code entirely and only keep a known
    # library row shape. The key invariant is the repeated `31-` row inside the
    # 2205/4202 section, even when the literal library label is mutilated.
    if _is_library_row(normalized, current_major):
        target = _infer_library_target(current_major, targets)
        if target is not None:
            amounts = _extract_amount_candidates(normalized)
            if amounts:
                return (
                    ExtractMatch(
                        code=target,
                        match_type="line_hint",
                        raw_line=raw_line,
                        amount_candidates=amounts,
                        selected_amount=amounts[-1],
                    ),
                    current_major,
                    current_submajor,
                )

    # OCR sometimes drops key words around the 31-line for public libraries.
    if current_major and _TITLELESS_LIBRARY_FALLBACK_RE.search(normalized):
        target = _infer_library_target(current_major, targets)
        if target is not None:
            amounts = _extract_amount_candidates(normalized)
            if amounts:
                return (
                    ExtractMatch(
                        code=target,
                        match_type="line_hint_fuzzy",
                        raw_line=raw_line,
                        amount_candidates=amounts,
                        selected_amount=amounts[-1],
                    ),
                    current_major,
                    current_submajor,
                )

    for token in tokens:
        major_match = re.sub(r"[^0-9]", "", token)
        if major_match in {meta["major"] for meta in targets.values()}:
            current_major = major_match
            break

    for token in tokens:
        sub_match = _SUBMAJOR_RE.match(token)
        if sub_match and current_major:
            target = next(
                (v for v in targets.values() if v["major"] == current_major and v["submajor"] == sub_match.group(1)),
                None,
            )
            if target:
                amounts = [
                    amount for raw in _AMOUNT_RE.findall(normalized) if (amount := amount_to_float(raw)) is not None
                ]
                if len(amounts) >= 1:
                    return (
                        ExtractMatch(
                            code=f"{target['major']}-{target['submajor']}-???",
                            match_type="submajor_total",
                            raw_line=raw_line,
                            amount_candidates=amounts,
                            selected_amount=amounts[-1],
                        ),
                        current_major,
                        current_submajor,
                    )
            break

    # Fallback to sub-major totals when a major marker appears on the line and context is set.
    total_marker_match = _MAJOR_TOTAL_MARKER_RE.search(normalized)
    if current_major and current_submajor and total_marker_match:
        marker_major = total_marker_match.group("major")
        if marker_major == current_major:
            target = next(
                (
                    v
                    for v in targets.values()
                    if v["major"] == current_major and v["submajor"] == current_submajor
                ),
                None,
            )
            if target:
                amounts = _extract_amount_candidates(normalized)
                if amounts:
                    return (
                        ExtractMatch(
                            code=f"{target['major']}-{target['submajor']}-???",
                            match_type="submajor_total",
                            raw_line=raw_line,
                            amount_candidates=amounts,
                            selected_amount=amounts[-1],
                        ),
                        current_major,
                        current_submajor,
                    )

    # OCR often destroys sub-major separators. Accept both `xx-...` and `(xx)-...` forms.
    if current_major:
        sub_match = _SUBMAJOR_HEADING_RE.search(normalized)
        if sub_match:
            candidate = (sub_match.group("sub_a") or sub_match.group("sub_b")).zfill(2)
            current_submajor = candidate

    return None, current_major, current_submajor


def _target_for_match(match: ExtractMatch, canonical_map: dict[str, str]) -> str | None:
    if match.code in canonical_map:
        return canonical_map[match.code]

    major, sub = match.code.split("-")[:2]
    for candidate in TARGETS:
        if candidate.startswith(f"{major}-{sub}-"):
            return candidate
    return None


def _html_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def _surya_table_rows(html: str) -> Iterable[list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if cells:
            yield cells


def _extract_surya_cell_amounts(cells: list[str]) -> list[float]:
    amounts = []
    for cell in cells:
        for raw in _AMOUNT_RE.findall(cell):
            amount = amount_to_float(raw)
            if amount is not None:
                amounts.append(amount)
        normalized = normalize_text(cell).strip()
        if _PLAIN_AMOUNT_RE.fullmatch(normalized):
            amount = amount_to_float(normalized)
            if amount is not None:
                amounts.append(amount)
    return amounts


def _select_surya_amount(cells: list[str], amounts: list[float]) -> float | None:
    comma_amounts = []
    for cell in cells:
        for raw in _AMOUNT_RE.findall(cell):
            amount = amount_to_float(raw)
            if amount is not None:
                comma_amounts.append(amount)
    if comma_amounts:
        return comma_amounts[-1]
    if amounts:
        return amounts[-1]
    return None


def _extract_surya_summary_matches_from_results(results_path: Path) -> list[dict]:
    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    path_text = str(results_path).lower()
    default_major = None
    if "volume 3a" in path_text or "vol3a" in path_text:
        default_major = "4202"
    elif "volume 2c" in path_text or "vol2c" in path_text:
        default_major = "2205"

    matches: list[dict] = []
    for pages in payload.values():
        if not isinstance(pages, list):
            continue
        pending_public_library_total = False
        for page in pages:
            blocks = page.get("blocks", []) if isinstance(page, dict) else []
            current_major: str | None = default_major
            for block in blocks:
                html = block.get("html", "") if isinstance(block, dict) else ""
                label = block.get("label", "") if isinstance(block, dict) else ""
                text = _html_text(html)
                major_match = re.search(r"\b(2205|4202)\b", text)
                if major_match:
                    current_major = major_match.group(1)
                if label != "Table" or current_major not in _SURYA_SUMMARY_MAJORS:
                    continue
                target = _SURYA_SUMMARY_MAJORS[current_major]
                for cells in _surya_table_rows(html):
                    row_text = " ".join(cells)
                    amounts = _extract_surya_cell_amounts(cells)
                    if _SURYA_PUBLIC_LIBRARY_LABEL_RE.search(row_text):
                        if not amounts:
                            pending_public_library_total = True
                            continue
                    elif pending_public_library_total and _SURYA_MINOR_105_TOTAL_RE.search(row_text):
                        pending_public_library_total = False
                    else:
                        continue

                    if not amounts:
                        continue
                    matches.append(
                        {
                            "target": target,
                            "status": "surya_ocr_summary",
                            "code_detected": target,
                            "selected_amount_thousand_rupees": _select_surya_amount(cells, amounts),
                            "amount_candidates_thousand_rupees": amounts,
                            "raw_line": "\t".join(cells),
                            "source": _repo_relative(results_path),
                            "source_engine": "surya_ocr",
                        }
                    )
    return matches


def _extract_surya_summary_matches(state: str, fy: str) -> list[dict]:
    root = OUT_DIR / "surya" / state.lower() / fy
    if not root.exists():
        return []
    matches: list[dict] = []
    for results_path in sorted(root.glob("**/results.json")):
        matches.extend(_extract_surya_summary_matches_from_results(results_path))
    return matches


def _replace_result_if_better(results: dict[str, dict], target: str, candidate: dict) -> None:
    if candidate.get("status") not in _FINAL_OBSERVED_STATUSES:
        return
    existing = results.get(target, {"status": "not_found"})
    existing_priority = _MATCH_PRIORITY.get(existing.get("status", "not_found"), 0)
    candidate_priority = _MATCH_PRIORITY.get(candidate.get("status", "not_found"), 0)
    if candidate_priority >= existing_priority:
        results[target] = candidate


def extract_year(state: str, fy: str) -> dict:
    profile = state_profiles.profile_for(state, fy)

    # Prefer cached parser-memory if pdftotext fails in local runtime.
    memory_path = (
        state_profiles.MEMORY_DIR / f"{profile.slug}.json"
    )
    memory = None
    if memory_path.exists():
        with memory_path.open("r", encoding="utf-8") as handle:
            try:
                memory = json.loads(handle.read())
            except json.JSONDecodeError:
                memory = None

    def _extract_window_text(document_window: object) -> str:
        source_path = REPO_ROOT / document_window.source_relpath
        try:
            return state_profiles._extract_window_text(source_path, document_window.page_start, document_window.page_end)
        except (subprocess.CalledProcessError, FileNotFoundError):
            if memory is None:
                return ""
            for row in memory.get("windows", []):
                if (
                    row.get("source_relpath") == document_window.source_relpath
                    and int(row.get("page_start", -1)) == document_window.page_start
                    and int(row.get("page_end", -1)) == document_window.page_end
                ):
                    return row.get("text", "")
            return ""

    target_alias: dict[str, str] = {}
    target_info: dict[str, dict[str, str]] = {}
    window_targets: list[str] = []
    for canonical in TARGETS:
        for variant in TARGET_VARIANTS.get(canonical, (canonical,)):
            target_alias[variant] = canonical
            parts = variant.split("-")
            if len(parts) == 3:
                target_info[variant] = {"major": parts[0], "submajor": parts[1], "minor": parts[2], "canonical": canonical}
            window_targets.append(variant)

    windows = []
    for document in profile.documents:
        for window in document.windows:
            for target in window_targets:
                if target.startswith(window.code_family):
                    windows.append((document, window, target))

    if not windows:
        return {
            "state": state,
            "fy": fy,
            "targets": {t: {"status": "missing", "reason": "no_matching_window"} for t in TARGETS},
            "windows": [],
        }

    results: dict[str, dict] = {target: {"status": "not_found"} for target in TARGETS}
    parsed_windows = []
    surya_matches = _extract_surya_summary_matches(state, fy)

    for document, window, target in windows:
        text = _extract_window_text(window)
        parsed_windows.append(
            {
                "document_type": document.document_type,
                "document_family": document.document_family,
                "source_relpath": window.source_relpath,
                "page_start": window.page_start,
                "page_end": window.page_end,
                "code_family": window.code_family,
                "source_path": window.source_relpath,
                "text_length": len(text),
            }
        )

        for surya_match in surya_matches:
            surya_target = surya_match["target"]
            if not surya_target.startswith(window.code_family):
                continue
            enriched_match = {
                key: value for key, value in surya_match.items() if key != "target"
            }
            enriched_match["document_type"] = document.document_type
            enriched_match["window_pages"] = [window.page_start, window.page_end]
            _replace_result_if_better(results, surya_target, enriched_match)

        if not text:
            existing = results.get(target, {"status": "not_found"})
            if existing.get("status") == "not_found":
                existing["status"] = "extraction_error"
                existing["reason"] = "empty_window_text"
            continue

        current_major: str | None = None
        current_submajor: str | None = None
        for line in text.splitlines():
            match, current_major, current_submajor = parse_target_line(
                line,
                current_major,
                current_submajor,
                target_info,
                target_alias,
            )
            if not match:
                continue
            target = _target_for_match(match, target_alias)
            if target is None:
                continue
            _replace_result_if_better(
                results,
                target,
                {
                    "status": match.match_type,
                    "code_detected": match.code,
                    "selected_amount_thousand_rupees": match.selected_amount,
                    "amount_candidates_thousand_rupees": match.amount_candidates,
                    "raw_line": match.raw_line,
                    "document_type": document.document_type,
                    "source": window.source_relpath,
                    "window_pages": [window.page_start, window.page_end],
                },
            )

    return {
        "state": state,
        "fy": fy,
        "targets": results,
        "windows": parsed_windows,
    }


def write_outputs(payload: dict, out_dir: Path, state: str, fys: Iterable[str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for fy in fys:
        year_payload = payload[fy]
        out_path = out_dir / f"{state.lower()}_observed_{fy}.json"
        out_path.write_text(json.dumps(year_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(out_path)

    combined = {
        "state": state,
        "fiscal_years": [fy for fy in fys],
        "targets": TARGETS,
        "years": payload,
    }
    combined_path = out_dir / f"{state.lower()}_observed_time_series.json"
    combined_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(combined_path)
    return paths


def parse_years_argument(values: str) -> tuple[str, ...]:
    years = tuple(part.strip() for part in values.split(",") if part.strip())
    if not years:
        raise ValueError("--fys must include at least one FY")
    return years


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Rajasthan LMMHA target rows from parser-memory windows")
    parser.add_argument("--state", default="Rajasthan")
    parser.add_argument(
        "--fys",
        default=",".join(state_profiles.RAJASTHAN_FYS),
        help=f"Comma-separated FY list, e.g. {state_profiles.RAJASTHAN_FYS[0]},{state_profiles.RAJASTHAN_FYS[1]},{state_profiles.RAJASTHAN_FYS[2]},{state_profiles.RAJASTHAN_FYS[3]}",
    )
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    fys = parse_years_argument(args.fys)
    payload = {fy: extract_year(args.state, fy) for fy in fys}
    paths = write_outputs(payload, Path(args.out_dir), args.state, fys)
    for path in paths:
        if path.is_relative_to(REPO_ROOT):
            print(path.relative_to(REPO_ROOT))
        else:
            print(path)


if __name__ == "__main__":
    main()
