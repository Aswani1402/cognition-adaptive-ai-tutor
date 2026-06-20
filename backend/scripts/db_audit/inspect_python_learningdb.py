import sqlite3

conn = sqlite3.connect("external/core_data/python_learning.db")
cur = conn.cursor()

tables = cur.execute("""
SELECT name FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

print("Tables:", [t[0] for t in tables])

for table in [t[0] for t in tables]:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")

conn.close()

import sqlite3

conn = sqlite3.connect("external/core_data/python_learning.db")
cur = conn.cursor()

rows = cur.execute("""
SELECT * FROM concepts
ORDER BY concept_id
""").fetchall()

for row in rows:
    print(row)

conn.close()


import sqlite3

conn = sqlite3.connect("external/core_data/python_learning.db")
cur = conn.cursor()

rows = cur.execute("""
SELECT * FROM concept_dependencies
ORDER BY 1, 2
""").fetchall()

for row in rows:
    print(row)

conn.close()