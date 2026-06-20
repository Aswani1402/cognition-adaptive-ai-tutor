from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter

from tutor.api.dependencies import (
    column_exists,
    connect,
    latest_concept_from_logs,
    latest_session_state,
    now_iso,
    reward_state_packet,
    revision_due_packet,
    row_to_dict,
    rows_to_dicts,
    safe_json_loads,
    safe_error,
    table_exists,
)
from tutor.api.schemas import SaveSessionRequest, SelectSubjectRequest, api_response
from tutor.memory.semantic_notebook_search import SemanticNotebookSearch
from tutor.system.user_persistence_store import save_session_state


router = APIRouter(prefix="/learner", tags=["learner"])


SUBJECT_NAMES = ["Python", "SQL / Database", "HTML/Web Basics", "Git", "Data Structures"]


@router.get("/context/{learner_id}")
def learner_context(learner_id: str) -> dict:
    module = "LearnerRoutes"
    try:
        conn = connect()
        try:
            profile = row_to_dict(
                conn.execute("SELECT * FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone()
            )
            session = latest_session_state(learner_id)
            active_subject = profile.get("active_subject") or profile.get("current_domain") or session.get("current_domain")
            current_concept_id = profile.get("current_concept_id") or session.get("current_concept_id")
            current_concept_name = profile.get("current_concept_name") or session.get("current_concept_name")
            current_difficulty = profile.get("current_difficulty") or session.get("current_difficulty") or "easy"
            current_teaching_view = (
                profile.get("current_teaching_view")
                or profile.get("preferred_teaching_view")
                or session.get("current_teaching_view")
                or "code_view"
            )
            subject_progress = _subject_progress_packet(conn, learner_id, active_subject)
        finally:
            conn.close()
        return api_response(
            module=module,
            data={
                "auto_flow": True,
                "learner_id": learner_id,
                "active_subject": active_subject,
                "current_concept_id": current_concept_id,
                "current_concept_name": current_concept_name,
                "current_difficulty": current_difficulty,
                "current_teaching_view": current_teaching_view,
                "subject_progress": subject_progress,
                "learner_profile": profile,
                "latest_session_state": session,
                "current_concept": {
                    "concept_id": current_concept_id,
                    "concept_name": current_concept_name,
                    "domain": active_subject,
                    "difficulty": current_difficulty,
                    "teaching_view": current_teaching_view,
                },
                "reward_state": reward_state_packet(learner_id),
                "revision_due_summary": {
                    "due_count": len(revision_due_packet(learner_id)),
                    "due_items": revision_due_packet(learner_id),
                },
                "current_activity": {
                    "type": "returning_revision" if revision_due_packet(learner_id) else "teaching",
                    "frontend_component": "GuidedTutorJourney",
                    "payload": {},
                },
                "next_recommended_activity": {
                    "type": "flashcard_revision" if revision_due_packet(learner_id) else "teaching",
                    "label": "Start revision" if revision_due_packet(learner_id) else "Continue learning",
                    "reason": "Revision schedule has due items." if revision_due_packet(learner_id) else "No due revision found.",
                },
                "guide_message": "Welcome back! It's been a while, so let's revise before continuing." if revision_due_packet(learner_id) else "Let's continue your guided learning session.",
                "backend_connected": True,
            },
        )
    except Exception as exc:
        return safe_error(module, exc)


@router.post("/select-subject")
def select_subject(payload: SelectSubjectRequest) -> dict:
    module = "LearnerRoutes"
    subject = payload.subject.strip()
    try:
        from tutor.api.integration_routes import _concepts

        subject_id = _subject_id(subject)
        concepts = _concepts(subject_id)
        first = concepts[0] if concepts else {"id": "concept_1", "name": f"{subject} basics"}
        now = now_iso()
        conn = connect()
        try:
            _ensure_subject_switch_schema(conn)
            _snapshot_active_subject(conn, payload.learner_id, now)
            restored = _restore_subject_state(conn, payload.learner_id, subject, first, now)
            concept_id = restored["concept_id"]
            concept_name = restored["concept_name"]
            current_difficulty = restored["current_difficulty"]
            current_teaching_view = restored["current_teaching_view"]
            updated_profile = conn.execute(
                """
                UPDATE learner_profile
                SET active_subject = ?, current_domain = ?, current_concept_id = ?,
                    current_concept_name = ?, current_difficulty = ?,
                    preferred_teaching_view = COALESCE(preferred_teaching_view, ?),
                    updated_at = ?
                WHERE learner_id = ?
                """,
                (subject, subject, concept_id, concept_name, current_difficulty, current_teaching_view, now, payload.learner_id),
            )
            if updated_profile.rowcount == 0:
                conn.execute(
                    """
                    INSERT INTO learner_profile (
                        learner_id, display_name, active_subject, current_domain,
                        current_concept_id, current_concept_name, current_difficulty, preferred_teaching_view,
                        profile_json, created_at, updated_at
                    )
                    VALUES (?, 'Learner', ?, ?, ?, ?, ?, ?, '{"source":"select_subject"}', ?, ?)
                    """,
                    (
                        payload.learner_id,
                        subject,
                        subject,
                        concept_id,
                        concept_name,
                        current_difficulty,
                        current_teaching_view,
                        now,
                        now,
                    ),
                )
            conn.execute(
                """
                INSERT INTO learner_session_log (
                    learner_id, session_id, event_type, domain, concept_id, concept_name,
                    teaching_view, difficulty, event_json, created_at, selected_view, started_at, mode
                )
                VALUES (?, 'guided_session', 'subject_selected', ?, ?, ?, ?, ?,
                        '{"auto_flow":true}', ?, 'code_view', ?, 'guided')
                """,
                (payload.learner_id, subject, concept_id, concept_name, current_teaching_view, current_difficulty, now, now),
            )
            subject_progress = _subject_progress_packet(conn, payload.learner_id, subject)
            conn.commit()
        finally:
            conn.close()
        return api_response(
            module=module,
            data={
                "auto_flow": True,
                "learner_id": payload.learner_id,
                "active_subject": subject,
                "current_concept_id": concept_id,
                "current_concept_name": concept_name,
                "current_difficulty": current_difficulty,
                "difficulty": current_difficulty,
                "current_teaching_view": current_teaching_view,
                "subject_progress": subject_progress,
                "difficulty_progress": {"easy": "current", "medium": "locked", "hard": "locked"},
                "next_route": f"/lesson/{concept_id}",
                "current_activity": {
                    "type": "teaching",
                    "frontend_component": "SelectedTeachingViewRenderer",
                    "payload": {"concept_id": concept_id, "concept_name": concept_name},
                },
                "next_recommended_activity": {
                    "type": "assessment",
                    "label": "Try a quick check",
                    "reason": "Check understanding after the first teaching view.",
                },
                "guide_message": f"Great choice! I'll start from {concept_name} for you.",
                "backend_connected": True,
            },
        )
    except Exception as exc:
        return safe_error(module, exc)


def _subject_id(subject: str) -> str:
    normalized = subject.strip().lower()
    if "sql" in normalized or "database" in normalized:
        return "sql-database"
    if "html" in normalized or "web" in normalized:
        return "html-web-basics"
    if "git" in normalized:
        return "git"
    if "data" in normalized:
        return "data-structures"
    return "python"


def _ensure_subject_switch_schema(conn: sqlite3.Connection) -> None:
    if not column_exists(conn, "learner_profile", "active_subject"):
        conn.execute("ALTER TABLE learner_profile ADD COLUMN active_subject TEXT")
    if not column_exists(conn, "learner_profile", "current_difficulty"):
        conn.execute("ALTER TABLE learner_profile ADD COLUMN current_difficulty TEXT")
    if not table_exists(conn, "concept_unlock_state"):
        conn.execute(
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
            """
        )


def _snapshot_active_subject(conn: sqlite3.Connection, learner_id: str, now: str) -> None:
    profile = row_to_dict(conn.execute("SELECT * FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone())
    subject = profile.get("active_subject") or profile.get("current_domain")
    concept_id = profile.get("current_concept_id")
    if not subject or not concept_id:
        return
    concept_name = profile.get("current_concept_name") or str(concept_id)
    difficulty = profile.get("current_difficulty") or "easy"
    existing = _unlock_row(conn, learner_id, str(concept_id), str(subject))
    evidence = safe_json_loads((existing or {}).get("evidence_json"))
    evidence.update({"source": "subject_switch_snapshot", "current_difficulty": difficulty})
    mastery = float((existing or {}).get("mastery_score") or 0.0)
    status = (existing or {}).get("unlock_status") or "current"
    _upsert_unlock_state(
        conn,
        learner_id=learner_id,
        subject=str(subject),
        concept_id=str(concept_id),
        concept_name=str(concept_name),
        unlock_status=str(status),
        mastery_score=mastery,
        promotion_confidence=float((existing or {}).get("promotion_confidence") or 1.0),
        evidence=evidence,
        now=now,
    )


def _restore_subject_state(
    conn: sqlite3.Connection,
    learner_id: str,
    subject: str,
    first_concept: dict[str, Any],
    now: str,
) -> dict[str, Any]:
    first_id = str(first_concept.get("id") or "concept_1")
    first_name = str(first_concept.get("name") or first_id.replace("_", " ").title())
    progress = _latest_subject_progress(conn, learner_id, subject)
    concept_id = str(progress.get("concept_id") or first_id)
    concept_name = str(progress.get("concept_name") or first_name)
    unlock = _unlock_row(conn, learner_id, concept_id, subject)
    kt = _knowledge_state_for_concept(conn, learner_id, subject, concept_id)
    evidence = safe_json_loads((unlock or {}).get("evidence_json"))
    difficulty = (
        progress.get("current_difficulty")
        or evidence.get("current_difficulty")
        or evidence.get("next_difficulty")
        or kt.get("difficulty")
        or "easy"
    )
    teaching_view = evidence.get("current_teaching_view") or progress.get("current_teaching_view") or "code_view"
    mastery = _first_float(progress.get("mastery"), (unlock or {}).get("mastery_score"), kt.get("mastery"), default=0.0)
    status = str((unlock or {}).get("unlock_status") or progress.get("status") or "current")
    if status == "locked":
        status = "current"
    evidence.update(
        {
            "source": "select_subject_restore" if progress or unlock or kt else "select_subject_initialize",
            "current_difficulty": difficulty,
            "current_teaching_view": teaching_view,
        }
    )
    _upsert_unlock_state(
        conn,
        learner_id=learner_id,
        subject=subject,
        concept_id=concept_id,
        concept_name=concept_name,
        unlock_status=status,
        mastery_score=mastery,
        promotion_confidence=float((unlock or {}).get("promotion_confidence") or 1.0),
        evidence=evidence,
        now=now,
    )
    if not progress:
        existing_progress = conn.execute(
            """
            SELECT id FROM learner_concept_progress
            WHERE learner_id = ? AND domain = ? AND concept_id = ?
            LIMIT 1
            """,
            (learner_id, subject, concept_id),
        ).fetchone()
        if not existing_progress:
            conn.execute(
                """
                INSERT INTO learner_concept_progress (
                    learner_id, domain, concept_id, concept_name, status, mastery,
                    attempts, last_score, last_activity_at, unlocked_at, updated_at
                )
                VALUES (?, ?, ?, ?, 'current', ?, 0, 0.0, ?, ?, ?)
                """,
                (learner_id, subject, concept_id, concept_name, mastery, now, now, now),
            )
    return {
        "concept_id": concept_id,
        "concept_name": concept_name,
        "current_difficulty": str(difficulty).lower(),
        "current_teaching_view": str(teaching_view),
        "mastery": mastery,
    }


def _latest_subject_progress(conn: sqlite3.Connection, learner_id: str, subject: str) -> dict[str, Any]:
    if table_exists(conn, "learner_concept_progress"):
        row = conn.execute(
            """
            SELECT * FROM learner_concept_progress
            WHERE learner_id = ? AND domain = ?
            ORDER BY updated_at DESC, last_activity_at DESC
            LIMIT 1
            """,
            (learner_id, subject),
        ).fetchone()
        data = row_to_dict(row)
        if data:
            return data
    if table_exists(conn, "concept_unlock_state"):
        row = conn.execute(
            """
            SELECT * FROM concept_unlock_state
            WHERE learner_id = ? AND domain = ?
            ORDER BY
                CASE unlock_status WHEN 'current' THEN 0 WHEN 'unlocked' THEN 1 WHEN 'mastered' THEN 2 ELSE 3 END,
                updated_at DESC
            LIMIT 1
            """,
            (learner_id, subject),
        ).fetchone()
        data = row_to_dict(row)
        if data:
            evidence = safe_json_loads(data.get("evidence_json"))
            data["mastery"] = data.get("mastery_score")
            data["status"] = data.get("unlock_status")
            data["current_difficulty"] = evidence.get("current_difficulty") or evidence.get("next_difficulty")
            data["current_teaching_view"] = evidence.get("current_teaching_view")
            return data
    return {}


def _unlock_row(conn: sqlite3.Connection, learner_id: str, concept_id: str, subject: str) -> dict[str, Any]:
    if not table_exists(conn, "concept_unlock_state"):
        return {}
    return row_to_dict(
        conn.execute(
            """
            SELECT * FROM concept_unlock_state
            WHERE learner_id = ? AND concept_id = ? AND (domain = ? OR domain IS NULL OR domain = '')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (learner_id, concept_id, subject),
        ).fetchone()
    )


