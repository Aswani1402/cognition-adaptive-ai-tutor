from __future__ import annotations

from typing import Any, Dict, List


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_text(value: Any) -> str:
    return " ".join(_safe_str(value).lower().strip().split())


def _normalize_output_lines(value: Any) -> List[str]:
    text = _safe_str(value)
    if not text:
        return []

    # Normalize common separators.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if "\n" not in text and "," in text:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = [part.strip() for part in text.split("\n")]

    return [part for part in parts if part]


def _expected_output_text(expected_answer: Any) -> str:
    if isinstance(expected_answer, dict):
        return _safe_str(
            expected_answer.get("output")
            or expected_answer.get("expected_output")
            or expected_answer.get("answer")
            or expected_answer.get("value")
            or ""
        )

    return _safe_str(expected_answer)


def _code_from_question(question: Dict[str, Any]) -> str:
    metadata = question.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return _safe_str(
        metadata.get("code")
        or question.get("code")
        or question.get("prompt")
        or question.get("question")
        or ""
    )


def _score_label(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.65:
        return "partial_strong"
    if score >= 0.45:
        return "partial"
    if score > 0:
        return "weak"
    return "incorrect"


def _classify_output_error(
    expected: str,
    answer: str,
    expected_lines: List[str],
    answer_lines: List[str],
) -> str:
    if not answer:
        return "no_answer"

    if _normalize_text(expected) == _normalize_text(answer):
        return "none"

    if len(expected_lines) != len(answer_lines):
        return "line_count_mismatch"

    if expected_lines and answer_lines:
        normalized_expected = [_normalize_text(line) for line in expected_lines]
        normalized_answer = [_normalize_text(line) for line in answer_lines]

        matched_lines = sum(
            1
            for expected_line, answer_line in zip(normalized_expected, normalized_answer)
            if expected_line == answer_line
        )

        if matched_lines > 0:
            return "partial_line_match"

    if answer.isdigit() and not expected.isdigit():
        return "numeric_instead_of_text"

    if expected.isdigit() and not answer.isdigit():
        return "text_instead_of_numeric"

    return "wrong_value"


def evaluate_output_prediction_answer(
    question: Dict[str, Any],
    learner_answer: Any,
) -> Dict[str, Any]:
    """
    Specialized evaluator for output prediction questions.

    It checks:
    - exact output match
    - normalized output match
    - line count match
    - partial line match
    - trace reasoning quality
    - output error type
    """

    answer_raw = _safe_str(learner_answer)
    answer = answer_raw.strip()

    expected_raw = _expected_output_text(question.get("expected_answer"))
    expected = expected_raw.strip()

    code = _code_from_question(question)

    expected_lines = _normalize_output_lines(expected)
    answer_lines = _normalize_output_lines(answer)

    if not answer:
        return {
            "status": "success",
            "module": "OutputPredictionEvaluator",
            "assessment_type": "output_prediction",
            "overall_score": 0.0,
            "quality_label": "no_answer",
            "output_scores": {
                "exact_output_match": 0.0,
                "normalized_output_match": 0.0,
                "line_count_match": 0.0,
                "partial_line_match": 0.0,
                "trace_reasoning_quality": 0.0,
            },
            "output_error_type": "no_answer",
            "feedback": "No output prediction answer was provided.",
            "evidence": {
                "code": code,
                "expected_output": expected_raw,
                "learner_answer": answer_raw,
            },
        }

    exact_output_match = 0.0
    normalized_output_match = 0.0
    line_count_match = 0.0
    partial_line_match = 0.0
    trace_reasoning_quality = 0.0

    if expected and answer == expected:
        exact_output_match = 1.0

    if expected and _normalize_text(answer) == _normalize_text(expected):
        normalized_output_match = 1.0

    if expected_lines and len(expected_lines) == len(answer_lines):
        line_count_match = 1.0

    if expected_lines and answer_lines:
        normalized_expected = [_normalize_text(line) for line in expected_lines]
        normalized_answer = [_normalize_text(line) for line in answer_lines]

        matched_lines = sum(
            1
            for expected_line, answer_line in zip(normalized_expected, normalized_answer)
            if expected_line == answer_line
        )

        partial_line_match = matched_lines / max(1, len(normalized_expected))

    # Reasoning quality is optional. For pure answer-only output prediction,
    # exact answers can still get high score.
    reasoning_markers = [
        "because",
        "first",
        "then",
        "print",
        "stores",
        "variable",
        "value",
        "line",
    ]

    normalized_answer = _normalize_text(answer)
    if any(marker in normalized_answer for marker in reasoning_markers):
        trace_reasoning_quality = 0.7

    if exact_output_match or normalized_output_match:
        trace_reasoning_quality = max(trace_reasoning_quality, 0.8)

    if len(answer.split()) >= 8:
        trace_reasoning_quality = max(trace_reasoning_quality, 0.8)

    output_error_type = _classify_output_error(
        expected=expected,
        answer=answer,
        expected_lines=expected_lines,
        answer_lines=answer_lines,
    )

    output_scores = {
        "exact_output_match": round(exact_output_match, 4),
        "normalized_output_match": round(normalized_output_match, 4),
        "line_count_match": round(line_count_match, 4),
        "partial_line_match": round(partial_line_match, 4),
        "trace_reasoning_quality": round(trace_reasoning_quality, 4),
    }

    weights = {
        "exact_output_match": 0.35,
        "normalized_output_match": 0.25,
        "line_count_match": 0.15,
        "partial_line_match": 0.15,
        "trace_reasoning_quality": 0.10,
    }

    overall_score = sum(
        output_scores[key] * weight
        for key, weight in weights.items()
    )

    overall_score = round(max(0.0, min(1.0, overall_score)), 4)

    feedback_parts = []

    if output_scores["normalized_output_match"] < 1.0:
        feedback_parts.append("The predicted output does not match the expected output.")
    if output_scores["line_count_match"] < 1.0:
        feedback_parts.append("The number of output lines does not match.")
    if output_scores["partial_line_match"] < 0.5:
        feedback_parts.append("Line-by-line output tracing needs more practice.")
    if output_scores["trace_reasoning_quality"] < 0.5:
        feedback_parts.append("Add brief reasoning by tracing what each print statement produces.")

    if not feedback_parts:
        feedback_parts.append("Good output prediction with correct result.")

    return {
        "status": "success",
        "module": "OutputPredictionEvaluator",
        "assessment_type": "output_prediction",
        "overall_score": overall_score,
        "quality_label": _score_label(overall_score),
        "output_scores": output_scores,
        "output_error_type": output_error_type,
        "feedback": " ".join(feedback_parts),
        "evidence": {
            "code": code,
            "expected_output": expected_raw,
            "learner_answer": answer_raw,
        },
    }


def evaluate_output_predictions_from_assessment(
    assessment_output: Dict[str, Any],
    learner_answers: Dict[str, Any],
) -> Dict[str, Any]:
    questions = assessment_output.get("questions", [])

    results = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        q_type = (
            question.get("assessment_type")
            or question.get("question_type")
            or ""
        )

        if str(q_type).strip().lower() != "output_prediction":
            continue

        learner_answer = learner_answers.get("output_prediction", "")

        result = evaluate_output_prediction_answer(
            question=question,
            learner_answer=learner_answer,
        )

        results.append(
            {
                "question_id": question.get("question_id"),
                "learner_answer": learner_answer,
                **result,
            }
        )

    if not results:
        return {
            "status": "success",
            "module": "OutputPredictionEvaluator",
            "output_prediction_question_count": 0,
            "overall_score": None,
            "results": [],
            "reason": "No output prediction questions found.",
        }

    scores = [
        float(item.get("overall_score", 0.0) or 0.0)
        for item in results
    ]

    overall_score = round(sum(scores) / len(scores), 4)

    error_type_counts: Dict[str, int] = {}
    for item in results:
        error_type = item.get("output_error_type", "unknown")
        error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

    dominant_error_type = (
        max(error_type_counts, key=error_type_counts.get)
        if error_type_counts
        else None
    )

    return {
        "status": "success",
        "module": "OutputPredictionEvaluator",
        "output_prediction_question_count": len(results),
        "overall_score": overall_score,
        "quality_label": _score_label(overall_score),
        "dominant_output_error_type": dominant_error_type,
        "output_error_type_counts": error_type_counts,
        "results": results,
    }