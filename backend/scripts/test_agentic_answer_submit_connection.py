from __future__ import annotations


def main() -> None:
    from fastapi.testclient import TestClient

    from tutor.api.app import app

    client = TestClient(app)
    learner_id = "agentic_answer_submit_learner"
    response = client.post(
        "/answer/submit",
        json={
            "learner_id": learner_id,
            "subject": "Python",
            "concept_id": "P1",
            "concept_name": "Variables",
            "difficulty": "easy",
            "question_type": "mcq",
            "answer": "B",
            "confidence": 0.4,
            "time_taken_sec": 70,
            "hint_used": True,
            "hint_count": 1,
            "question": {
                "question_id": "agentic_submit_q1",
                "prompt": "Which option is correct?",
                "expected_answer": "A",
                "task_type": "mcq",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "agentic_trace" in payload
    assert payload["agentic_trace"]["orchestrator_type"] == "safe_tutor_orchestrator"
    assert payload["agentic_trace"]["is_fully_autonomous"] is False
    assert payload["agentic_orchestrator"]["safety_checks"]["promotion_allowed"] is False
    trace_response = client.get(f"/agentic/trace/{learner_id}")
    assert trace_response.status_code == 200
    assert trace_response.json()["status"] == "success"
    print("agentic answer submit connection test success")


if __name__ == "__main__":
    main()
