import sqlite3
from pathlib import Path

CORE_DATA_DIR = Path("external/core_data")

DBS = [
    "python_learning.db",
    "database_sql.db",
    "html_web_basics.db",
    "git_version_control.db",
    "data_structures.db",
]

for db_name in DBS:
    db_path = CORE_DATA_DIR / db_name
    print("\n" + "=" * 80)
    print("DB:", db_name, "EXISTS:", db_path.exists())

    if not db_path.exists():
        continue

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    print("TABLES:", [t[0] for t in tables])

    for (table_name,) in tables:
        print("\nTABLE:", table_name)

        cols = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
        print("COLUMNS:", [c[1] for c in cols])

        try:
            count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print("ROWS:", count)

            sample = cur.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
            print("SAMPLE:", sample)
        except Exception as e:
            print("ERROR:", e)

    conn.close()