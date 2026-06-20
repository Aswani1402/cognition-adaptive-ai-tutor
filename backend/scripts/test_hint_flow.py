from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def main() -> None:
    client = TestClient(app)
    response = client.post("/hint/predict", json={
        "learner_id": "quality_hint_learner",
        "subject": "Python",
        "concept_id": "P1",
        "concept_name": "Variables",
        "difficulty": "easy",
        "question_type": "mcq",
        "question_id": "hint_q1",
        "current_answer": "",
        "hint_count": 0,
        "mastery_score": None,
        "behaviour_risk": None,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("hint_text") or data.get("message"), data
    assert data.get("hint_type"), data
    assert data.get("hint_level") == 1, data
    assert not data.get("reveal_answer"), data
    print("STATUS: success")
    print("MODULE: test_hint_flow")


if __name__ == "__main__":
    main()
