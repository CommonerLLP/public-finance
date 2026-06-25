import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_base_2001.json"
DOLT_DIR = REPO_ROOT / "db" / "lmmha"


def sql_literal(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def normalise_heads(heads):
    rows = []
    seen = {}

    for head in heads:
        code = str(head.get("code") or "").strip()
        label = str(head.get("label") or head.get("description") or "").strip()
        type_value = str(head.get("type") or "").strip()
        parent_code = head.get("parent_code")
        if parent_code == "":
            parent_code = None

        if not code or not label or not type_value:
            raise ValueError(f"Incomplete LMMHA row: {head!r}")

        major = int(code.split("-", 1)[0])
        row = {
            "code": code,
            "parent_code": parent_code,
            "type": type_value,
            "label": label,
            "is_receipt": 1 if major < 4000 else 0,
            "is_expenditure": 1 if major >= 2000 else 0,
        }

        existing = seen.get(code)
        if existing:
            if existing != row:
                raise ValueError(f"Conflicting LMMHA code {code}: {existing!r} != {row!r}")
            continue

        rows.append(row)
        seen[code] = row

    codes = set(seen)
    missing_parents = sorted({row["parent_code"] for row in rows if row["parent_code"] and row["parent_code"] not in codes})
    if missing_parents:
        raise ValueError(f"Missing parent LMMHA codes: {missing_parents}")

    return rows


def run_dolt_sql(sql, dolt_dir):
    res = subprocess.run(["dolt", "sql", "-q", sql], cwd=dolt_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to execute SQL:\n{sql}\n\n{res.stderr}")


def seed_database(input_path=BASE_JSON, dolt_dir=DOLT_DIR):
    input_path = Path(input_path)
    dolt_dir = Path(dolt_dir)
    with input_path.open("r", encoding="utf-8") as f:
        rows = normalise_heads(json.load(f))

    run_dolt_sql(
        """
        CREATE TABLE IF NOT EXISTS lmmha (
            code VARCHAR(30) NOT NULL,
            parent_code VARCHAR(30),
            type VARCHAR(50),
            label VARCHAR(255),
            is_receipt BOOLEAN,
            is_expenditure BOOLEAN,
            PRIMARY KEY (code)
        );
        """,
        dolt_dir,
    )
    run_dolt_sql("DELETE FROM lmmha;", dolt_dir)

    batch_size = 500
    for index in range(0, len(rows), batch_size):
        values = []
        for row in rows[index:index + batch_size]:
            values.append(
                "("
                f"{sql_literal(row['code'])}, "
                f"{sql_literal(row['parent_code'])}, "
                f"{sql_literal(row['type'])}, "
                f"{sql_literal(row['label'])}, "
                f"{row['is_receipt']}, "
                f"{row['is_expenditure']}"
                ")"
            )

        sql = (
            "INSERT INTO lmmha (code, parent_code, type, label, is_receipt, is_expenditure) VALUES "
            + ", ".join(values)
            + ";"
        )
        run_dolt_sql(sql, dolt_dir)

    subprocess.run(["dolt", "add", "."], cwd=dolt_dir, check=True)
    subprocess.run(
        ["dolt", "commit", "-m", "Seed Dolt DB with true 2001 Base Edition from parsed HTML"],
        cwd=dolt_dir,
        check=True,
    )
    print(f"Inserted and committed {len(rows)} LMMHA rows from {input_path}.")


if __name__ == "__main__":
    seed_database()
