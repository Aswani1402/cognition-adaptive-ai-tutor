from __future__ import annotations

import sqlite3
import time

from fastapi.testclient import TestClient

from tutor.api.app import app
from tutor.api.dependencies import DB_PATH


REQUIRED_TABLES = [
    "users",
    "learner_profile",
    "learner_session_log",
    "quiz_results",
    "knowledge_state",
    "behaviour_state",
    "learner_mistake_log",
    "learner_doubt_log",
    "revision_card",
    "revision_schedule",
    "reward_event_log",
    "learner_xp_state",
    "learner_streak_state",
    "learner_badges",
    "concept_unlock_state",
    "teaching_strategy_log",
    "xai_log",
]


def main() -> None:
    client = TestClient(app)
    suffix = int(time.time() * 1000)
    email = f"db_persist_{suffix}@example.com"
    password = "demo-pass-123"
    learner_id = client.post("/auth/register", json={"name": "DB Persist", "email": email, "password": password}).json()["learner_id"]
    selected = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "Python"}).json()
    concept_id = selected["current_concept_id"]
    concept_name = selected["current_concept_name"]
    question = client.get(f"/assessment/{learner_id}/{concept_id}?subject=Python&difficulty=easy").json()["questions"][0]
    submitted = client.post(
        "/answer/submit",
        json={
            "learner_id": learner_id,
            "subject": "Python",
            "concept_id": concept_id,
            "concept_name": concept_name,
            "difficulty": "easy",
            "question_id": question["question_id"],
            "question_type": question["question_type"],
            "answer": question["correct_answer"],
            "confidence": 0.6,
            "time_taken_sec": 42,
            "hint_used": True,
            "hint_count": 1,
            "option_change_count": 2,
            "answer_change_count": 3,
            "run_code_count": 1,
            "attempt_count": 1,
            "wrong_attempt_count": 0,
            "question": question,
        },
    ).json()
    assert submitted["behaviour_update"]
    client.post("/doubt/ask", json={"learner_id": learner_id, "subject": "Python", "concept_id": concept_id, "concept_name": concept_name, "doubt_text": "debug this"})

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        missing = [table for table in REQUIRED_TABLES if table not in tables]
        assert not missing, f"Missing persistence tables: {missing}"
        non_empty_checks = {
            "users": "SELECT COUNT(*) FROM users",
            "learner_profile": "SELECT COUNT(*) FROM learner_profile WHERE learner_id = ?",
            "learner_session_log": "SELECT COUNT(*) FROM learner_session_log WHERE learner_id = ?",
            "quiz_results": "SELECT COUNT(*) FROM quiz_results WHERE learner_id = ?",
            "behaviour_state": "SELECT COUNT(*) FROM behaviour_state WHERE learner_id = ?",
            "learner_doubt_log": "SELECT COUNT(*) FROM learner_doubt_log WHERE learner_id = ?",
            "concept_unlock_state": "SELECT COUNT(*) FROM concept_unlock_state WHERE learner_id = ?",
        }
        for table, sql in non_empty_checks.items():
            params = () if table == "users" else (learner_id,)
            assert conn.execute(sql, params).fetchone()[0] > 0, table
    finally:
        conn.close()
    print("user db persistence flow ok")


if __name__ == "__main__":
    main()
