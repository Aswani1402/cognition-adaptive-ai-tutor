import sqlite3
from pathlib import Path

DB_PATH = Path("external/core_data/tutor.db")


def print_header(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def get_tables(conn):
    cursor = conn.cursor()
    tables = cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name;
    """).fetchall()
    return [t[0] for t in tables]


def get_table_info(conn, table_name):
    cursor = conn.cursor()

    # Columns
    columns = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()

    # Row count
    row_count = cursor.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]

    return columns, row_count


def print_table_schema(columns):
    print("Columns:")
    for col in columns:
        cid, name, col_type, notnull, default, pk = col
        print(f"  - {name} ({col_type}) | NOT NULL={notnull} | PK={pk}")


def print_sample_rows(conn, table_name, limit=5):
    cursor = conn.cursor()
    try:
        rows = cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};").fetchall()
        if rows:
            print(f"\nSample rows (up to {limit}):")
            for row in rows:
                print(row)
        else:
            print("\nNo data in this table.")
    except Exception as e:
        print(f"Error reading rows: {e}")

import sqlite3

conn = sqlite3.connect("external/core_data/tutor.db")
cur = conn.cursor()

rows = cur.execute("""
SELECT system_concept_id, content_concept_id, domain, concept_name, source_db
FROM concept_id_map
ORDER BY CAST(system_concept_id AS INTEGER)
""").fetchall()

for row in rows:
    print(row)

conn.close()
def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    print_header("TUTOR.DB INSPECTION")

    tables = get_tables(conn)

    if not tables:
        print("❌ No tables found.")
        return

    print(f"Total tables: {len(tables)}")

    for table in tables:
        print_header(f"TABLE: {table}")

        try:
            columns, row_count = get_table_info(conn, table)

            print(f"Row count: {row_count}")
            print_table_schema(columns)
            print_sample_rows(conn, table)

        except Exception as e:
            print(f"❌ Error inspecting table {table}: {e}")

    conn.close()
    print("\n✅ Inspection complete.")


if __name__ == "__main__":
    main()