"""Parse the Union Budget Expenditure Profile establishment-strength statement.

Source: "Estimated strength of establishment and provisions therefor" —
Statement 22 of the Expenditure Profile (2017-18 onwards; standalone
``stat22.pdf`` from 2019-20, inside the combined ``vol1.pdf`` for 2017-18 and
2018-19) and Annex-7 of Expenditure Budget Vol. I (2015-16, 2016-17).

Input PDFs live under ``data/union_budget/expenditure_profile/<budget_year>/``
(``stat22.pdf`` or ``vol1.pdf``). Output: one combined CSV across all years at
``references/expenditure_profile/establishment_strength_all_years.csv``.

CAVEAT: this table reports actual/estimated STRENGTH of establishment, not
sanctioned-vs-vacant posts. Actual-vs-estimated strength is only a proxy for
vacancy; do not present it as vacancy data.

Run: .venv/bin/python -m publicfinance.expenditure_profile_strength
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PDF_DIR = REPO / "data" / "union_budget" / "expenditure_profile"
OUT_CSV = REPO / "references" / "expenditure_profile" / "establishment_strength_all_years.csv"

MARKER = "STRENGTH OF ESTABLISHMENT"

FIELDS = [
    "budget_year",
    "ministry",
    "department_or_org",
    "strength_actual_1mar",
    "strength_actual_year",
    "strength_est_re_1mar",
    "strength_est_re_year",
    "strength_est_be_1mar",
    "strength_est_be_year",
    "pay_actuals_cr",
    "allowances_actuals_cr",
    "travel_actuals_cr",
    "pay_re_cr",
    "allowances_re_cr",
    "travel_re_cr",
    "pay_be_cr",
    "allowances_be_cr",
    "travel_be_cr",
]

# Lines that are page furniture / column headers, never data.
_SKIP_SUBSTRINGS = (
    "STRENGTH OF ESTABLISHMENT",
    "STATEMENT 22",
    "ANNEX-7",
    "₹ CRORES",
    "` CRORES",
    "(IN CRORES",
    "IN CRORES OF RUPEES",
    "STRENGTH AS ON",
    "MINISTRY/DEPARTMENT",
    "MINISTRY CODE",
    "(SALARY)",
    "(OTHER THAN",
    "EXPENDITURE PROFILE",
    "EXPENDITURE BUDGET",
    "REVISED ESTIMATE",
    "BUDGET ESTIMATE",
    "TRAVEL                ",  # header row fragment "Travel  Expenses" columns
)

# number token: integer or decimal, optional thousands commas, or "..." blank
_NUM_RE = re.compile(r"(?<![\w./()-])(\d[\d,]*(?:\.\d+)?|\.\.\.)(?![\w.%-])")
_MINISTRY_RE = re.compile(r"^(\d{1,3})\.\s+(.*)$")
_DEPT_RE = re.compile(r"^\(([ivx]+)\)\s*(.*)$", re.IGNORECASE)


_STOP_RE = re.compile(r"ANNEX\s*-?\s*(7A|8)|STATEMENT\s+2[13-9]")


def _statement_lines(pdf: Path) -> list[str]:
    """Lines from the first ALL-CAPS statement header onward.

    The header is repeated on most (not all) statement pages; contents pages
    reference the statement in title case, so a case-sensitive match skips
    them. The caller stops at the grand total / next-statement boundary.
    """
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    lines = text.replace("\f", "\n").splitlines()
    for i, line in enumerate(lines):
        if MARKER in line:  # case-sensitive: the statement header is in caps
            return lines[i:]
    raise ValueError(f"{pdf}: no line contains '{MARKER}'")


def _is_skip_line(line: str) -> bool:
    u = line.upper()
    if any(s in u for s in _SKIP_SUBSTRINGS):
        return True
    # column-header fragments like "Pay       Allowances    Travel"
    stripped = set(re.sub(r"[^A-Za-z ]", " ", line).split())
    if stripped and stripped <= {"Pay", "Allowances", "Travel", "Expenses", "Actuals", "Estimated"}:
        return True
    return False


def _num(tok: str) -> str:
    return "" if tok == "..." else tok.replace(",", "")


class _Entity:
    def __init__(self, kind: str, name: str):
        self.kind = kind  # "ministry" | "dept" | "total"
        self.name_parts = [name] if name else []
        self.strengths: list[str] | None = None
        self.money: list[str] | None = None

    @property
    def name(self) -> str:
        joined = " ".join(self.name_parts).replace("Â", " ").replace(" ", " ")
        return re.sub(r"\s+", " ", joined).strip()

    @property
    def has_numbers(self) -> bool:
        return self.strengths is not None or self.money is not None


def parse_year(pdf: Path, budget_year: str, anomalies: list[str]) -> list[dict]:
    start = int(budget_year[:4])
    strength_years = (start - 1, start, start + 1)
    header_year_triple = [str(y) for y in strength_years]
    money_years = (
        f"{start - 2}-{start - 1}",  # actuals
        f"{start - 1}-{start}",      # RE
        f"{start}-{start + 1}",      # BE
    )

    rows: list[dict] = []
    ministry: str | None = None
    entity: _Entity | None = None

    def flush():
        nonlocal entity
        if entity is None:
            return
        if entity.has_numbers:
            if entity.strengths is None or entity.money is None:
                anomalies.append(
                    f"{budget_year}: incomplete numbers for '{entity.name}' "
                    f"(strengths={entity.strengths}, money={entity.money})"
                )
            s = entity.strengths or ["", "", ""]
            m = entity.money or [""] * 9
            rows.append({
                "budget_year": budget_year,
                "ministry": entity.name if entity.kind != "dept" else ministry,
                "department_or_org": entity.name,
                "strength_actual_1mar": s[0],
                "strength_actual_year": strength_years[0],
                "strength_est_re_1mar": s[1],
                "strength_est_re_year": strength_years[1],
                "strength_est_be_1mar": s[2],
                "strength_est_be_year": strength_years[2],
                "pay_actuals_cr": m[0],
                "allowances_actuals_cr": m[1],
                "travel_actuals_cr": m[2],
                "pay_re_cr": m[3],
                "allowances_re_cr": m[4],
                "travel_re_cr": m[5],
                "pay_be_cr": m[6],
                "allowances_be_cr": m[7],
                "travel_be_cr": m[8],
            })
        entity = None

    for raw in _statement_lines(pdf):
        line = raw.rstrip()
        if not line.strip():
            continue
        if _STOP_RE.search(line):
            break
        if _is_skip_line(line):
            continue

        toks = [m.group(1) for m in _NUM_RE.finditer(line)]
        # strip numbers out to get the name text
        name_text = re.sub(r"\s+", " ", _NUM_RE.sub(" ", line)).strip()

        # header sub-line carrying just the three 1st-March years
        if toks == header_year_triple and not name_text:
            continue
        # money-year header line e.g. "2024-2025   2025-2026   2026-2027"
        if not name_text and toks and all(
                t in [y for pair in money_years for y in pair.split("-")] for t in toks):
            continue
        # bare page number
        if not name_text and len(toks) == 1 and "." not in toks[0]:
            continue

        if "GRAND TOTAL" in line.upper():
            flush()
            entity = _Entity("total", "GRAND TOTAL")
        elif entity is not None and entity.kind == "total":
            pass  # keep the total's name canonical; numbers still attach below
        elif re.match(r"TOTAL\b", name_text):
            # subtotal row, e.g. "TOTAL (excluding Ministry of Railways)"
            flush()
            entity = _Entity("subtotal", name_text)
        else:
            m_min = _MINISTRY_RE.match(name_text)
            m_dept = _DEPT_RE.match(name_text)
            if m_min:
                flush()
                entity = _Entity("ministry", m_min.group(2))
                ministry = None  # ministry-with-numbers rows carry their own name
            elif m_dept:
                # a dept begins: the open ministry heading (if numberless)
                # becomes the current ministry context
                if entity is not None and entity.kind == "ministry" and not entity.has_numbers:
                    ministry = entity.name
                    entity = None
                flush()
                entity = _Entity("dept", m_dept.group(2))
            elif name_text and entity is not None:
                entity.name_parts.append(name_text)
            elif name_text and entity is None:
                anomalies.append(f"{budget_year}: orphan text '{name_text[:80]}'")

        # assign numbers
        if entity is not None and toks:
            ints = [t for t in toks if "." not in t and t != "..."]
            if len(toks) in (12, 13):
                # 13th token = page number printed at far right of the
                # page's last body line; drop it
                if entity.strengths is not None and entity.money is not None:
                    anomalies.append(
                        f"{budget_year}: full number row ignored (entity "
                        f"'{entity.name[:50]}' already filled): '{line.strip()[:80]}'")
                if entity.strengths is None:
                    entity.strengths = [_num(t) for t in toks[:3]]
                if entity.money is None:
                    entity.money = [_num(t) for t in toks[3:12]]
                if len(toks) == 13:
                    anomalies.append(
                        f"{budget_year}: dropped trailing token '{toks[12]}' "
                        f"(page no.) on '{line.strip()[:80]}'")
            elif len(toks) == 3 and len(ints) == 3 and entity.strengths is None:
                entity.strengths = [_num(t) for t in toks]
            elif len(toks) in (9, 10) and entity.money is None:
                # 10th token = trailing page number
                entity.money = [_num(t) for t in toks[:9]]
                if len(toks) == 10:
                    anomalies.append(
                        f"{budget_year}: dropped trailing token '{toks[9]}' "
                        f"(page no.) on '{line.strip()[:80]}'")
            else:
                anomalies.append(
                    f"{budget_year}: unassigned {len(toks)} numbers on "
                    f"'{line.strip()[:90]}'")

        if (entity is not None and entity.kind == "total"
                and entity.strengths is not None and entity.money is not None):
            flush()
            break  # statement ends at its grand total

    flush()
    return rows


def main() -> int:
    years = sorted(p.name for p in PDF_DIR.iterdir() if p.is_dir())
    all_rows: list[dict] = []
    anomalies: list[str] = []
    for fy in years:
        pdf = PDF_DIR / fy / "stat22.pdf"
        if not pdf.exists():
            pdf = PDF_DIR / fy / "vol1.pdf"
        if not pdf.exists():
            print(f"{fy}: no PDF found, skipping", file=sys.stderr)
            continue
        year_anoms: list[str] = []
        rows = parse_year(pdf, fy, year_anoms)
        data_rows = [r for r in rows
                     if not r["department_or_org"].startswith(("GRAND TOTAL", "TOTAL"))]
        total_rows = [r for r in rows if r["department_or_org"] == "GRAND TOTAL"]
        check = ""
        if total_rows:
            gt = total_rows[0]
            for col in ("strength_actual_1mar", "pay_be_cr"):
                parsed = sum(float(r[col]) for r in data_rows if r[col])
                stated = float(gt[col]) if gt[col] else None
                if stated is not None:
                    ok = abs(parsed - stated) < max(0.5, 0.001 * abs(stated))
                    check += f" {col}: parsed={parsed:.2f} stated={stated:.2f} {'OK' if ok else 'MISMATCH'};"
        print(f"{fy}: {len(data_rows)} rows, {len(year_anoms)} anomalies;{check}")
        for a in year_anoms:
            print(f"   ! {a}")
        all_rows.extend(rows)
        anomalies.extend(year_anoms)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {len(all_rows)} rows -> {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
