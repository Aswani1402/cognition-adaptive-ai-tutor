# scripts/db_audit/compare_tutor_schema.py

import sqlite3
from pathlib import Path

OLD_DB = Path("external/core_data/tutor.db")
NEW_DB = Path("rag_dyna/core_data/tutor.db")

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'index')
        ORDER BY name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

old_schema = get_schema(OLD_DB)
new_schema = get_schema(NEW_DB)

old_map = {name: sql for name, sql in old_schema}
new_map = {name: sql for name, sql in new_schema}

all_names = sorted(set(old_map) | set(new_map))

for name in all_names:
    o = old_map.get(name)
    n = new_map.get(name)
    if o == n:
        continue
    print(f"\n=== {name} ===")
    print("OLD:", "EXISTS" if o else "MISSING")
    print("NEW:", "EXISTS" if n else "MISSING")