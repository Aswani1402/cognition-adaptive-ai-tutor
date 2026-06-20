from __future__ import annotations

from scripts.live_truth_test_helpers import client


def main() -> None:
    c = client()
    lesson = c.get("/lesson/test_learner/S1?subject=SQL%20%2F%20Database").json()
    text = " ".join(str(lesson.get(k, "")) for k in ["subject", "concept_name", "adaptiveExplanation", "workedExample"])
    assert lesson["subject"] == "SQL / Database", lesson
    assert "Python Variables" not in text and "score = 10" not in text, text
    assert "database" in text.lower() or "sql" in text.lower(), text
    print(lesson)


if __name__ == "__main__":
    main()
