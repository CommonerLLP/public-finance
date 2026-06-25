import argparse
import csv
import io
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOLT_DIR = REPO_ROOT / "db" / "lmmha"
TIMELINE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_timeline.json"
CORRIGENDUM_TO_SLIP_RE = re.compile(r"\bcorrigendum\s+to\s+correction\s+slip\s+no\.?\s+(\d{3,4})\b", re.IGNORECASE)
CORRIGENDUM_RE = re.compile(r"\bcorrigendum\s+no\.?\s+(\d{1,4})\b", re.IGNORECASE)
CS_SEGMENT_RE = re.compile(r"\bcs\.?\s+((?:\d{3,4}\s*){1,8})", re.IGNORECASE)
SLIP_SEGMENT_RE = re.compile(
    r"\bcorrection\s+slips?\s*(?:nos?|numbers?|number)?(?:\s+from)?\s+((?:\d{3,4}\s*(?:(?:to|and|&|-)\s*)?){1,8})",
    re.IGNORECASE,
)


def empty_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def diff_value(row, prefix, name):
    return empty_to_none(row.get(f"{prefix}_{name}"))


def change_from_diff_row(row):
    diff_type = str(row.get("diff_type") or "").strip().lower()
    if diff_type == "added":
        return {
            "action": "INSERT",
            "code": diff_value(row, "to", "code"),
            "parent_code": diff_value(row, "to", "parent_code"),
            "type": diff_value(row, "to", "type"),
            "label": diff_value(row, "to", "label"),
        }

    if diff_type == "removed":
        return {
            "action": "DELETE",
            "code": diff_value(row, "from", "code"),
            "parent_code": diff_value(row, "from", "parent_code"),
            "type": diff_value(row, "from", "type"),
            "label": diff_value(row, "from", "label"),
        }

    if diff_type == "modified":
        code = diff_value(row, "to", "code") or diff_value(row, "from", "code")
        label = diff_value(row, "to", "label")
        old_label = diff_value(row, "from", "label")
        action = "RENAME" if old_label and label and old_label != label else "UPDATE"
        change = {
            "action": action,
            "code": code,
            "parent_code": diff_value(row, "to", "parent_code"),
            "type": diff_value(row, "to", "type"),
            "label": label,
        }
        if old_label and old_label != label:
            change["old_label"] = old_label
        old_code = diff_value(row, "from", "code")
        if old_code and old_code != code:
            change["old_code"] = old_code
        return change

    return None


def slip_number_range(start, end):
    if end <= start or end - start > 50:
        return [str(start), str(end)]
    return [str(number) for number in range(start, end + 1)]


def clean_trailing_file_id(numbers):
    while len(numbers) > 1 and numbers[-1] < numbers[-2]:
        numbers.pop()
    return numbers


def extract_slip_numbers(message):
    message = str(message or "")
    corrigendum = CORRIGENDUM_TO_SLIP_RE.search(message)
    if corrigendum:
        return [corrigendum.group(1)]

    match = SLIP_SEGMENT_RE.search(message)
    if not match:
        cs_match = CS_SEGMENT_RE.search(message)
        if not cs_match:
            return []
        numbers = clean_trailing_file_id([int(value) for value in re.findall(r"\d{3,4}", cs_match.group(1))])
        return [str(number) for number in numbers]

    segment = match.group(1)
    numbers = clean_trailing_file_id([int(value) for value in re.findall(r"\d{3,4}", segment)])

    if len(numbers) == 2:
        explicit_list = bool(re.search(r"\b(?:and|&)\b", segment, re.IGNORECASE))
        if not explicit_list:
            return slip_number_range(numbers[0], numbers[1])

    return [str(number) for number in numbers]


def compress_slip_numbers(numbers):
    if not numbers:
        return ""
    values = [int(number) for number in numbers]
    if len(values) == 1:
        return str(values[0])
    if values == list(range(values[0], values[-1] + 1)):
        return f"{values[0]}-{values[-1]}"
    return ", ".join(str(value) for value in values)


