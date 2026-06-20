import sqlite3
from datetime import date
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


def column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def main() -> None:
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not column_exists(cursor, "learner_xp_state", "last_daily_reset_date"):
        cursor.execute(
            """
            ALTER TABLE learner_xp_state
            ADD COLUMN last_daily_reset_date TEXT
            """
        )

    if not column_exists(cursor, "learner_xp_state", "last_weekly_reset_date"):
        cursor.execute(
            """
            ALTER TABLE learner_xp_state
            ADD COLUMN last_weekly_reset_date TEXT
            """
        )

    cursor.execute(
        """
        UPDATE learner_xp_state
        SET last_daily_reset_date = COALESCE(last_daily_reset_date, ?),
            last_weekly_reset_date = COALESCE(last_weekly_reset_date, ?)
        """,
        (today, today),
    )

    conn.commit()
    conn.close()

    print("Reward reset columns migration completed.")
    print("DB:", DB_PATH)
    print("Columns:")
    print("- learner_xp_state.last_daily_reset_date")
    print("- learner_xp_state.last_weekly_reset_date")


if __name__ == "__main__":
    main()