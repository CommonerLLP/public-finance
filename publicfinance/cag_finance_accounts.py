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
# A sub-major head opens with a two-digit code then its name ("01 Elementary
# Education", "04 Art and Culture"). Needed to tell 4202-01-201 (school capital)
# from a minor 201 under any other sub-major.
_SUBMAJOR_RE = re.compile(r"^(\d{2})\s*[-–—]?\s+(?=[A-Za-z])")
# Bounds for a capital block scan.
_ANY_TOTAL_RE = re.compile(r"^Total\b", re.IGNORECASE)                       # sub-major/major total -> stop
_FY_TOKEN_RE = re.compile(r"^\(?\d{4}\s*[-–—]\s*\d{2,4}\b")                  # "2022-2023" column header, never a head
_NEW_HEAD_RE = re.compile(r"^\(?\d{3,4}\b(?!\.\d)")                       # a new minor/major head -> stop; (?!\.\d) keeps a wrapped bare amount ("117.37") from reading as a head


def _total_re(code: str) -> re.Pattern:
    """``Total - <code>`` for the wanted head, anchored so 201 never matches 20."""
    return re.compile(rf"^Total\s*[-–—]?\s*{code}\b", re.IGNORECASE)


_MINOR_TOTAL_105_RE = _total_re("105")

# Assam lists ~12 sub-head lines before its Total-105, and its 4202-01-201 block
# runs over two page breaks (page headers included) before its Total-201. The
# block still stops at the first new head or foreign Total, so the window only
# has to be long enough, not tight.
_SPILL_SCAN_LINES = 120
# Tolerance (percentage points) for matching a row's own increase/decrease col.
_PCT_TOL = 0.6


def _amounts(line: str) -> list[float]:
    return [float(t.replace(",", "")) for t in _AMOUNT_RE.findall(line)]


# Sign printed with the trailing increase/decrease per-cent, e.g. "(-)66.44".
_PCT_SIGN_RE = re.compile(r"\(\s*([+-])\s*\)\s*(\d{1,3}(?:,\d{2,3})*\.\d+)\s*$")


def _pct_sign(line: str) -> str | None:
    m = _PCT_SIGN_RE.search(line)
    return m.group(1) if m else None


def _sum_proof(nums: list[float]) -> float | None:
    """Return the Total column when the row's own arithmetic proves it.

    CAG prints ``State Fund Expenditure | Central Assistance | Total`` next to
    each other, so a value equal to the exact sum of the two (or three) values
    immediately before it is the Total. Requires a UNIQUE such value, and both
    addends non-zero, so a row of dots or a repeated figure cannot fake it.
    """
    hits = []
    # The rightmost column is never the in-year Total (it is the per-cent in
    # Statements 15/16, a closing balance in 18), so excluding it costs nothing
    # and kills the false accept found on Tamil Nadu 2022-23 loans, where
    # (-)0.10 + 0.88 = 0.98 reproduced the trailing 0.98 exactly.
    for i in range(2, len(nums) - 1):
        for width in (2, 3):
            if i - width < 0:
                continue
            parts = nums[i - width:i]
            if all(p > 0 for p in parts) and abs(sum(parts) - nums[i]) <= 0.02 and nums[i] > 0:
                hits.append(round(nums[i], 2))
                break
    uniq = sorted(set(hits))
    return uniq[0] if len(uniq) == 1 else None


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
    # A printed "(-)100.00" is itself the figure: the current year is exactly
    # zero (dots print in the in-year columns, so no zero token appears).
    # Page-verified on Haryana 2022-23 Statement 16.
    if pct_sign == "-" and nums and abs(nums[-1] - 100.0) <= 0.005:
        return 0.0, True
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
    # Second proof, for rows whose per-cent column is a BARE INTEGER ("(+)136")
    # and so invisible to the decimal-only amount rule — common in Assam and in
    # every sub-major total. CAG prints State Fund + Central Assistance = Total
    # on the same row, so a value that is the exact sum of the columns before it
    # is the Total column, proved by the row's own arithmetic.
    summed = _sum_proof(nums)
    if summed is not None:
        return summed, True
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


