from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.migration.create_user_persistence_tables import create_tables


DB_PATH = Path("external/core_data/tutor.db")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def demo_password_hash(email: str, password: str) -> str:
    digest = hashlib.sha256(f"demo-api:{email.lower()}:{password}".encode("utf-8")).hexdigest()
    return f"demo-sha256:{digest}"


def connect() -> sqlite3.Connection:
    create_tables(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row else {}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except sqlite3.Error:
        return False


def safe_json_loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return {} if default is None else default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {} if default is None else default


def latest_session_state(learner_id: str) -> dict[str, Any]:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM learner_session_state
            WHERE learner_id = ?
            ORDER BY last_active_at DESC, updated_at DESC
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()
        data = row_to_dict(row)
        if data.get("last_frontend_packet_json"):
            data["last_frontend_packet"] = safe_json_loads(data.get("last_frontend_packet_json"))
        return data
    finally:
        conn.close()


def latest_concept_from_logs(learner_id: str) -> dict[str, Any]:
    conn = connect()
    try:
        for table_name in ["learner_concept_progress", "knowledge_state", "quiz_results"]:
            if not table_exists(conn, table_name):
                continue
            if table_name in {"knowledge_state", "quiz_results"} and not column_exists(conn, table_name, "learner_id"):
                continue
            if table_name == "learner_concept_progress":
                row = conn.execute(
                    """
                    SELECT concept_id, concept_name, domain, mastery, status
                    FROM learner_concept_progress
                    WHERE learner_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (learner_id,),
                ).fetchone()
            elif table_name == "knowledge_state":
                row = conn.execute(
                    "SELECT * FROM knowledge_state WHERE learner_id = ? LIMIT 1",
                    (learner_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM quiz_results WHERE learner_id = ? ORDER BY rowid DESC LIMIT 1",
                    (learner_id,),
                ).fetchone()
            data = row_to_dict(row)
            if data:
                return data
        session = latest_session_state(learner_id)
        if session:
            return {
                "concept_id": session.get("current_concept_id"),
                "concept_name": session.get("current_concept_name"),
                "domain": session.get("current_domain"),
                "status": "current",
            }
        return {}
    finally:
        conn.close()


def reward_state_packet(learner_id: str) -> dict[str, Any]:
    conn = connect()
    try:
        packet: dict[str, Any] = {"xp": {}, "streak": {}, "badges": [], "daily_goal": {}, "concept_unlock": []}
        if table_exists(conn, "learner_xp_state"):
            packet["xp"] = row_to_dict(conn.execute("SELECT * FROM learner_xp_state WHERE learner_id = ?", (learner_id,)).fetchone())
        if table_exists(conn, "learner_streak_state"):
            packet["streak"] = row_to_dict(conn.execute("SELECT * FROM learner_streak_state WHERE learner_id = ?", (learner_id,)).fetchone())
        if table_exists(conn, "learner_badges"):
            packet["badges"] = rows_to_dicts(
                conn.execute(
                    """
                    SELECT * FROM learner_badges
                    WHERE learner_id = ?
                    ORDER BY awarded_at DESC
                    LIMIT 20
                    """,
                    (learner_id,),
                ).fetchall()
            )
        if table_exists(conn, "daily_goal_state"):
            packet["daily_goal"] = row_to_dict(
                conn.execute(
                    """
                    SELECT * FROM daily_goal_state
                    WHERE learner_id = ?
                    ORDER BY goal_date DESC, updated_at DESC
                    LIMIT 1
                    """,
                    (learner_id,),
                ).fetchone()
            )
        if table_exists(conn, "concept_unlock_state"):
            packet["concept_unlock"] = rows_to_dicts(
                conn.execute(
                    """
                    SELECT * FROM concept_unlock_state
                    WHERE learner_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 50
                    """,
                    (learner_id,),
                ).fetchall()
            )
        return packet
    finally:
        conn.close()


def revision_due_packet(learner_id: str) -> list[dict[str, Any]]:
    conn = connect()
    try:
        if not table_exists(conn, "revision_schedule"):
            return []
        return rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM revision_schedule
                WHERE learner_id = ? AND COALESCE(status, 'due') = 'due'
                ORDER BY due_at ASC, updated_at DESC
                LIMIT 20
                """,
                (learner_id,),
            ).fetchall()
        )
    finally:
        conn.close()


def safe_error(module: str, exc: Exception) -> dict[str, Any]:
    return {
        "status": "warning",
        "module": module,
        "fallback_used": True,
        "reason": f"{type(exc).__name__}: {exc}",
    }
