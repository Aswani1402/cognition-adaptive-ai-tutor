import sqlite3

DB_PATH = "external/core_data/tutor.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # learners present in knowledge_state
    cur.execute("SELECT DISTINCT student_id FROM knowledge_state LIMIT 20;")
    ks = [r[0] for r in cur.fetchall()]
    print("knowledge_state student_ids:", ks)

    # learners present in quiz_results
    cur.execute("SELECT DISTINCT learner_id FROM quiz_results LIMIT 20;")
    qr = [r[0] for r in cur.fetchall()]
    print("quiz_results learner_ids:", qr)

    conn.close()

if __name__ == "__main__":
    main()