@dataclass(frozen=True)
class HeadSpec:
    """One wanted head and how its figure is printed.

    ``mode`` is the shape of the read, not the account class:

    * ``inline`` — the figure sits on the minor-head line itself
      (2205-00-105, 0202-04-102 in Statement 15).
    * ``block``  — the minor head opens a block of sub-head lines closed by a
      ``Total - <total_code>`` line (Statement 16 capital/loans, and the school
      capital minors 4202-01-201/202).
    * ``total``  — the head is a SUB-MAJOR whose block runs over several pages,
      so only its printed ``Total - <total_code>`` line is read (2202-01/02/80).
      Reading the sub-major total is what REQ-0047 needs: 2202-01 has a dozen
      minor heads and no single line carries the sub-major figure.
    """
    label: str
    code: str
    majors: frozenset[str]
    mode: str
    total_code: str = ""
    minor: str = ""
    submajor: str = ""
    name_re: re.Pattern | None = None


LIBRARY_SPECS = (
    HeadSpec("receipts", "0202-04-102", frozenset({"0202", "0210"}), "inline",
             minor="102", name_re=_LIBRARY_RE),
    HeadSpec("revenue", "2205-00-105", frozenset({"2205"}), "inline",
             minor="105", name_re=_LIBRARY_RE),
    HeadSpec("capital", "4202-04-105", frozenset({"4202"}), "block",
             minor="105", total_code="105", name_re=_LIBRARY_RE),
    HeadSpec("loans", "6202-04-105", frozenset({"6202"}), "block",
             minor="105", total_code="105", name_re=_LIBRARY_RE),
)

# REQ-0047 (theright2read): school-education heads on the same reader.
SCHOOL_SPECS = (
    HeadSpec("elementary_rev", "2202-01", frozenset({"2202"}), "total", total_code="01"),
    HeadSpec("secondary_rev", "2202-02", frozenset({"2202"}), "total", total_code="02"),
    HeadSpec("general_rev", "2202-80", frozenset({"2202"}), "total", total_code="80"),
    HeadSpec("elementary_cap", "4202-01-201", frozenset({"4202"}), "block",
             minor="201", submajor="01", total_code="201",
             name_re=re.compile(r"elementary\s+education", re.IGNORECASE)),
    HeadSpec("secondary_cap", "4202-01-202", frozenset({"4202"}), "block",
             minor="202", submajor="01", total_code="202",
             name_re=re.compile(r"secondary\s+education", re.IGNORECASE)),
)


