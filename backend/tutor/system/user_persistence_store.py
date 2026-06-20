from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row else {}


def _demo_password_hash(username: str) -> str:
    digest = hashlib.sha256(f"demo:{username}:cognitutor".encode("utf-8")).hexdigest()
    return f"demo-sha256:{digest}"


def create_demo_user(username: str, email: str | None = None, display_name: str | None = None) -> dict[str, Any]:
    username = _safe_str(username)
    if not username:
        return {"status": "error", "module": "UserPersistenceStore", "reason": "Missing username."}

    created = _now()
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    learner_id = f"learner_{uuid.uuid4().hex[:12]}"
    email = _safe_str(email) or None
    display_name = _safe_str(display_name, username)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing = cursor.fetchone()
    if existing:
        row = _row_to_dict(existing)
        cursor.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
            (created, created, row["user_id"]),
        )
        conn.commit()
        conn.close()
        profile = get_or_create_learner_profile(row["user_id"])
        return {
            "status": "success",
            "module": "UserPersistenceStore",
            "created": False,
            "user_id": row["user_id"],
            "learner_id": profile.get("learner_id"),
            "username": row.get("username"),
        }

    cursor.execute(
        """
        INSERT INTO users (
            user_id, username, email, password_hash, role,
            created_at, updated_at, last_login_at, is_active
        )
        VALUES (?, ?, ?, ?, 'learner', ?, ?, ?, 1)
        """,
        (user_id, username, email, _demo_password_hash(username), created, created, created),
    )
    cursor.execute(
        """
        INSERT INTO learner_profile (
            learner_id, user_id, display_name, profile_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (learner_id, user_id, display_name, _json({"source": "create_demo_user"}), created, created),
    )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "module": "UserPersistenceStore",
        "created": True,
        "user_id": user_id,
        "learner_id": learner_id,
        "username": username,
    }


def get_or_create_learner_profile(user_id: str, learner_id: str | None = None) -> dict[str, Any]:
    user_id = _safe_str(user_id)
    if not user_id:
        return {"status": "error", "module": "UserPersistenceStore", "reason": "Missing user_id."}

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM learner_profile WHERE user_id = ? ORDER BY created_at LIMIT 1", (user_id,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        row = _row_to_dict(existing)
        row.update({"status": "success", "module": "UserPersistenceStore", "created": False})
        return row

    created = _now()
    learner_id = _safe_str(learner_id) or f"learner_{uuid.uuid4().hex[:12]}"
    cursor.execute(
        """
        INSERT INTO learner_profile (
            learner_id, user_id, profile_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (learner_id, user_id, _json({"source": "get_or_create_learner_profile"}), created, created),
    )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "module": "UserPersistenceStore",
        "created": True,
        "learner_id": learner_id,
        "user_id": user_id,
    }


