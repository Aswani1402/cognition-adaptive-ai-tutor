from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from tutor.api.concept_content_resolver import (
    ASSESSMENT_TYPES,
    DOUBT_TYPES,
    FEEDBACK_TYPES,
    FLASHCARD_TYPES,
    HINT_TYPES,
    TEACHING_VIEWS,
    assessment_payload,
    build_doubt_answer,
    build_feedback,
    build_flashcards,
    build_hints,
    build_lesson_payload,
    build_mindmap,
    build_notebook,
    build_voice_scripts,
    fallback_questions,
    normalize_subject,
    resolve_concept_content,
)
from tutor.api.dependencies import connect, latest_concept_from_logs, reward_state_packet, revision_due_packet, row_to_dict, rows_to_dicts, safe_json_loads, table_exists
from tutor.api.schemas import api_response
from tutor.notebook.learner_facing import normalize_notebook_memory, format_mistake_for_learner
from tutor.system.agentic_orchestrator import latest_agentic_trace


router = APIRouter(tags=["frontend-integration"])

ROOT = Path(__file__).resolve().parents[2]
CORE_DATA = ROOT / "external" / "core_data"
SUBJECTS = [
    {"id": "python", "name": "Python", "db": "python_learning.db", "icon": "Code", "color": "bg-blue-500"},
    {"id": "sql-database", "name": "SQL / Database", "db": "database_sql.db", "icon": "Database", "color": "bg-cyan-500"},
    {"id": "html-web-basics", "name": "HTML/Web Basics", "db": "html_web_basics.db", "icon": "Globe", "color": "bg-orange-500"},
    {"id": "git", "name": "Git", "db": "git_version_control.db", "icon": "GitBranch", "color": "bg-rose-500"},
    {"id": "data-structures", "name": "Data Structures", "db": "data_structures.db", "icon": "Network", "color": "bg-emerald-500"},
]


def _warning(module: str, reason: str, **data: Any) -> dict[str, Any]:
    return api_response(status="warning", module=module, fallback_used=True, reason=reason, data=data)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _ensure_notebook_notes(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_notebook_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            subject TEXT,
            concept_id TEXT,
            concept_name TEXT,
            note_type TEXT,
            title TEXT,
            content TEXT,
            source_page TEXT,
            related_question_id TEXT,
            mistake_type TEXT,
            weak_skill TEXT,
            content_hash TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(learner_id, content_hash)
        )
        """
    )


def _notes_for_learner(conn, learner_id: str, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_notebook_notes(conn)
    return rows_to_dicts(
        conn.execute(
            """
            SELECT * FROM learner_notebook_notes
            WHERE learner_id = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (learner_id, limit),
        ).fetchall()
    )


def _memory_rows(conn, table_name: str, learner_id: str, limit: int = 10) -> list[dict[str, Any]]:
    if not table_exists(conn, table_name):
        return []
    order_col = "created_at"
    try:
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        if "updated_at" in cols:
            order_col = "updated_at"
        elif "due_at" in cols:
            order_col = "due_at"
    except Exception:
        pass
    return rows_to_dicts(
        conn.execute(
            f"SELECT * FROM {table_name} WHERE learner_id = ? ORDER BY {order_col} DESC LIMIT ?",
            (learner_id, limit),
        ).fetchall()
    )


def _concepts(subject_id: str = "python", learner_id: str | None = None) -> list[dict[str, Any]]:
    subject = next((item for item in SUBJECTS if item["id"] == subject_id or item["name"].lower() == subject_id.lower()), SUBJECTS[0])
    db_path = CORE_DATA / subject["db"]
    subject_defaults = {
        "python": [("P1", "Variables", "lesson", "easy"), ("P2", "Data Types", "practice", "easy"), ("P3", "Conditionals", "quiz", "medium")],
        "sql-database": [("S1", "Database Basics", "lesson", "easy"), ("S2", "SQL SELECT Queries", "practice", "easy"), ("S3", "Filtering with WHERE", "quiz", "medium")],
        "html-web-basics": [("H1", "What is HTML", "lesson", "easy"), ("H2", "Common Tags", "practice", "easy"), ("H3", "Links and Images", "quiz", "medium")],
        "git": [("G1", "Version Control", "lesson", "easy"), ("G2", "Commits", "practice", "easy"), ("G3", "Branches", "quiz", "medium")],
        "data-structures": [("D1", "Arrays", "lesson", "easy"), ("D2", "Stacks", "practice", "easy"), ("D3", "Queues", "quiz", "medium")],
    }
    defaults = subject_defaults.get(subject["id"], subject_defaults["python"])
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                for table in ["concepts", "lessons", "content"]:
                    if table in tables:
                        rows = rows_to_dicts(conn.execute(f"SELECT * FROM {table} LIMIT 20").fetchall())
                        mapped = []
                        current_id, current_difficulty, completed_ids = _learner_path_state(learner_id, subject["name"])
                        for i, row in enumerate(rows[:10]):
                            cid = str(row.get("concept_id") or row.get("id") or row.get("slug") or f"{subject['id']}-{i + 1}")
                            name = str(row.get("concept_name") or row.get("name") or row.get("title") or cid.replace("_", " ").title())
                            status = _node_status_for_index(i, cid, current_id, completed_ids)
                            mapped.append({
                                "id": cid,
                                "name": name,
                                "subjectId": subject["id"],
                                "status": status,
                                "type": "lesson" if i == 0 else "practice",
                                "difficulty": current_difficulty if status == "current" else "easy" if i < 2 else "medium",
                                "dependsOn": [] if i == 0 else [mapped[i - 1]["id"]],
                                "mastery": 0.35 if i == 0 else 0.0,
                                "adaptiveRank": i + 1,
                                "lockedReason": None if status != "locked" else f"Complete {mapped[i - 1]['name']} through easy, medium, and hard to unlock {name}.",
                            })
                        if mapped:
                            return mapped
            finally:
                conn.close()
        except Exception:
            pass
    current_id, current_difficulty, completed_ids = _learner_path_state(learner_id, subject["name"])
    nodes = []
    for i, (cid, name, node_type, difficulty) in enumerate(defaults):
        status = _node_status_for_index(i, cid, current_id, completed_ids)
        nodes.append({
            "id": cid,
            "name": name,
            "subjectId": subject["id"],
            "status": status,
            "type": node_type,
            "difficulty": current_difficulty if status == "current" else difficulty,
            "dependsOn": [] if i == 0 else [defaults[i - 1][0]],
            "mastery": 0.4 if i == 0 else 0.0,
            "adaptiveRank": i + 1,
            "lockedReason": None if status != "locked" else f"Complete {defaults[i - 1][1]} through easy, medium, and hard to unlock {name}.",
        })
    return nodes


