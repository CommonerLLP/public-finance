# Generated helper — builds the compact payload for the LMMHA public browser.
# DO NOT hand-edit the output (viz/lmmha_browser.json); rerun this script.
#
# Sources (all clean, repaired-key data):
#   references/lmmha/lmmha_base_2001.json        5,768 codes, 3-part keys
#   references/lmmha/lmmha_scope_notes_2001.json 1,046 scope notes
#   references/lmmha/lmmha_timeline.json         205 cleaned correction-slip events (2012-2026)
#
# Output: viz/lmmha_browser.json  — a single compact fetch for the static browser.

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REF = REPO / "references" / "lmmha"
OUT = REF / "lod" / "lmmha_browser.json"   # emit into the published deploy dir

# The six account classes, keyed by the first digit of the four-digit Major Head.
# Basis: Government Accounting Rules 1990 / CAG "Structure of Government Accounts".
# This is the frame the public page must teach before it exposes the vocabulary.
ACCOUNT_CLASSES = [
    {"key": "0", "digits": "0, 1", "name": "Revenue Receipts",
     "summary": "What the government earns in a year: tax revenue, non-tax revenue, and grants-in-aid.",
     "detail": "Heads beginning 0 or 1. Tax revenue (e.g. 0020 Corporation Tax, 0021 Taxes on Income), "
               "non-tax revenue (interest, dividends, fees), and grants-in-aid received."},
    {"key": "2", "digits": "2, 3", "name": "Revenue Expenditure",
     "summary": "What the government spends running the state: salaries, subsidies, grants, services.",
     "detail": "Heads beginning 2 or 3. Spending that does not create a lasting physical asset — "
               "e.g. 2202 General Education, 2210 Medical and Public Health, 2235 Social Security and Welfare."},
    {"key": "4", "digits": "4, 5", "name": "Capital Expenditure",
     "summary": "Spending that builds lasting assets: buildings, roads, irrigation, equipment.",
     "detail": "Heads beginning 4 or 5 — e.g. 4202 Capital Outlay on Education, Sports, Art and Culture. "
               "Head 4000 is the single Capital Receipt head."},
    {"key": "6", "digits": "6, 7", "name": "Public Debt, Loans and Advances",
     "summary": "Money the government borrows, and loans it gives out and recovers.",
     "detail": "Heads beginning 6 or 7. Public debt (6001 Internal Debt), and loans and advances by the "
               "government to states, bodies and individuals. 7999 is the appropriation to the Contingency Fund."},
    {"key": "8", "digits": "8", "name": "Contingency Fund and Public Account",
     "summary": "Money the government holds but does not own outright: deposits, reserves, suspense.",
     "detail": "Heads beginning 8. The Contingency Fund (8000) and the Public Account (8001 onward) — "
               "small savings, provident funds, deposits, reserve funds and remittances held in trust."},
]


def class_key_for(code):
    """First digit of the major head -> account-class group key."""
    d = code[0]
    if d in "01":
        return "0"
    if d in "23":
        return "2"
    if d in "45":
        return "4"
    if d in "67":
        return "6"
    return "8"


def load(name):
    return json.loads((REF / name).read_text(encoding="utf-8"))


def main():
    base = load("lmmha_base_2001.json")
    notes_doc = load("lmmha_scope_notes_2001.json")
    timeline = load("lmmha_timeline.json")

    # --- nodes: compact keys to keep the payload small ---
    # c=code p=parent t=type d=description k=account-class g=group(mh) s=submajor m=minor
    nodes = []
    for r in base:
        nodes.append({
            "c": r["code"],
            "p": r["parent_code"],
            "t": r["type"],
            "d": r["description"],
            "k": class_key_for(r["code"]),
            "mh": r["major_head"],
            "sm": r["sub_major_head"],
            "mn": r["minor_head"],
        })

    # --- scope notes: code -> [note, ...] (a code can carry several numbered notes) ---
    notes = {}
    for n in notes_doc["notes"]:
        notes.setdefault(n["code"], []).append({
            "num": n.get("note_number"),
            "text": n["note"],
        })

    # --- timeline events: keep cleaned label + changes; tag the major heads each touches ---
    # Events are keyed on legacy flattened codes, so we record the major head (reliable join)
    # and the raw change code (best-effort minor join, flagged in the UI).
    events = []
    for e in timeline["events"]:
        changes = []
        majors = set()
        for ch in e.get("changes", []):
            code = ch.get("code") or ""
            mh = code.split("-")[0] if code else None
            if mh:
                majors.add(mh)
            changes.append({
                "action": ch.get("action"),
                "code": code,
                "mh": mh,
                "type": ch.get("type"),
                "label": ch.get("label"),
                "old_label": ch.get("old_label"),
            })
        events.append({
            "date": e.get("date"),
            "slip": e.get("message"),
            "majors": sorted(majors),
            "changes": changes,
        })

    payload = {
        "meta": {
            "title": "List of Major and Minor Heads of Account (LMMHA)",
            "base_year": 2001,
            "counts": {
                "total": len(nodes),
                "major": sum(1 for n in nodes if n["t"] == "Major Head"),
                "sub_major": sum(1 for n in nodes if n["t"] == "Sub-Major Head"),
                "minor": sum(1 for n in nodes if n["t"] == "Minor Head"),
                "notes": sum(len(v) for v in notes.values()),
                "events": len(events),
            },
            "timeline_coverage": timeline.get("coverage_note", ""),
            "source": "Controller General of Accounts (CGA), Government of India",
        },
        "classes": ACCOUNT_CLASSES,
        "nodes": nodes,
        "notes": notes,
        "events": events,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT.relative_to(REPO)}  ({kb:.0f} KB)")
    print(f"  nodes={len(nodes)}  notes_codes={len(notes)}  events={len(events)}")


if __name__ == "__main__":
    main()
