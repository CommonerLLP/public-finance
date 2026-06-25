import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_HTML_DIR = REPO_ROOT / "references" / "lmmha" / "base_html"
SCOPE_NOTES_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_scope_notes_2001.json"

NOTE_MARKER_RE = re.compile(r"\(\s*(\d+)\s*\)")
NOTE_START_RE = re.compile(r"^\(?\s*(\d+)\s*\)\s*(.+)$")


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def label_markers(label):
    return [marker.lstrip("0") or "0" for marker in NOTE_MARKER_RE.findall(label or "")]


def row_texts(row):
    values = []
    for cell in row.find_all("td"):
        colspan = int(cell.get("colspan") or 1)
        values.append(clean_text(cell.get_text(" ")))
        values.extend([""] * (colspan - 1))
    return values


def first_non_empty_after(values, index):
    for value in values[index + 1:]:
        if value:
            return value
    return ""


def find_major(values):
    for index, value in enumerate(values):
        if re.match(r"^\d{4}$", value):
            return value, first_non_empty_after(values, index)
    return None, None


def find_sub_major(values):
    for index, value in enumerate(values):
        sub_match = re.match(r"^(\d{2})(?:\s*[-.]\s*|\s+)(.+)$", value)
        if sub_match:
            return sub_match.group(1), sub_match.group(2)

        if re.match(r"^\d{2}$", value):
            label = first_non_empty_after(values, index)
            if label and not re.match(r"^\d{3}$", label):
                return value, label
    return None, None


def find_minor(values):
    for index, value in enumerate(values):
        if re.match(r"^\d{3}$", value):
            label = first_non_empty_after(values, index)
            if label:
                return value, label
    return None, None


def add_markers(marker_to_codes, code, label):
    for marker in label_markers(label):
        marker_to_codes.setdefault(marker, []).append(code)


def note_paragraphs_after(table):
    paragraphs = []
    for sibling in table.next_siblings:
        if getattr(sibling, "name", None) == "table":
            break
        if not hasattr(sibling, "find_all"):
            continue
        if getattr(sibling, "name", None) == "p":
            paragraphs.append(clean_text(sibling.get_text(" ")))
        for paragraph in sibling.find_all("p"):
            paragraphs.append(clean_text(paragraph.get_text(" ")))
    return [text for text in paragraphs if text]


def notes_by_number_after(table):
    notes = {}
    current_number = None
    for text in note_paragraphs_after(table):
        heading = text.strip().lower().rstrip(":")
        if heading in {"note", "notes"}:
            continue

        match = NOTE_START_RE.match(text)
        if match:
            current_number = match.group(1).lstrip("0") or "0"
            notes[current_number] = clean_text(match.group(2))
        elif current_number:
            notes[current_number] = clean_text(notes[current_number] + " " + text)
    return notes


def parse_table_notes(table, source_name):
    current_major = None
    current_sub_major = None
    marker_to_codes = {}

    for row in table.find_all("tr"):
        values = row_texts(row)
        if not any(values):
            continue

        header_text = " ".join(values).upper()
        if "MAJOR / SUB-MAJOR HEADS" in header_text or "MINOR HEADS" in header_text:
            continue

        major_code, major_label = find_major(values)
        if major_code:
            current_major = major_code
            current_sub_major = None
            add_markers(marker_to_codes, current_major, major_label)

        sub_code, sub_label = find_sub_major(values)
        if sub_code and current_major:
            current_sub_major = sub_code
            add_markers(marker_to_codes, f"{current_major}-{current_sub_major}", sub_label)

        minor_code, minor_label = find_minor(values)
        if minor_code and minor_label and current_major:
            sub_major = current_sub_major or "00"
            code = f"{current_major}-{sub_major}-{minor_code}"
            add_markers(marker_to_codes, code, minor_label)

    note_texts = notes_by_number_after(table)
    notes = []
    seen = set()
    for number, codes in marker_to_codes.items():
        note_text = note_texts.get(number)
        if not note_text:
            continue
        for code in codes:
            key = (code, number, note_text)
            if key in seen:
                continue
            notes.append(
                {
                    "code": code,
                    "note_number": number,
                    "note": note_text,
                    "source": source_name,
                }
            )
            seen.add(key)
    return notes


def parse_html_string(html, source_name="<string>"):
    soup = BeautifulSoup(html, "html.parser")
    notes = []
    for table in soup.find_all("table"):
        notes.extend(parse_table_notes(table, source_name=source_name))
    return notes


def parse_html_file(path):
    path = Path(path)
    html = path.read_text(encoding="windows-1252", errors="ignore")
    return parse_html_string(html, source_name=path.name)


def build_scope_notes(input_dir=BASE_HTML_DIR):
    notes = []
    seen = set()
    for path in sorted(Path(input_dir).glob("part*.htm")):
        for note in parse_html_file(path):
            key = (note["code"], note["note_number"], note["note"], note["source"])
            if key in seen:
                continue
            notes.append(note)
            seen.add(key)

    notes.sort(key=lambda item: (item["code"], int(item["note_number"]), item["source"]))
    return {
        "generated_by": "publicfinance/lmmha_notes.py",
        "source": "converted CGA LMMHA base HTML",
        "coverage_note": (
            "Notes are extracted when a numbered note marker is attached to a "
            "parsed major, sub-major, or minor head label and matching note text "
            "appears immediately after that table."
        ),
        "notes": notes,
    }


def write_scope_notes(input_dir=BASE_HTML_DIR, output_path=SCOPE_NOTES_JSON):
    payload = build_scope_notes(input_dir=input_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(payload['notes'])} LMMHA scope notes to {output_path}.")
    return payload


def main():
    parser = argparse.ArgumentParser(description="Extract numbered LMMHA scope notes from converted base HTML.")
    parser.add_argument("--input-dir", default=str(BASE_HTML_DIR))
    parser.add_argument("--output", default=str(SCOPE_NOTES_JSON))
    args = parser.parse_args()
    write_scope_notes(input_dir=args.input_dir, output_path=args.output)


if __name__ == "__main__":
    main()
