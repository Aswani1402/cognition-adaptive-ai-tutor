from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def main() -> None:
    client = TestClient(app)
    for difficulty, expected in {
        "easy": {"mcq", "fill_blank", "true_or_false"},
        "medium": {"output_prediction", "debug_task", "syntax_completion"},
        "hard": {"coding_question", "transfer_question", "challenge_question"},
    }.items():
        response = client.get(f"/assessment/quality_rotation/P1?subject=Python&difficulty={difficulty}")
        assert response.status_code == 200, response.text
        data = response.json()
        questions = data.get("questions") or []
        assert len(questions) >= 2, data
        ids = [q.get("questionId") for q in questions]
        assert len(ids) == len(set(ids)), questions
        types = {q.get("taskType") or q.get("questionType") for q in questions}
        assert types & expected, (difficulty, types)
        assert "Apply C2" not in str(questions) and "What C2 means" not in str(questions), questions
    print("STATUS: success")
    print("MODULE: test_question_rotation_quality")


if __name__ == "__main__":
    main()
