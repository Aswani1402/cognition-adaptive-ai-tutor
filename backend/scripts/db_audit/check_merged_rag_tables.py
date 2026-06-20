# scripts/db_audit/check_merged_rag_tables.py

import sqlite3
from pathlib import Path

DB = Path("external/core_data/tutor.db")

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for table in ["rag_chunks", "rag_resource_bundle"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count}")

    conn.close()

if __name__ == "__main__":
    main()