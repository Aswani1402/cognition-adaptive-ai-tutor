from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


TABLE_NAMES = [
    "users",
    "learner_profile",
    "learner_session_state",
    "learner_concept_progress",
    "learner_session_log",
    "learner_mistake_log",
    "learner_doubt_log",
    "learner_view_progress",
    "learner_revision_log",
    "revision_schedule",
    "revision_card",
    "revision_attempt_log",
    "agent_orchestration_log",
]


REQUIRED_COLUMNS = {
    "users": {
        "user_id": "TEXT",
        "username": "TEXT",
        "email": "TEXT",
        "password_hash": "TEXT",
        "role": "TEXT DEFAULT 'learner'",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "last_login_at": "TEXT",
        "is_active": "INTEGER DEFAULT 1",
    },
    "learner_profile": {
        "learner_id": "TEXT",
        "user_id": "TEXT",
        "display_name": "TEXT",
        "current_domain": "TEXT",
        "current_concept_id": "TEXT",
        "current_concept_name": "TEXT",
        "preferred_difficulty": "TEXT",
        "preferred_teaching_view": "TEXT",
        "preferred_subject": "TEXT",
        "active_subject": "TEXT",
        "current_difficulty": "TEXT",
        "skill_level": "TEXT",
        "learning_goal": "TEXT",
        "profile_json": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    },
}


def _ensure_columns(cursor: sqlite3.Cursor, table_name: str, columns: dict[str, str]) -> None:
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in columns.items():
        if column_name not in existing:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def create_tables(db_path: Path | str = DB_PATH) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'learner',
            created_at TEXT,
            updated_at TEXT,
            last_login_at TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_profile (
            learner_id TEXT PRIMARY KEY,
            user_id TEXT,
            display_name TEXT,
            current_domain TEXT,
            current_concept_id TEXT,
            current_concept_name TEXT,
            active_subject TEXT,
            current_difficulty TEXT,
            preferred_subject TEXT,
            preferred_difficulty TEXT,
            preferred_teaching_view TEXT,
            skill_level TEXT,
            learning_goal TEXT,
            profile_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_session_state (
            session_id TEXT PRIMARY KEY,
            learner_id TEXT,
            current_domain TEXT,
            current_concept_id TEXT,
            current_concept_name TEXT,
            current_teaching_view TEXT,
            current_difficulty TEXT,
            current_assessment_types TEXT,
            last_frontend_packet_json TEXT,
            session_status TEXT,
            started_at TEXT,
            updated_at TEXT,
            last_active_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_concept_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            domain TEXT,
            concept_id TEXT,
            concept_name TEXT,
            status TEXT,
            mastery REAL,
            attempts INTEGER,
            last_score REAL,
            last_activity_at TEXT,
            unlocked_at TEXT,
            mastered_at TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_session_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            session_id TEXT,
            event_type TEXT,
            domain TEXT,
            concept_id TEXT,
            concept_name TEXT,
            teaching_view TEXT,
            difficulty TEXT,
            event_json TEXT,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_mistake_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            session_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            question_id TEXT,
            task_type TEXT,
            mistake_type TEXT,
            severity TEXT,
            learner_answer TEXT,
            expected_answer TEXT,
            feedback TEXT,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_doubt_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            session_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            doubt_text TEXT,
            doubt_type TEXT,
            answer_summary TEXT,
            rag_grounded INTEGER,
            grounding_score REAL,
            follow_up_question_json TEXT,
            memory_updated INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_view_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            teaching_view TEXT,
            view_status TEXT,
            score REAL,
            attempts INTEGER,
            last_seen_at TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_revision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            revision_view TEXT,
            revision_reason TEXT,
            completed INTEGER DEFAULT 0,
            score REAL,
            created_at TEXT,
            completed_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revision_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            due_at TEXT,
            interval_label TEXT,
            priority TEXT,
            reason TEXT,
            status TEXT DEFAULT 'due',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revision_card (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            card_type TEXT,
            prompt TEXT,
            answer TEXT,
            difficulty TEXT,
            source TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revision_attempt_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            revision_card_id INTEGER,
            answer TEXT,
            score REAL,
            correct INTEGER,
            feedback TEXT,
            attempted_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_orchestration_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            session_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            trace_step INTEGER,
            agent_name TEXT,
            status TEXT,
            primary_decision TEXT,
            primary_output TEXT,
            reason TEXT,
            trace_json TEXT,
            created_at TEXT
        )
        """
    )

    for table_name, columns in REQUIRED_COLUMNS.items():
        _ensure_columns(cursor, table_name, columns)

    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_learner_profile_user_id ON learner_profile(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_session_state_learner_id ON learner_session_state(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_session_state_session_id ON learner_session_state(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_concept_progress_learner_id ON learner_concept_progress(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_concept_progress_concept_id ON learner_concept_progress(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_concept_progress_updated_at ON learner_concept_progress(updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_learner_session_log_learner_id ON learner_session_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_session_log_session_id ON learner_session_log(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_session_log_created_at ON learner_session_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_learner_mistake_log_learner_id ON learner_mistake_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_mistake_log_session_id ON learner_mistake_log(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_mistake_log_concept_id ON learner_mistake_log(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_mistake_log_created_at ON learner_mistake_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_learner_doubt_log_learner_id ON learner_doubt_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_doubt_log_session_id ON learner_doubt_log(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_doubt_log_concept_id ON learner_doubt_log(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_doubt_log_created_at ON learner_doubt_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_learner_view_progress_learner_id ON learner_view_progress(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_view_progress_concept_id ON learner_view_progress(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_revision_log_learner_id ON learner_revision_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_revision_log_concept_id ON learner_revision_log(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_learner_revision_log_created_at ON learner_revision_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_revision_schedule_learner_id ON revision_schedule(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_schedule_concept_id ON revision_schedule(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_schedule_due_at ON revision_schedule(due_at)",
        "CREATE INDEX IF NOT EXISTS idx_revision_schedule_created_at ON revision_schedule(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_revision_card_learner_id ON revision_card(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_card_concept_id ON revision_card(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_card_created_at ON revision_card(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_revision_attempt_log_learner_id ON revision_attempt_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_revision_attempt_log_created_at ON revision_attempt_log(attempted_at)",
        "CREATE INDEX IF NOT EXISTS idx_agent_orchestration_log_learner_id ON agent_orchestration_log(learner_id)",
        "CREATE INDEX IF NOT EXISTS idx_agent_orchestration_log_session_id ON agent_orchestration_log(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_agent_orchestration_log_concept_id ON agent_orchestration_log(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_agent_orchestration_log_created_at ON agent_orchestration_log(created_at)",
    ]
    for statement in index_statements:
        cursor.execute(statement)

    conn.commit()
    conn.close()


def main() -> None:
    create_tables()
    print("STATUS: success")
    print("MODULE: create_user_persistence_tables")
    print(f"DB: {DB_PATH}")
    print("TABLES:", ", ".join(TABLE_NAMES))


if __name__ == "__main__":
    main()