def save_session_state(learner_id: str, session_packet: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    packet = _safe_dict(session_packet)
    if not learner_id:
        return {"status": "error", "module": "UserPersistenceStore", "reason": "Missing learner_id."}

    now = _now()
    session_id = _safe_str(packet.get("session_id")) or f"session_{uuid.uuid4().hex[:12]}"
    assessment_types = packet.get("current_assessment_types") or packet.get("assessment_types") or []
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT started_at FROM learner_session_state WHERE session_id = ?", (session_id,))
    existing = cursor.fetchone()
    started_at = existing["started_at"] if existing else _safe_str(packet.get("started_at"), now)
    cursor.execute(
        """
        INSERT OR REPLACE INTO learner_session_state (
            session_id, learner_id, current_domain, current_concept_id, current_concept_name,
            current_teaching_view, current_difficulty, current_assessment_types,
            last_frontend_packet_json, session_status, started_at, updated_at, last_active_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            learner_id,
            _safe_str(packet.get("current_domain") or packet.get("domain")),
            _safe_str(packet.get("current_concept_id") or packet.get("concept_id")),
            _safe_str(packet.get("current_concept_name") or packet.get("concept_name")),
            _safe_str(packet.get("current_teaching_view") or packet.get("teaching_view")),
            _safe_str(packet.get("current_difficulty") or packet.get("difficulty")),
            _json(assessment_types),
            _json(packet),
            _safe_str(packet.get("session_status"), "active"),
            started_at,
            now,
            now,
        ),
    )
    cursor.execute(
        """
        INSERT INTO learner_session_log (
            learner_id, session_id, event_type, domain, concept_id, concept_name,
            teaching_view, difficulty, event_json, created_at
        )
        VALUES (?, ?, 'session_state_saved', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            learner_id,
            session_id,
            _safe_str(packet.get("current_domain") or packet.get("domain")),
            _safe_str(packet.get("current_concept_id") or packet.get("concept_id")),
            _safe_str(packet.get("current_concept_name") or packet.get("concept_name")),
            _safe_str(packet.get("current_teaching_view") or packet.get("teaching_view")),
            _safe_str(packet.get("current_difficulty") or packet.get("difficulty")),
            _json(packet),
            now,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "module": "UserPersistenceStore", "session_id": session_id}


def load_session_state(learner_id: str) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM learner_session_state
        WHERE learner_id = ?
        ORDER BY last_active_at DESC, updated_at DESC
        LIMIT 1
        """,
        (learner_id,),
    )
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    if not row:
        return {"status": "empty", "module": "UserPersistenceStore", "learner_id": learner_id}
    try:
        row["last_frontend_packet"] = json.loads(row.get("last_frontend_packet_json") or "{}")
    except Exception:
        row["last_frontend_packet"] = {}
    return {"status": "success", "module": "UserPersistenceStore", "session_state": row}


def save_mistake_from_evaluation(learner_id: str, session_id: str, evaluation_output: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    session_id = _safe_str(session_id)
    output = _safe_dict(evaluation_output)
    mistakes = (
        output.get("mistakes")
        or output.get("mistake_log")
        or output.get("mistake_analysis", {}).get("mistakes")
        or output.get("results")
        or [output]
    )
    now = _now()
    conn = _connect()
    cursor = conn.cursor()
    inserted = 0
    for mistake in _safe_list(mistakes):
        item = _safe_dict(mistake)
        score = _safe_float(item.get("score", output.get("score")))
        correct_value = item.get("correct", item.get("is_correct", output.get("correct", output.get("is_correct"))))
        label = _safe_str(item.get("label") or item.get("quality_label") or output.get("label") or output.get("quality_label")).lower()
        mistake_type = _safe_str(item.get("mistake_type") or output.get("dominant_mistake_type") or output.get("mistake_type")).lower()
        resolved = str(item.get("resolved", item.get("status", ""))).lower() in {"1", "true", "resolved", "closed"}
        is_correct = correct_value in {1, True, "1", "true", "True"} or label in {"correct", "mastered"} or (score is not None and score >= 0.8)
        if resolved or is_correct or mistake_type in {"", "none", "correct"}:
            continue
        cursor.execute(
            """
            INSERT INTO learner_mistake_log (
                learner_id, session_id, concept_id, concept_name, domain, question_id,
                task_type, mistake_type, severity, learner_answer, expected_answer,
                feedback, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                session_id,
                _safe_str(item.get("concept_id") or output.get("concept_id")),
                _safe_str(item.get("concept_name") or output.get("concept_name")),
                _safe_str(item.get("domain") or output.get("domain")),
                _safe_str(item.get("question_id")),
                _safe_str(item.get("task_type") or item.get("assessment_type") or output.get("task_type")),
                _safe_str(item.get("mistake_type") or output.get("dominant_mistake_type")),
                _safe_str(item.get("severity") or output.get("severity")),
                _safe_str(item.get("learner_answer") or item.get("answer")),
                _safe_str(item.get("expected_answer") or item.get("correct_answer")),
                _safe_str(item.get("feedback") or output.get("feedback")),
                now,
            ),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return {"status": "success", "module": "UserPersistenceStore", "rows_inserted": inserted}


def save_doubt_log(learner_id: str, session_id: str, doubt_output: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    session_id = _safe_str(session_id)
    output = _safe_dict(doubt_output)
    now = _now()
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO learner_doubt_log (
            learner_id, session_id, concept_id, concept_name, domain, doubt_text,
            doubt_type, answer_summary, rag_grounded, grounding_score,
            follow_up_question_json, memory_updated, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            learner_id,
            session_id,
            _safe_str(output.get("concept_id")),
            _safe_str(output.get("concept_name")),
            _safe_str(output.get("domain")),
            _safe_str(output.get("doubt_text") or output.get("question")),
            _safe_str(output.get("doubt_type")),
            _safe_str(output.get("answer_summary") or output.get("answer")),
            1 if output.get("rag_grounded") else 0,
            _safe_float(output.get("grounding_score")),
            _json(output.get("follow_up_question_json") or output.get("follow_up_questions") or []),
            1 if output.get("memory_updated") else 0,
            now,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return {"status": "success", "module": "UserPersistenceStore", "id": row_id}


def save_revision_schedule(learner_id: str, revision_packet: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    packet = _safe_dict(revision_packet)
    now_dt = datetime.utcnow().replace(microsecond=0)
    now = now_dt.isoformat() + "Z"
    schedules = packet.get("schedules") or packet.get("revision_schedule") or [packet]
    cards = packet.get("cards") or packet.get("revision_cards") or packet.get("spaced_repetition_cards") or []

    conn = _connect()
    cursor = conn.cursor()
    schedule_count = 0
    card_count = 0
    for index, schedule in enumerate(_safe_list(schedules)):
        item = _safe_dict(schedule)
        due_at = _safe_str(item.get("due_at"))
        if not due_at:
            due_at = (now_dt + timedelta(days=max(index, 0))).isoformat() + "Z"
        cursor.execute(
            """
            INSERT INTO revision_schedule (
                learner_id, concept_id, concept_name, domain, due_at, interval_label,
                priority, reason, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                _safe_str(item.get("concept_id") or packet.get("concept_id")),
                _safe_str(item.get("concept_name") or packet.get("concept_name")),
                _safe_str(item.get("domain") or packet.get("domain")),
                due_at,
                _safe_str(item.get("interval_label") or item.get("interval")),
                _safe_str(item.get("priority") or packet.get("priority")),
                _safe_str(item.get("reason") or packet.get("revision_reason")),
                _safe_str(item.get("status"), "due"),
                now,
                now,
            ),
        )
        schedule_count += 1

    for card in _safe_list(cards):
        item = _safe_dict(card)
        cursor.execute(
            """
            INSERT INTO revision_card (
                learner_id, concept_id, concept_name, domain, card_type, prompt,
                answer, difficulty, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                _safe_str(item.get("concept_id") or packet.get("concept_id")),
                _safe_str(item.get("concept_name") or packet.get("concept_name")),
                _safe_str(item.get("domain") or packet.get("domain")),
                _safe_str(item.get("card_type") or item.get("type"), "review"),
                _safe_str(item.get("prompt")),
                _safe_str(item.get("answer") or item.get("expected_answer")),
                _safe_str(item.get("difficulty") or packet.get("difficulty")),
                _safe_str(item.get("source"), "user_persistence_store"),
                now,
                now,
            ),
        )
        card_count += 1
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "module": "UserPersistenceStore",
        "schedules_inserted": schedule_count,
        "cards_inserted": card_count,
    }


def save_agent_trace(learner_id: str, session_id: str, agentic_trace_output: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    session_id = _safe_str(session_id)
    output = _safe_dict(agentic_trace_output)
    trace = output.get("trace_steps") or output.get("agent_trace") or output.get("trace") or [output]
    now = _now()
    conn = _connect()
    cursor = conn.cursor()
    inserted = 0
    for index, step in enumerate(_safe_list(trace), start=1):
        item = _safe_dict(step)
        cursor.execute(
            """
            INSERT INTO agent_orchestration_log (
                learner_id, session_id, concept_id, concept_name, trace_step,
                agent_name, status, primary_decision, primary_output, reason,
                trace_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                session_id,
                _safe_str(item.get("concept_id") or output.get("concept_id")),
                _safe_str(item.get("concept_name") or output.get("concept_name")),
                _safe_int(item.get("trace_step") or item.get("step"), index),
                _safe_str(item.get("agent_name") or item.get("agent")),
                _safe_str(item.get("status")),
                _safe_str(item.get("primary_decision") or item.get("decision")),
                _safe_str(item.get("primary_output") or item.get("output")),
                _safe_str(item.get("reason")),
                _json(item),
                now,
            ),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return {"status": "success", "module": "UserPersistenceStore", "rows_inserted": inserted}


def update_concept_progress(learner_id: str, concept_id: str, progress_data: dict[str, Any]) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    concept_id = _safe_str(concept_id)
    data = _safe_dict(progress_data)
    now = _now()
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, attempts FROM learner_concept_progress
        WHERE learner_id = ? AND concept_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (learner_id, concept_id),
    )
    existing = cursor.fetchone()
    attempts = _safe_int(data.get("attempts"), 0)
    if existing and not attempts:
        attempts = _safe_int(existing["attempts"], 0) + 1
    elif not attempts:
        attempts = 1

    values = (
        learner_id,
        _safe_str(data.get("domain")),
        concept_id,
        _safe_str(data.get("concept_name")),
        _safe_str(data.get("status"), "current"),
        _safe_float(data.get("mastery")),
        attempts,
        _safe_float(data.get("last_score")),
        _safe_str(data.get("last_activity_at"), now),
        _safe_str(data.get("unlocked_at")),
        _safe_str(data.get("mastered_at")),
        now,
    )
    if existing:
        cursor.execute(
            """
            UPDATE learner_concept_progress
            SET learner_id = ?, domain = ?, concept_id = ?, concept_name = ?,
                status = ?, mastery = ?, attempts = ?, last_score = ?,
                last_activity_at = ?, unlocked_at = ?, mastered_at = ?, updated_at = ?
            WHERE id = ?
            """,
            values + (existing["id"],),
        )
    else:
        cursor.execute(
            """
            INSERT INTO learner_concept_progress (
                learner_id, domain, concept_id, concept_name, status, mastery,
                attempts, last_score, last_activity_at, unlocked_at, mastered_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    conn.commit()
    conn.close()
    return {"status": "success", "module": "UserPersistenceStore", "learner_id": learner_id, "concept_id": concept_id}


def build_returning_user_context(learner_id: str) -> dict[str, Any]:
    learner_id = _safe_str(learner_id)
    conn = _connect()
    cursor = conn.cursor()
    profile = _row_to_dict(cursor.execute("SELECT * FROM learner_profile WHERE learner_id = ?", (learner_id,)).fetchone())
    session = _row_to_dict(
        cursor.execute(
            """
            SELECT * FROM learner_session_state
            WHERE learner_id = ?
            ORDER BY last_active_at DESC, updated_at DESC
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()
    )
    progress = [
        dict(row)
        for row in cursor.execute(
            """
            SELECT * FROM learner_concept_progress
            WHERE learner_id = ?
            ORDER BY updated_at DESC
            LIMIT 10
            """,
            (learner_id,),
        ).fetchall()
    ]
    mistakes = [
        dict(row)
        for row in cursor.execute(
            """
            SELECT * FROM learner_mistake_log
            WHERE learner_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (learner_id,),
        ).fetchall()
    ]
    doubts = [
        dict(row)
        for row in cursor.execute(
            """
            SELECT * FROM learner_doubt_log
            WHERE learner_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (learner_id,),
        ).fetchall()
    ]
    revisions_due = [
        dict(row)
        for row in cursor.execute(
            """
            SELECT * FROM revision_schedule
            WHERE learner_id = ? AND status = 'due'
            ORDER BY due_at ASC
            LIMIT 10
            """,
            (learner_id,),
        ).fetchall()
    ]
    agent_trace = [
        dict(row)
        for row in cursor.execute(
            """
            SELECT * FROM agent_orchestration_log
            WHERE learner_id = ?
            ORDER BY created_at DESC, trace_step DESC
            LIMIT 10
            """,
            (learner_id,),
        ).fetchall()
    ]
    conn.close()
    return {
        "status": "success",
        "module": "UserPersistenceStore",
        "learner_id": learner_id,
        "profile": profile,
        "latest_session_state": session,
        "recent_concept_progress": progress,
        "recent_mistakes": mistakes,
        "recent_doubts": doubts,
        "revisions_due": revisions_due,
        "recent_agent_trace": agent_trace,
        "resume_ready": bool(profile and session),
        "personalization_ready": bool(progress or mistakes or doubts or revisions_due or agent_trace),
    }
