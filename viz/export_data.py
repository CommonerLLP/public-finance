import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOLT_DIR = REPO_ROOT / "db" / "lmmha"
OUTPUT_PATH = REPO_ROOT / "viz" / "data.json"


def run_dolt(args, dolt_dir):
    res = subprocess.run(["dolt", *args], cwd=dolt_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"dolt {' '.join(args)} failed:\n{res.stderr}")
    return res.stdout


def export_timeseries(output_path=OUTPUT_PATH, dolt_dir=DOLT_DIR):
    print("Fetching timeline of commits...")
    dolt_dir = Path(dolt_dir)
    output_path = Path(output_path)
    log_output = run_dolt(
        ["sql", "-q", "SELECT commit_hash, date, message FROM dolt_log ORDER BY date ASC;", "-r", "json"],
        dolt_dir,
    )
    commits = json.loads(log_output).get("rows", [])

    print("Fetching commit diffs...")
    timeline = []

    for index, commit in enumerate(commits):
        commit_hash = commit["commit_hash"]
        commit_date = commit["date"]
        commit_message = commit["message"]

        if "Initial commit" in commit_message or "Seed Dolt DB" in commit_message or "fix(data): Re-parse" in commit_message:
            continue

        diff_output = run_dolt(["diff", "-r", "json", f"{commit_hash}^", commit_hash, "lmmha"], dolt_dir)

        try:
            diff = json.loads(diff_output)
        except json.JSONDecodeError:
            continue

        if not diff.get("tables") or not diff["tables"][0].get("data_diff"):
            continue

        cleaned_diffs = []
        for item in diff["tables"][0]["data_diff"]:
            from_row = item.get("from_row", {})
            to_row = item.get("to_row", {})

            if not from_row and to_row:
                action = "INSERT"
                row = to_row
            elif from_row and not to_row:
                action = "DELETE"
                row = from_row
            else:
                action = "RENAME"
                row = to_row

            cleaned_diffs.append({
                "action": action,
                "code": row.get("code"),
                "parent_code": row.get("parent_code"),
                "type": row.get("type"),
                "label": row.get("label"),
                "old_label": from_row.get("label") if action == "RENAME" else None,
            })

        timeline.append({
            "date": commit_date.split(" ")[0],
            "message": commit_message.replace("Correction Slip: ", "").strip(),
            "changes": cleaned_diffs,
        })

        if index % 10 == 0:
            print(f"Processed {index}/{len(commits)} commits...")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2)
    print(f"Exported {len(timeline)} events to {output_path}")


if __name__ == "__main__":
    export_timeseries()
