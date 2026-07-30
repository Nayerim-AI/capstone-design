"""
Backfill CSV measurement_log.csv -> SQLite database capstone.db

This migrates historical CSV data into the database.
Note: raw_measurements table cannot be backfilled (CSV only has averages).
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, insert_measurement

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "measurement_log.csv"


def backfill_csv_to_db():
    """Migrate all rows from measurement_log.csv to SQLite."""
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        return 0

    init_db()

    count = 0
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert empty strings to None
            cleaned = {k: (v if v != "" else None) for k, v in row.items()}

            # Insert without raw_measurements (CSV doesn't have individual samples)
            try:
                insert_measurement(cleaned, raw_measurements=None, session_id=None)
                count += 1
            except Exception as e:
                print(f"  Failed row {count+1}: {e}")

    print(f"Backfilled {count} measurements from CSV to database")
    return count


if __name__ == "__main__":
    backfill_csv_to_db()
