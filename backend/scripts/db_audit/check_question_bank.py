# scripts/check_question_bank.py

import sqlite3

TUTOR_DB = "external/core_data/tutor.db"

def main():
    conn = sqlite3.connect(TUTOR_DB)
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT question_id, concept_id, question_text
        FROM question_bank
        LIMIT 20
    """).fetchall()

    for row in rows:
        print(row)

    conn.close()

if __name__ == "__main__":
    main()