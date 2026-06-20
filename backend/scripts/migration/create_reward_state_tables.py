import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


def create_tables() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_xp_state (
            learner_id TEXT PRIMARY KEY,
            total_xp INTEGER NOT NULL DEFAULT 0,
            daily_xp INTEGER NOT NULL DEFAULT 0,
            weekly_xp INTEGER NOT NULL DEFAULT 0,
            current_level INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_streak_state (
            learner_id TEXT PRIMARY KEY,
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_active_date TEXT,
            streak_updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            xp_awarded INTEGER NOT NULL DEFAULT 0,
            reward_reason TEXT,
            celebration_type TEXT,
            progression_action TEXT,
            promotion_allowed INTEGER DEFAULT 0,
            model_progression_action TEXT,
            model_promotion_allowed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()

    print("Reward state tables created successfully.")
    print("DB:", DB_PATH)
    print("Tables:")
    print("- learner_xp_state")
    print("- learner_streak_state")
    print("- reward_event_log")


if __name__ == "__main__":
    create_tables()