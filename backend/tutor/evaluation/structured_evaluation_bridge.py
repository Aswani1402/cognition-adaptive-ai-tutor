from __future__ import annotations

from typing import Any, Dict, List

from tutor.evaluation.structured_answer_evaluator import (
    SUPPORTED_STRUCTURED_EVALUATION_TYPES,
    evaluate_structured_answer_batch,
)


def _safe_question_type(question: Dict[str, Any]) -> str:
    return str(question.get("question_type") or question.get("assessment_type") or "")


def _build_simulated_answer(question: Dict[str, Any]) -> Any:
    """
    Temporary simulation for pipeline testing only.

    Later frontend/user answers will replace this.
    This lets us verify that structured evaluation works without breaking
    the existing evaluator flow.
    """
    question_type = _safe_question_type(question)
    expected_answer = question.get("expected_answer")
    metadata = question.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    if question_type == "syntax_completion":
        return expected_answer

    if question_type == "fill_blank":
        if isinstance(expected_answer, dict):
            blanks = expected_answer.get("blanks", [])
            if isinstance(blanks, list):
                return blanks
            return [blanks]
        return expected_answer

    if question_type in {"arrange_steps", "drag_order"}:
        if isinstance(expected_answer, dict):
            return expected_answer.get("correct_order", [])
        return []

    if question_type == "match_pairs":
        if isinstance(expected_answer, dict):
            pairs = expected_answer.get("pairs", [])
            if isinstance(pairs, list):
                return {
                    pair.get("left"): pair.get("right")
                    for pair in pairs
                    if isinstance(pair, dict)
                }
        return {}

    if question_type == "code_writing":
        concept_name = question.get("concept_name", "concept")
        return (
            f'example = "{concept_name}"\n'
            "print(example)\n"
            "This code uses the concept correctly and shows the result."
        )

    if question_type == "code_puzzle":
        if isinstance(expected_answer, dict):
            return expected_answer.get("answer", "")
        return expected_answer

    if question_type == "challenge":
        concept_name = question.get("concept_name", "concept")
        return (
            f"I can use {concept_name} in a practical example. "
            "I include a relevant example and explain why the result works."
        )

    return ""


def extract_structured_questions(assessment_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    assessment_output = assessment_output if isinstance(assessment_output, dict) else {}

    questions = assessment_output.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    structured_questions = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        question_type = _safe_question_type(question)

        if question_type in SUPPORTED_STRUCTURED_EVALUATION_TYPES:
            structured_questions.append(question)

    return structured_questions


def build_simulated_structured_answers(
    structured_questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    answers: Dict[str, Any] = {}

    for question in structured_questions:
        question_id = question.get("question_id")
        question_type = _safe_question_type(question)

        simulated_answer = _build_simulated_answer(question)

        if question_id:
            answers[question_id] = simulated_answer

        if question_type:
            answers[question_type] = simulated_answer

    return answers


def run_structured_evaluation_bridge(
    assessment_output: Dict[str, Any],
    learner_answers: Dict[str, Any] | None = None,
    use_simulated_answers: bool = True,
) -> Dict[str, Any]:
    """
    Runs StructuredAnswerEvaluator only for new structured question types.

    Does not replace the existing evaluator.
    It returns a separate structured_evaluation_output that can later be merged
    into fusion/policy/notebook memory.
    """
    structured_questions = extract_structured_questions(assessment_output)

    if not structured_questions:
        return {
            "status": "success",
            "module": "StructuredEvaluationBridge",
            "structured_question_count": 0,
            "structured_question_types": [],
            "used_simulated_answers": False,
            "evaluation": None,
            "reason": "No structured question types found in assessment output.",
        }

    if learner_answers is None:
        learner_answers = {}

    used_simulated_answers = False

    if use_simulated_answers:
        simulated_answers = build_simulated_structured_answers(structured_questions)

        merged_answers = dict(simulated_answers)
        merged_answers.update(learner_answers)

        learner_answers = merged_answers
        used_simulated_answers = True

    evaluation = evaluate_structured_answer_batch(
        questions=structured_questions,
        learner_answers=learner_answers,
    )

    structured_question_types = [
        _safe_question_type(question)
        for question in structured_questions
    ]

    return {
        "status": "success",
        "module": "StructuredEvaluationBridge",
        "structured_question_count": len(structured_questions),
        "structured_question_types": structured_question_types,
        "used_simulated_answers": used_simulated_answers,
        "evaluation": evaluation,
        "reason": (
            "Structured evaluation ran for new structured question types only. "
            "Existing evaluator output is not replaced."
        ),
    }
