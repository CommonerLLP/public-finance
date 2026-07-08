"""Account-code-targeted fiscal head extraction.

Reusable primitive for pulling specific government-chart-of-accounts heads out of
budget / finance-accounts PDFs *by account code*, not by (Hindi or English) label.

Why by code, not label
----------------------
Indian budget and CAG Finance-Accounts PDFs carry the account code (e.g.
``2205-00-105``) as clean ASCII digits, but the head *description* is set in a
legacy Devanagari font (KrutiDev / AksharUnicode) that ``pdftotext`` garbles
beyond reliable regex matching. The account code survives; the label does not.
So we run a ``major -> submajor -> minor`` state machine over the account codes
and read the amount row anchored on the code.

Two target shapes are supported:

* **Minor-head row** ``MMMM-SS-mmm`` (e.g. ``2205-00-105``, ``0202-04-102``) --
  used for CAG State Finance Accounts Vol-II detailed statements (Statement 14
  receipts, Statement 15 revenue expenditure, capital and loans statements) and
  for state-budget minor-head lines. Disambiguated by the *current major head*,
  because the same minor code (``105``) recurs under many majors.

* **Major-head grand total** ``MMMM`` (e.g. ``2851``, ``2852``) -- the
  ``मुख्य शीर्ष-NNNN-योग`` / ``Total NNNN`` summary line. Used for the RTR
  library-vs-industry comparison, where the comparator is the whole industry
  major head.

Units are declared *once per document*, never per row. This module never guesses
a per-row unit; the caller passes the document unit explicitly (``thousand`` for
Rajasthan detailed demand volumes, ``lakh`` for CAG Finance Accounts) and every
figure is converted to crore with the arithmetic shown, so the crore/lakh trap
cannot silently 100x a figure.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ₹ conversion to crore. 1 crore = 1e7 rupees.
_RUPEES_PER_CRORE = 1e7
_UNIT_TO_RUPEES = {
    "rupee": 1.0,
    "thousand": 1e3,   # Rajasthan detailed demand volumes ("हजार रुपयों में")
    "lakh": 1e5,       # CAG State Finance Accounts Vol-II ("₹ in lakh")
    "crore": 1e7,
}

# comma-grouped amount, either Indian (9,81,18,62) or plain (168010); also "0" /
# "1"; and CAG-style decimals (806.38, 1,234.56 -- Finance Accounts are ₹ lakh to
# two decimals, so the decimal tail must stay attached, not split into 806 / 38).
_AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?")
# major-head grand-total line: Hindi "…ष-2851 -…" or English "Total 2851".
_HINDI_MAJOR_TOTAL_RE = re.compile(r"ष\s*[-–—]\s*(\d{4})\s*[-–—]")
_ENGLISH_MAJOR_TOTAL_RE = re.compile(r"[Tt]otal\D{0,12}(\d{4})\b")
# printed page footer token e.g. "(257)".
_PRINTED_PAGE_RE = re.compile(r"\((\d{2,4})\)")
# CAG detailed-statement account tokens.
_MAJOR_TOKEN_RE = re.compile(r"\b(\d{4})\b")
_MINOR_TRIPLE_RE = re.compile(r"\b(\d{4})[-\s](\d{2})[-\s](\d{3})\b")


def to_crore(value_in_unit: float, unit: str) -> float:
    """Convert an amount expressed in ``unit`` to ₹ crore.

    ``unit`` is the *document's* declared unit ('thousand' | 'lakh' | 'crore' |
    'rupee'). Raises on an unknown unit rather than silently passing the number
    through unscaled.
    """
    key = unit.strip().lower()
    if key not in _UNIT_TO_RUPEES:
        raise ValueError(f"unknown unit {unit!r}; expected one of {sorted(_UNIT_TO_RUPEES)}")
    return value_in_unit * _UNIT_TO_RUPEES[key] / _RUPEES_PER_CRORE


def _amount_tokens(text: str) -> list[str]:
    """All amount-shaped tokens on a line, filtering out account-code triples."""
    # Blank out account codes first so 2205/00/105 aren't read as amounts.
    scrubbed = _MINOR_TRIPLE_RE.sub(" ", text)
    return _AMOUNT_RE.findall(scrubbed)


def _to_number(token: str) -> float | None:
    token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def iter_pdf_pages(pdf_path: Path, first: int | None = None, last: int | None = None):
    """Yield ``(physical_page_no, layout_text)`` for each page.

    Uses ``pdftotext -layout`` (column alignment preserved) and splits on the
    form-feed page separator so each page's physical number is exact.
    """
    cmd = ["pdftotext", "-layout"]
    if first is not None:
        cmd += ["-f", str(first)]
    if last is not None:
        cmd += ["-l", str(last)]
    cmd += [str(pdf_path), "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    proc.check_returncode()
    base = first or 1
    for offset, page_text in enumerate(proc.stdout.split("\f")):
        yield base + offset, page_text


@dataclass
class HeadMatch:
    code: str
    kind: str                       # "major_total" | "minor_head"
    unit: str
    raw_line: str
    amount_tokens: list[str]
    selected_token: str | None      # the total / last column
    value_crore: float | None
    physical_page: int | None = None
    printed_page: str | None = None
    all_matches: list[str] = field(default_factory=list)


def _printed_page_for(page_text: str) -> str | None:
    hits = _PRINTED_PAGE_RE.findall(page_text)
    return hits[-1] if hits else None


def extract_major_head_totals(
    pdf_path: Path,
    major_codes: list[str],
    *,
    unit: str,
    first: int | None = None,
    last: int | None = None,
) -> dict[str, HeadMatch]:
    """Extract the grand total of each major head ``MMMM``.

    Matches the summary grand-total line (Hindi ``…ष-NNNN-…योग`` or English
    ``Total NNNN``). The *last* amount token on that line is the total column
    (revenue-voted + charged); earlier tokens are prior-year / BE / RE columns.
    Returns the first (summary) total found per code.
    """
    wanted = set(major_codes)
    results: dict[str, HeadMatch] = {}
    for page_no, page_text in iter_pdf_pages(pdf_path, first, last):
        printed = _printed_page_for(page_text)
        for line in page_text.splitlines():
            for rx in (_HINDI_MAJOR_TOTAL_RE, _ENGLISH_MAJOR_TOTAL_RE):
                m = rx.search(line)
                if not m:
                    continue
                code = m.group(1)
                if code not in wanted or code in results:
                    continue
                tokens = _amount_tokens(line)
                if not tokens:
                    continue
                selected = tokens[-1]
                val = _to_number(selected)
                results[code] = HeadMatch(
                    code=code,
                    kind="major_total",
                    unit=unit,
                    raw_line=line.strip(),
                    amount_tokens=tokens,
                    selected_token=selected,
                    value_crore=to_crore(val, unit) if val is not None else None,
                    physical_page=page_no,
                    printed_page=printed,
                )
    return results


def extract_minor_head_rows(
    pdf_path: Path,
    targets: list[str],
    *,
    unit: str,
    first: int | None = None,
    last: int | None = None,
) -> dict[str, HeadMatch]:
    """Extract minor-head rows ``MMMM-SS-mmm`` via a major->submajor->minor machine.

    Tracks the current major (``MMMM``) and submajor (``SS``) from account-code
    tokens as pages stream past, so an ambiguous minor code (``105`` appears
    under many majors) is only matched inside the correct major/submajor block.
    Designed for CAG State Finance Accounts Vol-II detailed statements, whose
    rows read ``<code>  <description>  <plan> <non-plan> <total>`` in English.
    """
    want = {}
    for t in targets:
        parts = t.split("-")
        if len(parts) != 3:
            raise ValueError(f"minor-head target must be MMMM-SS-mmm, got {t!r}")
        want[t] = (parts[0], parts[1], parts[2])
    results: dict[str, HeadMatch] = {}
    cur_major = cur_sub = None
    for page_no, page_text in iter_pdf_pages(pdf_path, first, last):
        printed = _printed_page_for(page_text)
        for line in page_text.splitlines():
            triple = _MINOR_TRIPLE_RE.search(line)
            if triple:
                cur_major, cur_sub, cur_minor = triple.groups()
                for code, (mj, sb, mn) in want.items():
                    if code in results:
                        continue
                    if cur_major == mj and cur_sub == sb and cur_minor == mn:
                        tokens = _amount_tokens(line)
                        selected = tokens[-1] if tokens else None
                        val = _to_number(selected) if selected else None
                        results[code] = HeadMatch(
                            code=code,
                            kind="minor_head",
                            unit=unit,
                            raw_line=line.strip(),
                            amount_tokens=tokens,
                            selected_token=selected,
                            value_crore=to_crore(val, unit) if val is not None else None,
                            physical_page=page_no,
                            printed_page=printed,
                        )
                continue
            # bare major-head heading (updates state even without submajor/minor)
            majors = _MAJOR_TOKEN_RE.findall(line)
            for mj in majors:
                if any(mj == v[0] for v in want.values()):
                    cur_major = mj
    return results
