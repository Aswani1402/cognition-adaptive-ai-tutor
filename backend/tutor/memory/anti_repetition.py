from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("external/core_data/tutor.db")


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_generation_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            item_type TEXT NOT NULL,
            strategy TEXT,
            content_hash TEXT,
            question_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def store_generated_item(
    learner_id: str,
    concept_id: str,
    item_type: str,
    strategy: str | None = None,
    content_hash: str | None = None,
    question_hash: str | None = None,
    db_path: str | Path = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    try:
        ensure_generation_history_table(conn)
        conn.execute(
            """
            INSERT INTO generation_history
            (learner_id, concept_id, item_type, strategy, content_hash, question_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(learner_id),
                str(concept_id) if concept_id is not None else None,
                str(item_type),
                strategy,
                content_hash,
                question_hash,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_recent_history(
    learner_id: str,
    item_type: str | None = None,
    limit: int = 30,
    db_path: str | Path = DB_PATH,
) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        ensure_generation_history_table(conn)

        if item_type:
            rows = conn.execute(
                """
                SELECT learner_id, concept_id, item_type, strategy, content_hash, question_hash, created_at
                FROM generation_history
                WHERE learner_id = ? AND item_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(learner_id), str(item_type), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT learner_id, concept_id, item_type, strategy, content_hash, question_hash, created_at
                FROM generation_history
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(learner_id), int(limit)),
            ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()


def is_recent_question_repeat(
    learner_id: str,
    question_hash: str,
    limit: int = 30,
    db_path: str | Path = DB_PATH,
) -> bool:
    history = fetch_recent_history(
        learner_id=learner_id,
        item_type="question",
        limit=limit,
        db_path=db_path,
    )
    return any(str(item.get("question_hash")) == str(question_hash) for item in history)


def is_recent_content_repeat(
    learner_id: str,
    content_hash: str,
    limit: int = 30,
    db_path: str | Path = DB_PATH,
) -> bool:
    history = fetch_recent_history(
        learner_id=learner_id,
        item_type="content",
        limit=limit,
        db_path=db_path,
    )
    return any(str(item.get("content_hash")) == str(content_hash) for item in history)