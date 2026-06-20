import os
import sqlite3

DB_PATH = os.path.join("external", "core_data", "tutor.db")

TABLES = [
    "quiz_results",
    "knowledge_state",
    "behaviour_state",
    "decay_state"
]

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table in TABLES:
        print("\n" + "=" * 60)
        print(f"TABLE: {table}")
        print("=" * 60)

        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()

        if not columns:
            print("No table or no columns found.")
            continue

        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            print(f"{cid:>2} | {name:<25} | {col_type:<12} | NOTNULL={notnull} | PK={pk}")

    conn.close()

if __name__ == "__main__":
    main()