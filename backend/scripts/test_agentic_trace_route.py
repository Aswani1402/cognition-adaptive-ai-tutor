from __future__ import annotations


def main() -> None:
    from fastapi.testclient import TestClient

    from tutor.api.app import app
    from tutor.system.agentic_orchestrator import SafeTutorOrchestrator

    learner_id = "agentic_trace_route_learner"
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
    response = TestClient(app).get(f"/agentic/trace/{learner_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"success", "warning"}
    assert payload.get("orchestrator_type") == "safe_tutor_orchestrator"
    assert payload.get("is_fully_autonomous") is False
    assert payload.get("safety_controlled") is True
    assert payload.get("trace")
    print("agentic trace route test success")
    print("status:", payload.get("status"))


if __name__ == "__main__":
    main()
