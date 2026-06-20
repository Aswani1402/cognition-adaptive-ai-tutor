import sqlite3
from pathlib import Path

DB_PATH = Path("external/core_data/tutor.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
DELETE FROM knowledge_state
WHERE state_json LIKE '%"mastery"%'
""")

conn.commit()
print("Old KS rows removed")
conn.close()