import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s*\(\d+\)\s*', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def row_texts(row):
    values = []
    for cell in row.find_all('td'):
        colspan = int(cell.get('colspan') or 1)
        values.append(clean_text(cell.get_text()))
        values.extend([""] * (colspan - 1))

    return values


def first_non_empty_after(values, index):
    for value in values[index + 1:]:
        if value:
            return value
    return ""


def find_major(values):
    for index, value in enumerate(values):
        if re.match(r'^\d{4}$', value):
            return index, value, first_non_empty_after(values, index)
    return None, None, None


def find_sub_major(values):
    for index, value in enumerate(values):
        sub_match = re.match(r'^(\d{2})(?:\s*[-.]\s*|\s+)(.+)$', value)
        if sub_match:
            return sub_match.group(1), sub_match.group(2)

        if re.match(r'^\d{2}$', value):
            label = first_non_empty_after(values, index)
            if label and not re.match(r'^\d{3}$', label):
                return value, label

    return None, None


def find_minor(values):
    for index, value in enumerate(values):
        if re.match(r'^\d{3}$', value):
            label = first_non_empty_after(values, index)
            if label:
                return value, label
    return None, None


def add_head(heads, seen, head):
    existing = seen.get(head["code"])
    if existing:
        comparable = {k: existing.get(k) for k in ("type", "parent_code", "description")}
        incoming = {k: head.get(k) for k in ("type", "parent_code", "description")}
        if comparable != incoming:
            raise ValueError(f"Conflicting LMMHA code {head['code']}: {comparable} != {incoming}")
        return

    heads.append(head)
    seen[head["code"]] = head


def parse_html_files(input_dir=None, output_path=None):
    input_dir = Path(input_dir) if input_dir else REPO_ROOT / "references" / "lmmha" / "base_html"
    output_path = Path(output_path) if output_path else REPO_ROOT / "references" / "lmmha" / "lmmha_base_2001.json"
    files = sorted(input_dir.glob("part*.htm"))
    heads = []
    seen = {}

    for filepath in files:
        with open(filepath, 'r', encoding='windows-1252', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

            tables = soup.find_all('table')
            current_major = None
            current_sub_major = None

            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    if not row.find_all('td'):
                        continue

                    values = row_texts(row)
                    if not any(values):
                        continue

                    header_text = " ".join(values).upper()
                    if "MAJOR / SUB-MAJOR HEADS" in header_text or "MINOR HEADS" in header_text:
                        continue

                    _, major_code, major_label = find_major(values)
                    if major_code:
                        current_major = major_code
                        current_sub_major = None
                        add_head(heads, seen, {
                            "code": current_major,
                            "parent_code": None,
                            "type": "Major Head",
                            "description": major_label,
                            "major_head": current_major,
                            "sub_major_head": None,
                            "minor_head": None,
                        })

                    sub_code, sub_label = find_sub_major(values)
                    if sub_code and current_major:
                        current_sub_major = sub_code
                        code = f"{current_major}-{current_sub_major}"
                        add_head(heads, seen, {
                            "code": code,
                            "parent_code": current_major,
                            "type": "Sub-Major Head",
                            "description": sub_label,
                            "major_head": current_major,
                            "sub_major_head": current_sub_major,
                            "minor_head": None,
                        })

                    minor_code, minor_label = find_minor(values)
                    if minor_code and minor_label:
                        if not current_major:
                            continue

                        sub_major = current_sub_major or "00"
                        code = f"{current_major}-{sub_major}-{minor_code}"
                        parent_code = current_major if sub_major == "00" else f"{current_major}-{sub_major}"
                        add_head(heads, seen, {
                            "code": code,
                            "parent_code": parent_code,
                            "type": "Minor Head",
                            "description": minor_label,
                            "major_head": current_major,
                            "sub_major_head": sub_major,
                            "minor_head": minor_code,
                        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(heads, f, indent=2)

    print(f"Successfully extracted {len(heads)} heads to {output_path}")
    return heads


if __name__ == "__main__":
    parse_html_files()
