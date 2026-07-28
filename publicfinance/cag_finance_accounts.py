"""Public-library head extraction from CAG State Finance Accounts Vol-II.

Separate from :mod:`account_code_extract` (whose code-triple state machine is
tuned for Rajasthan detailed-demand budget volumes) because CAG Finance Accounts
Vol-II lay the same data out differently, and per-State layout variance breaks any
fixed-column rule. What makes robust, *self-validating* extraction possible:

1. **The English label.** "Public Libraries" appears a handful of times per
   volume, each an org-relevant head, disambiguated by the current major head and
   the minor code on the line:
   * major ``0202`` / ``0210``, minor ``102`` -> library **receipts** (0202-04-102)
   * major ``2205``,            minor ``105`` -> library **revenue** (2205-00-105)
   * major ``4202``,            minor ``105`` -> library **capital** (4202-04-105)
   * major ``6202``,            minor ``105`` -> library **loans**   (6202-04-105)

2. **The per-cent column self-validates the pick.** CAG prints, for a head,
   current-year and previous-year figures and an increase/decrease per-cent
   ``Q = (current - previous)/previous x 100``. Column *order* varies between
   Statement 15 (revenue) and Statement 16 (capital) and between States, so we do
   NOT read by position. Instead we find the value ``V`` for which some other
   value ``P`` in the row reproduces the printed per-cent ``Q``. When that holds,
   the read is *proved correct against the document itself* — no external ground
   truth required, which is what lets us trust States beyond the hand-checked few.
   A figure that cannot be self-validated is flagged, never silently trusted.

Capital/loans figures often sit not on the minor-head line but on a ``Total-105``
minor-total line or the head's sub-head lines; the block reader prefers the
``Total-105`` line, never reads a sub-major/major total (``Total-04``,
``Total-4202``), and records a confident NIL only when the whole block carries no
decimal figure at all.

Units are the document's, declared once by the caller (``lakh`` for CAG Finance
Accounts) and converted to crore via :func:`account_code_extract.to_crore`.
Interpretation (aggregation, per-capita, real-terms) lives in the consuming repo.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .account_code_extract import iter_pdf_pages, to_crore

# ₹ lakh to two decimals; the decimal point is mandatory so bare head codes
# (105, 2205, 4202) and integer counts are never read as amounts. Indian digit
# grouping (1,058.49 / 15,927.59 / 1,47,744.54) is allowed before the decimal.
_AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d+")
# A line opening a major head: 4-digit code then a dash/space then the head NAME
# (a letter). Requiring the letter separates a real head ("2205-Art and Culture")
# from a fiscal-year column token ("2022-23"), which would otherwise be misread
# as a major head and mis-scope the rows that follow.
_MAJOR_RE = re.compile(r"^\(?(\d{4})\)?\s*[-–—]?\s*(?=[A-Za-z])")
_MINOR_RE = re.compile(r"\b(105|102)\b")
_LIBRARY_RE = re.compile(r"public\s+librar", re.IGNORECASE)
# Bounds for a capital block scan.
_MINOR_TOTAL_105_RE = re.compile(r"^Total\s*[-–—]?\s*105\b", re.IGNORECASE)  # the wanted minor total
_ANY_TOTAL_RE = re.compile(r"^Total\b", re.IGNORECASE)                       # sub-major/major total -> stop
_NEW_HEAD_RE = re.compile(r"^\(?\d{3,4}\b")                                  # a new minor/major head -> stop

_REVENUE = ({"2205"}, "105")
_CAPITAL = ({"4202"}, "105")
_LOANS = ({"6202"}, "105")
_RECEIPTS = ({"0202", "0210"}, "102")

_SPILL_SCAN_LINES = 10
# Tolerance (percentage points) for matching a row's own increase/decrease col.
_PCT_TOL = 0.6


def _amounts(line: str) -> list[float]:
    return [float(t.replace(",", "")) for t in _AMOUNT_RE.findall(line)]


# Sign printed with the trailing increase/decrease per-cent, e.g. "(-)66.44".
_PCT_SIGN_RE = re.compile(r"\(\s*([+-])\s*\)\s*(\d{1,3}(?:,\d{2,3})*\.\d+)\s*$")


def _pct_sign(line: str) -> str | None:
    m = _PCT_SIGN_RE.search(line)
    return m.group(1) if m else None


def _pick_current_year(nums: list[float], pct_sign: str | None = None) -> tuple[float | None, bool]:
    """Return (current-year value, self_validated).

    Self-validating: the last numeric on a CAG head row is the increase/decrease
    per-cent ``Q``; the current-year value ``V`` is the one for which some other
    value ``P`` in the row gives ``|(V - P)/P| x 100 == Q``. Order-independent, so
    it works across the differing revenue/capital column layouts.

    For small |Q| (under ~8 per-cent) the backward ratio ``|(P - V)/V|`` also lands
    inside the tolerance, so the match alone cannot tell current from previous.
    A zero V is a spurious candidate for any Q near 100 (0 against any previous
    is exactly -100), so V = 0 validates only against an exact 100.00.
    Disambiguators, in order: the printed sign of Q when the caller passes it
    (``(+)`` means V > P); row structure — the current-year total equals the sum
    of two other figures on the row (State + Central share, or voted + charged)
    while the previous-year figure sums with nothing; and repetition — the
    current-year figure prints at least twice (voted and total) while the
    previous-year figure prints once. If none resolves a unique V, the row is
    NOT self-validated. If no matching triple exists at all (new head with nil
    previous year, or an unparseable row), fall back and flag likewise.
    """
    if len(nums) >= 3:
        q = nums[-1]
        body = nums[:-1]
        cands: list[float] = []
        for vi, v in enumerate(body):
            for pj, p in enumerate(body):
                if vi == pj or p == 0:
                    continue
                change = (v - p) / p * 100.0
                if pct_sign == "+" and change < 0:
                    continue
                if pct_sign == "-" and change > 0:
                    continue
                if v == 0 and abs(q - 100.0) > 0.005:
                    continue
                if abs(abs(change) - q) <= _PCT_TOL:
                    cands.append(v)
                    break
        uniq = sorted({round(v, 2) for v in cands})
        if len(uniq) == 1:
            return cands[0], True
        if len(uniq) > 1:
            pair_sums = {round(body[j] + body[k], 2)
                         for j in range(len(body)) for k in range(j + 1, len(body))
                         if body[j] and body[k]}
            summed = [v for v in uniq if v in pair_sums]
            if len(summed) == 1:
                return summed[0], True
            counts = Counter(round(n, 2) for n in body)
            repeated = [v for v in uniq if counts[v] >= 2]
            if len(repeated) == 1:
                return repeated[0], True
    # No self-validating per-cent (a first-year / no-previous-year head). The
    # current-year total still prints as voted AND total (charged nil), so it
    # appears at least twice; the (larger) expenditure-to-end column appears
    # once. Take the repeated non-max value. NOT self-validated — caller flags.
    counts = Counter(round(n, 2) for n in nums)
    repeated = [v for v, c in counts.items() if c >= 2]
    if repeated:
        mx = max(nums)
        cands = [v for v in repeated if v != mx] or repeated
        return max(cands), False
    return (nums[0] if nums else None), False


@dataclass
class HeadFigure:
    code: str
    label: str            # "revenue" | "capital" | "loans" | "receipts"
    value_lakh: float | None
    value_crore: float | None
    self_validated: bool
    physical_page: int | None
    raw_line: str
    note: str = ""


@dataclass
class LibraryHeads:
    pdf: str
    unit: str
    revenue: HeadFigure | None = None
    capital: HeadFigure | None = None
    loans: HeadFigure | None = None
    receipts: HeadFigure | None = None

    def as_row(self) -> dict:
        def cr(h: HeadFigure | None) -> float | None:
            return h.value_crore if h else None
        return {
            "lib_receipts_cr": cr(self.receipts),
            "lib_rev_exp_cr": cr(self.revenue),
            "lib_cap_exp_cr": cr(self.capital),
            "lib_loans_cr": cr(self.loans),
        }

    def all_self_validated(self) -> bool:
        return all(h.self_validated for h in (self.revenue, self.capital, self.loans, self.receipts) if h)


def _classify(cur_major: str | None, minor: str) -> tuple[str, str] | None:
    if cur_major in _REVENUE[0] and minor == _REVENUE[1]:
        return "revenue", "2205-00-105"
    if cur_major in _CAPITAL[0] and minor == _CAPITAL[1]:
        return "capital", "4202-04-105"
    if cur_major in _LOANS[0] and minor == _LOANS[1]:
        return "loans", "6202-04-105"
    if cur_major in _RECEIPTS[0] and minor == _RECEIPTS[1]:
        return "receipts", "0202-04-102"
    return None


def _capital_block(lines: list[str], start: int) -> tuple[float | None, str, bool, str]:
    """Read a capital/loans minor-head figure that may spill past its head line.

    Returns (value_lakh, raw_line, self_validated, note). Prefers a ``Total-105``
    minor-total line; else the head line; else the sum of the head's own sub-head
    lines. Bounds the block at the next head or any sub-major/major ``Total``.
    Records a confident NIL (0.0) only when the whole block has no decimal figure.
    """
    head = lines[start].strip()
    total_line: str | None = None
    subheads: list[tuple[float, str, bool]] = []
    saw_any_amount = bool(_amounts(head))
    for k in range(start + 1, min(start + 1 + _SPILL_SCAN_LINES, len(lines))):
        s = lines[k].strip()
        if not s:
            continue
        if _MINOR_TOTAL_105_RE.match(s):        # the wanted minor-head total
            total_line = s
            break
        if _ANY_TOTAL_RE.match(s) or _NEW_HEAD_RE.match(s):  # sub-major/major total, or next head
            break
        if not s[:1].isalpha():                 # bare numeric line = column-wrap fragment
            if _amounts(s):                     # its figures still veto a "confident NIL"
                saw_any_amount = True
            continue
        amts = _amounts(s)
        if amts:                                # a real sub-head detail line
            saw_any_amount = True
            v, sv = _pick_current_year(amts, _pct_sign(s))
            if v is not None:
                subheads.append((v, s, sv))

    def _cand(line: str | None) -> tuple[float, str, bool] | None:
        if not line:
            return None
        amts = _amounts(line)
        if not amts:
            return None
        v, sv = _pick_current_year(amts, _pct_sign(line))
        return (v, line, sv) if v is not None else None

    tl, hl = _cand(total_line), _cand(head)
    # 1) prefer a SELF-VALIDATED source: Total-105 line, then head, then sub-heads.
    for c in (tl, hl):
        if c and c[2]:
            return c[0], c[1], True, "self-validated"
    sv_subs = [x for x in subheads if x[2]]
    if len(sv_subs) == 1:
        return sv_subs[0][0], sv_subs[0][1], True, "self-validated sub-head"
    if sv_subs:
        return (sum(v for v, _, _ in sv_subs), "; ".join(l for _, l, _ in sv_subs)[:90],
                True, f"sum of {len(sv_subs)} self-validated sub-heads")
    # 2) a value is present but not %-validated (first-year head, no comparator) — flag it.
    for c in (tl, hl):
        if c:
            return c[0], c[1], False, "value present, NOT %-validated — review"
    if subheads:
        return subheads[0][0], subheads[0][1], False, "sub-head value, NOT %-validated — review"
    # 3) no decimal figure anywhere in the block -> genuine NIL.
    if not saw_any_amount:
        return 0.0, head, True, "block carries no figure — recorded NIL"
    return None, head, False, "figures present but none self-validated — needs manual review"


def parse_pages(pages, *, unit: str = "lakh", pdf: str = "") -> LibraryHeads:
    """Scan ``(physical_page_no, layout_text)`` pairs for the four library heads.

    Pure over its input, so it is unit-testable with synthetic page text; the
    PDF-reading front door is :func:`extract_library_heads`. A head absent from
    the volume stays ``None``. ``cur_major`` is carried ACROSS pages: CAG detailed
    statements run a major head's minor rows over several pages, so a "105 Public
    Libraries" row often sits on the page after its major-head line.
    """
    result = LibraryHeads(pdf=pdf, unit=unit)
    slot = {"revenue": "revenue", "capital": "capital", "loans": "loans", "receipts": "receipts"}
    cur_major: str | None = None
    for page_no, page_text in pages:
        lines = page_text.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            mjr = _MAJOR_RE.match(stripped)
            if mjr:
                cur_major = mjr.group(1)
            if not _LIBRARY_RE.search(stripped):
                continue
            minor_m = _MINOR_RE.search(stripped)
            if not minor_m:
                continue
            hit = _classify(cur_major, minor_m.group(1))
            if hit is None:
                continue
            label, code = hit
            if getattr(result, slot[label]) is not None:
                continue  # first occurrence wins

            if label in ("capital", "loans"):
                value_lakh, raw, sv, note = _capital_block(lines, i)
            else:  # revenue / receipts: figure is on the head line
                value_lakh, sv = _pick_current_year(_amounts(stripped), _pct_sign(stripped))
                raw, note = stripped, ("self-validated" if sv else "NOT self-validated (fell back to first column)")

            setattr(result, slot[label], HeadFigure(
                code=code,
                label=label,
                value_lakh=value_lakh,
                value_crore=to_crore(value_lakh, unit) if value_lakh is not None else None,
                self_validated=sv,
                physical_page=page_no,
                raw_line=raw,
                note=note,
            ))
    return result


def extract_library_heads(pdf_path: Path, *, unit: str = "lakh") -> LibraryHeads:
    """Extract the four public-library heads from a CAG Finance Accounts Vol-II."""
    return parse_pages(iter_pdf_pages(Path(pdf_path)), unit=unit, pdf=str(pdf_path))