def slip_label(message):
    message = str(message or "")
    numbers = extract_slip_numbers(message)
    if numbers:
        suffix = compress_slip_numbers(numbers)
        if CORRIGENDUM_TO_SLIP_RE.search(message):
            return f"Corrigendum to Correction Slip No. {suffix}"
        if len(numbers) == 1:
            return f"Correction Slip No. {suffix}"
        return f"Correction Slip Nos. {suffix}"

    corrigendum = CORRIGENDUM_RE.search(message)
    if corrigendum:
        return f"Corrigendum No. {corrigendum.group(1)}"

    return ""


def source_entry_label(message):
    label = re.sub(r"^\s*Correction Slip:\s*", "", str(message or ""), flags=re.IGNORECASE).strip()
    label = re.sub(r"\s+\d{3,4}\s*$", "", label).strip()
    return label


def public_event_message(message):
    return slip_label(message) or source_entry_label(message)


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def run_dolt_csv(query, dolt_dir=DOLT_DIR):
    result = subprocess.run(
        ["dolt", "sql", "-r", "csv", "-q", query],
        cwd=Path(dolt_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Dolt query failed:\n{query}\n\n{result.stderr}")

    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def load_correction_slip_commits(dolt_dir=DOLT_DIR):
    return run_dolt_csv(
        """
        select commit_hash, parents, date, message, commit_order
        from dolt_log
        where message like 'Correction Slip:%'
        order by commit_order asc
        """,
        dolt_dir=dolt_dir,
    )


def diff_commit(parent_hash, commit_hash, dolt_dir=DOLT_DIR):
    query = (
        "select * from dolt_diff("
        f"{sql_literal(parent_hash)}, {sql_literal(commit_hash)}, 'lmmha'"
        ")"
    )
    return run_dolt_csv(query, dolt_dir=dolt_dir)


def event_from_commit(commit, dolt_dir=DOLT_DIR):
    parent_hash = empty_to_none(str(commit.get("parents") or "").split(",", 1)[0])
    if not parent_hash:
        return None

    changes = []
    for row in diff_commit(parent_hash, commit["commit_hash"], dolt_dir=dolt_dir):
        change = change_from_diff_row(row)
        if change and change.get("code"):
            changes.append(change)

    label = slip_label(commit["message"])
    public_message = label or source_entry_label(commit["message"])
    event = {
        "date": str(commit["date"])[:10],
        "commit_hash": commit["commit_hash"],
        "parent_hash": parent_hash,
        "message": public_message,
        "changes": changes,
    }
    numbers = extract_slip_numbers(commit["message"])
    if numbers:
        event["slip_numbers"] = numbers
    if label:
        event["slip_label"] = label
    else:
        event["source_label"] = public_message

    return event


def build_timeline(dolt_dir=DOLT_DIR):
    events = []
    for commit in load_correction_slip_commits(dolt_dir=dolt_dir):
        event = event_from_commit(commit, dolt_dir=dolt_dir)
        if event:
            events.append(event)

    date_range = ""
    if events:
        date_range = f" Exported correction-slip events run from {events[0]['date']} through {events[-1]['date']}."

    return {
        "generated_by": "publicfinance/lmmha_history.py",
        "source": "Dolt correction-slip history ledger, table lmmha",
        "coverage_note": (
            "The LMMHA begins before the machine-readable base used here. "
            "This timeline tracks the 2001 base imported into Dolt and later "
            "correction-slip commits represented in the export ledger."
            f"{date_range}"
        ),
        "events": events,
    }


def write_timeline(output_path=TIMELINE_JSON, dolt_dir=DOLT_DIR):
    payload = build_timeline(dolt_dir=dolt_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(payload['events'])} Dolt correction-slip events to {output_path}.")
    return payload


def main():
    parser = argparse.ArgumentParser(description="Export LMMHA Dolt correction-slip history to JSON.")
    parser.add_argument("--dolt-dir", default=str(DOLT_DIR))
    parser.add_argument("--output", default=str(TIMELINE_JSON))
    args = parser.parse_args()
    write_timeline(output_path=args.output, dolt_dir=args.dolt_dir)


if __name__ == "__main__":
    main()
