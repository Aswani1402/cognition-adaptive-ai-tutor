# db_changes/check_concept_id_map_schema.py

import sqlite3

DB_PATH = "external/core_data/tutor.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=== concept_id_map columns ===")
    cur.execute("PRAGMA table_info(concept_id_map);")
    columns = cur.fetchall()
    for col in columns:
        print(col)

    print("\n=== sample rows ===")
    cur.execute("SELECT * FROM concept_id_map LIMIT 10;")
    rows = cur.fetchall()
    for row in rows:
        print(row)

    conn.close()

if __name__ == "__main__":
    main()