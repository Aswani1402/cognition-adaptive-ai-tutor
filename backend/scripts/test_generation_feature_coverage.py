from __future__ import annotations

from fastapi.testclient import TestClient

from tutor.api.app import app


REQUIRED_TASKS = {
    "explanation",
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "comparison_view",
    "real_world_connection_view",
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",
    "practice_question",
    "revision_summary",
    "concept_recall_flashcard",
    "concept_mindmap",
    "doubt_answer",
    "teaching_voice_script",
}


def main() -> None:
    client = TestClient(app)
    response = client.get("/generation/tasks/S1?subject=SQL")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("status") == "success", payload
    task_types = set(payload.get("task_types") or [])
    missing = sorted(REQUIRED_TASKS - task_types)
    assert not missing, f"Missing generated task coverage: {missing}"
    assert payload.get("rag_connected") is True
    print("generation feature coverage test success")


if __name__ == "__main__":
    main()
