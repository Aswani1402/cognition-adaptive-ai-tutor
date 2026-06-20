import sqlite3

conn = sqlite3.connect("external/core_data/tutor.db")
cur = conn.cursor()

print("Total rows:", cur.execute("SELECT COUNT(*) FROM knowledge_state").fetchone()[0])

rows = cur.execute("""
SELECT student_id, state_json
FROM knowledge_state
WHERE state_json LIKE '%"mastery"%'
LIMIT 10
""").fetchall()

print("Rows with mastery key:", len(rows))
for row in rows:
    print(row)

conn.close()