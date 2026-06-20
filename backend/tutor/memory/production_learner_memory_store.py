from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    if value is None:
        value = {}
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict(row)
    for key in list(payload):
        if key.endswith("_json"):
            payload[key[:-5]] = _json_loads(payload[key], [] if key.endswith("s_json") else {})
    return payload


class ProductionLearnerMemoryStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DB_PATH
        from scripts.migration.add_learner_memory_tables import run_migration

        run_migration(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log_session(
        self,
        learner_id: str,
        session_id: str | None = None,
        concept_id: str | None = None,
        concept_name: str | None = None,
        domain: str | None = None,
        selected_view: str | None = None,
        difficulty: str | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
        mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started_at = started_at or _utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learner_session_log (
                    learner_id, session_id, concept_id, concept_name, domain,
                    selected_view, difficulty, started_at, ended_at, mode, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    session_id,
                    concept_id,
                    concept_name,
                    domain,
                    selected_view,
                    difficulty,
                    started_at,
                    ended_at,
                    mode,
                    _json_dumps(_as_dict(metadata)),
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "id": cursor.lastrowid,
                "learner_id": learner_id,
                "session_id": session_id,
                "started_at": started_at,
            }

    def log_mistake(
        self,
        learner_id: str,
        concept_id: str | None = None,
        concept_name: str | None = None,
        domain: str | None = None,
        question_id: str | None = None,
        question_type: str | None = None,
        mistake_type: str | None = None,
        score: float | None = None,
        feedback: str | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or _utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learner_mistake_log (
                    learner_id, concept_id, concept_name, domain, question_id,
                    question_type, mistake_type, score, feedback, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    concept_id,
                    concept_name,
                    domain,
                    question_id,
                    question_type,
                    mistake_type,
                    score,
                    feedback,
                    created_at,
                    _json_dumps(_as_dict(metadata)),
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "id": cursor.lastrowid,
                "learner_id": learner_id,
                "mistake_type": mistake_type,
                "created_at": created_at,
            }

    def log_doubt(
        self,
        learner_id: str,
        concept_id: str | None = None,
        concept_name: str | None = None,
        domain: str | None = None,
        doubt_text: str | None = None,
        doubt_type: str | None = None,
        answer_summary: str | None = None,
        rag_context_used: bool | int = False,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or _utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learner_doubt_log (
                    learner_id, concept_id, concept_name, domain, doubt_text,
                    doubt_type, answer_summary, rag_context_used, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    concept_id,
                    concept_name,
                    domain,
                    doubt_text,
                    doubt_type,
                    answer_summary,
                    1 if rag_context_used else 0,
                    created_at,
                    _json_dumps(_as_dict(metadata)),
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "id": cursor.lastrowid,
                "learner_id": learner_id,
                "doubt_type": doubt_type,
                "created_at": created_at,
            }

    def log_revision(
        self,
        learner_id: str,
        concept_id: str | None = None,
        concept_name: str | None = None,
        domain: str | None = None,
        revision_type: str | None = None,
        recommended_views: list[Any] | None = None,
        weak_question_types: list[Any] | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or _utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learner_revision_log (
                    learner_id, concept_id, concept_name, domain, revision_type,
                    recommended_views, weak_question_types, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    concept_id,
                    concept_name,
                    domain,
                    revision_type,
                    _json_dumps(_as_list(recommended_views)),
                    _json_dumps(_as_list(weak_question_types)),
                    created_at,
                    _json_dumps(_as_dict(metadata)),
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "id": cursor.lastrowid,
                "learner_id": learner_id,
                "revision_type": revision_type,
                "created_at": created_at,
            }

    def upsert_view_progress(
        self,
        learner_id: str,
        concept_id: str,
        view_name: str,
        concept_name: str | None = None,
        domain: str | None = None,
        status: str | None = None,
        score: float | None = None,
        last_seen_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_seen_at = last_seen_at or _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO learner_view_progress (
                    learner_id, concept_id, concept_name, domain, view_name,
                    status, score, last_seen_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(learner_id, concept_id, view_name) DO UPDATE SET
                    concept_name = excluded.concept_name,
                    domain = excluded.domain,
                    status = excluded.status,
                    score = excluded.score,
                    last_seen_at = excluded.last_seen_at,
                    metadata_json = excluded.metadata_json
                """,
                (
                    learner_id,
                    concept_id,
                    concept_name,
                    domain,
                    view_name,
                    status,
                    score,
                    last_seen_at,
                    _json_dumps(_as_dict(metadata)),
                ),
            )
            conn.commit()
        return {
            "status": "success",
            "learner_id": learner_id,
            "concept_id": concept_id,
            "view_name": view_name,
            "last_seen_at": last_seen_at,
        }

    def get_view_progress(self, learner_id: str, concept_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM learner_view_progress
                WHERE learner_id = ? AND concept_id = ?
                ORDER BY last_seen_at DESC, id DESC
                """,
                (learner_id, concept_id),
            ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]

    def update_memory_state(
        self,
        learner_id: str,
        last_active_at: str | None = None,
        last_concept_id: str | None = None,
        last_concept_name: str | None = None,
        last_domain: str | None = None,
        last_teaching_view: str | None = None,
        last_difficulty: str | None = None,
        weak_concepts: list[Any] | None = None,
        weak_question_types: list[Any] | None = None,
        strong_question_types: list[Any] | None = None,
        mistake_summary: dict[str, Any] | None = None,
        recommended_revision_views: list[Any] | None = None,
        next_recommended_action: str | None = None,
        recent_scores: list[Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        last_active_at = last_active_at or now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO learner_memory_state (
                    learner_id, last_active_at, last_concept_id, last_concept_name,
                    last_domain, last_teaching_view, last_difficulty,
                    weak_concepts_json, weak_question_types_json,
                    strong_question_types_json, mistake_summary_json,
                    recommended_revision_views_json, next_recommended_action,
                    recent_scores_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(learner_id) DO UPDATE SET
                    last_active_at = excluded.last_active_at,
                    last_concept_id = excluded.last_concept_id,
                    last_concept_name = excluded.last_concept_name,
                    last_domain = excluded.last_domain,
                    last_teaching_view = excluded.last_teaching_view,
                    last_difficulty = excluded.last_difficulty,
                    weak_concepts_json = excluded.weak_concepts_json,
                    weak_question_types_json = excluded.weak_question_types_json,
                    strong_question_types_json = excluded.strong_question_types_json,
                    mistake_summary_json = excluded.mistake_summary_json,
                    recommended_revision_views_json = excluded.recommended_revision_views_json,
                    next_recommended_action = excluded.next_recommended_action,
                    recent_scores_json = excluded.recent_scores_json,
                    updated_at = excluded.updated_at
                """,
                (
                    learner_id,
                    last_active_at,
                    last_concept_id,
                    last_concept_name,
                    last_domain,
                    last_teaching_view,
                    last_difficulty,
                    _json_dumps(_as_list(weak_concepts)),
                    _json_dumps(_as_list(weak_question_types)),
                    _json_dumps(_as_list(strong_question_types)),
                    _json_dumps(_as_dict(mistake_summary)),
                    _json_dumps(_as_list(recommended_revision_views)),
                    next_recommended_action,
                    _json_dumps(_as_list(recent_scores)),
                    now,
                ),
            )
            conn.commit()
        return {
            "status": "success",
            "learner_id": learner_id,
            "updated_at": now,
        }

    def get_memory_state(self, learner_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM learner_memory_state WHERE learner_id = ?",
                (learner_id,),
            ).fetchone()
        decoded = _row_to_dict(row)
        if decoded is None:
            return {
                "status": "not_found",
                "learner_id": learner_id,
                "weak_concepts": [],
                "weak_question_types": [],
                "strong_question_types": [],
                "mistake_summary": {},
                "recommended_revision_views": [],
                "recent_scores": [],
            }
        decoded["status"] = "success"
        return decoded

    def get_returning_learner_context(self, learner_id: str) -> dict[str, Any]:
        memory_state = self.get_memory_state(learner_id)
        with self._connect() as conn:
            recent_sessions = conn.execute(
                """
                SELECT *
                FROM learner_session_log
                WHERE learner_id = ?
                ORDER BY COALESCE(started_at, '') DESC, id DESC
                LIMIT 5
                """,
                (learner_id,),
            ).fetchall()
            recent_mistakes = conn.execute(
                """
                SELECT *
                FROM learner_mistake_log
                WHERE learner_id = ?
                ORDER BY COALESCE(created_at, '') DESC, id DESC
                LIMIT 10
                """,
                (learner_id,),
            ).fetchall()
            recent_doubts = conn.execute(
                """
                SELECT *
                FROM learner_doubt_log
                WHERE learner_id = ?
                ORDER BY COALESCE(created_at, '') DESC, id DESC
                LIMIT 5
                """,
                (learner_id,),
            ).fetchall()
            recent_revisions = conn.execute(
                """
                SELECT *
                FROM learner_revision_log
                WHERE learner_id = ?
                ORDER BY COALESCE(created_at, '') DESC, id DESC
                LIMIT 5
                """,
                (learner_id,),
            ).fetchall()

        concept_id = memory_state.get("last_concept_id")
        view_progress = (
            self.get_view_progress(learner_id, concept_id)
            if concept_id
            else []
        )
        return {
            "status": "success",
            "learner_id": learner_id,
            "returning_learner_available": memory_state.get("status") == "success",
            "memory_state": memory_state,
            "recent_sessions": [_row_to_dict(row) or {} for row in recent_sessions],
            "recent_mistakes": [_row_to_dict(row) or {} for row in recent_mistakes],
            "recent_doubts": [_row_to_dict(row) or {} for row in recent_doubts],
            "recent_revisions": [_row_to_dict(row) or {} for row in recent_revisions],
            "view_progress": view_progress,
            "recommended_revision_views": memory_state.get("recommended_revision_views", []),
            "weak_concepts": memory_state.get("weak_concepts", []),
            "weak_question_types": memory_state.get("weak_question_types", []),
            "next_recommended_action": memory_state.get("next_recommended_action"),
        }
