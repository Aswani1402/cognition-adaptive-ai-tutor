# scripts/db_audit/merge_rag_tables.py

import sqlite3
from pathlib import Path

CURRENT_DB = Path("external/core_data/tutor.db")
PACKAGE_DB = Path("rag_dyna/core_data/tutor.db")

TABLES = ["rag_chunks", "rag_resource_bundle"]


def create_table_from_source(dst_cur, src_cur, table_name):
    row = src_cur.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()

    if not row or not row[0]:
        raise ValueError(f"Could not find schema for table: {table_name}")

    dst_cur.execute(row[0])


def copy_rows(dst_cur, src_cur, table_name):
    rows = src_cur.execute(f"SELECT * FROM {table_name}").fetchall()
    if not rows:
        return 0

    col_count = len(rows[0])
    placeholders = ",".join(["?"] * col_count)
    dst_cur.executemany(
        f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})",
        rows,
    )
    return len(rows)


def main():
    if not CURRENT_DB.exists():
        raise FileNotFoundError(f"Current DB not found: {CURRENT_DB}")
    if not PACKAGE_DB.exists():
        raise FileNotFoundError(f"Package DB not found: {PACKAGE_DB}")

    dst_conn = sqlite3.connect(CURRENT_DB)
    src_conn = sqlite3.connect(PACKAGE_DB)

    try:
        dst_cur = dst_conn.cursor()
        src_cur = src_conn.cursor()

        for table in TABLES:
            print(f"\n=== Merging {table} ===")
            create_table_from_source(dst_cur, src_cur, table)
            inserted = copy_rows(dst_cur, src_cur, table)
            print(f"Copied rows: {inserted}")

        dst_conn.commit()
        print("\nRAG tables merged successfully.")

    finally:
        dst_conn.close()
        src_conn.close()


if __name__ == "__main__":
    main()