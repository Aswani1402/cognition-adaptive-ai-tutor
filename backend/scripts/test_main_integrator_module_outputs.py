from __future__ import annotations


def main() -> None:
    from fastapi.testclient import TestClient

    from tutor.api.app import app
    from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once

    output = run_integrated_tutor_once(learner_id="14", reward_dry_run=True)
    assert output.get("status") in {"success", "error"}
    if output.get("status") == "success":
        expected = [
            "policy_output",
            "teaching_strategy",
            "assessment",
            "evaluation",
            "xai",
            "progression_reward_output",
        ]
        missing = [key for key in expected if key not in output]
        assert not missing, f"Missing integrated output keys: {missing}"

    client = TestClient(app)
    response = client.get("/tutor/adaptive-session/14?reward_dry_run=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"success", "warning"}
    assert "frontend_response" in payload

    submit = client.post(
        "/answer/submit",
        json={
            "learner_id": "14",
            "concept_id": "P1",
            "concept_name": "Variables",
            "subject": "Python",
            "difficulty": "easy",
            "question_type": "mcq",
            "answer": "A",
            "confidence": 0.8,
            "time_taken_sec": 12,
            "question": {
                "question_id": "integrator_audit_q1",
                "prompt": "Which option is correct?",
                "expected_answer": "A",
                "task_type": "mcq",
            },
        },
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    for key in [
        "kt_update",
        "behaviour_update",
        "path_update",
        "reward_update",
        "xai",
        "policy_update",
        "rag_evidence",
        "agentic_trace",
    ]:
        assert key in submit_payload, key
    assert submit_payload["kt_update"]["model_used"] == "fallback_cumulative"
    assert submit_payload["behaviour_update"]["model_used"] == "scoring_formula"
    print("main integrator module outputs test success")
    print("integrated_status:", output.get("status"))


if __name__ == "__main__":
    main()
