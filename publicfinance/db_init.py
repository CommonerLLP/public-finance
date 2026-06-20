import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import ensure_db


def init_db(db_path="db/budget_metadata.db"):
    """Initializes the SQLite database for tracking budget documents."""
    ensure_db(db_path)
    print(f"Database initialized at {db_path}")


if __name__ == "__main__":
    os.makedirs("db", exist_ok=True)
    init_db("db/budget_metadata.db")
