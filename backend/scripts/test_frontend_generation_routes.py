from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tutor.api.app import app


FRONTEND_API = Path(__file__).resolve().parents[1].parent / "frontend_ui" / "KP-UI" / "src" / "lib" / "api.ts"


def main() -> None:
    client = TestClient(app)
    routes = [
        "/lesson/demo_learner/S1?subject=SQL&view=code_view",
        "/assessment/demo_learner/S1?subject=SQL&difficulty=medium",
        "/flashcards/demo_learner/S1?subject=SQL",
        "/mindmap/S1?subject=SQL",
        "/generation/coverage/demo_learner",
        "/generation/tasks/S1?subject=SQL",
        "/ai/evidence/demo_learner?concept_id=S1&subject=SQL",
        "/agentic/trace/demo_learner",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, f"{route}: {response.text}"
        assert response.json().get("status") in {"success", "warning"}, response.json()
    similar = client.post(
        "/question/similar",
        json={"learner_id": "demo_learner", "concept_id": "S1", "subject": "SQL", "difficulty": "easy", "exclude_question_ids": []},
    )
    assert similar.status_code == 200, similar.text
    assert similar.json().get("question"), similar.json()

    api_text = FRONTEND_API.read_text(encoding="utf-8")
    for name in ["getGenerationCoverage", "getGenerationTasks", "getSimilarQuestion", "getAIEvidence", "getAgenticTrace"]:
        assert f"export async function {name}" in api_text, f"Missing frontend API export: {name}"
    print("frontend generation routes test success")


if __name__ == "__main__":
    main()
