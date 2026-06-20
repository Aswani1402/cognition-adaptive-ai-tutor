from __future__ import annotations

from scripts.live_truth_test_helpers import register


def main() -> None:
    c, auth = register("progress_zero")
    data = c.get(f"/learner/subject-progress/{auth['learner_id']}").json()
    subjects = data["subjects"]
    assert len(subjects) >= 5, data
    for item in subjects:
        assert item["average_mastery"] == 0.0, item
        assert item["progress_percent"] == 0, item
        assert item["status"] == "Not Started", item
        assert item["current_concept_id"] is None, item
    print(data)


if __name__ == "__main__":
    main()
