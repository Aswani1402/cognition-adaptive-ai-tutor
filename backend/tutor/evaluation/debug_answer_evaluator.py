from __future__ import annotations

from typing import Any, Dict, List


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize(value: Any) -> str:
    return _safe_str(value).lower().strip()


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _expected_fix_text(expected_answer: Any) -> str:
    if isinstance(expected_answer, dict):
        return _safe_str(
            expected_answer.get("expected_fix")
            or expected_answer.get("fix_text")
            or expected_answer.get("answer")
            or expected_answer.get("corrected_code")
            or ""
        )

    return _safe_str(expected_answer)


def _bug_category(question: Dict[str, Any]) -> str:
    metadata = question.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    expected = question.get("expected_answer", {})
    if not isinstance(expected, dict):
        expected = {}

    return _normalize(
        metadata.get("bug_category")
        or metadata.get("bug_type")
        or expected.get("bug_category")
        or expected.get("bug_type")
        or ""
    )


def _buggy_code(question: Dict[str, Any]) -> str:
    metadata = question.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return _safe_str(
        metadata.get("buggy_code")
        or question.get("buggy_code")
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


def evaluate_debug_answer(
    question: Dict[str, Any],
    learner_answer: Any,
) -> Dict[str, Any]:
    """
    Specialized evaluator for debug questions.

    It checks:
    - whether the learner detected a bug
    - whether the bug type was identified
    - whether the fix was explained
    - whether corrected code/fix is present
    - whether reasoning is specific enough
    """

    answer_raw = _safe_str(learner_answer)
    answer = _normalize(answer_raw)

    expected_fix_raw = _expected_fix_text(question.get("expected_answer"))
    expected_fix = _normalize(expected_fix_raw)

    bug_category = _bug_category(question)
    buggy_code = _buggy_code(question)

    if not answer:
        return {
            "status": "success",
            "module": "DebugAnswerEvaluator",
            "assessment_type": "debug",
            "overall_score": 0.0,
            "quality_label": "no_answer",
            "debug_scores": {
                "bug_detected": 0.0,
                "bug_type_identified": 0.0,
                "fix_explained": 0.0,
                "corrected_code_present": 0.0,
                "debug_reasoning_quality": 0.0,
            },
            "detected_bug_category": bug_category,
            "feedback": "No debug answer was provided.",
            "evidence": {
                "buggy_code": buggy_code,
                "expected_fix": expected_fix_raw,
                "learner_answer": answer_raw,
            },
        }

    bug_detected = 0.0
    bug_type_identified = 0.0
    fix_explained = 0.0
    corrected_code_present = 0.0
    debug_reasoning_quality = 0.0

    no_bug_markers = [
        "no mistake",
        "nothing wrong",
        "no error",
        "code is correct",
        "it is correct",
    ]

    if _contains_any(answer, no_bug_markers):
        bug_detected = 0.0
        bug_type_identified = 0.0
        fix_explained = 0.0
        corrected_code_present = 0.0
        debug_reasoning_quality = 0.0
    else:
        bug_detected = 1.0

    fix_markers = [
        "fix",
        "correct",
        "change",
        "replace",
        "add",
        "use",
        "should be",
        "missing",
    ]

    if _contains_any(answer, fix_markers):
        fix_explained = 0.7

    if bug_category == "string_syntax":
        quote_markers = [
            "quote",
            "quotes",
            "quotation",
            "string",
            "missing quote",
            "alice",
            "\"alice\"",
            "'alice'",
        ]

        if _contains_any(answer, quote_markers):
            bug_type_identified = 1.0
            fix_explained = max(fix_explained, 0.85)

        if "\"alice\"" in answer or "'alice'" in answer:
            corrected_code_present = 1.0

    elif bug_category in {"variable_name", "name_error", "undefined_variable"}:
        variable_markers = [
            "variable",
            "undefined",
            "nameerror",
            "name error",
            "wrong name",
            "same variable",
            "consistent",
        ]

        if _contains_any(answer, variable_markers):
            bug_type_identified = 1.0
            fix_explained = max(fix_explained, 0.85)

    elif bug_category in {"indentation", "indentation_error"}:
        indentation_markers = [
            "indent",
            "indentation",
            "space",
            "tab",
        ]

        if _contains_any(answer, indentation_markers):
            bug_type_identified = 1.0
            fix_explained = max(fix_explained, 0.85)

    elif bug_category in {"operator", "logic_error"}:
        logic_markers = [
            "operator",
            "logic",
            "condition",
            "comparison",
            "wrong calculation",
        ]

        if _contains_any(answer, logic_markers):
            bug_type_identified = 1.0
            fix_explained = max(fix_explained, 0.8)

    else:
        if bug_detected:
            bug_type_identified = 0.4

    if expected_fix and expected_fix in answer:
        corrected_code_present = 1.0
        fix_explained = max(fix_explained, 0.9)
        bug_type_identified = max(bug_type_identified, 0.9)

    if "\n" in answer_raw or "print(" in answer or "=" in answer:
        corrected_code_present = max(corrected_code_present, 0.6)

    word_count = len(answer.split())

    if word_count >= 12:
        debug_reasoning_quality = 1.0
    elif word_count >= 6:
        debug_reasoning_quality = 0.7
    elif word_count >= 3:
        debug_reasoning_quality = 0.45
    else:
        debug_reasoning_quality = 0.2

    vague_markers = [
        "there is a mistake",
        "something wrong",
        "maybe",
        "not sure",
        "i think",
    ]

    if _contains_any(answer, vague_markers):
        debug_reasoning_quality = min(debug_reasoning_quality, 0.45)
        fix_explained = min(fix_explained, 0.45)

    debug_scores = {
        "bug_detected": round(bug_detected, 4),
        "bug_type_identified": round(bug_type_identified, 4),
        "fix_explained": round(fix_explained, 4),
        "corrected_code_present": round(corrected_code_present, 4),
        "debug_reasoning_quality": round(debug_reasoning_quality, 4),
    }

    weights = {
        "bug_detected": 0.2,
        "bug_type_identified": 0.25,
        "fix_explained": 0.25,
        "corrected_code_present": 0.15,
        "debug_reasoning_quality": 0.15,
    }

    overall_score = sum(
        debug_scores[key] * weight
        for key, weight in weights.items()
    )

    overall_score = round(max(0.0, min(1.0, overall_score)), 4)

    feedback_parts = []

    if debug_scores["bug_detected"] < 0.5:
        feedback_parts.append("The answer does not identify that the code has a bug.")
    if debug_scores["bug_type_identified"] < 0.5:
        feedback_parts.append("The exact bug type is not identified clearly.")
    if debug_scores["fix_explained"] < 0.5:
        feedback_parts.append("The fix needs to be explained more clearly.")
    if debug_scores["corrected_code_present"] < 0.5:
        feedback_parts.append("A corrected code snippet or exact fix is missing.")
    if debug_scores["debug_reasoning_quality"] < 0.5:
        feedback_parts.append("The debugging reasoning is too vague.")

    if not feedback_parts:
        feedback_parts.append("Good debugging answer with clear bug identification and fix.")

    return {
        "status": "success",
        "module": "DebugAnswerEvaluator",
        "assessment_type": "debug",
        "overall_score": overall_score,
        "quality_label": _score_label(overall_score),
        "debug_scores": debug_scores,
        "detected_bug_category": bug_category,
        "feedback": " ".join(feedback_parts),
        "evidence": {
            "buggy_code": buggy_code,
            "expected_fix": expected_fix_raw,
            "learner_answer": answer_raw,
        },
    }


def evaluate_debug_answers_from_assessment(
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

        if str(q_type).strip().lower() not in {"debug", "debug_task"}:
            continue

        learner_answer = (
            learner_answers.get("debug")
            or learner_answers.get("debug_task")
            or ""
        )

        result = evaluate_debug_answer(
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
            "module": "DebugAnswerEvaluator",
            "debug_question_count": 0,
            "overall_score": None,
            "results": [],
            "reason": "No debug questions found.",
        }

    scores = [
        float(item.get("overall_score", 0.0) or 0.0)
        for item in results
    ]

    overall_score = round(sum(scores) / len(scores), 4)

    return {
        "status": "success",
        "module": "DebugAnswerEvaluator",
        "debug_question_count": len(results),
        "overall_score": overall_score,
        "quality_label": _score_label(overall_score),
        "results": results,
    }