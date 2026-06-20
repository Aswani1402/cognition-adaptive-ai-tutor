from __future__ import annotations

from typing import Any, Dict, List


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize(text: Any) -> str:
    return _safe_str(text).lower().strip()


def _canonical_type(q_type: str) -> str:
    q_type = _safe_str(q_type).strip().lower()

    aliases = {
        "short_explanation": "explanation",
        "explanation": "explanation",
        "debug_task": "debug",
        "debug": "debug",
        "output_prediction": "output_prediction",
        "mcq": "mcq",
        "transfer": "transfer",
        "code_writing": "code_writing",
        "syntax_completion": "syntax_completion",
    }

    return aliases.get(q_type, q_type)


def _expected_text(expected_answer: Any) -> str:
    if isinstance(expected_answer, dict):
        return _safe_str(
            expected_answer.get("fix_text")
            or expected_answer.get("expected_fix")
            or expected_answer.get("answer")
            or expected_answer.get("output")
            or expected_answer.get("value")
            or ""
        )

    return _safe_str(expected_answer)


def _question_type(question: Dict[str, Any]) -> str:
    return _safe_str(
        question.get("assessment_type") or question.get("question_type"),
        "unknown",
    )


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_mistake_type(
    question: Dict[str, Any],
    learner_answer: Any,
    score: float | None = None,
) -> Dict[str, Any]:
    """
    Classifies learner mistake type from question + answer + optional score.

    This is a baseline classifier.
    Later this can be replaced by a trained mistake classifier.
    """

    raw_q_type = _question_type(question)
    q_type = _canonical_type(raw_q_type)

    answer_raw = _safe_str(learner_answer)
    answer = _normalize(answer_raw)
    expected = _normalize(_expected_text(question.get("expected_answer")))
    prompt = _normalize(question.get("prompt") or question.get("question"))
    metadata = (
        question.get("metadata", {})
        if isinstance(question.get("metadata"), dict)
        else {}
    )

    try:
        numeric_score = float(score) if score is not None else None
    except Exception:
        numeric_score = None

    if not answer:
        return {
            "mistake_type": "no_answer",
            "severity": "high",
            "reason": "Learner did not provide an answer.",
        }

    # Score-based override must happen early so high-score answers are not
    # incorrectly marked as vague because they are short but correct.
    if numeric_score is not None:
        if numeric_score >= 0.85:
            return {
                "mistake_type": "correct",
                "severity": "none",
                "reason": "Score is high.",
            }

    low_confidence_markers = [
        "not sure",
        "maybe",
        "i think",
        "i don't know",
        "dont know",
        "don't know",
        "no idea",
    ]

    if _contains_any(answer, low_confidence_markers):
        if numeric_score is not None and numeric_score >= 0.7:
            return {
                "mistake_type": "low_confidence_correct",
                "severity": "low",
                "reason": "Answer is likely correct but learner expressed low confidence.",
            }

        return {
            "mistake_type": "low_confidence",
            "severity": "medium",
            "reason": "Learner used uncertainty markers.",
        }

    if numeric_score is not None and 0.45 <= numeric_score < 0.85:
        return {
            "mistake_type": "partial",
            "severity": "medium",
            "reason": "Score indicates partial understanding.",
        }

    unrelated_markers = [
        "loop",
        "class",
        "html",
        "sql",
        "database",
        "branch",
        "commit",
    ]

    if q_type in {"explanation", "transfer"}:
        if _contains_any(answer, unrelated_markers) and not _contains_any(
            prompt + " " + expected,
            unrelated_markers,
        ):
            return {
                "mistake_type": "unrelated_answer",
                "severity": "high",
                "reason": "Answer appears unrelated to the current concept.",
            }

    if q_type == "output_prediction":
        if expected and answer != expected:
            return {
                "mistake_type": "wrong_output",
                "severity": "high",
                "reason": "Learner predicted an output different from the expected output.",
            }

    if q_type == "debug":
        bug_category = _normalize(
            metadata.get("bug_category") or metadata.get("bug_type")
        )

        if "no mistake" in answer or "nothing wrong" in answer:
            return {
                "mistake_type": "debug_misdiagnosis",
                "severity": "high",
                "reason": "Learner failed to detect that the code contains a bug.",
            }

        if bug_category == "string_syntax":
            quote_markers = ["quote", "quotes", "string", '"', "'"]
            if not _contains_any(answer, quote_markers):
                return {
                    "mistake_type": "syntax_misunderstanding",
                    "severity": "high",
                    "reason": "Expected string/quote syntax issue, but learner diagnosed a different issue.",
                }

        if expected and expected not in answer:
            return {
                "mistake_type": "debug_partial_or_wrong_fix",
                "severity": "medium",
                "reason": "Learner noticed a bug but did not provide the expected fix.",
            }

    if q_type == "mcq":
        options = question.get("options") or []
        correct_index = question.get("correct_option_index")

        if isinstance(correct_index, int) and 0 <= correct_index < len(options):
            correct_option = _normalize(options[correct_index])
            if answer != correct_option:
                return {
                    "mistake_type": "wrong_mcq_choice",
                    "severity": "medium",
                    "reason": "Learner selected an incorrect MCQ option.",
                }

    misconception_markers = [
        "changing thing",
        "only for advanced",
        "used before assignment",
        "same as constant",
        "stores directly",
    ]

    if _contains_any(answer, misconception_markers):
        return {
            "mistake_type": "concept_misconception",
            "severity": "high",
            "reason": "Answer contains a known misconception.",
        }

    vague_markers = [
        "something",
        "thing",
        "there is a mistake",
        "used in coding",
        "value",
    ]

    if len(answer.split()) <= 4 or _contains_any(answer, vague_markers):
        return {
            "mistake_type": "vague_answer",
            "severity": "medium",
            "reason": "Answer is too vague to show complete understanding.",
        }

    if numeric_score is not None and numeric_score < 0.45:
        return {
            "mistake_type": "incorrect_unknown",
            "severity": "high",
            "reason": "Low score but no specific mistake pattern matched.",
        }

    return {
        "mistake_type": "uncertain",
        "severity": "medium",
        "reason": "No clear mistake pattern matched.",
    }


