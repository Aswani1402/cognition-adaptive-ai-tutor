from __future__ import annotations


def main() -> None:
    from fastapi.testclient import TestClient

    from tutor.api.app import app
    from tutor.system.agentic_orchestrator import SafeTutorOrchestrator

    learner_id = "agentic_ai_evidence_learner"
    SafeTutorOrchestrator().run(
        {
            "learner_id": learner_id,
            "subject": "Python",
            "concept_id": "P1",
            "concept_name": "Variables",
            "difficulty": "easy",
            "activity_type": "lesson",
        }
    )
    response = TestClient(app).get(f"/ai/evidence/{learner_id}?concept_id=P1&subject=Python")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"success", "warning"}
    for key in ["kt", "behaviour", "adaptive_path", "policy_rl", "rag", "xai_summary", "agentic_trace", "agentic_evidence"]:
        assert key in payload, key
    assert payload["policy_rl"]["rl_comparison_status"] == "offline comparison only"
    assert payload["agentic_trace"]["orchestrator_type"] == "safe_tutor_orchestrator"
    assert payload["agentic_trace"]["is_fully_autonomous"] is False
    print("ai evidence route test success")


if __name__ == "__main__":
    main()
