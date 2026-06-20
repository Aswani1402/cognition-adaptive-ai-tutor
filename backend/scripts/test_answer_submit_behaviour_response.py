from __future__ import annotations

import time

from fastapi.testclient import TestClient

from scripts.migration.add_behaviour_payload_columns import add_columns
from tutor.api.app import app


REQUIRED_SIGNALS = [
    "time_taken_sec",
    "confidence",
    "hint_used",
    "hint_count",
    "option_change_count",
    "answer_change_count",
    "run_code_count",
    "attempt_count",
    "wrong_attempt_count",
]


def main() -> None:
    add_columns()
    client = TestClient(app)
    suffix = int(time.time() * 1000)
    response = client.post(
        "/answer/submit",
        json={
            "learner_id": f"behaviour_response_{suffix}",
            "subject": "Python",
            "concept_id": "variables",
            "concept_name": "Variables",
            "question_id": f"behaviour_response_question_{suffix}",
            "question_type": "mcq",
            "answer": "A",
            "question": {
                "question_id": f"behaviour_response_question_{suffix}",
                "task_type": "mcq",
                "prompt": "Choose A.",
                "correct_answer": "A",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in {"success", "warning"}
    update = data.get("behaviour_update")
    assert isinstance(update, dict), data
    assert update["status"] in {"success", "warning"}
    assert set(REQUIRED_SIGNALS).issubset(set(update.get("signals_used") or []))
    assert "signal_rates" in update
    assert "behaviour_label" in update
    assert "behaviour_risk" in update
    assert update["confidence"] == 0.5
    assert update["time_taken_sec"] == 0
    assert update["hint_used"] is False
    assert update["hint_count"] == 0
    assert update["attempt_count"] == 1
    print("STATUS: success")
    print("MODULE: test_answer_submit_behaviour_response")
    print("SIGNALS_USED:", ", ".join(update["signals_used"]))


if __name__ == "__main__":
    main()