def _capital_block(lines: list[str], start: int, total_code: str = "105",
                   own_codes: frozenset[str] = frozenset()) -> tuple[float | None, str, bool, str]:
    """Read a capital/loans minor-head figure that may spill past its head line.

    Returns (value_lakh, raw_line, self_validated, note). Prefers a ``Total-105``
    minor-total line; else the head line; else the sum of the head's own sub-head
    lines. Bounds the block at the next head or any sub-major/major ``Total``.
    Records a confident NIL (0.0) only when the whole block has no decimal figure.
    """
    head = lines[start].strip()
    wanted_total = _total_re(total_code)
    total_line: str | None = None
    subheads: list[tuple[float, str, bool]] = []
    saw_any_amount = bool(_amounts(head))
    for k in range(start + 1, min(start + 1 + _SPILL_SCAN_LINES, len(lines))):
        s = lines[k].strip()
        if not s:
            continue
        if wanted_total.match(s):               # the wanted minor-head total
            # Some volumes wrap the total's figures onto the next line(s)
            # (Assam prints "Total 105" and the amounts a line below). A line
            # opening a NEW head ("106 Museums") is never a continuation.
            total_line = _absorb_wrap(lines, k, s)
            if _amounts(total_line):            # total figures veto a "confident NIL"
                saw_any_amount = True
            break
        # Page furniture between the head and its Total: the printed page number
        # ("269"), the column-number rule ("1 2 3 4 5 6"), and the repeated column
        # header ("2022-2023   Expenditure   Assistance"). Each reads as a new head
        # if left alone, which ends the block one page short of its Total.
        if s.replace(" ", "").isdigit() or _FY_TOKEN_RE.match(s):
            continue
        # A head line carrying one of the block's OWN codes is a restatement, not
        # a new head: CAG repeats major / sub-major / minor lines after every page
        # break ("4202 ... - Contd.", "201 Elementary Education - Concld."), and
        # Assam restates its minor head twice in a row. Breaking there truncates
        # the block before its Total and silently records NIL.
        if _NEW_HEAD_RE.match(s) and any(re.match(rf"^\(?{c}\b", s) for c in own_codes):
            continue
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
            if v is not None and (sv or len(amts) > 1):  # lone unvalidated figure = cumulative-only
                subheads.append((v, s, sv))

    def _cand(line: str | None) -> tuple[float, str, bool] | None:
        if not line:
            return None
        amts = _amounts(line)
        if not amts:
            return None
        v, sv = _pick_current_year(amts, _pct_sign(line))
        # A lone unvalidated figure on a capital line is indistinguishable from
        # the "expenditure to end of the year" column (when the in-year columns
        # are dots, the cumulative is the only decimal that prints) — page-
        # verified on Haryana/Tripura/AP/Telangana 2023-24. Never return it.
        if not sv and len(amts) == 1:
            return None
        return (v, line, sv) if v is not None else None

    tl, hl = _cand(total_line), _cand(head)
    # 1) prefer a SELF-VALIDATED source: Total-105 line, then head, then sub-heads.
    for c in (tl, hl):
        if c and c[2]:
            return c[0], c[1], True, "self-validated"
    sv_subs = [x for x in subheads if x[2]]
    # A sub-head sum is validated only when EVERY sub-head in the block
    # validated — a partial sum understates while carrying a True flag.
    if len(sv_subs) == len(subheads) and len(sv_subs) == 1:
        return sv_subs[0][0], sv_subs[0][1], True, "self-validated sub-head"
    if sv_subs and len(sv_subs) == len(subheads):
        return (sum(v for v, _, _ in sv_subs), "; ".join(l for _, l, _ in sv_subs)[:90],
                True, f"sum of {len(sv_subs)} self-validated sub-heads")
    # A partial sub-head sum understates, so it is rejected — but only the SUM is
    # unusable. A Total-105/head figure that is complete-but-unvalidated is still
    # the best available read, so fall through to the unvalidated fallback below.
    if sv_subs and not (tl or hl):
        return (None, "; ".join(l for _, l, _ in subheads)[:90], False,
                f"mixed block: {len(sv_subs)}/{len(subheads)} sub-heads validated — review")
    # 2) a value is present but not %-validated (first-year head, no comparator) — flag it.
    mixed = (f"mixed block: {len(sv_subs)}/{len(subheads)} sub-heads validated; "
             if sv_subs else "")
    for c in (tl, hl):
        if c:
            return c[0], c[1], False, f"{mixed}value present, NOT %-validated — review"
    if subheads:
        return subheads[0][0], subheads[0][1], False, "sub-head value, NOT %-validated — review"
    # 3) no decimal figure anywhere in the block -> genuine NIL.
    if not saw_any_amount:
        return 0.0, head, True, "block carries no figure — recorded NIL"
    return None, head, False, "figures present but none self-validated — needs manual review"


def _absorb_wrap(lines: list[str], k: int, line: str) -> str:
    """Append column-wrap continuation lines to a total line.

    A sub-major total often prints its charged (italic) figure on the total line
    and the State Fund / Central / Total / previous-year / per-cent columns on
    the next line (Gujarat "Total - 01"). A line opening a new head is never a
    continuation.
    """
    for w in range(k + 1, min(k + 3, len(lines))):
        nxt = lines[w].strip()
        if not nxt:
            continue
        if nxt[:1].isalpha() or _NEW_HEAD_RE.match(nxt) or _SUBMAJOR_RE.match(nxt):
            break
        line += " " + nxt
    return line


