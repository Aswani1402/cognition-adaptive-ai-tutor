import sqlite3

conn = sqlite3.connect("external/core_data/tutor.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM policy_decision_log")
count = cur.fetchone()[0]

print("Total rows:", count)

cur.execute("""
SELECT learner_id, mastery_score, evaluation_score, final_action
FROM policy_decision_log
ORDER BY id DESC
LIMIT 5
""")

rows = cur.fetchall()

print("\nLatest rows:")
for r in rows:
    print(r)

conn.close()