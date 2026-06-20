from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


def main() -> None:
    client = TestClient(app)
    response = client.get("/lesson/quality_lesson/P1?subject=Python&difficulty=easy&view=definition_view")
    assert response.status_code == 200, response.text
    data = response.json()
    text = str(data)
    for expected in ["A variable is a name", "Key points", "Variables are names", "Common mistake", "Real-world use"]:
        assert expected in text, expected
    assert "Apply C2" not in text and "What C2 means" not in text, text
    assert data.get("keyPoints") or data.get("teaching_content", {}).get("key_points"), data
    assert data.get("commonMistakes") or data.get("teaching_content", {}).get("common_mistakes"), data
    print("STATUS: success")
    print("MODULE: test_concept_resource_teaching_content")


if __name__ == "__main__":
    main()
