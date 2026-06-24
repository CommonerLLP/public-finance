# LMMHA — List of Major and Minor Heads of Account (Union & States)

**The canonical head-code → name classification for all Indian government budgets.**
Use this to label any `major_head` (4-digit) / `minor_head` (3-digit) in budget data.

- `LMMHA_CGA_2026.pdf` — official CGA / Ministry of Finance (Dept of Expenditure)
  edition, **correction slips incorporated up to 1097 dated 30-03-2026**. 520 pp.
  Source: https://cga.nic.in/Book/Published/7.aspx (filenameid=1957).
- `lmmha_parsed.json` — parsed lookup: 494 major heads + 3,919 minor heads,
  records `{code, level, name, parent_major}`. Parser:
  `twenty27/scripts/parse_lmmha.py` (2-column positional extraction).

## Standardization (why these codes are comparable across states)
Per **Article 150 of the Constitution**, the accounts of the Union and States are
kept in the form the President prescribes on the advice of the C&AG. This LMMHA
IS that prescribed list — **major (4-digit) and minor (3-digit) heads are uniform
across every state and the Union; a state cannot invent or change them.** Below
the minor head (sub-head/detailed/object head) states have latitude. So compare
across states at major/minor-head level; treat below-minor + booking-choice
differences with care.
