from __future__ import annotations

import re
from typing import Any, Dict, List


SUPPORTED_STRUCTURED_EVALUATION_TYPES = [
    "syntax_completion",
    "fill_blank",
    "arrange_steps",
    "drag_order",
    "match_pairs",
    "code_puzzle",
    "code_writing",
    "challenge",
]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _normalize_text(value: Any) -> str:
    text = _safe_str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("'", '"')
    return text


def _token_set(value: Any) -> set[str]:
    text = _normalize_text(value)
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|\d+", text))


def _score_exact_or_contains(learner_answer: Any, expected: Any) -> float:
    learner = _normalize_text(learner_answer)
    expected_text = _normalize_text(expected)

    if not learner or not expected_text:
        return 0.0

    if learner == expected_text:
        return 1.0

    if expected_text in learner:
        return 0.85

    if learner in expected_text and len(learner) >= 3:
        return 0.65

    learner_tokens = _token_set(learner)
    expected_tokens = _token_set(expected_text)

    if not expected_tokens:
        return 0.0

    overlap = len(learner_tokens & expected_tokens) / len(expected_tokens)
    return round(min(overlap, 1.0), 4)


def _label_from_score(score: float) -> str:
    if score >= 0.85:
        return "correct"
    if score >= 0.5:
        return "partial"
    return "incorrect"


def evaluate_syntax_completion(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected = question.get("expected_answer")
    score = _score_exact_or_contains(learner_answer, expected)

    return {
        "assessment_type": "syntax_completion",
        "score": score,
        "is_correct": score >= 0.85,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Syntax completion is correct."
            if score >= 0.85
            else f"Expected missing syntax: {expected}"
        ),
    }


def evaluate_fill_blank(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    blanks = expected_answer.get("blanks", []) if isinstance(expected_answer, dict) else []

    if not isinstance(blanks, list):
        blanks = [blanks]

    if isinstance(learner_answer, list):
        learner_values = learner_answer
    else:
        learner_values = [_safe_str(learner_answer)]

    if not blanks:
        score = 0.0
    else:
        scores = []
        for idx, expected_blank in enumerate(blanks):
            learner_value = learner_values[idx] if idx < len(learner_values) else ""
            scores.append(_score_exact_or_contains(learner_value, expected_blank))

        score = round(sum(scores) / len(scores), 4)

    return {
        "assessment_type": "fill_blank",
        "score": score,
        "is_correct": score >= 0.85,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Fill-in-the-blank answer is correct."
            if score >= 0.85
            else f"Expected blank value(s): {blanks}"
        ),
    }


def evaluate_ordered_items(
    question: Dict[str, Any],
    learner_answer: Any,
    assessment_type: str,
) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    correct_order = expected_answer.get("correct_order", []) if isinstance(expected_answer, dict) else []

    if not isinstance(correct_order, list):
        correct_order = []

    if isinstance(learner_answer, list):
        learner_order = learner_answer
    else:
        learner_order = []

    if not correct_order:
        score = 0.0
    elif learner_order == correct_order:
        score = 1.0
    else:
        correct_positions = 0
        for idx, expected_item in enumerate(correct_order):
            if idx < len(learner_order) and learner_order[idx] == expected_item:
                correct_positions += 1

        score = round(correct_positions / len(correct_order), 4)

    return {
        "assessment_type": assessment_type,
        "score": score,
        "is_correct": score >= 0.85,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Ordering is correct."
            if score >= 0.85
            else f"Expected order: {correct_order}"
        ),
    }