def classify_mistakes_for_evaluation(
    assessment_output: Dict[str, Any],
    learner_answers: Dict[str, Any],
    evaluation_output: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    questions = assessment_output.get("questions", [])
    results = (
        evaluation_output.get("results", [])
        if isinstance(evaluation_output, dict)
        else []
    )

    score_by_type: Dict[str, float] = {}

    for result in results:
        if not isinstance(result, dict):
            continue

        raw_type = _safe_str(
            result.get("assessment_type") or result.get("question_type")
        )
        q_type = _canonical_type(raw_type)

        try:
            score_by_type[q_type] = float(result.get("score", 0.0))
        except Exception:
            score_by_type[q_type] = 0.0

    classified = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        raw_q_type = _question_type(question)
        q_type = _canonical_type(raw_q_type)

        learner_answer = (
            learner_answers.get(raw_q_type)
            or learner_answers.get(q_type)
            or ""
        )

        score = score_by_type.get(q_type)

        classification = classify_mistake_type(
            question=question,
            learner_answer=learner_answer,
            score=score,
        )

        classified.append(
            {
                "assessment_type": raw_q_type,
                "canonical_assessment_type": q_type,
                "learner_answer": learner_answer,
                "score": score,
                **classification,
            }
        )

    high_severity = [
        item for item in classified
        if item.get("severity") == "high"
    ]

    medium_or_high = [
        item for item in classified
        if item.get("severity") in {"medium", "high"}
    ]

    mistake_type_counts: Dict[str, int] = {}
    for item in classified:
        mistake_type = item.get("mistake_type", "unknown")
        mistake_type_counts[mistake_type] = mistake_type_counts.get(mistake_type, 0) + 1

    severe_counts: Dict[str, int] = {}

    for item in classified:
        mistake_type = item.get("mistake_type", "unknown")
        severity = item.get("severity")

        if mistake_type in {"correct", "low_confidence_correct"}:
            continue

        if severity in {"high", "medium"}:
            severe_counts[mistake_type] = severe_counts.get(mistake_type, 0) + 1

    non_correct_counts = {
        key: value
        for key, value in mistake_type_counts.items()
        if key not in {"correct", "low_confidence_correct"}
    }

    dominant_mistake_type = (
        max(severe_counts, key=severe_counts.get)
        if severe_counts
        else (
            max(non_correct_counts, key=non_correct_counts.get)
            if non_correct_counts
            else (
                max(mistake_type_counts, key=mistake_type_counts.get)
                if mistake_type_counts
                else None
            )
        )
    )

    return {
        "status": "success",
        "module": "MistakeTypeClassifier",
        "classified_mistakes": classified,
        "mistake_type_counts": mistake_type_counts,
        "high_severity_count": len(high_severity),
        "medium_or_high_count": len(medium_or_high),
        "dominant_mistake_type": dominant_mistake_type,
    }