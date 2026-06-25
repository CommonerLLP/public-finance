import os
import glob
import json
import re
import time
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOLT_DIR = REPO_ROOT / "db" / "lmmha"


def clean_code(value, width):
    text = re.sub(r"\D", "", str(value or ""))
    if not text:
        return ""
    if len(text) > width:
        raise ValueError(f"Expected a {width}-digit code, got {value!r}")
    return text.zfill(width)


def normalise_change(change):
    action = str(change.get("action", "")).strip().upper()
    if action not in {"INSERT", "DELETE", "RENAME"}:
        raise ValueError(f"Unsupported correction-slip action: {change!r}")

    major = clean_code(change.get("major_head"), 4)
    sub_major = clean_code(change.get("sub_major_head") or change.get("submajor_head"), 2)
    raw_minor = re.sub(r"\D", "", str(change.get("minor_head") or ""))
    label = str(change.get("label") or "").strip()

    if not major:
        raise ValueError(f"Correction-slip change is missing major_head: {change!r}")

    if raw_minor and len(raw_minor) == 2 and not sub_major:
        sub_major = raw_minor
        minor = ""
    elif raw_minor:
        minor = clean_code(raw_minor, 3)
    else:
        minor = ""

    if minor:
        sub_major = sub_major or "00"
        code = f"{major}-{sub_major}-{minor}"
        parent_code = major if sub_major == "00" else f"{major}-{sub_major}"
        head_type = "Minor Head"
    elif sub_major:
        code = f"{major}-{sub_major}"
        parent_code = major
        head_type = "Sub-Major Head"
    else:
        code = major
        parent_code = None
        head_type = "Major Head"

    major_int = int(major)
    return {
        "action": action,
        "code": code,
        "parent_code": parent_code,
        "type": head_type,
        "label": label,
        "is_receipt": 1 if major_int < 4000 else 0,
        "is_expenditure": 1 if major_int >= 2000 else 0,
    }


def sql_literal(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"

def process_pdf(client, file_path):
    print(f"Uploading and processing {file_path} with Gemini Vision...", flush=True)

    prompt = """
    You are an expert accountant parsing Indian Government Correction Slips for the List of Major and Minor Heads of Account (LMMHA).
    Extract all structural changes mandated in this Correction Slip PDF.
    Return ONLY a JSON array of objects. Each object MUST have:
    - "action": strictly one of "INSERT", "DELETE", or "RENAME"
    - "major_head": the 4-digit Major Head code (e.g. "0075")
    - "sub_major_head": the 2-digit Sub-Major Head code if the change is under a Sub-Major Head, otherwise blank or empty
    - "minor_head": the 3-digit Minor Head code (e.g. "109"). If the change is to the Major Head or Sub-Major Head itself, leave blank or empty.
    - "label": The textual name of the head (e.g. "Penal Guarantee Fees")
    - "effective_year": e.g. "2026-27" if specified, else ""

    If there are no changes or it is unreadable, return an empty array [].
    ONLY return raw JSON. Do not include markdown formatting or backticks like ```json.
    """

    try:
        # Upload the file
        uploaded_file = client.files.upload(file=file_path)

        # Generate content with gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt]
        )

        # Clean up the file immediately
        client.files.delete(name=uploaded_file.name)

        content = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        error_msg = str(e)
        if "The document has no pages" in error_msg or "INVALID_ARGUMENT" in error_msg:
            print(f"Warning: Corrupted or empty PDF {file_path}. Skipping and treating as 0 changes.", flush=True)
            return []
        else:
            print(f"FATAL ERROR on {file_path}: {e}", flush=True)
            exit(1)

def run_dolt_sql(sql, dolt_dir):
    res = subprocess.run(["dolt", "sql", "-q", sql], cwd=dolt_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to execute SQL:\n{sql}\n\n{res.stderr}")


def apply_to_dolt(changes, date_str, title_str, dolt_dir=None):
    dolt_dir = Path(dolt_dir) if dolt_dir else DOLT_DIR
    for change in changes:
        normalised = normalise_change(change)
        action = normalised["action"]
        code = sql_literal(normalised["code"])
        parent_code = sql_literal(normalised["parent_code"])
        head_type = sql_literal(normalised["type"])
        label = sql_literal(normalised["label"])

        if action == "INSERT":
            sql = (
                "INSERT INTO lmmha (code, parent_code, type, label, is_receipt, is_expenditure) "
                f"VALUES ({code}, {parent_code}, {head_type}, {label}, "
                f"{normalised['is_receipt']}, {normalised['is_expenditure']});"
            )
        elif action == "RENAME":
            sql = f"UPDATE lmmha SET label = {label} WHERE code = {code};"
        else:
            sql = f"DELETE FROM lmmha WHERE code = {code};"

        run_dolt_sql(sql, dolt_dir)

    # ALWAYS commit, even if empty, so it doesn't get re-processed infinitely!
    subprocess.run(["dolt", "add", "."], cwd=dolt_dir, capture_output=True, check=True)
    subprocess.run(["dolt", "commit", "--allow-empty", "--date", f"{date_str}T12:00:00Z", "-m", f"Correction Slip: {title_str}"], cwd=dolt_dir, capture_output=True, check=True)
    print(f"Committed changes for {title_str}", flush=True)

def main():
    from dotenv import load_dotenv
    from google import genai

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set in .env", flush=True)
        return

    client = genai.Client(api_key=api_key)

    # Pre-fetch dolt logs to know what's already processed
    res = subprocess.run(["dolt", "log", "--oneline"], cwd=DOLT_DIR, capture_output=True, text=True)
    dolt_log_output = res.stdout

    pdfs = sorted(glob.glob(str(REPO_ROOT / "references" / "lmmha" / "correction_slips" / "pdfs" / "*.pdf")))
    print(f"Found {len(pdfs)} total PDFs.", flush=True)

    for pdf_path in pdfs:
        filename = os.path.basename(pdf_path)

        parts = filename.split('_')
        date_str = parts[0]
        title_str = " ".join(parts[1:]).replace(".pdf", "")

        # Check if already in dolt
        if f"Correction Slip: {title_str}" in dolt_log_output:
            continue

        print(f"\n--- Processing {filename} ---", flush=True)
        changes = process_pdf(client, pdf_path)
        print(f"Extracted changes: {json.dumps(changes, indent=2)}", flush=True)
        apply_to_dolt(changes, date_str, title_str)

        # Sleep to be polite to the API and respect 15 RPM limit
        time.sleep(4)

if __name__ == "__main__":
    main()
