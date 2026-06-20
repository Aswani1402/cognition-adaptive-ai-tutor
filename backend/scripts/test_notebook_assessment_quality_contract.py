from __future__ import annotations

from tutor.api.concept_content_resolver import build_assessment_questions
from tutor.api.evaluation_routes import _next_teaching_view_for, _open_ended_precheck
from tutor.notebook.learner_facing import normalize_notebook_memory


def _assert_no_raw_labels(value: object) -> None:
    text = str(value).lower()
    forbidden = [
        "weak_answer",
        "wrong_option",
        "none",
        "apply c2",
        "fallback_cumulative",
        "exact_match",
    ]
    leaked = [label for label in forbidden if label in text]
    assert not leaked, f"Raw learner-facing labels leaked: {leaked}"


def test_notebook_learner_facing_normalization() -> None:
    packet = {
        "subject": "Python",
        "concept_id": "variables",
        "concept_name": "Variables",
        "base_content": "A variable stores and reuses a value.",
        "key_points": ["Variables are assigned with =", "Use clear names"],
        "resource_source": "concept_resources",
    }
    mistakes = [
        {"mistake_type": "weak_answer", "feedback": "The answer does not fully match the expected solution."},
        {"mistake_type": "weak_answer", "feedback": "The answer does not fully match the expected solution."},
        {"mistake_type": "wrong_option", "feedback": "wrong_option"},
        {"mistake_type": "none", "feedback": "Correct. Your answer matches the expected answer."},
    ]
    revisions = [{"reason": "wrong_output"}, {"reason": "transfer_question"}]
    cards = [
        {"front": "Apply C2 at easy level", "back": "none"},
        {"front": "What is a variable?", "back": "A variable is a name used to store a value."},
        {"front": "What is a variable?", "back": "A variable is a name used to store a value."},
    ]
    doubts = [{"doubt_text": "What is this concept?", "answer": "Variables store values."}]

    result = normalize_notebook_memory(
        packet=packet,
        mistakes=mistakes,
        revisions=revisions,
        cards=cards,
        doubts=doubts,
    )

    _assert_no_raw_labels(result)
    assert len(result["learner_facing_mistakes"]) == 2
    assert all("Correct. Your answer matches" not in item for item in result["learner_facing_mistakes"])
    assert result["learner_facing_flashcards"][0]["front"].startswith("What")
    assert result["learner_facing_doubts"][0]["question"] == "What is Variables in Python?"
    assert any("Predict the output" in item for item in result["learner_facing_revision_plan"])


def test_assessment_questions_have_hidden_hints_and_rendering_fields() -> None:
    questions = build_assessment_questions("Python", "variables", "hard")
    by_type = {question["task_type"]: question for question in questions}
    assert "mcq" in by_type
    assert len(by_type["mcq"]["options"]) == 4
    assert by_type["mcq"].get("correct_answer")
    for question in questions:
        assert question.get("prompt")
        assert question.get("instruction")
        assert question.get("hidden_hint")
        assert question.get("frontend_render_type")
        assert question.get("expected_answer") is not None or question.get("expected_idea")
    transfer = by_type["transfer_question"]
    assert "scenario" in transfer["prompt"].lower() or "wants to" in transfer["prompt"].lower() or "using" in transfer["prompt"].lower()
    assert "partial" in str(transfer.get("rubric", "")).lower()


def test_valid_assignment_transfer_is_partial_not_weak() -> None:
    question = {
        "task_type": "transfer_question",
        "concept_name": "Variables",
        "prompt": "A student wants to store a product name and price. Write two variables and explain why variables are useful.",
        "expected_answer": {
            "expected_points": ["two variable assignments", "short explanation"],
        },
    }
    result = _open_ended_precheck(question, "a = 2")
    assert result is not None
    assert result["label"] == "partial"
    assert result["score"] >= 0.45
    assert "Missing" in result["feedback"] or "missing" in result["feedback"]


def test_weak_answers_recommend_teaching_view_change() -> None:
    assert _next_teaching_view_for(score=0.3, task_type="transfer_question", mistake_type="weak_answer") == "simple_example_view"
    assert _next_teaching_view_for(score=0.3, task_type="syntax_completion", mistake_type="syntax_misunderstanding") == "code_view"
    assert _next_teaching_view_for(score=0.3, task_type="output_prediction", mistake_type="wrong_output") == "output_prediction_view"


if __name__ == "__main__":
    test_notebook_learner_facing_normalization()
    test_assessment_questions_have_hidden_hints_and_rendering_fields()
    test_valid_assignment_transfer_is_partial_not_weak()
    test_weak_answers_recommend_teaching_view_change()
    print("notebook_assessment_quality_contract: success")
