from __future__ import annotations

from scripts.live_truth_test_helpers import register


def main() -> None:
    c, auth = register("answer_eval")
    q = c.get("/assessment/test_learner/P1?subject=Python&difficulty=easy").json()["questions"][0]
    wrong = c.post("/answer/submit", json={
        "learner_id": auth["learner_id"],
        "concept_id": q["concept_id"],
        "concept_name": q["concept_name"],
        "subject": q["subject"],
        "question_id": q["question_id"],
        "question_type": q["question_type"],
        "answer": "totally random nonsense",
        "question": q,
    }).json()
    assert wrong["score"] < 0.8, wrong
    assert wrong["correct_answer"] and wrong["correct_answer"] != "Shown in the question feedback", wrong
    print(wrong)


if __name__ == "__main__":
    main()
