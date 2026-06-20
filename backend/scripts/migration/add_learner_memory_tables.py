from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("external/core_data/tutor.db")


TABLE_SQL = {
    "learner_session_log": """
        CREATE TABLE IF NOT EXISTS learner_session_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            session_id TEXT,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            selected_view TEXT,
            difficulty TEXT,
            started_at TEXT,
            ended_at TEXT,
            mode TEXT,
            metadata_json TEXT
        )
    """,
    "learner_mistake_log": """
        CREATE TABLE IF NOT EXISTS learner_mistake_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            question_id TEXT,
            question_type TEXT,
            mistake_type TEXT,
            score REAL,
            feedback TEXT,
            created_at TEXT,
            metadata_json TEXT
        )
    """,
    "learner_doubt_log": """
        CREATE TABLE IF NOT EXISTS learner_doubt_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            doubt_text TEXT,
            doubt_type TEXT,
            answer_summary TEXT,
            rag_context_used INTEGER DEFAULT 0,
            created_at TEXT,
            metadata_json TEXT
        )
    """,
    "learner_revision_log": """
        CREATE TABLE IF NOT EXISTS learner_revision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            revision_type TEXT,
            recommended_views TEXT,
            weak_question_types TEXT,
            created_at TEXT,
            metadata_json TEXT
        )
    """,
    "learner_view_progress": """
        CREATE TABLE IF NOT EXISTS learner_view_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            domain TEXT,
            view_name TEXT,
            status TEXT,
            score REAL,
            last_seen_at TEXT,
            metadata_json TEXT,
            UNIQUE(learner_id, concept_id, view_name)
        )
    """,
    "learner_memory_state": """
        CREATE TABLE IF NOT EXISTS learner_memory_state (
            learner_id TEXT PRIMARY KEY,
            last_active_at TEXT,
            last_concept_id TEXT,
            last_concept_name TEXT,
            last_domain TEXT,
            last_teaching_view TEXT,
            last_difficulty TEXT,
            weak_concepts_json TEXT,
            weak_question_types_json TEXT,
            strong_question_types_json TEXT,
            mistake_summary_json TEXT,
            recommended_revision_views_json TEXT,
            next_recommended_action TEXT,
            recent_scores_json TEXT,
            updated_at TEXT
        )
    """,
}


INDEX_SQL = [
    """
    CREATE INDEX IF NOT EXISTS idx_learner_session_log_learner_id
    ON learner_session_log(learner_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_learner_mistake_log_learner_concept
    ON learner_mistake_log(learner_id, concept_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_learner_doubt_log_learner_id
    ON learner_doubt_log(learner_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_learner_revision_log_learner_id
    ON learner_revision_log(learner_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_learner_view_progress_learner_concept
    ON learner_view_progress(learner_id, concept_id)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_learner_view_progress_unique_view
    ON learner_view_progress(learner_id, concept_id, view_name)
    """,
]


REQUIRED_COLUMNS = {
    "learner_session_log": {
        "selected_view": "TEXT",
        "started_at": "TEXT",
        "ended_at": "TEXT",
        "mode": "TEXT",
        "metadata_json": "TEXT",
    },
    "learner_mistake_log": {
        "question_type": "TEXT",
        "score": "REAL",
        "metadata_json": "TEXT",
    },
    "learner_doubt_log": {
        "rag_context_used": "INTEGER DEFAULT 0",
        "metadata_json": "TEXT",
    },
    "learner_revision_log": {
        "revision_type": "TEXT",
        "recommended_views": "TEXT",
        "weak_question_types": "TEXT",
        "metadata_json": "TEXT",
    },
    "learner_view_progress": {
        "view_name": "TEXT",
        "status": "TEXT",
        "metadata_json": "TEXT",
    },
}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _add_missing_columns(conn: sqlite3.Connection) -> list[str]:
    added = []
    for table_name, columns in REQUIRED_COLUMNS.items():
        existing = _existing_columns(conn, table_name)
        for column_name, column_type in columns.items():
            if column_name in existing:
                continue
            try:
                conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
                added.append(f"{table_name}.{column_name}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
    return added


def run_migration(db_path: Path | str = DB_PATH) -> dict:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        for sql in TABLE_SQL.values():
            conn.execute(sql)
        added_columns = _add_missing_columns(conn)
        for sql in INDEX_SQL:
            conn.execute(sql)
        conn.commit()

        tables = {
            table_name: "created/verified" if _table_exists(conn, table_name) else "missing"
            for table_name in TABLE_SQL
        }
        status = "success" if all(value == "created/verified" for value in tables.values()) else "warning"
        return {
            "status": status,
            "module": "add_learner_memory_tables",
            "db_path": str(db_path),
            "tables": tables,
            "added_columns": added_columns,
            "indexes_created_or_verified": len(INDEX_SQL),
        }
    finally:
        conn.close()


def main() -> None:
    report = run_migration()
    print("learner memory tables created/verified")
    print(f"STATUS: {report['status']}")
    print("MODULE: add_learner_memory_tables")
    print(f"DB_PATH: {report['db_path']}")
    for table_name, table_status in report["tables"].items():
        print(f"{table_name}: {table_status}")
    if report["added_columns"]:
        print(f"ADDED_COLUMNS: {report['added_columns']}")
    print(f"INDEXES: {report['indexes_created_or_verified']}")


if __name__ == "__main__":
    main()
