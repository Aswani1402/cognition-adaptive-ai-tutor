from __future__ import annotations

from scripts.live_truth_test_helpers import db_row, register


def main() -> None:
    c, auth = register("subject_select")
    selected = c.post("/learner/select-subject", json={"learner_id": auth["learner_id"], "subject": "SQL / Database"}).json()
    assert selected["active_subject"] == "SQL / Database", selected
    assert selected["current_concept_id"].startswith("S"), selected
    progress = c.get(f"/learner/subject-progress/{auth['learner_id']}").json()["subjects"]
    sql = next(item for item in progress if item["subject"] == "SQL / Database")
    python = next(item for item in progress if item["subject"] == "Python")
    assert sql["status"] == "In Progress", sql
    assert sql["progress_percent"] == 0, sql
    assert python["status"] == "Not Started", python
    profile = db_row("SELECT * FROM learner_profile WHERE learner_id = ?", (auth["learner_id"],))
    assert profile["active_subject"] == "SQL / Database", profile
    print({"selected": selected, "sql_progress": sql, "profile": profile})


if __name__ == "__main__":
    main()
