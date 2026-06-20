from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def _submit(client: TestClient, payload: dict) -> dict:
    response = client.post("/answer/submit", json={
        "learner_id": "quality_equivalence_learner",
        "subject": "Python",
        "concept_id": "P1",
        "concept_name": "Variables",
        "difficulty": payload.get("difficulty", "easy"),
        "question_id": payload["question_id"],
        "question_type": payload["question_type"],
        "answer": payload["answer"],
        "confidence": 0.8,
        "time_taken_sec": 12,
        "hint_used": False,
        "hint_count": 0,
        "option_change_count": 0,
        "answer_change_count": 1,
        "run_code_count": 0,
        "attempt_count": 1,
        "wrong_attempt_count": 0,
        "question": payload["question"],
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("status") in {"success", "warning"}, data
    return data


def main() -> None:
    client = TestClient(app)
    mcq = _submit(client, {
        "question_id": "var_mcq_equiv",
        "question_type": "mcq",
        "answer": "Referring to a value",
        "question": {"task_type": "mcq", "prompt": "What is a variable used for in Python?", "correctAnswer": "A name that refers to a value", "concept_name": "Variables"},
    })
    assert mcq["score"] >= 0.85 and mcq["correct"], mcq

    blank = _submit(client, {
        "question_id": "var_blank_equiv",
        "question_type": "fill_blank",
        "answer": {"answer": "value"},
        "question": {"task_type": "fill_blank", "prompt": "A variable is a name that refers to a _____.", "correctAnswer": "value", "concept_name": "Variables"},
    })
    assert blank["score"] >= 0.85 and blank["correct"], blank

    out = _submit(client, {
        "question_id": "var_output_equiv",
        "question_type": "output_prediction",
        "answer": "10",
        "difficulty": "medium",
        "question": {"task_type": "output_prediction", "prompt": "What is the output?", "code": "name = 'Alice'\nscore = 10\nprint(score)", "correctAnswer": "10", "expected_output": "10", "concept_name": "Variables"},
    })
    assert out["score"] >= 0.85 and out["correct"], out

    debug = _submit(client, {
        "question_id": "print_quote_equiv",
        "question_type": "debug_task",
        "answer": "print(\"hello\")",
        "difficulty": "medium",
        "question": {"task_type": "debug_task", "prompt": "Fix the code.", "code": "print('hello')", "expected_output": "hello", "correctAnswer": "print('hello')", "concept_name": "Variables"},
    })
    assert debug["score"] >= 0.85 and debug["correct"], debug
    for data in [mcq, blank, out, debug]:
        assert data.get("correct_answer") is not None
        assert data.get("explanation")
    print("STATUS: success")
    print("MODULE: test_answer_equivalence_cases")


if __name__ == "__main__":
    main()