def _upsert_unlock_state(
    conn: sqlite3.Connection,
    *,
    learner_id: str,
    subject: str,
    concept_id: str,
    concept_name: str,
    unlock_status: str,
    mastery_score: float,
    promotion_confidence: float,
    evidence: dict[str, Any],
    now: str,
) -> None:
    existing = row_to_dict(
        conn.execute(
            "SELECT id, unlocked_at FROM concept_unlock_state WHERE learner_id = ? AND concept_id = ? LIMIT 1",
            (learner_id, concept_id),
        ).fetchone()
    )
    if existing:
        conn.execute(
            """
            UPDATE concept_unlock_state
            SET domain = ?, concept_name = ?, unlock_status = ?,
                mastery_score = MAX(COALESCE(mastery_score, 0.0), ?),
                promotion_confidence = MAX(COALESCE(promotion_confidence, 0.0), ?),
                prerequisites_met = 1,
                unlocked_at = COALESCE(unlocked_at, ?),
                evidence_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                subject,
                concept_name,
                unlock_status,
                mastery_score,
                promotion_confidence,
                now,
                json.dumps(evidence),
                now,
                existing["id"],
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO concept_unlock_state (
                learner_id, concept_id, domain, concept_name, unlock_status,
                mastery_score, promotion_confidence, prerequisites_met, unlocked_at,
                evidence_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (learner_id, concept_id, subject, concept_name, unlock_status, mastery_score, promotion_confidence, now, json.dumps(evidence), now),
        )


def _knowledge_state_for_concept(conn: sqlite3.Connection, learner_id: str, subject: str, concept_id: str) -> dict[str, Any]:
    if not table_exists(conn, "knowledge_state"):
        return {}
    row = conn.execute("SELECT state_json FROM knowledge_state WHERE student_id = ? LIMIT 1", (learner_id,)).fetchone()
    state = safe_json_loads(row[0] if row else None)
    subjects = state.get("subjects") if isinstance(state, dict) else {}
    concept_state = (((subjects or {}).get(subject) or {}).get("concepts") or {}).get(concept_id)
    if isinstance(concept_state, dict):
        return concept_state
    if state.get("concept_id") == concept_id:
        return state
    return {}


def _subject_progress_packet(conn: sqlite3.Connection, learner_id: str, subject: Any) -> dict[str, Any]:
    if not subject:
        return {}
    progress_rows = []
    unlock_rows = []
    if table_exists(conn, "learner_concept_progress"):
        progress_rows = rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM learner_concept_progress
                WHERE learner_id = ? AND domain = ?
                ORDER BY updated_at DESC
                """,
                (learner_id, subject),
            ).fetchall()
        )
    if table_exists(conn, "concept_unlock_state"):
        unlock_rows = rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM concept_unlock_state
                WHERE learner_id = ? AND domain = ?
                ORDER BY updated_at DESC
                """,
                (learner_id, subject),
            ).fetchall()
        )
    mastered = [row for row in progress_rows if str(row.get("status")) == "mastered" or float(row.get("mastery") or 0) >= 0.85]
    total = max(len({row.get("concept_id") for row in unlock_rows}) or len(progress_rows), len(progress_rows), 1)
    return {
        "subject": subject,
        "concepts_seen": len({row.get("concept_id") for row in progress_rows + unlock_rows if row.get("concept_id")}),
        "mastered_concepts": len(mastered),
        "total_tracked_concepts": total,
        "mastery_percent": round((len(mastered) / total) * 100) if total else 0,
        "progress": progress_rows,
        "unlock_state": unlock_rows,
    }


@router.get("/subject-progress/{learner_id}")
def learner_subject_progress(learner_id: str) -> dict:
    module = "LearnerRoutes"
    try:
        from tutor.api.integration_routes import _concepts

        conn = connect()
        try:
            profile = row_to_dict(
                conn.execute("SELECT * FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone()
            )
            active_subject = profile.get("active_subject") or profile.get("current_domain")
            subjects = []
            for subject in SUBJECT_NAMES:
                subject_id = _subject_id(subject)
                concepts = _concepts(subject_id)
                total_concepts = len(concepts)
                progress_rows = []
                unlock_rows = []
                quiz_rows = []
                if table_exists(conn, "learner_concept_progress"):
                    progress_rows = rows_to_dicts(
                        conn.execute(
                            """
                            SELECT * FROM learner_concept_progress
                            WHERE learner_id = ? AND domain = ?
                            """,
                            (learner_id, subject),
                        ).fetchall()
                    )
                if table_exists(conn, "concept_unlock_state"):
                    unlock_rows = rows_to_dicts(
                        conn.execute(
                            """
                            SELECT * FROM concept_unlock_state
                            WHERE learner_id = ? AND domain = ?
                            """,
                            (learner_id, subject),
                        ).fetchall()
                    )
                if table_exists(conn, "quiz_results"):
                    quiz_rows = rows_to_dicts(
                        conn.execute(
                            """
                            SELECT * FROM quiz_results
                            WHERE learner_id = ? AND (subject = ? OR domain = ?)
                            """,
                            (learner_id, subject, subject),
                        ).fetchall()
                    )
                concept_ids = {
                    str(row.get("concept_id"))
                    for row in progress_rows + unlock_rows + quiz_rows
                    if row.get("concept_id")
                }
                completed_ids = {
                    str(row.get("concept_id"))
                    for row in progress_rows + unlock_rows
                    if str(row.get("status") or row.get("unlock_status")).lower() in {"mastered", "completed"}
                    or float(row.get("mastery") or row.get("mastery_score") or 0.0) >= 0.85
                }
                mastery_values = [
                    float(row.get("mastery") or row.get("mastery_score") or 0.0)
                    for row in progress_rows + unlock_rows
                    if row.get("concept_id")
                ]
                average_mastery = round(sum(mastery_values) / len(mastery_values), 4) if mastery_values else 0.0
                latest = progress_rows[0] if progress_rows else unlock_rows[0] if unlock_rows else {}
                has_activity = bool(concept_ids)
                is_active = active_subject == subject and has_activity
                status = "In Progress" if is_active else "Completed" if completed_ids and len(completed_ids) >= total_concepts else "Not Started"
                if not has_activity:
                    status = "Not Started"
                subjects.append(
                    {
                        "subject": subject,
                        "total_concepts": total_concepts,
                        "attempted_concepts": len(concept_ids),
                        "completed_concepts": len(completed_ids),
                        "average_mastery": average_mastery,
                        "progress_percent": round(average_mastery * 100),
                        "status": status,
                        "current_concept_id": latest.get("concept_id") if is_active else None,
                        "current_concept_name": latest.get("concept_name") if is_active else None,
                    }
                )
        finally:
            conn.close()
        return api_response(
            module=module,
            data={
                "learner_id": learner_id,
                "active_subject": active_subject,
                "current_concept_id": profile.get("current_concept_id"),
                "subjects": subjects,
            },
        )
    except Exception as exc:
        return safe_error(module, exc)


def _first_float(*values: Any, default: float = 0.0) -> float:
    for value in values:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return default


@router.get("/progress/{learner_id}")
def learner_progress(learner_id: str, subject: str | None = None) -> dict:
    module = "LearnerRoutes"
    try:
        conn = connect()
        try:
            progress_rows = []
            quiz_rows = []
            unlock_rows = []
            if table_exists(conn, "learner_concept_progress"):
                if subject:
                    progress_rows = rows_to_dicts(conn.execute(
                        """
                        SELECT * FROM learner_concept_progress
                        WHERE learner_id = ? AND domain = ?
                        ORDER BY updated_at DESC
                        """,
                        (learner_id, subject),
                    ).fetchall())
                else:
                    progress_rows = rows_to_dicts(conn.execute(
                        "SELECT * FROM learner_concept_progress WHERE learner_id = ? ORDER BY updated_at DESC",
                        (learner_id,),
                    ).fetchall())
            if table_exists(conn, "quiz_results"):
                if subject:
                    quiz_rows = rows_to_dicts(conn.execute(
                        """
                        SELECT * FROM quiz_results
                        WHERE learner_id = ? AND (subject = ? OR domain = ?)
                        ORDER BY timestamp DESC LIMIT 100
                        """,
                        (learner_id, subject, subject),
                    ).fetchall())
                else:
                    quiz_rows = rows_to_dicts(conn.execute(
                        "SELECT * FROM quiz_results WHERE learner_id = ? ORDER BY timestamp DESC LIMIT 100",
                        (learner_id,),
                    ).fetchall())
            if table_exists(conn, "concept_unlock_state"):
                if subject:
                    unlock_rows = rows_to_dicts(conn.execute(
                        "SELECT * FROM concept_unlock_state WHERE learner_id = ? AND domain = ? ORDER BY updated_at DESC",
                        (learner_id, subject),
                    ).fetchall())
                else:
                    unlock_rows = rows_to_dicts(conn.execute(
                        "SELECT * FROM concept_unlock_state WHERE learner_id = ? ORDER BY updated_at DESC",
                        (learner_id,),
                    ).fetchall())
        finally:
            conn.close()
        rewards = reward_state_packet(learner_id)
        xp = rewards.get("xp") or {}
        streak = rewards.get("streak") or {}
        mastered = [row for row in progress_rows if str(row.get("status")) == "mastered" or float(row.get("mastery") or 0) >= 0.85]
        correct_count = sum(1 for row in quiz_rows if row.get("is_correct") in {1, True, "1"})
        accuracy = round((correct_count / len(quiz_rows)) * 100) if quiz_rows else 0
        subject_name = subject or (progress_rows[0].get("domain") if progress_rows else "Selected subject")
        has_progress_data = bool(quiz_rows or any(float(row.get("mastery") or 0.0) > 0 for row in progress_rows) or int(xp.get("total_xp") or 0) > 0)
        total_concepts = max(len({row.get("concept_id") for row in unlock_rows}) or len(progress_rows), len(progress_rows), 1)
        return api_response(module=module, data={
            "learner_id": learner_id,
            "sourceLabel": "Live backend" if has_progress_data else "No progress yet",
            "hasProgressData": has_progress_data,
            "currentLevel": int(xp.get("current_level") or 1),
            "totalXP": int(xp.get("total_xp") or 0),
            "currentStreak": int(streak.get("current_streak") or 0),
            "conceptsMastered": len(mastered),
            "accuracy": accuracy,
            "averageConfidence": round(sum(float(row.get("confidence") or 0) for row in quiz_rows) / len(quiz_rows), 2) if quiz_rows else 0,
            "reviewDue": len(revision_due_packet(learner_id)),
            "xpToday": int(xp.get("daily_xp") or 0),
            "masteryPercent": round((len(mastered) / total_concepts) * 100) if total_concepts else 0,
            "subjectProgress": [{
                "subjectName": subject_name,
                "progressPercentage": round((len(mastered) / total_concepts) * 100) if total_concepts else 0,
                "masteredConcepts": len(mastered),
                "totalConcepts": total_concepts,
                "color": "#0284c7",
            }],
            "conceptMastery": [{
                "conceptName": row.get("concept_name") or row.get("concept_id"),
                "subject": row.get("domain") or subject_name,
                "mastery": round(float(row.get("mastery") or 0) * 100),
                "status": "mastered" if float(row.get("mastery") or 0) >= 0.85 else row.get("status") or "in_progress",
                "lastPracticed": row.get("last_activity_at") or row.get("updated_at") or "",
            } for row in progress_rows if has_progress_data],
            "recentAttempts": [{
                "conceptName": row.get("concept_name") or row.get("concept_id"),
                "subject": row.get("subject") or row.get("domain") or subject_name,
                "questionType": row.get("question_type"),
                "score": 100 if row.get("is_correct") in {1, True, "1"} else 0,
                "timestamp": row.get("timestamp") or "",
            } for row in quiz_rows[:5]],
            "weakAreas": [{
                "concept": row.get("concept_name") or row.get("concept_id") or "Current concept",
                "skill": row.get("question_type") or "current skill",
                "severity": "medium",
                "recommendedAction": "Review the expected answer, then try one similar task.",
            } for row in quiz_rows if row.get("is_correct") not in {1, True, "1"}][:5],
            "xpHistory": [],
            "streakCalendar": [],
        })
    except Exception as exc:
        return safe_error(module, exc)


@router.get("/notebook/search/{learner_id}")
def notebook_search(
    learner_id: str,
    q: str = "",
    top_k: int = 5,
    source_filter: str | None = None,
) -> dict:
    module = "LearnerRoutes"
    try:
        result = SemanticNotebookSearch().search(
            learner_id=learner_id,
            query=q,
            top_k=top_k,
            source_filter=source_filter,
        )
        return api_response(module=module, fallback_used=result.get("fallback_used", False), data=result)
    except Exception as exc:
        return safe_error(module, exc)


@router.get("/notebook/summary/{learner_id}")
def notebook_summary(learner_id: str) -> dict:
    module = "LearnerRoutes"
    try:
        result = SemanticNotebookSearch().get_weakness_summary(learner_id)
        return api_response(module=module, data=result)
    except Exception as exc:
        return safe_error(module, exc)


@router.get("/session/{learner_id}")
def learner_session(learner_id: str) -> dict:
    module = "LearnerRoutes"
    try:
        session = latest_session_state(learner_id)
        return api_response(
            module=module,
            fallback_used=not bool(session),
            data={
                "learner_id": learner_id,
                "learner_session_state": session,
            },
            reason=None if session else "No saved learner_session_state found.",
        )
    except Exception as exc:
        return safe_error(module, exc)


@router.post("/session")
def save_session(payload: SaveSessionRequest) -> dict:
    module = "LearnerRoutes"
    try:
        packet = dict(payload.active_session_packet or {})
        packet.update(
            {
                "domain": payload.subject or packet.get("domain"),
                "concept_id": payload.concept_id or packet.get("concept_id"),
                "concept_name": payload.concept_name or packet.get("concept_name"),
                "teaching_view": payload.teaching_view or packet.get("teaching_view"),
                "difficulty": payload.difficulty or packet.get("difficulty"),
            }
        )
        saved = save_session_state(payload.learner_id, packet)
        return api_response(module=module, fallback_used=saved.get("status") != "success", data=saved)
    except Exception as exc:
        return safe_error(module, exc)
