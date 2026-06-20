from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from scripts.migration.create_user_persistence_tables import TABLE_NAMES, create_tables
from tutor.system.user_persistence_store import (
    build_returning_user_context,
    create_demo_user,
    get_or_create_learner_profile,
    load_session_state,
    save_agent_trace,
    save_doubt_log,
    save_mistake_from_evaluation,
    save_revision_schedule,
    save_session_state,
    update_concept_progress,
)


DB_PATH = Path("external/core_data/tutor.db")


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def main() -> None:
    create_tables(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    missing = [table_name for table_name in TABLE_NAMES if not _table_exists(cursor, table_name)]
    conn.close()
    assert not missing, f"Missing tables: {missing}"

    suffix = uuid.uuid4().hex[:8]
    user = create_demo_user(
        username=f"demo_user_{suffix}",
        email=f"demo_user_{suffix}@example.test",
        display_name="Demo Learner",
    )
    assert user["status"] == "success"
    assert user.get("user_id")
    assert user.get("learner_id")

    profile = get_or_create_learner_profile(user["user_id"])
    assert profile["status"] == "success"
    learner_id = profile["learner_id"]

    session_packet = {
        "session_id": f"session_{suffix}",
        "domain": "Python",
        "concept_id": "1",
        "concept_name": "Variables",
        "teaching_view": "example_first",
        "difficulty": "medium",
        "assessment_types": ["debug", "output_prediction"],
        "frontend_packet": {"next_action": "answer"},
    }
    session = save_session_state(learner_id, session_packet)
    assert session["status"] == "success"

    loaded = load_session_state(learner_id)
    assert loaded["status"] == "success"
    assert loaded["session_state"]["session_id"] == session_packet["session_id"]

    progress = update_concept_progress(
        learner_id,
        "1",
        {
            "domain": "Python",
            "concept_name": "Variables",
            "status": "current",
            "mastery": 0.72,
            "last_score": 0.81,
        },
    )
    assert progress["status"] == "success"

    mistake = save_mistake_from_evaluation(
        learner_id,
        session["session_id"],
        {
            "domain": "Python",
            "concept_id": "1",
            "concept_name": "Variables",
            "mistakes": [
                {
                    "question_id": "q1",
                    "task_type": "debug",
                    "mistake_type": "syntax",
                    "severity": "medium",
                    "learner_answer": "x ==",
                    "expected_answer": "x = 1",
                    "feedback": "Assignment uses one equals sign.",
                }
            ],
        },
    )
    assert mistake["status"] == "success"
    assert mistake["rows_inserted"] >= 1

    doubt = save_doubt_log(
        learner_id,
        session["session_id"],
        {
            "domain": "Python",
            "concept_id": "1",
            "concept_name": "Variables",
            "doubt_text": "Why does the variable keep the latest value?",
            "doubt_type": "conceptual",
            "answer_summary": "A variable name points to the most recent assigned object.",
            "rag_grounded": True,
            "grounding_score": 0.91,
            "follow_up_questions": ["What happens after reassignment?"],
            "memory_updated": True,
        },
    )
    assert doubt["status"] == "success"

    revision = save_revision_schedule(
        learner_id,
        {
            "domain": "Python",
            "concept_id": "1",
            "concept_name": "Variables",
            "priority": "medium",
            "revision_reason": "syntax mistake and conceptual doubt",
            "revision_schedule": [{"interval_label": "tomorrow", "status": "due"}],
            "cards": [
                {
                    "card_type": "short_answer",
                    "prompt": "How do you assign a value to x?",
                    "answer": "x = value",
                    "difficulty": "easy",
                    "source": "test",
                }
            ],
        },
    )
    assert revision["status"] == "success"
    assert revision["schedules_inserted"] >= 1
    assert revision["cards_inserted"] >= 1

    trace = save_agent_trace(
        learner_id,
        session["session_id"],
        {
            "concept_id": "1",
            "concept_name": "Variables",
            "trace_steps": [
                {
                    "trace_step": 1,
                    "agent_name": "EvaluatorAgent",
                    "status": "success",
                    "primary_decision": "needs_feedback",
                    "primary_output": "syntax_feedback",
                    "reason": "Learner confused assignment with comparison.",
                }
            ],
        },
    )
    assert trace["status"] == "success"
    assert trace["rows_inserted"] >= 1

    context = build_returning_user_context(learner_id)
    assert context["status"] == "success"
    assert context["resume_ready"] is True
    assert context["personalization_ready"] is True
    assert context["recent_mistakes"]
    assert context["recent_doubts"]
    assert context["revisions_due"]
    assert context["recent_agent_trace"]

    print("STATUS: success")
    print("MODULE: user_persistence_tables_test")


if __name__ == "__main__":
    main()
