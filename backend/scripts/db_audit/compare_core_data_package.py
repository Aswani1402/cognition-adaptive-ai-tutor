# scripts/db_audit/compare_core_data_package.py

import sqlite3
from pathlib import Path

OLD_DIR = Path("external/core_data")
NEW_DIR = Path("core_data-20260407T085229Z/core_data")

DBS = [
    "tutor.db",
    "python_learning.db",
    "html_web_basics.db",
    "database_sql.db",
    "git_version_control.db",
    "data_structures.db",
]

def get_tables_and_counts(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    tables = [r[0] for r in cur.fetchall()]

    result = {}
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
        except Exception as e:
            count = f"ERROR: {e}"
        result[table] = count

    conn.close()
    return result

def main():
    for db_name in DBS:
        old_db = OLD_DIR / db_name
        new_db = NEW_DIR / db_name

        print(f"\n===== {db_name} =====")

        if not old_db.exists():
            print(f"OLD missing: {old_db}")
            continue
        if not new_db.exists():
            print(f"NEW missing: {new_db}")
            continue

        old_info = get_tables_and_counts(old_db)
        new_info = get_tables_and_counts(new_db)

        all_tables = sorted(set(old_info) | set(new_info))

        for table in all_tables:
            old_count = old_info.get(table, "MISSING")
            new_count = new_info.get(table, "MISSING")
            status = "SAME" if old_count == new_count else "DIFF"
            print(f"{table}: old={old_count} | new={new_count} | {status}")

if __name__ == "__main__":
    main()