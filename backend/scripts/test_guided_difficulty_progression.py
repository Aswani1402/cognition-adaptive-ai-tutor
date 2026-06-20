from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def _submit(client: TestClient, difficulty: str) -> dict:
    response = client.post("/answer/submit", json={
        "learner_id": "audit_progression_learner",
        "subject": "Python",
        "concept_id": "P1",
        "concept_name": "Variables",
        "difficulty": difficulty,
        "question_id": f"audit_{difficulty}",
        "question_type": "mcq",
        "answer": "A name that refers to a value",
        "confidence": 0.9,
        "time_taken_sec": 8,
        "question": {"concept_id": "P1", "concept_name": "Variables", "subject": "Python", "task_type": "mcq", "difficulty": difficulty, "correct_answer": "A name that refers to a value"},
    })
    assert response.status_code == 200, response.text
    return response.json()


def main() -> None:
    client = TestClient(app)
    easy = _submit(client, "easy")
    assert easy["path_update"]["next_difficulty"] == "medium", easy
    assert not easy["path_update"]["concept_completed"], easy
    medium = _submit(client, "medium")
    assert medium["path_update"]["next_difficulty"] == "hard", medium
    hard = _submit(client, "hard")
    assert hard["path_update"]["concept_completed"], hard
    assert hard["path_update"]["next_concept_id"], hard
    print("STATUS: success")
    print("MODULE: test_guided_difficulty_progression")


if __name__ == "__main__":
    main()
