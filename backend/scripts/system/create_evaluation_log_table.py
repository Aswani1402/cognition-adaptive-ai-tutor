import sqlite3
from pathlib import Path

DB_PATH = Path("external/core_data/tutor.db")


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS evaluation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        concept_id TEXT NOT NULL,

        overall_score REAL,
        verdict TEXT,
        feedback_summary TEXT,

        mcq_score REAL,
        explanation_score REAL,
        output_score REAL,
        transfer_score REAL,

        learning_signal TEXT,

        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("evaluation_log table ready.")


if __name__ == "__main__":
    main()