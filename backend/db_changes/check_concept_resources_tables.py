# db_changes/check_concept_resources_tables.py

import sqlite3
from pathlib import Path

DB_FILES = [
    "external/core_data/python_learning.db",
    "external/core_data/database_sql.db",
    "external/core_data/html_web_basics.db",
    "external/core_data/git_version_control.db",
    "external/core_data/data_structures.db",
]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS concept_resources (
    concept_id TEXT PRIMARY KEY,
    topic TEXT,
    base_content TEXT,
    examples TEXT,
    key_points TEXT,
    misconceptions TEXT,
    real_world_use TEXT,
    next_concept_link TEXT
);
"""

def main():
    for db_path in DB_FILES:
        print(f"\nChecking: {db_path}")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute(CREATE_SQL)
        conn.commit()

        cur.execute("PRAGMA table_info(concept_resources);")
        columns = cur.fetchall()

        if columns:
            print("concept_resources table exists.")
            print("Columns:")
            for col in columns:
                print(col)
        else:
            print("concept_resources table NOT found.")

        cur.execute("SELECT COUNT(*) FROM concept_resources;")
        count = cur.fetchone()[0]
        print(f"Row count: {count}")

        conn.close()

if __name__ == "__main__":
    main()