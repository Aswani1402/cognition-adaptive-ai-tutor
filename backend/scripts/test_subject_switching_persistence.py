from __future__ import annotations

import json
import sqlite3
import time

from fastapi.testclient import TestClient

from tutor.api.app import app
from tutor.api.dependencies import DB_PATH


def _ensure_knowledge_state_table() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_state (
                student_id TEXT PRIMARY KEY,
                state_json TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _row(sql: str, params: tuple) -> sqlite3.Row | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def main() -> None:
    _ensure_knowledge_state_table()
    client = TestClient(app)
    suffix = int(time.time() * 1000)
    learner_id = client.post(
        "/auth/register",
        json={"name": "Subject Switch", "email": f"subject_switch_{suffix}@example.com", "password": "demo-pass-123"},
    ).json()["learner_id"]

    python_selected = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "Python"}).json()
    assert python_selected["active_subject"] == "Python", python_selected
    python_concept_id = python_selected["current_concept_id"]
    python_concept_name = python_selected["current_concept_name"]

    question = client.get(f"/assessment/{learner_id}/{python_concept_id}?subject=Python&difficulty=easy").json()["questions"][0]
    submitted = client.post(
        "/answer/submit",
        json={
            "learner_id": learner_id,
            "subject": "Python",
            "concept_id": python_concept_id,
            "concept_name": python_concept_name,
            "difficulty": "easy",
            "question_id": question["question_id"],
            "question_type": question["question_type"],
            "answer": question["correct_answer"],
            "confidence": 0.9,
            "time_taken_sec": 20,
            "question": question,
        },
    ).json()
    assert submitted["status"] == "success", submitted
    expected_python_difficulty = submitted.get("path_update", {}).get("next_difficulty") or "easy"

    python_progress = _row(
        """
        SELECT * FROM learner_concept_progress
        WHERE learner_id = ? AND domain = ? AND concept_id = ?
        """,
        (learner_id, "Python", python_concept_id),
    )
    assert python_progress, "Python progress was not saved"
    assert float(python_progress["mastery"] or 0.0) > 0.0, dict(python_progress)

    sql_selected = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "SQL / Database"}).json()
    assert sql_selected["active_subject"] == "SQL / Database", sql_selected
    assert sql_selected["current_difficulty"] == "easy", sql_selected
    assert sql_selected["current_concept_id"] != python_concept_id, sql_selected

    restored_python = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "Python"}).json()
    assert restored_python["active_subject"] == "Python", restored_python
    assert restored_python["current_concept_id"] == python_concept_id, restored_python
    assert restored_python["current_concept_name"] == python_concept_name, restored_python
    assert restored_python["current_difficulty"] == expected_python_difficulty, restored_python

    restored_progress = _row(
        """
        SELECT * FROM learner_concept_progress
        WHERE learner_id = ? AND domain = ? AND concept_id = ?
        """,
        (learner_id, "Python", python_concept_id),
    )
    assert restored_progress, "Python progress disappeared after subject switch"
    assert float(restored_progress["mastery"] or 0.0) == float(python_progress["mastery"] or 0.0), dict(restored_progress)

    python_unlock = _row(
        """
        SELECT * FROM concept_unlock_state
        WHERE learner_id = ? AND domain = ? AND concept_id = ?
        """,
        (learner_id, "Python", python_concept_id),
    )
    sql_unlock = _row(
        """
        SELECT * FROM concept_unlock_state
        WHERE learner_id = ? AND domain = ?
        """,
        (learner_id, "SQL / Database"),
    )
    assert python_unlock and float(python_unlock["mastery_score"] or 0.0) > 0.0, dict(python_unlock or {})
    assert sql_unlock, "SQL unlock state was not initialized"

    kt_row = _row("SELECT state_json FROM knowledge_state WHERE student_id = ?", (learner_id,))
    kt_state = json.loads(kt_row["state_json"]) if kt_row else {}
    kt_python = kt_state.get("subjects", {}).get("Python", {}).get("concepts", {}).get(python_concept_id, {})
    assert float(kt_python.get("mastery") or 0.0) > 0.0, kt_state

    context = client.get(f"/learner/context/{learner_id}").json()
    assert context["active_subject"] == "Python", context
    assert context["current_concept_id"] == python_concept_id, context
    assert context["current_concept_name"] == python_concept_name, context
    assert context["current_difficulty"], context
    assert context["current_teaching_view"], context
    assert context["subject_progress"]["subject"] == "Python", context

    print("subject switching persistence test success")


if __name__ == "__main__":
    main()