def evaluate_drag_order(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    return evaluate_ordered_items(question, learner_answer, assessment_type="drag_order")


def evaluate_arrange_steps(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    return evaluate_ordered_items(question, learner_answer, assessment_type="arrange_steps")


def evaluate_match_pairs(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    pairs = expected_answer.get("pairs", []) if isinstance(expected_answer, dict) else []
    correct_pairs = expected_answer.get("correct_pairs", []) if isinstance(expected_answer, dict) else []

    if not isinstance(pairs, list):
        pairs = []
    if not isinstance(correct_pairs, list):
        correct_pairs = []

    if isinstance(learner_answer, list) and correct_pairs:
        normalized_expected = {tuple(item) for item in correct_pairs if isinstance(item, list) and len(item) == 2}
        normalized_learner = {tuple(item) for item in learner_answer if isinstance(item, list) and len(item) == 2}
        score = round(len(normalized_expected & normalized_learner) / len(normalized_expected), 4) if normalized_expected else 0.0
        return {
            "assessment_type": "match_pairs",
            "score": score,
            "is_correct": score >= 0.85,
            "quality_label": _label_from_score(score),
            "feedback": (
                "Matched pairs are correct."
                if score >= 0.85
                else "Some pairs do not match the expected meanings."
            ),
        }

    expected_map = {
        _normalize_text(pair.get("left")): _normalize_text(pair.get("right"))
        for pair in pairs
        if isinstance(pair, dict)
    }

    if isinstance(learner_answer, dict):
        learner_map = {
            _normalize_text(k): _normalize_text(v)
            for k, v in learner_answer.items()
        }
    elif isinstance(learner_answer, list):
        learner_map = {
            _normalize_text(item.get("left")): _normalize_text(item.get("right"))
            for item in learner_answer
            if isinstance(item, dict)
        }
    else:
        learner_map = {}

    if not expected_map:
        score = 0.0
    else:
        correct = 0
        for left, expected_right in expected_map.items():
            if learner_map.get(left) == expected_right:
                correct += 1

        score = round(correct / len(expected_map), 4)

    return {
        "assessment_type": "match_pairs",
        "score": score,
        "is_correct": score >= 0.85,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Matched pairs are correct."
            if score >= 0.85
            else "Some pairs do not match the expected meanings."
        ),
    }


def evaluate_code_writing(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    expected_features = (
        expected_answer.get("expected_features", [])
        if isinstance(expected_answer, dict)
        else []
    )

    if not isinstance(expected_features, list):
        expected_features = [expected_features]

    answer_text = _normalize_text(learner_answer)
    raw_answer = _safe_str(learner_answer)

    feature_scores = []

    for feature in expected_features:
        feature_text = _normalize_text(feature)

        if "assignment" in feature_text or "uses variables" in feature_text or "uses correct syntax" in feature_text:
            feature_scores.append(1.0 if "=" in raw_answer else 0.0)
        elif "print" in feature_text or "produces" in feature_text:
            feature_scores.append(1.0 if "print(" in answer_text or "return" in answer_text else 0.0)
        elif "calculation" in feature_text:
            feature_scores.append(1.0 if any(op in raw_answer for op in ["+", "-", "*", "/", "%"]) else 0.0)
        elif "explains" in feature_text or "reasoning" in feature_text:
            feature_scores.append(1.0 if len(answer_text.split()) >= 8 else 0.0)
        else:
            feature_scores.append(_score_exact_or_contains(answer_text, feature_text))

    if not feature_scores:
        score = 0.0
    else:
        score = round(sum(feature_scores) / len(feature_scores), 4)

    return {
        "assessment_type": "code_writing",
        "score": score,
        "is_correct": score >= 0.75,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Code writing answer satisfies the expected features."
            if score >= 0.75
            else f"Expected features: {expected_features}"
        ),
    }


def evaluate_code_puzzle(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    expected_code = (
        expected_answer.get("answer", "")
        if isinstance(expected_answer, dict)
        else expected_answer
    )
    score = _score_exact_or_contains(learner_answer, expected_code)

    return {
        "assessment_type": "code_puzzle",
        "score": score,
        "is_correct": score >= 0.85,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Code puzzle answer is correct."
            if score >= 0.85
            else f"Expected missing code: {expected_code}"
        ),
    }


def evaluate_challenge(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    expected_answer = question.get("expected_answer", {})
    success_criteria = (
        expected_answer.get("success_criteria", [])
        if isinstance(expected_answer, dict)
        else []
    )

    if not isinstance(success_criteria, list):
        success_criteria = [success_criteria]

    answer_text = _normalize_text(learner_answer)

    if not success_criteria:
        score = 0.0
    else:
        scores = []
        for criterion in success_criteria:
            criterion_text = _normalize_text(criterion)

            if "example" in criterion_text:
                scores.append(1.0 if len(answer_text.split()) >= 6 else 0.0)
            elif "explains" in criterion_text or "reasoning" in criterion_text:
                scores.append(1.0 if len(answer_text.split()) >= 10 else 0.0)
            elif "uses the concept" in criterion_text:
                scores.append(1.0 if len(answer_text.split()) >= 5 else 0.0)
            else:
                scores.append(_score_exact_or_contains(answer_text, criterion_text))

        score = round(sum(scores) / len(scores), 4)

    return {
        "assessment_type": "challenge",
        "score": score,
        "is_correct": score >= 0.7,
        "quality_label": _label_from_score(score),
        "feedback": (
            "Challenge response satisfies the success criteria."
            if score >= 0.7
            else f"Expected success criteria: {success_criteria}"
        ),
    }


def evaluate_structured_answer(
    question: Dict[str, Any],
    learner_answer: Any,
) -> Dict[str, Any]:
    question_type = question.get("question_type") or question.get("assessment_type")

    if question_type == "syntax_completion":
        result = evaluate_syntax_completion(question, learner_answer)
    elif question_type == "fill_blank":
        result = evaluate_fill_blank(question, learner_answer)
    elif question_type == "arrange_steps":
        result = evaluate_arrange_steps(question, learner_answer)
    elif question_type == "drag_order":
        result = evaluate_drag_order(question, learner_answer)
    elif question_type == "match_pairs":
        result = evaluate_match_pairs(question, learner_answer)
    elif question_type == "code_puzzle":
        result = evaluate_code_puzzle(question, learner_answer)
    elif question_type == "code_writing":
        result = evaluate_code_writing(question, learner_answer)
    elif question_type == "challenge":
        result = evaluate_challenge(question, learner_answer)
    else:
        result = {
            "assessment_type": question_type,
            "score": 0.0,
            "is_correct": False,
            "quality_label": "unsupported",
            "feedback": f"Unsupported structured question type: {question_type}",
        }

    result.update(
        {
            "question_id": question.get("question_id"),
            "question_type": question_type,
            "prompt": question.get("prompt"),
            "learner_answer": learner_answer,
            "expected_answer": question.get("expected_answer"),
            "frontend_component": question.get("frontend_component"),
            "render_mode": (
                question.get("metadata", {}).get("render_mode")
                if isinstance(question.get("metadata"), dict)
                else None
            ),
            "method": "structured_rule_evaluator",
        }
    )

    return result


def evaluate_structured_answer_batch(
    questions: List[Dict[str, Any]],
    learner_answers: Dict[str, Any],
) -> Dict[str, Any]:
    results = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        question_id = question.get("question_id")
        question_type = question.get("question_type") or question.get("assessment_type")

        learner_answer = None

        if isinstance(learner_answers, dict):
            learner_answer = learner_answers.get(question_id)

            if learner_answer is None:
                learner_answer = learner_answers.get(question_type)

        result = evaluate_structured_answer(
            question=question,
            learner_answer=learner_answer,
        )

        results.append(result)

    total_score = sum(float(result.get("score", 0.0)) for result in results)
    max_score = len(results)
    overall_score = round(total_score / max_score, 4) if max_score else 0.0

    weak_types = [
        result.get("assessment_type")
        for result in results
        if float(result.get("score", 0.0)) < 0.5
    ]

    strong_types = [
        result.get("assessment_type")
        for result in results
        if float(result.get("score", 0.0)) >= 0.85
    ]

    if overall_score >= 0.85:
        verdict = "strong"
    elif overall_score >= 0.6:
        verdict = "partial"
    else:
        verdict = "needs_review"

    return {
        "status": "success",
        "module": "StructuredAnswerEvaluator",
        "results": results,
        "total_score": round(total_score, 4),
        "max_score": max_score,
        "overall_score": overall_score,
        "verdict": verdict,
        "weak_assessment_types": weak_types,
        "strong_assessment_types": strong_types,
        "feedback_summary": (
            "Structured answers evaluated successfully."
            if not weak_types
            else f"Needs improvement in: {weak_types}"
        ),
    }
