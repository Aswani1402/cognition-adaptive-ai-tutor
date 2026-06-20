# scripts/db_audit/check_new_rag_tables.py

import sqlite3
from pathlib import Path

NEW_DB = Path("rag_dyna/core_data/tutor.db")

def main():
    conn = sqlite3.connect(NEW_DB)
    cur = conn.cursor()

    for table in ["rag_chunks", "rag_resource_bundle"]:
        print(f"\n=== {table} ===")

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print("Row count:", count)

        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        print("Columns:")
        for col in cols:
            print(col)

        cur.execute(f"SELECT * FROM {table} LIMIT 3")
        rows = cur.fetchall()
        print("Sample rows:")
        for row in rows:
            print(row)

    conn.close()

if __name__ == "__main__":
    main()