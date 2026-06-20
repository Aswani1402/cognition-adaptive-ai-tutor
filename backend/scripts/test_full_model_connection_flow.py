from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.audit_full_system_module_connections import run_audit
from tutor.api.app import app


def main() -> None:
    report = run_audit()
    assert report["modules"], "No module audit rows produced."
    client = TestClient(app)
    learner_id = "audit_full_flow_learner"
    subject = "SQL / Database"
    select = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": subject})
    assert select.status_code == 200, select.text
    selected = select.json()
    assert selected.get("active_subject") == subject, selected
    concept_id = selected.get("current_concept_id") or "S1"
    lesson = client.get(f"/lesson/{learner_id}/{concept_id}?subject=SQL%20%2F%20Database&difficulty=easy")
    assert lesson.status_code == 200, lesson.text
    assessment = client.get(f"/assessment/{learner_id}/{concept_id}?subject=SQL%20%2F%20Database&difficulty=easy")
    assert assessment.status_code == 200, assessment.text
    answer = client.post("/answer/submit", json={
        "learner_id": learner_id,
        "subject": subject,
        "concept_id": concept_id,
        "concept_name": selected.get("current_concept_name") or "Database Basics",
        "difficulty": "easy",
        "question_id": "audit_full_q1",
        "question_type": "fill_blank",
        "answer": "SELECT",
        "confidence": 0.9,
        "time_taken_sec": 12,
        "hint_used": False,
        "hint_count": 0,
        "option_change_count": 0,
        "answer_change_count": 1,
        "run_code_count": 0,
        "attempt_count": 1,
        "wrong_attempt_count": 0,
        "question": {"concept_id": concept_id, "concept_name": "Database Basics", "subject": subject, "task_type": "fill_blank", "difficulty": "easy", "correct_answer": "SELECT"},
    })
    assert answer.status_code == 200, answer.text
    data = answer.json()
    for key in ["behaviour_update", "kt_update", "path_update", "policy_update", "rag_update", "llm_generation"]:
        assert key in data, f"missing {key}: {data}"
    print("STATUS: success")
    print("MODULE: test_full_model_connection_flow")


if __name__ == "__main__":
    main()