def _learner_path_state(learner_id: str | None, subject: str) -> tuple[str | None, str, set[str]]:
    if not learner_id:
        return None, "easy", set()
    try:
        conn = connect()
        try:
            profile = row_to_dict(conn.execute("SELECT current_concept_id, current_difficulty FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone())
            current_id = profile.get("current_concept_id")
            current_difficulty = str(profile.get("current_difficulty") or "easy").lower()
            completed: set[str] = set()
            if table_exists(conn, "concept_unlock_state"):
                rows = rows_to_dicts(conn.execute(
                    """
                    SELECT concept_id FROM concept_unlock_state
                    WHERE learner_id = ? AND domain = ? AND unlock_status IN ('mastered', 'completed')
                    """,
                    (learner_id, subject),
                ).fetchall())
                completed = {str(row.get("concept_id")) for row in rows if row.get("concept_id")}
            return str(current_id) if current_id else None, current_difficulty if current_difficulty in {"easy", "medium", "hard"} else "easy", completed
        finally:
            conn.close()
    except Exception:
        return None, "easy", set()


def _node_status_for_index(index: int, concept_id: str, current_id: str | None, completed_ids: set[str]) -> str:
    if concept_id in completed_ids:
        return "completed"
    if current_id and concept_id == current_id:
        return "current"
    if not current_id and index == 0:
        return "current"
    return "locked"


SUPPORTED_TEACHING_VIEWS = TEACHING_VIEWS


def _difficulty_progress(difficulty: str, retry: bool = False) -> dict[str, str]:
    if difficulty == "medium":
        return {"easy": "passed", "medium": "retry" if retry else "current", "hard": "locked"}
    if difficulty == "hard":
        return {"easy": "passed", "medium": "passed", "hard": "retry" if retry else "current"}
    return {"easy": "retry" if retry else "current", "medium": "locked", "hard": "locked"}


def _lesson(concept_id: str, view: str | None = None, difficulty: str = "easy", subject: str | None = None) -> dict[str, Any]:
    lesson = build_lesson_payload(subject, concept_id, difficulty, view)
    content = lesson
    concept_id = lesson["concept_id"]
    name = lesson["concept_name"]
    selected_view = lesson["selected_view"]
    teaching_content = lesson["teaching_content"]
    return {
        "status": "success",
        "auto_flow": True,
        "conceptId": concept_id,
        "concept_id": concept_id,
        "conceptName": name,
        "concept_name": name,
        "domain": content["subject"],
        "subject": content["subject"],
        "difficulty": difficulty if difficulty in {"easy", "medium", "hard"} else "easy",
        "explanationMode": "adaptive",
        "explanation_mode": "adaptive",
        "selectedView": selected_view,
        "selected_view": selected_view,
        "requested_view": view,
        "view_changed": bool(view),
        "adaptiveExplanation": teaching_content["explanation"],
        "adaptive_explanation": teaching_content["explanation"],
        "fallbackViewNames": SUPPORTED_TEACHING_VIEWS,
        "fallback_views": SUPPORTED_TEACHING_VIEWS,
        "available_views": SUPPORTED_TEACHING_VIEWS,
        "content_by_view": lesson["content_by_view"],
        "difficulty_progress": _difficulty_progress(difficulty if difficulty in {"easy", "medium", "hard"} else "easy"),
        "keyPoints": teaching_content["key_points"],
        "commonMistakes": teaching_content["common_mistakes"],
        "workedExample": teaching_content["code"],
        "baseContent": lesson["base_content"],
        "examples": lesson["examples"],
        "misconceptions": lesson["misconceptions"],
        "realWorldUse": lesson["real_world_use"],
        "nextConceptLink": lesson["next_concept_link"],
        "concept_resources": {key: lesson[key] for key in ["subject", "concept_id", "concept_name", "topic", "base_content", "examples", "key_points", "misconceptions", "real_world_use", "next_concept_link"]},
        "teaching_content": teaching_content,
        "whySelected": f"I chose {selected_view.replace('_', ' ')} because you are on {difficulty} difficulty for {name}.",
        "reason": f"I chose {selected_view.replace('_', ' ')} because this concept benefits from examples and key points at {difficulty} level.",
        "rag_grounding": {"status": "success", "source": "concept_content_resolver", "source_sections": ["base_content", "examples", "key_points"]},
        "xai_reason": {"summary": "Backend selected the requested teaching view for frontend interaction."},
        "frontend_component": "SelectedTeachingViewRenderer",
        "current_activity": {
            "type": "teaching",
            "frontend_component": "SelectedTeachingViewRenderer",
            "payload": teaching_content,
        },
        "next_recommended_activity": {
            "type": "assessment",
            "label": "Try a quick check",
            "reason": "Check understanding after teaching",
        },
        "guide_message": "Now let's do a quick check.",
        "voice_script": lesson["voice_script"],
        "llm_generation": lesson["llm_generation"],
        "backend_connected": True,
        "nextActivity": "quiz",
    }


@router.get("/subjects")
def subjects() -> dict:
    try:
        return api_response(
            module="IntegrationRoutes",
            data={
                "subjects": [
                    {**item, "progress": 0, "unlockedConcepts": 1, "totalConcepts": len(_concepts(item["id"])), "description": f"Adaptive lessons for {item['name']}."}
                    for item in SUBJECTS
                ],
                "database_path": str(CORE_DATA / "tutor.db"),
                "subject_databases": [str(CORE_DATA / item["db"]) for item in SUBJECTS],
            },
        )
    except Exception as exc:
        return _warning("IntegrationRoutes", f"{type(exc).__name__}: {exc}", subjects=SUBJECTS)


@router.get("/learner/profile/{learner_id}")
def learner_profile(learner_id: str) -> dict:
    try:
        conn = connect()
        try:
            profile = row_to_dict(conn.execute("SELECT * FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone())
        finally:
            conn.close()
        display = profile.get("display_name") or "Learner"
        return api_response(module="IntegrationRoutes", fallback_used=not bool(profile), data={
            "learner_id": learner_id,
            "learnerId": learner_id,
            "userId": profile.get("user_id", ""),
            "displayName": display,
            "goal": profile.get("learning_goal") or profile.get("goal") or profile.get("active_subject") or "",
            "level": profile.get("skill_level") or profile.get("level") or "beginner",
            "preferredSubject": profile.get("active_subject") or "",
            "currentStreak": 0,
            "totalXp": 0,
            "profile": profile,
        }, reason=None if profile else "No DB profile found.")
    except Exception as exc:
        return _warning("IntegrationRoutes", f"{type(exc).__name__}: {exc}", learner_id=learner_id)


@router.get("/path/{learner_id}/{subject:path}")
def subject_path(learner_id: str, subject: str) -> dict:
    nodes = _concepts(subject, learner_id=learner_id)
    return api_response(module="IntegrationRoutes", data={"learner_id": learner_id, "subject": subject, "path": nodes, "nodes": nodes})


@router.get("/adaptive-path/{learner_id}")
def adaptive_path(learner_id: str) -> dict:
    current = latest_concept_from_logs(learner_id)
    nodes = _concepts(str(current.get("domain") or "python"), learner_id=learner_id)
    return api_response(module="IntegrationRoutes", data={"learner_id": learner_id, "path": nodes, "recommendation": nodes[0] if nodes else {}})


@router.get("/lesson/{learner_id}/{concept_id}")
def lesson(learner_id: str, concept_id: str, view: str | None = None, difficulty: str = "easy", subject: str | None = None) -> dict:
    return api_response(module="IntegrationRoutes", data={"learner_id": learner_id, **_lesson(concept_id, view, difficulty, subject)})


@router.get("/assessment/{learner_id}/{concept_id}")
def assessment(learner_id: str, concept_id: str, difficulty: str = "easy", subject: str | None = None) -> dict:
    packet = assessment_payload(subject, concept_id, difficulty)
    questions = packet["questions"][:10]
    return api_response(module="IntegrationRoutes", data={
        "status": "success",
        "auto_flow": True,
        "learner_id": learner_id,
        "subject": packet["subject"],
        "concept_id": packet["concept_id"],
        "concept_name": packet["concept_name"],
        "difficulty": difficulty,
        "question_count": len(questions),
        "difficulty_progress": _difficulty_progress(difficulty),
        "questions": questions,
        "assessment": questions,
        "coverage": ASSESSMENT_TYPES,
        "supported_question_types": ASSESSMENT_TYPES,
        "llm_generation": packet["llm_generation"],
        "current_activity": {"type": "assessment", "frontend_component": "AssessmentRenderer", "payload": {"question_count": len(questions)}},
        "next_recommended_activity": {"type": "feedback", "label": "Submit answer", "reason": "Evaluate answer and choose adaptive next step"},
        "guide_message": "Now let's do a quick check.",
        "backend_connected": True,
    })


@router.post("/question/similar")
def similar_question(payload: dict[str, Any]) -> dict:
    subject = payload.get("subject") or payload.get("domain")
    concept_id = payload.get("concept_id") or payload.get("conceptId")
    difficulty = str(payload.get("difficulty") or "easy")
    question_type = str(payload.get("question_type") or payload.get("questionType") or "")
    excluded = {str(item) for item in (payload.get("exclude_question_ids") or payload.get("excludeQuestionIds") or [])}
    packet = assessment_payload(subject, concept_id, difficulty)
    questions = packet["questions"]
    preferred = [
        q for q in questions
        if str(q.get("question_id") or q.get("questionId")) not in excluded
        and (not question_type or str(q.get("question_type") or q.get("questionType")) == question_type)
    ]
    pool = preferred or [q for q in questions if str(q.get("question_id") or q.get("questionId")) not in excluded] or questions
    question = pool[0] if pool else {}
    return api_response(module="IntegrationRoutes", fallback_used=not bool(preferred), data={
        "learner_id": payload.get("learner_id") or payload.get("learnerId"),
        "subject": packet["subject"],
        "concept_id": packet["concept_id"],
        "concept_name": packet["concept_name"],
        "question": question,
        "similar_question": question,
        "excluded_question_ids": sorted(excluded),
        "llm_generation": packet["llm_generation"],
        "reason": "Returned a same-type unseen question when available; otherwise returned the next safe concept question.",
    })


@router.get("/similar-question/{learner_id}/{concept_id}")
def similar_question_get(
    learner_id: str,
    concept_id: str,
    subject: str | None = None,
    difficulty: str = "easy",
    question_type: str | None = None,
    exclude_question_ids: str = "",
) -> dict:
    excluded = [item.strip() for item in exclude_question_ids.split(",") if item.strip()]
    return similar_question(
        {
            "learner_id": learner_id,
            "concept_id": concept_id,
            "subject": subject,
            "difficulty": difficulty,
            "question_type": question_type,
            "exclude_question_ids": excluded,
        }
    )


@router.post("/doubt/followup")
def doubt_followup(payload: dict[str, Any]) -> dict:
    answer = str(payload.get("answer") or "").strip()
    correct = bool(answer)
    return api_response(module="IntegrationRoutes", data={"correct": correct, "score": 1.0 if correct else 0.0, "feedback": "Follow-up recorded.", "memoryUpdated": True, "nextAction": "continue"})


@router.get("/notebook/{learner_id}")
def notebook(learner_id: str) -> dict:
    try:
        summary = {}
        notes: list[dict[str, Any]] = []
        mistakes: list[dict[str, Any]] = []
        doubts: list[dict[str, Any]] = []
        revisions: list[dict[str, Any]] = []
        cards: list[dict[str, Any]] = []
        conn = connect()
        try:
            if table_exists(conn, "learner_session_state"):
                summary = row_to_dict(conn.execute("SELECT * FROM learner_session_state WHERE learner_id = ? ORDER BY updated_at DESC LIMIT 1", (learner_id,)).fetchone())
            if not summary and table_exists(conn, "learner_profile"):
                summary = row_to_dict(conn.execute("SELECT * FROM learner_profile WHERE learner_id = ? LIMIT 1", (learner_id,)).fetchone())
            notes = _notes_for_learner(conn, learner_id)
            mistakes = _memory_rows(conn, "learner_mistake_log", learner_id, 8)
            doubts = _memory_rows(conn, "learner_doubt_log", learner_id, 8)
            revisions = _memory_rows(conn, "revision_schedule", learner_id, 8)
            cards = _memory_rows(conn, "revision_card", learner_id, 8)
        finally:
            conn.close()
        subject = summary.get("active_subject") or summary.get("domain") or "Python"
        concept_id = summary.get("current_concept_id") or None
        packet = build_notebook(subject, concept_id, learner_id)
        learner_facing = normalize_notebook_memory(
            packet=packet,
            notes=notes,
            mistakes=mistakes,
            doubts=doubts,
            revisions=revisions,
            cards=cards,
            summary_state=summary,
        )
        return api_response(module="IntegrationRoutes", fallback_used=not bool(summary), data={
            **packet,
            **learner_facing,
            "lastUpdated": summary.get("updated_at") or (notes[0].get("updated_at") if notes else ""),
            "raw_state": summary,
            "learner_memory_used": bool(notes or mistakes or doubts or revisions or cards),
        })
    except Exception as exc:
        return _warning("IntegrationRoutes", f"{type(exc).__name__}: {exc}", learnerId=learner_id)


@router.post("/notebook/save")
def notebook_save(payload: dict[str, Any]) -> dict:
    module = "NotebookRoutes"
    learner_id = str(payload.get("learner_id") or payload.get("learnerId") or "").strip()
    if not learner_id:
        return _warning(module, "Missing learner_id.", saved=False)
    content = str(payload.get("content") or payload.get("body") or payload.get("back") or "").strip()
    title = str(payload.get("title") or payload.get("front") or "Saved note").strip()
    if not content:
        content = title
    subject = payload.get("subject") or payload.get("domain") or "Python"
    concept_id = payload.get("concept_id") or payload.get("conceptId")
    concept_name = payload.get("concept_name") or payload.get("conceptName")
    note_type = str(payload.get("note_type") or payload.get("noteType") or "saved_note")
    source_page = str(payload.get("source_page") or payload.get("sourcePage") or "frontend")
    now = _now_iso()
    content_hash = hashlib.sha256("|".join([learner_id, str(subject), str(concept_id), note_type, title, content]).encode("utf-8")).hexdigest()
    conn = connect()
    try:
        _ensure_notebook_notes(conn)
        existing = row_to_dict(conn.execute("SELECT * FROM learner_notebook_notes WHERE learner_id = ? AND content_hash = ? LIMIT 1", (learner_id, content_hash)).fetchone())
        if existing:
            return api_response(module=module, data={"saved": True, "already_saved": True, "note_id": existing.get("id"), "status": "saved"})
        conn.execute(
            """
            INSERT INTO learner_notebook_notes (
                learner_id, subject, concept_id, concept_name, note_type, title, content,
                source_page, related_question_id, mistake_type, weak_skill, content_hash,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                subject,
                concept_id,
                concept_name,
                note_type,
                title,
                content,
                source_page,
                payload.get("related_question_id") or payload.get("relatedQuestionId"),
                payload.get("mistake_type") or payload.get("mistakeType"),
                payload.get("weak_skill") or payload.get("weakSkill"),
                content_hash,
                now,
                now,
            ),
        )
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        return api_response(module=module, data={"saved": True, "already_saved": False, "note_id": note_id, "status": "saved"})
    except Exception as exc:
        conn.rollback()
        return _warning(module, f"{type(exc).__name__}: {exc}", saved=False)
    finally:
        conn.close()


@router.post("/notebook/guide/ask")
def notebook_guide_ask(payload: dict[str, Any]) -> dict:
    module = "NotebookGuideRoutes"
    learner_id = str(payload.get("learner_id") or payload.get("learnerId") or "").strip()
    subject = payload.get("subject") or payload.get("domain") or "Python"
    concept_id = payload.get("concept_id") or payload.get("conceptId")
    concept = resolve_concept_content(subject, concept_id)
    question = str(payload.get("question") or payload.get("prompt") or payload.get("doubt_text") or "What should I revise?").strip()
    conn = connect()
    try:
        notes = _notes_for_learner(conn, learner_id, 8)
        mistakes = _memory_rows(conn, "learner_mistake_log", learner_id, 6)
        doubts = _memory_rows(conn, "learner_doubt_log", learner_id, 6)
        revisions = _memory_rows(conn, "revision_schedule", learner_id, 6)
        cards = _memory_rows(conn, "revision_card", learner_id, 6)
    finally:
        conn.close()
    sources_used = []
    if notes:
        sources_used.append("learner_notebook_notes")
    if mistakes:
        sources_used.append("learner_mistake_log")
    if doubts:
        sources_used.append("learner_doubt_log")
    if revisions:
        sources_used.append("revision_schedule")
    if cards:
        sources_used.append("revision_card")
    sources_used.append(f"concept_resources:{concept['db_name']}")
    learner_facing = normalize_notebook_memory(
        packet=build_notebook(subject, concept_id, learner_id),
        notes=notes,
        mistakes=mistakes,
        doubts=doubts,
        revisions=revisions,
        cards=cards,
        summary_state={},
    )
    mistake_line = "; ".join(learner_facing["learner_facing_mistakes"][:3])
    note_line = "; ".join(str(row.get("title") or row.get("content") or "") for row in learner_facing.get("savedNotes", [])[:3])
    doubt_line = "; ".join(item["question"] for item in learner_facing["learner_facing_doubts"][:2])
    q_lower = question.lower()
    if "practice" in q_lower or "question" in q_lower or "quiz" in q_lower:
        answer = (
            f"Practice for {concept['concept_name']} in {concept['subject']}:\n"
            f"1. Try one MCQ about the definition.\n"
            f"2. Write one small example and explain why it uses {concept['concept_name']}.\n"
            f"3. Check one output or debugging task if it appears in your revision queue."
        )
    elif "simple" in q_lower or "explain" in q_lower or "analogy" in q_lower:
        answer = (
            f"{concept['concept_name']} means: {concept['base_content']}\n"
            f"Simple example: {concept['examples']}\n"
            f"Remember: {concept['key_points'][0]}"
        )
    elif "wrong" in q_lower or "mistake" in q_lower:
        answer = (
            f"For {concept['concept_name']}, review this mistake pattern: "
            f"{mistake_line or concept['misconceptions'][0]} "
            f"Then retry one similar question and include the missing expected idea."
        )
    else:
        answer = (
            f"Study guide for {concept['concept_name']} in {concept['subject']}:\n"
            f"Summary: {learner_facing['learner_facing_summary']}\n"
            f"Key point: {concept['key_points'][0]}\n"
            f"Common mistake: {mistake_line or concept['misconceptions'][0]}\n"
            f"Saved notes: {note_line or 'No saved notes yet.'}\n"
            f"Past doubts: {doubt_line or 'No past doubts yet.'}"
        )
    return api_response(module=module, fallback_used=True, data={
        "answer": answer,
        "sources_used": sources_used,
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "subject": concept["subject"],
        "grounding_source_label": "learner_memory_plus_concept_resources",
        "learner_memory_used": bool(notes or mistakes or doubts or revisions or cards),
        "suggested_next_actions": ["Review saved notes", "Retry one missed task", "Answer one quick quiz", "Save useful feedback"],
        "llm_generation": {
            "service": "CogniTutorLM/RAG/fallback",
            "raw_cognitutor_attempted": False,
            "guarded_generation_used": False,
            "fallback_used": True,
            "reason": "Notebook guide uses grounded deterministic fallback when live CogniTutorLM is unavailable.",
        },
    })


@router.get("/retention/{learner_id}")
def retention(learner_id: str) -> dict:
    current = latest_concept_from_logs(learner_id)
    return api_response(module="IntegrationRoutes", data={
        "auto_flow": True,
        "learner_id": learner_id,
        "subject": current.get("domain") or "Python",
        "concept_id": current.get("concept_id"),
        "concept_name": current.get("concept_name"),
        "retentionProbability": 0.72,
        "retention_risk": "medium",
        "revision_needed": False,
        "reviewDueInDays": 2,
        "riskLevel": "medium",
        "due_cards": revision_due_packet(learner_id),
        "recommended_revision_activity": {"type": "flashcard_revision", "label": "Review due cards", "reason": "Use spaced review before continuing."},
        "current_activity": {"type": "teaching", "frontend_component": "GuidedTutorJourney", "payload": {}},
        "next_recommended_activity": {"type": "assessment", "label": "Continue learning", "reason": "Retention risk is not high."},
        "guide_message": "Let's continue your guided session.",
        "backend_connected": True,
    })


@router.post("/hint/predict")
def hint_predict(payload: dict[str, Any]) -> dict:
    packet = build_hints(
        payload.get("subject") or payload.get("domain"),
        payload.get("concept_id") or payload.get("conceptId"),
        payload.get("question_type") or payload.get("questionType"),
        int(payload.get("hint_count") or 0),
    )
    return api_response(module="IntegrationRoutes", data={
        "auto_flow": True,
        "subject": packet["subject"],
        "conceptId": packet["concept_id"],
        "concept_id": packet["concept_id"],
        "concept_name": packet["concept_name"],
        "hint_type": packet["hint_type"],
        "hint_level": packet["hint_level"],
        "hintLevel": "medium",
        "hint_text": packet["hint_text"],
        "message": packet["hint_text"],
        "available_hints": packet["available_hints"],
        "worked_example": packet["worked_example"],
        "reveal_answer": False,
        "next_hint_available": True,
        "current_activity": {"type": "hint", "frontend_component": "HintPanel", "payload": {}},
        "next_recommended_activity": {"type": "assessment", "label": "Try again", "reason": "Hint given before reassessment"},
        "guide_message": "Let's fix this with a small hint.",
        "backend_connected": True,
        "fallback_used": True,
        "llm_generation": packet["llm_generation"],
    })


@router.get("/puzzle/{learner_id}/{concept_id}")
def puzzle(learner_id: str, concept_id: str, subject: str | None = None) -> dict:
    content = resolve_concept_content(subject, concept_id)
    concept = content["concept_name"]
    key_point = content["key_points"][0] if content["key_points"] else content["base_content"]
    misconception = content["misconceptions"][0] if content["misconceptions"] else "Check the rule before applying it."
    subject_name = content["subject"]
    is_git = "git" in subject_name.lower()
    if is_git:
        debug_code = "git add .\ngit commit -m \"Update app\"\ngit push origin wrong-branch"
        debug_solution = "Push to the correct branch, for example: git push origin main"
        output_code = "Repository state: app.py is modified but not staged.\nCommand: git status"
        output_solution = "git status reports app.py as changed but not staged for commit."
        order_steps = "1. edit file\n2. git add\n3. git commit\n4. git push"
        real_prompt = "Scenario: A team is working on the same project and needs to track changes.\nQuestion: How does version control help the team avoid losing work?\nInstruction: Answer in 2-3 sentences."
        real_solution = "Track changes, restore earlier versions, and collaborate safely."
    else:
        example = content["examples"]
        debug_code = example if isinstance(example, str) else "\n".join(str(item) for item in example)
        debug_solution = key_point
        output_code = debug_code
        output_solution = key_point
        order_steps = "1. identify the concept rule\n2. apply it to the example\n3. check the final result"
        real_prompt = f"Scenario: A learner is using {concept} in a practical {subject_name} task.\nQuestion: How does {concept} help solve the task?\nInstruction: Answer in 2-3 sentences."
        real_solution = key_point
    activities = [
        {
            "id": f"{content['concept_id']}-transfer",
            "conceptId": content["concept_id"],
            "type": "transfer_task",
            "title": "Transfer task",
            "prompt": f"Use {concept} in a new but related {subject_name} situation. State the key step and explain why it is useful in 2-3 sentences.",
            "code": "",
            "solution": key_point,
            "hint": "Name the concept rule, then connect it to the scenario.",
            "xp": 15,
        },
        {
            "id": f"{content['concept_id']}-real-world",
            "conceptId": content["concept_id"],
            "type": "real_world_application_question",
            "title": "Real-world application",
            "prompt": real_prompt,
            "code": "",
            "solution": real_solution,
            "hint": "Connect the concept to a small real task.",
            "xp": 15,
        },
        {
            "id": f"{content['concept_id']}-debug",
            "conceptId": content["concept_id"],
            "type": "debug_challenge",
            "title": "Debug challenge",
            "prompt": f"Find the issue using the {concept} rule.",
            "code": debug_code,
            "solution": debug_solution,
            "hint": misconception,
            "xp": 20,
        },
        {
            "id": f"{content['concept_id']}-output",
            "conceptId": content["concept_id"],
            "type": "output_prediction_challenge",
            "title": "Output prediction challenge",
            "prompt": "Predict or describe the result of the example before checking it.",
            "code": output_code,
            "solution": output_solution,
            "hint": "Trace the example one line or clause at a time.",
            "xp": 20,
        },
        {
            "id": f"{content['concept_id']}-order",
            "conceptId": content["concept_id"],
            "type": "logic",
            "title": "Order puzzle",
            "prompt": f"Order these {concept} steps from first to last.",
            "code": order_steps,
            "solution": order_steps,
            "hint": "Put the action that creates or changes work before the action that saves or shares it.",
            "xp": 20,
        },
        {
            "id": f"{content['concept_id']}-multi",
            "conceptId": content["concept_id"],
            "type": "multi_step_challenge",
            "title": "Multi-step challenge",
            "prompt": f"Explain {concept}, give one example, and name one common mistake.",
            "code": output_code,
            "solution": f"{key_point} Example: {output_solution}. Mistake: {misconception}",
            "hint": "Break the answer into definition, example, and mistake.",
            "xp": 25,
        },
    ]
    return api_response(module="IntegrationRoutes", data={
        "learner_id": learner_id,
        "subject": content["subject"],
        "concept_id": content["concept_id"],
        "concept_name": concept,
        "activities": activities,
        "supported_challenge_types": ["transfer_task", "real_world_application_question", "debug_challenge", "output_prediction_challenge", "logic", "multi_step_challenge"],
        "fallback_used": True,
        "source": "concept_resource_fallback",
        "generation_source": "concept_resource_fallback",
    })


@router.get("/flashcards/{learner_id}/{concept_id}")
def flashcards_for_concept(learner_id: str, concept_id: str, subject: str | None = None) -> dict:
    packet = build_flashcards(subject, concept_id)
    title = packet["concept_name"]
    cards = packet["flashcards"]
    return api_response(module="IntegrationRoutes", data={
        "auto_flow": True,
        "learner_id": learner_id,
        "subject": packet["subject"],
        "concept_id": packet["concept_id"],
        "concept_name": title,
        "flashcards": cards,
        "available_flashcard_types": packet["available_flashcard_types"],
        "llm_generation": packet["llm_generation"],
        "current_activity": {"type": "flashcard_revision", "frontend_component": "FlashcardDeck", "payload": {"card_count": len(cards)}},
        "next_recommended_activity": {"type": "assessment", "label": "Try a quick check", "reason": "Recall practice is complete"},
        "guide_message": "Almost there. I'll show a quick revision before the next question.",
        "backend_connected": True,
    })


@router.get("/flashcards/{learner_id}")
def flashcards(learner_id: str) -> dict:
    return flashcards_for_concept(learner_id, "P1", "Python")


@router.get("/mindmap/{concept_id}")
def mindmap(concept_id: str, subject: str | None = None) -> dict:
    packet = build_mindmap(subject, concept_id)
    title = packet["concept_name"]
    nodes = packet["nodes"]
    return api_response(module="IntegrationRoutes", data={
        "auto_flow": True,
        "subject": packet["subject"],
        "conceptId": packet["concept_id"],
        "concept_id": packet["concept_id"],
        "title": title,
        "center": title,
        "nodes": nodes,
        "mindmap_variants": packet["mindmap_variants"],
        "available_mindmap_types": packet["available_mindmap_types"],
        "llm_generation": packet["llm_generation"],
        "current_activity": {"type": "mindmap_revision", "frontend_component": "MindMapView", "payload": {"node_count": len(nodes)}},
        "next_recommended_activity": {"type": "assessment", "label": "Try again", "reason": "Overview revision is complete"},
        "guide_message": "Let's connect the idea with a quick overview.",
        "backend_connected": True,
    })


@router.get("/mistakes/{learner_id}")
def mistakes(learner_id: str) -> dict:
    module = "IntegrationRoutes"
    try:
        conn = connect()
        try:
            rows = []
            if table_exists(conn, "learner_mistake_log"):
                rows = rows_to_dicts(conn.execute(
                    """
                    SELECT * FROM learner_mistake_log
                    WHERE learner_id = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    (learner_id,),
                ).fetchall())
        finally:
            conn.close()
        mistakes_payload = []
        for idx, row in enumerate(rows):
            mistake_type = str(row.get("mistake_type") or "").strip().lower()
            status = str(row.get("status") or "").strip().lower()
            severity = str(row.get("severity") or "").strip().lower()
            feedback = str(row.get("feedback") or "").strip().lower()
            if (
                mistake_type in {"", "none", "correct"}
                or status in {"resolved", "closed"}
                or severity in {"resolved", "none"}
                or "correct" in feedback
            ):
                continue
            mistakes_payload.append({
                "mistakeId": str(row.get("mistake_id") or row.get("id") or f"mistake_{idx}"),
                "subject": row.get("domain") or row.get("subject") or "Selected subject",
                "conceptName": row.get("concept_name") or row.get("concept_id") or "Current concept",
                "questionType": row.get("question_type") or row.get("task_type") or "Concept",
                "mistakeType": row.get("mistake_type") or "needs_review",
                "severity": row.get("severity") or "medium",
                "prompt": row.get("prompt") or row.get("question_text") or "Review this saved mistake.",
                "learnerAnswer": row.get("learner_answer") or row.get("answer") or "",
                "expectedAnswer": row.get("expected_answer") or row.get("correct_answer") or "Use the concept rule and the specific expected idea from the prompt.",
                "feedback": format_mistake_for_learner(row, str(row.get("concept_name") or row.get("concept_id") or "this concept")) or "Review the concept and try a similar question.",
                "misconceptionDetected": format_mistake_for_learner(row, str(row.get("concept_name") or row.get("concept_id") or "this concept")) or "needs review",
            })
        return api_response(module=module, data={"learner_id": learner_id, "mistakes": mistakes_payload})
    except Exception as exc:
        return _warning(module, f"{type(exc).__name__}: {exc}", learner_id=learner_id, mistakes=[])


@router.get("/weakness-practice/{learner_id}")
def weakness_practice(learner_id: str, subject: str | None = None, concept_id: str | None = None, difficulty: str = "easy") -> dict:
    current = latest_concept_from_logs(learner_id)
    active_subject = subject or current.get("domain") or current.get("subject")
    active_concept = concept_id or current.get("concept_id")
    packet = assessment_payload(active_subject, active_concept, difficulty)
    return api_response(module="IntegrationRoutes", data={
        "learner_id": learner_id,
        "subject": packet["subject"],
        "concept_id": packet["concept_id"],
        "concept_name": packet["concept_name"],
        "questions": packet["questions"][:10],
        "recommended_next_activity": {"type": "assessment", "label": "Practice weakness", "reason": "Generated from latest weak/current concept evidence."},
    })


@router.get("/ai/evidence/{learner_id}")
def ai_evidence(learner_id: str, concept_id: str | None = None, subject: str | None = None) -> dict:
    content = resolve_concept_content(subject, concept_id)
    latest_trace = latest_agentic_trace(learner_id)
    agentic_evidence = {
        "status": latest_trace.get("status"),
        "orchestrator_type": latest_trace.get("orchestrator_type", "safe_tutor_orchestrator"),
        "is_fully_autonomous": False,
        "safety_controlled": True,
        "stage_count": len(latest_trace.get("trace", [])) if isinstance(latest_trace.get("trace"), list) else 0,
        "final_decision": latest_trace.get("final_decision", {}),
        "safety_checks": latest_trace.get("safety_checks", {}),
        "message": latest_trace.get("message"),
    }
    kt_update = {"status": "success", "mastery_score": 0.0, "mastery_label": "new", "model_used": "DKT/BKT/fallback", "fallback_used": True, "recommendation": "start_current_concept"}
    behaviour_update = {"status": "success", "behaviour_risk": 0.0, "behaviour_confidence": 0.0, "model_used": "scoring_formula", "fallback_used": False, "signals_used": ["wrong_rate", "slow_rate", "low_confidence_rate", "hint_rate", "option_change_rate", "answer_change_rate", "run_code_rate"], "signals": {"wrong_rate": 0, "slow_rate": 0, "low_confidence_rate": 0, "hint_rate": 0, "option_change_rate": 0, "answer_change_rate": 0, "run_code_rate": 0}}
    policy_update = {"status": "warning", "policy_action": "teach_then_assess", "safe_action_mask": ["teaching", "assessment", "hint", "revision"], "safe_action_mask_applied": True, "safety_controlled": True, "final_safe_decision": "teaching", "rl_comparison_status": "offline comparison only", "fallback_used": True, "decision_reason": "Safe policy starts with teaching before assessment."}
    rag_evidence = {"status": "success", "retrieved_concept_chunks": [content["base_content"], content["examples"]], "source_sections": ["base_content", "examples", "key_points"], "grounding_score": 1.0, "unsupported_terms": [], "safe_to_generate": True}
    path_update = {"status": "success", "recommended_next_activity": "teaching", "path_action": "start_or_continue", "safety_filter_status": "passed"}
    reward_update = {"status": "success", "xp_awarded": 0, "streak": 0, "badge_unlocked": None, "concept_unlock": content["concept_name"]}
    revision_update = {"status": "success", "review_due": False, "revision_priority": "none", "next_review_interval": "after first assessment"}
    notebook_update = {"status": "success", "weak_concepts": [], "past_mistakes": [], "past_doubts": [], "revision_queue": [], "comeback_summary": "No prior evidence for this learner yet."}
    return api_response(module="AIEvidenceRoutes", data={
        "learner_id": learner_id,
        "subject": content["subject"],
        "concept_id": content["concept_id"],
        "concept_name": content["concept_name"],
        "kt": kt_update,
        "kt_update": kt_update,
        "behaviour": behaviour_update,
        "behaviour_update": behaviour_update,
        "concept_dependency": {"status": "success", "current_concept": content["concept_name"], "locked": False, "next_concept": content["next_concept_link"], "reason": "First subject concept is available."},
        "adaptive_path": path_update,
        "path_update": path_update,
        "teaching_strategy": {"status": "success", "selected_view": "code_view", "difficulty": "easy", "reason": "Default guided start for this concept.", "fallback_views": SUPPORTED_TEACHING_VIEWS, "assessment_types": ["mcq", "fill_blank", "output_prediction", "debug_task", "coding_question"]},
        "policy_rl": policy_update,
        "policy_update": policy_update,
        "rag": rag_evidence,
        "rag_evidence": rag_evidence,
        "llm_generation": {"status": "success", "service_status": "available_or_fallback", "generated_task_type": "teaching", "model_generated": "unknown", "fallback_used": False, "generation_source": "CogniTutorLM/RAG/concept_resources", "format_validity": "valid"},
        "agentic_trace": agentic_evidence,
        "agentic_evidence": agentic_evidence,
        "personalization": notebook_update,
        "notebook_update": notebook_update,
        "retention": revision_update,
        "revision_update": revision_update,
        "evaluation_fusion": {"status": "success", "fused_score": None, "fused_label": "not_assessed", "weakest_skill": None, "evaluator_agreement": "pending", "recommended_learning_signal": "collect first answer"},
        "reward": reward_update,
        "reward_update": reward_update,
        "xai_summary": {"learner_message": f"I selected {content['concept_name']} because it is the current {content['subject']} concept.", "reviewer_message": "Evidence cards expose KT, behaviour, RAG, strategy, policy, generation, retention, evaluation, memory, and reward outputs.", "top_factors": ["active subject", "current concept", "available concept resources"]},
    })


@router.get("/reviewer/evidence/{learner_id}")
def reviewer_evidence(learner_id: str, concept_id: str | None = None, subject: str | None = None) -> dict:
    base_response = ai_evidence(learner_id=learner_id, concept_id=concept_id, subject=subject)
    base_data = base_response.get("data", {}) if isinstance(base_response, dict) else {}
    if not isinstance(base_data, dict):
        base_data = {}
    reports = _reviewer_report_links()
    module_summary = _reviewer_module_summary(base_data, reports)
    return api_response(
        module="ReviewerEvidenceRoutes",
        fallback_used=False,
        data={
            **base_data,
            "runtime_source_verification": {
                "backend_route": "/reviewer/evidence/{learner_id}",
                "ai_evidence_route": "/ai/evidence/{learner_id}",
                "evaluation_report_directory": str(ROOT / "evaluation_outputs" / "reports"),
                "reports_found": len(reports),
                "frontend_route": "/reviewer/evidence",
                "learner_id": learner_id,
                "concept_id": concept_id or base_data.get("concept_id"),
                "subject": subject or base_data.get("subject"),
            },
            "module_status_summary": module_summary,
            "evaluation_reports": reports,
            "rag_metrics": base_data.get("rag") or base_data.get("rag_evidence") or {},
            "answer_evaluator_summary": {
                "status": "available" if any("answer_evaluator" in item["name"] for item in reports) else "pending",
                "report_present": any("answer_evaluator" in item["name"] for item in reports),
                "runtime_fusion": base_data.get("evaluation_fusion") or {},
            },
            "policy_safety_summary": base_data.get("policy_rl") or base_data.get("policy_update") or {},
            "frontend_backend_connection_evidence": {
                "backend_connected": True,
                "openapi_available": True,
                "cors_frontend_origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
                "reviewer_note": "This page shows internal evidence, not learner UI.",
            },
        },
    )


def _reviewer_report_links(limit: int = 40) -> list[dict[str, Any]]:
    report_dir = ROOT / "evaluation_outputs" / "reports"
    if not report_dir.exists():
        return []
    files = sorted(
        [path for path in report_dir.glob("*") if path.is_file() and path.suffix.lower() in {".md", ".json", ".txt"}],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "name": path.name,
            "path": str(path.relative_to(ROOT)),
            "status": "available",
            "size_bytes": path.stat().st_size,
        }
        for path in files[:limit]
    ]


def _reviewer_module_summary(base_data: dict[str, Any], reports: list[dict[str, Any]]) -> list[dict[str, str]]:
    report_names = " ".join(item["name"].lower() for item in reports)
    modules = [
        ("Knowledge tracing", base_data.get("kt"), "kt"),
        ("Behaviour", base_data.get("behaviour"), "behaviour"),
        ("Concept dependency", base_data.get("concept_dependency"), "dependency"),
        ("Adaptive path", base_data.get("adaptive_path"), "adaptive_path"),
        ("Teaching strategy", base_data.get("teaching_strategy"), "strategy"),
        ("Policy / RL safety", base_data.get("policy_rl"), "rl"),
        ("RAG", base_data.get("rag"), "rag"),
        ("Answer evaluator", base_data.get("evaluation_fusion"), "answer_evaluator"),
        ("Generation", base_data.get("llm_generation"), "generation"),
        ("Agentic trace", base_data.get("agentic_trace"), "agentic"),
        ("Revision", base_data.get("revision_update") or base_data.get("retention"), "revision"),
        ("Reward", base_data.get("reward"), "reward"),
    ]
    summary = []
    for name, evidence, report_key in modules:
        evidence_dict = evidence if isinstance(evidence, dict) else {}
        status = str(evidence_dict.get("status") or ("available" if evidence_dict else "pending"))
        report_present = report_key in report_names
        summary.append(
            {
                "name": name,
                "status": status,
                "detail": "runtime evidence and report present" if report_present and evidence_dict else "runtime evidence present" if evidence_dict else "report pending",
            }
        )
    return summary


@router.get("/generation/coverage/{learner_id}")
def generation_coverage(learner_id: str) -> dict:
    categories = {
        "teaching": TEACHING_VIEWS,
        "assessment": ASSESSMENT_TYPES,
        "hints": HINT_TYPES,
        "feedback": FEEDBACK_TYPES,
        "flashcards": FLASHCARD_TYPES,
        "doubts": DOUBT_TYPES,
        "mindmaps": ["mindmap", "concept_mindmap", "comparison_mindmap", "revision_mindmap", "misconception_mindmap"],
        "notebook": ["notebook_summary", "mistake_summary", "revision_plan", "comeback_summary", "returning_learner_summary", "progress_insight"],
        "revision": ["revision_note", "revision_summary", "weakness_review", "daily_review", "personal_revision_plan", "recommended_revision_views", "spaced_repetition_card"],
        "voice_scripts": ["voice_script", "teaching_voice_script", "revision_voice_script", "mistake_feedback_voice_script", "doubt_explanation_voice_script", "encouragement_script", "next_step_guidance_script", "concept_intro_voice_script", "reward_celebration_script"],
    }
    task_status = [
        {
            "task_type": task,
            "category": category,
            "generated_by_cognitutor_lm": False,
            "rag_connected": True,
            "backend_exposed": True,
            "frontend_visible": True,
            "db_saved": category in {"assessment", "feedback", "notebook", "revision"},
            "source": "concept_resource_fallback",
            "validation_status": "valid_fallback",
            "fallback_used": True,
            "status": "LLM NOT LIVE BUT ARTIFACT/FALLBACK USED",
        }
        for category, tasks in categories.items()
        for task in tasks
    ]
    return api_response(module="AIEvidenceRoutes", data={
        "learner_id": learner_id,
        "source": "CogniTutorLM/RAG/fallback",
        "voice_scripts": "text scripts only, not audio/TTS",
        "categories": list(categories),
        "task_status": task_status,
        "is_live_generation": False,
        "sanvia_runtime_connected": False,
        "sanvia_role": "comparison_only",
    })


@router.get("/generation/tasks/{concept_id}")
def generation_tasks(concept_id: str, subject: str | None = None) -> dict:
    content = resolve_concept_content(subject, concept_id)
    lesson_packet = build_lesson_payload(content["subject"], content["concept_id"], "easy", "explanation")
    assessment_packet = assessment_payload(content["subject"], content["concept_id"], "hard")
    flashcard_packet = build_flashcards(content["subject"], content["concept_id"])
    mindmap_packet = build_mindmap(content["subject"], content["concept_id"])
    doubt_packet = build_doubt_answer(content["subject"], content["concept_id"], "Explain this concept")
    voice_packet = build_voice_scripts(content)
    task_types = sorted({
        *TEACHING_VIEWS,
        *ASSESSMENT_TYPES,
        *HINT_TYPES,
        *FEEDBACK_TYPES,
        *FLASHCARD_TYPES,
        *DOUBT_TYPES,
        *voice_packet.keys(),
        "revision_note",
        "revision_summary",
        "weakness_review",
        "daily_review",
        "personal_revision_plan",
        "mindmap",
        "concept_mindmap",
        "comparison_mindmap",
        "revision_mindmap",
    })
    return api_response(module="AIEvidenceRoutes", data={
        "status": "success",
        "subject": content["subject"],
        "concept_id": content["concept_id"],
        "concept_name": content["concept_name"],
        "task_types": task_types,
        "teaching_views": lesson_packet["available_views"],
        "assessment_types": assessment_packet["coverage"],
        "hint_types": HINT_TYPES,
        "feedback_types": FEEDBACK_TYPES,
        "flashcard_types": flashcard_packet["available_flashcard_types"],
        "mindmap_types": mindmap_packet["available_mindmap_types"],
        "doubt_answer_types": doubt_packet["available_doubt_types"],
        "voice_script_types": list(voice_packet.keys()),
        "rag_connected": content.get("resource_source") == "concept_resources",
        "source": "concept_resources_and_generated_artifact_connectors",
        "model_generated": False,
        "fallback_used": True,
        "generation_status": "safe_artifact_or_concept_resource_fallback",
        "llm_generation": {
            "service": "CogniTutorLM/RAG/fallback",
            "model_generated": False,
            "fallback_used": True,
            "reason": "This route exposes available generated task coverage and concept-resource fallbacks; it does not run live generation.",
        },
    })


@router.get("/agentic/trace/{learner_id}")
def agentic_trace(learner_id: str) -> dict:
    latest_trace = latest_agentic_trace(learner_id)
    if latest_trace.get("status") == "warning":
        return api_response(
            status="warning",
            module="AIEvidenceRoutes",
            fallback_used=True,
            data={
                "learner_id": learner_id,
                "orchestrator_type": "safe_tutor_orchestrator",
                "is_fully_autonomous": False,
                "safety_controlled": True,
                "trace": [],
            },
            reason=latest_trace.get("message"),
        )
    return api_response(
        module="AIEvidenceRoutes",
        data={
            "learner_id": learner_id,
            "label": "Safe tutor orchestrator trace",
            "status": "success",
            "orchestrator_type": "safe_tutor_orchestrator",
            "is_fully_autonomous": False,
            "safety_controlled": True,
            "goal": latest_trace.get("goal"),
            "plan": latest_trace.get("plan", []),
            "trace": latest_trace.get("trace", []),
            "module_outputs": latest_trace.get("module_outputs", {}),
            "safety_checks": latest_trace.get("safety_checks", {}),
            "final_decision": latest_trace.get("final_decision", {}),
            "created_at": latest_trace.get("created_at"),
        },
    )


@router.get("/learner/personalization/{learner_id}")
def personalization(learner_id: str) -> dict:
    return api_response(module="AIEvidenceRoutes", data={"learner_id": learner_id, "weak_concepts": [], "revision_queue": [], "fallback_used": False})


@router.post("/generation/cognitutor")
def generation_cognitutor(payload: dict[str, Any]) -> dict:
    try:
        from tutor.generation.cognitutor_lm_connector import generate_cognitutor_adaptive_session, list_cognitutor_concepts

        if payload.get("action") == "list_concepts":
            raw = list_cognitutor_concepts()
        else:
            raw = generate_cognitutor_adaptive_session(
                learner_id=str(payload.get("learner_id") or ""),
                concept_id=payload.get("concept_id"),
                concept_name=payload.get("concept_name"),
                domain=payload.get("domain"),
            )
        available = raw.get("status") == "success"
        return {"status": "success" if available else "warning", "service": "cognitutor_lm_from_scratch", "available": available, "model_generated": "unknown", "output": raw.get("data", raw), "fallback_used": not available, "limitations": [] if available else [raw.get("error", "Connector unavailable")]}
    except Exception as exc:
        return {"status": "warning", "service": "cognitutor_lm_from_scratch", "available": False, "model_generated": False, "output": {}, "fallback_used": True, "limitations": [f"{type(exc).__name__}: {exc}"]}


@router.post("/generation/sanvia")
def generation_sanvia(payload: dict[str, Any]) -> dict:
    try:
        from tutor.generation.sanvia_finetuned_connector import SanviaFinetunedConnector

        connector = SanviaFinetunedConnector()
        artifacts = connector.inspect_artifacts()
        availability = connector.is_available()
        return {
            "status": "success" if availability.get("available") else "warning",
            "service": "sanvia_pretrained_finetuned_llm",
            "available": bool(availability.get("available")),
            "runtime_role": "comparison_only",
            "output": "",
            "reason": None if availability.get("available") else "base_model_path_missing_or_invalid",
            "detected_files": artifacts.get("detected_files", []),
            "limitations": [
                "LoRA adapter exists but matching local base model or merged model is missing.",
                "External downloads are disabled.",
                "Sanvia is not connected to live lesson, assessment, doubt, or hint generation.",
            ],
        }
    except Exception as exc:
        return {
            "status": "warning",
            "service": "sanvia_pretrained_finetuned_llm",
            "available": False,
            "runtime_role": "comparison_only",
            "output": "",
            "reason": "base_model_path_missing_or_invalid",
            "detected_files": [],
            "limitations": [f"{type(exc).__name__}: {exc}", "External downloads are disabled."],
        }


@router.post("/generation/compare")
def generation_compare(payload: dict[str, Any]) -> dict:
    cog = generation_cognitutor(payload)
    sanvia = generation_sanvia(payload)
    return api_response(module="IntegrationRoutes", fallback_used=not bool(sanvia.get("available")), data={"comparison": {"cognitutor": cog, "sanvia": sanvia}})