def parse_specs(pages, specs, *, unit: str = "lakh") -> dict[str, HeadFigure]:
    """Scan ``(physical_page_no, layout_text)`` pairs for each :class:`HeadSpec`.

    Pure over its input, so it is unit-testable with synthetic page text. A head
    absent from the volume is absent from the result. ``cur_major`` and
    ``cur_submajor`` are carried ACROSS pages: CAG detailed statements run a
    head's rows over several pages, so a wanted row often sits on the page after
    the line that scopes it. First occurrence of a head wins.
    """
    # Flattened once, because a head's block can run past a page break: Assam's
    # 4202-01-201 opens on one page and closes on its "Total 201" two pages on.
    flat: list[str] = []
    page_of: list[int] = []
    for page_no, page_text in pages:
        for line in page_text.splitlines():
            flat.append(line)
            page_of.append(page_no)

    found: dict[str, HeadFigure] = {}
    cur_major: str | None = None
    cur_submajor: str | None = None
    for i, line in enumerate(flat):
        stripped = line.strip()
        mjr = _MAJOR_RE.match(stripped)
        if mjr:
            cur_major, cur_submajor = mjr.group(1), None
        else:
            sub = _SUBMAJOR_RE.match(stripped)
            if sub:
                cur_submajor = sub.group(1)
        for spec in specs:
            if spec.label in found or cur_major not in spec.majors:
                continue
            if spec.submajor and cur_submajor != spec.submajor:
                continue

            if spec.mode == "total":
                if not _total_re(spec.total_code).match(stripped):
                    continue
                raw = _absorb_wrap(flat, i, stripped)
                value_lakh, sv = _pick_current_year(_amounts(raw), _pct_sign(raw))
                note = "self-validated"
                if not sv:
                    # An unproved pick on a sub-major total row is a mis-picked
                    # column (charged, previous-year, cumulative), not an
                    # approximate figure. Report the gap, never the guess.
                    value_lakh, note = None, "sub-major total not proved — review"
            else:
                if spec.name_re is not None and not spec.name_re.search(stripped):
                    continue
                if spec.minor and not re.search(rf"\b{spec.minor}\b", stripped):
                    continue
                if spec.mode == "block":
                    own = frozenset({spec.minor, spec.submajor, *spec.majors} - {""})
                    value_lakh, raw, sv, note = _capital_block(flat, i, spec.total_code, own)
                else:  # inline: the figure is on the head line itself
                    value_lakh, sv = _pick_current_year(_amounts(stripped), _pct_sign(stripped))
                    raw = stripped
                    note = "self-validated" if sv else "NOT self-validated (fell back to first column)"

            found[spec.label] = HeadFigure(
                code=spec.code,
                label=spec.label,
                value_lakh=value_lakh,
                value_crore=to_crore(value_lakh, unit) if value_lakh is not None else None,
                self_validated=sv,
                physical_page=page_of[i],
                raw_line=raw,
                note=note,
            )
            break
    return found


def parse_pages(pages, *, unit: str = "lakh", pdf: str = "") -> LibraryHeads:
    """Scan pages for the four public-library heads (:data:`LIBRARY_SPECS`)."""
    found = parse_specs(pages, LIBRARY_SPECS, unit=unit)
    return LibraryHeads(pdf=pdf, unit=unit, **found)


def extract_library_heads(pdf_path: Path, *, unit: str = "lakh") -> LibraryHeads:
    """Extract the four public-library heads from a CAG Finance Accounts Vol-II."""
    return parse_pages(iter_pdf_pages(Path(pdf_path)), unit=unit, pdf=str(pdf_path))


def extract_school_heads(pdf_path: Path, *, unit: str = "lakh") -> dict[str, HeadFigure]:
    """Extract the five school-education heads (:data:`SCHOOL_SPECS`) from a Vol-II."""
    return parse_specs(iter_pdf_pages(Path(pdf_path)), SCHOOL_SPECS, unit=unit)
