from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.migration.add_behaviour_payload_columns import add_columns
from tutor.api.app import app


DB_PATH = Path("external/core_data/tutor.db")


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def main() -> None:
    add_columns()
    client = TestClient(app)
    suffix = int(time.time() * 1000)
    learner_id = f"behaviour_db_{suffix}"
    question_id = f"behaviour_db_question_{suffix}"
    payload = {
        "learner_id": learner_id,
        "subject": "Python",
        "concept_id": "variables",
        "concept_name": "Variables",
        "difficulty": "medium",
        "question_id": question_id,
        "question_type": "coding_prompt",
        "answer": "print('A')",
        "confidence": 0.4,
        "time_taken_sec": 65,
        "hint_used": True,
        "hint_count": 2,
        "option_change_count": 0,
        "answer_change_count": 4,
        "run_code_count": 2,
        "attempt_count": 2,
        "wrong_attempt_count": 1,
        "question": {
            "question_id": question_id,
            "task_type": "coding_prompt",
            "prompt": "Print A.",
            "correct_answer": "print('A')",
            "difficulty": "medium",
        },
    }
    response = client.post("/answer/submit", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in {"success", "warning"}
    assert data["behaviour_update"]["status"] in {"success", "warning"}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        quiz_columns = _columns(conn, "quiz_results")
        row = conn.execute(
            "SELECT * FROM quiz_results WHERE learner_id=? AND question_id=? ORDER BY rowid DESC LIMIT 1",
            (learner_id, question_id),
        ).fetchone()
        assert row is not None
        row_dict = dict(row)
        for column, expected in {
            "confidence": 0.4,
            "time_taken_sec": 65,
            "hint_used": 1,
            "hint_count": 2,
            "answer_change_count": 4,
            "run_code_count": 2,
            "attempt_count": 2,
            "wrong_attempt_count": 1,
            "question_type": "coding_prompt",
            "difficulty": "medium",
            "subject": "Python",
            "concept_id": "variables",
        }.items():
            if column in quiz_columns:
                assert row_dict[column] == expected, (column, row_dict.get(column), expected)

        behaviour_row = conn.execute(
            "SELECT * FROM behaviour_state WHERE learner_id=? ORDER BY rowid DESC LIMIT 1",
            (learner_id,),
        ).fetchone()
        assert behaviour_row is not None
        behaviour = dict(behaviour_row)
        assert behaviour.get("behavior_source") == "answer_submit_payload"
        if "answer_change_rate" in behaviour:
            assert behaviour["answer_change_rate"] > 0
        if "run_code_rate" in behaviour:
            assert behaviour["run_code_rate"] > 0
    finally:
        conn.close()

    print("STATUS: success")
    print("MODULE: test_behaviour_payload_db_persistence")
    print("LEARNER_ID:", learner_id)
    print("QUESTION_ID:", question_id)


if __name__ == "__main__":
    main()
