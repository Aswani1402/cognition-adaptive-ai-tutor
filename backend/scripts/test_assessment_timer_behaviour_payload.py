from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def main() -> None:
    client = TestClient(app)
    payload = {
        "learner_id": "quality_behaviour_learner",
        "subject": "Python",
        "concept_id": "P1",
        "concept_name": "Variables",
        "difficulty": "easy",
        "question_id": "quality_behaviour_q",
        "question_type": "mcq",
        "answer": "Referring to a value",
        "confidence": 0.6,
        "time_taken_sec": 42,
        "hint_used": True,
        "hint_count": 1,
        "option_change_count": 2,
        "answer_change_count": 3,
        "run_code_count": 1,
        "attempt_count": 1,
        "wrong_attempt_count": 0,
        "question": {"task_type": "mcq", "prompt": "What is a variable used for in Python?", "correctAnswer": "Referring to a value", "concept_name": "Variables"},
    }
    response = client.post("/answer/submit", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    behaviour = data.get("behaviour_update") or {}
    signals = behaviour.get("signals_used") or {}
    for key in ["hint_rate", "option_change_rate", "answer_change_rate", "run_code_rate", "retry_rate"]:
        assert key in signals, behaviour
    assert behaviour.get("time_taken_sec") == 42, behaviour
    assert behaviour.get("hint_count") == 1, behaviour
    print("STATUS: success")
    print("MODULE: test_assessment_timer_behaviour_payload")


if __name__ == "__main__":
    main()
