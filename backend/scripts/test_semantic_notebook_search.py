from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tutor.api.app import app
from tutor.api.dependencies import connect
from tutor.memory.semantic_notebook_search import SemanticNotebookSearch


TEST_LEARNER_ID = "semantic_notebook_test_learner"


def seed_notebook_search_data(learner_id: str = TEST_LEARNER_ID) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO learner_mistake_log (
                learner_id, session_id, concept_id, concept_name, domain,
                question_id, task_type, mistake_type, severity,
                learner_answer, expected_answer, feedback, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                "semantic_session",
                "variables",
                "Variables",
                "Python",
                "q_debug",
                "debug",
                "syntax_misunderstanding",
                "high",
                "2score = 10",
                "score2 = 10",
                "Variable names cannot start with a number.",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO learner_mistake_log (
                learner_id, session_id, concept_id, concept_name, domain,
                question_id, task_type, mistake_type, severity,
                learner_answer, expected_answer, feedback, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                "semantic_session",
                "loops",
                "Loops",
                "Python",
                "q_output",
                "output_prediction",
                "wrong_output",
                "medium",
                "5",
                "0 1 2",
                "Trace the loop variable step by step.",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO learner_doubt_log (
                learner_id, session_id, concept_id, concept_name, domain,
                doubt_text, doubt_type, answer_summary, rag_grounded,
                grounding_score, follow_up_question_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                "semantic_session",
                "loops",
                "Loops",
                "Python",
                "Why does the loop print three values?",
                "why_explanation",
                "The loop runs once for each value in range.",
                1,
                0.9,
                "{}",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO revision_card (
                learner_id, concept_id, concept_name, domain,
                card_type, prompt, answer, difficulty, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                "variables",
                "Variables",
                "Python",
                "short_answer",
                "What is a valid variable name?",
                "A name like score2 is valid; 2score is not.",
                "easy",
                "semantic_test",
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO learner_session_log (
                learner_id, session_id, event_type, domain, concept_id,
                concept_name, teaching_view, difficulty, event_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                "semantic_session",
                "teaching_summary",
                "Python",
                "variables",
                "Variables",
                "debug_view",
                "easy",
                json.dumps({"note": "Learner struggled with debug mistakes and variable naming."}),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return learner_id


def main() -> None:
    learner_id = seed_notebook_search_data()
    service = SemanticNotebookSearch()

    index = service.build_search_index(learner_id)
    assert index["status"] == "success"
    assert index["module"] == "SemanticNotebookSearch"
    assert index["record_count"] >= 4

    search = service.search(learner_id, "show my mistakes in variables", top_k=5)
    assert search["status"] == "success"
    assert search["result_count"] >= 1
    assert search["results"]

    mistakes = service.search(learner_id, "mistakes", top_k=5)
    assert mistakes["status"] == "success"
    assert isinstance(mistakes["results"], list)

    summary = service.get_weakness_summary(learner_id)
    assert summary["status"] == "success"
    for key in [
        "weak_concepts",
        "dominant_mistake_types",
        "weak_question_types",
        "recent_doubts",
        "recommended_revision_focus",
    ]:
        assert key in summary

    fallback = SemanticNotebookSearch(force_keyword=True).search(learner_id, "debug mistakes", top_k=3)
    assert fallback["status"] == "success"
    assert fallback["method"] == "keyword_fallback"
    assert fallback["fallback_used"] is True

    client = TestClient(app)
    response = client.get(f"/learner/notebook/search/{learner_id}?q=debug%20mistakes&top_k=3")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    summary_response = client.get(f"/learner/notebook/summary/{learner_id}")
    assert summary_response.status_code == 200
    assert summary_response.json()["status"] == "success"

    print("STATUS: success")
    print("MODULE: semantic_notebook_search_test")


if __name__ == "__main__":
    main()
