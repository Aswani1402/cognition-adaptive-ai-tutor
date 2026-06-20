import sqlite3
from pathlib import Path

DB_PATH = Path("external/core_data/tutor.db")


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS policy_decision_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        current_concept_id TEXT,
        next_concept_id TEXT,
        mastery_score REAL,
        behavior_label TEXT,
        behavior_score REAL,
        review_due INTEGER,
        evaluation_score REAL,
        learning_signal TEXT,
        final_action TEXT,
        recommended_strategy TEXT,
        recommended_difficulty TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("policy_decision_log table ready.")


if __name__ == "__main__":
    main()