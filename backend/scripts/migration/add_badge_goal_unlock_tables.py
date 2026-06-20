from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")
JSON_REPORT = Path("evaluation_outputs/json/reward_gamification_migration_report.json")
MD_REPORT = Path("evaluation_outputs/reports/reward_gamification_migration_report.md")


TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS achievement_badges (
        badge_id TEXT PRIMARY KEY,
        badge_name TEXT NOT NULL,
        badge_type TEXT NOT NULL,
        description TEXT,
        criteria_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learner_badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        badge_id TEXT NOT NULL,
        awarded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        evidence_json TEXT,
        UNIQUE(learner_id, badge_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_goal_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        goal_date TEXT NOT NULL,
        target_xp INTEGER NOT NULL DEFAULT 20,
        earned_xp INTEGER NOT NULL DEFAULT 0,
        target_questions INTEGER NOT NULL DEFAULT 3,
        completed_questions INTEGER NOT NULL DEFAULT 0,
        target_revision_cards INTEGER NOT NULL DEFAULT 1,
        completed_revision_cards INTEGER NOT NULL DEFAULT 0,
        goal_completed INTEGER NOT NULL DEFAULT 0,
        completion_rate REAL NOT NULL DEFAULT 0.0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(learner_id, goal_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS concept_unlock_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        concept_id TEXT NOT NULL,
        domain TEXT,
        concept_name TEXT,
        unlock_status TEXT NOT NULL,
        mastery_score REAL NOT NULL DEFAULT 0.0,
        promotion_confidence REAL NOT NULL DEFAULT 0.0,
        prerequisites_met INTEGER NOT NULL DEFAULT 0,
        unlocked_at TEXT,
        locked_reason TEXT,
        evidence_json TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(learner_id, concept_id)
    )
    """,
]


BADGES = [
    ("first_step", "First Step", "starter", "Completed the first successful answer or reward session.", {"reward_event_count": 1}),
    ("debug_detective", "Debug Detective", "skill", "Completed or practiced a debug task.", {"debug_activity_count": 1}),
    ("output_predictor", "Output Predictor", "skill", "Practiced output prediction with improvement evidence.", {"output_prediction_activity_count": 1}),
    ("revision_hero", "Revision Hero", "revision", "Completed a revision card or revision session.", {"revision_completed_count": 1}),
    ("streak_starter", "Streak Starter", "streak", "Maintained a 2 day streak.", {"current_streak": 2}),
    ("consistent_learner", "Consistent Learner", "consistency", "Completed 5 or more sessions or repeated practice events.", {"practice_event_count": 5}),
    ("concept_climber", "Concept Climber", "mastery", "Showed concept mastery or promotion-confidence growth.", {"mastery_score": 0.65}),
    ("challenge_solver", "Challenge Solver", "challenge", "Completed or practiced a challenge task.", {"challenge_activity_count": 1}),
]


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def run_migration(db_path: Path | str = DB_PATH) -> dict:
    db_path = Path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        for sql in TABLE_SQL:
            conn.execute(sql)
        for badge_id, name, badge_type, description, criteria in BADGES:
            conn.execute(
                """
                INSERT OR IGNORE INTO achievement_badges
                (badge_id, badge_name, badge_type, description, criteria_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (badge_id, name, badge_type, description, json.dumps(criteria)),
            )
        conn.commit()
        report = {
            "status": "success",
            "module": "add_badge_goal_unlock_tables",
            "db_path": str(db_path),
            "tables": {
                "achievement_badges": _table_count(conn, "achievement_badges"),
                "learner_badges": _table_count(conn, "learner_badges"),
                "daily_goal_state": _table_count(conn, "daily_goal_state"),
                "concept_unlock_state": _table_count(conn, "concept_unlock_state"),
            },
            "seeded_badges": len(BADGES),
        }
    finally:
        conn.close()

    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT.write_text(
        "# Reward Gamification Migration Report\n\n"
        f"Status: **{report['status']}**\n\n"
        f"- Seeded badges: {report['seeded_badges']}\n"
        f"- Tables: {report['tables']}\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    report = run_migration()
    print(f"STATUS: {report['status']}")
    print("MODULE: add_badge_goal_unlock_tables")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
