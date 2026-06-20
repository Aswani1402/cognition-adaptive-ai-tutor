from __future__ import annotations

from typing import Any, Dict, List


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _question_type(question: Dict[str, Any]) -> str:
    return _safe_str(
        question.get("assessment_type") or question.get("question_type"),
        "unknown",
    )


def _expected_text(question: Dict[str, Any]) -> str:
    expected = question.get("expected_answer")

    if isinstance(expected, dict):
        return _safe_str(
            expected.get("fix_text")
            or expected.get("answer")
            or expected.get("expected_fix")
            or expected.get("output")
            or "",
            "",
        )

    return _safe_str(expected, "")


def simulate_answer_for_question(
    question: Dict[str, Any],
    learner_profile: str = "average",
) -> str:
    """
    Simulates learner answers for testing assessment/evaluation.

    Profiles:
    - strong: mostly correct
    - average: partially correct
    - weak: mostly incorrect
    - debug_weak: fails debug/code tracing
    - low_confidence: vague answers
    """
    profile = _safe_str(learner_profile, "average").lower()
    q_type = _question_type(question)
    expected = _expected_text(question)

    if profile == "strong":
        if q_type in {"debug", "debug_task"}:
            return expected or "Fix the syntax error and use the correct variable/value."
        if q_type in {"output_prediction"}:
            return expected or "Alice"
        if q_type in {"mcq"}:
            options = question.get("options") or []
            correct_index = question.get("correct_option_index")
            if isinstance(correct_index, int) and 0 <= correct_index < len(options):
                return str(options[correct_index])
            return expected or "Correct option"
        if q_type in {"short_explanation", "explanation"}:
            return "A variable is a name that stores or refers to a value and can be reused in code."
        if q_type in {"transfer"}:
            return "Variables can store prices, names, counters, configuration values, and API results."
        if q_type in {"code_writing"}:
            return 'name = "Alice"\nprint(name)'
        return expected or "Correct answer."

    if profile == "weak":
        if q_type in {"mcq"}:
            return "I do not know"
        if q_type in {"debug", "debug_task"}:
            return "There is no mistake."
        if q_type in {"output_prediction"}:
            return "10"
        if q_type in {"short_explanation", "explanation"}:
            return "Variable means changing thing."
        if q_type in {"transfer"}:
            return ""
        if q_type in {"code_writing"}:
            return "print(variable)"
        return "Not sure"

    if profile == "debug_weak":
        if q_type in {"debug", "debug_task"}:
            return "The variable name is wrong. Use another name."
        if q_type in {"output_prediction"}:
            return "15"
        return expected or "Partially correct answer."

    if profile == "low_confidence":
        if q_type in {"debug", "debug_task"}:
            return "Maybe quotes are wrong?"
        if q_type in {"output_prediction"}:
            return expected or "Alice"
        return "I think it stores a value, but I am not sure."

    # average
    if q_type in {"debug", "debug_task"}:
        return "There is a mistake in the code, maybe the variable name or quotes."
    if q_type in {"output_prediction"}:
        return "15"
    if q_type in {"mcq"}:
        options = question.get("options") or []
        if options:
            return str(options[0])
        return expected or "A variable stores a value."
    if q_type in {"short_explanation", "explanation"}:
        return "A variable stores a value that can be used later."
    if q_type in {"transfer"}:
        return "Variables are used to store names, prices, and values."
    if q_type in {"code_writing"}:
        return 'name = Alice\nprint(name)'
    return expected or "Partial answer."


def simulate_answers_for_assessment(
    assessment_output: Dict[str, Any],
    learner_profile: str = "average",
) -> Dict[str, str]:
    questions: List[Dict[str, Any]] = assessment_output.get("questions", [])

    answers: Dict[str, str] = {}

    for question in questions:
        if not isinstance(question, dict):
            continue

        q_type = _question_type(question)
        answers[q_type] = simulate_answer_for_question(
            question=question,
            learner_profile=learner_profile,
        )

    return answers