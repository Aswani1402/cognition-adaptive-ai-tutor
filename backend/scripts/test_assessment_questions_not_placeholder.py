from __future__ import annotations

from scripts.live_truth_test_helpers import client


PLACEHOLDERS = ["A rule or pattern used in", "A common mistake in", "A worked example of", "A related next step after"]


def main() -> None:
    data = client().get("/assessment/test_learner/S1?subject=SQL%20%2F%20Database&difficulty=hard").json()
    questions = data["questions"]
    assert questions, data
    blob = str(questions)
    assert not any(text in blob for text in PLACEHOLDERS), blob
    assert all(q.get("subject") == "SQL / Database" for q in questions), questions
    print({"question_count": len(questions), "first": questions[0]})


if __name__ == "__main__":
    main()
