from __future__ import annotations

import re
from typing import Any


def _normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip().lower())


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 6)


def _label(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.45:
        return "partial"
    return "weak"


def _feedback(puzzle_type: str, score: float) -> str:
    label = _label(score)
    if label == "strong":
        return f"Strong {puzzle_type} answer. Most structured checks passed."
    if label == "partial":
        return f"Partial {puzzle_type} answer. Some positions or matches need correction."
    return f"Weak {puzzle_type} answer. Review the concept and try the structured steps again."


def _extract_answer(learner_answer: Any, *keys: str) -> Any:
    if isinstance(learner_answer, dict):
        for key in keys:
            if key in learner_answer:
                return learner_answer[key]
    return learner_answer


def _score_fill_blank(puzzle: dict[str, Any], learner_answer: Any) -> tuple[float, dict[str, Any]]:
    expected = _as_list(puzzle.get("correct_answer") or puzzle.get("blanks"))
    answers = _as_list(_extract_answer(learner_answer, "blanks", "answers", "answer"))
    total = max(1, len(expected))
    correct = sum(
        1
        for index, expected_value in enumerate(expected)
        if index < len(answers) and _normalize(answers[index]) == _normalize(expected_value)
    )
    return correct / total, {"correct_blanks": correct, "total_blanks": total}


def _score_order(puzzle: dict[str, Any], learner_answer: Any) -> tuple[float, dict[str, Any]]:
    expected = [str(item) for item in _as_list(puzzle.get("correct_order"))]
    submitted = [str(item) for item in _as_list(_extract_answer(learner_answer, "order", "correct_order", "items"))]
    total = max(1, len(expected))
    correct_positions = sum(
        1
        for index, expected_id in enumerate(expected)
        if index < len(submitted) and submitted[index] == expected_id
    )
    score = correct_positions / total
    return score, {
        "correct_positions": correct_positions,
        "total_positions": total,
        "sequence_accuracy": _clamp(score),
    }


def _pair_key(pair: Any) -> tuple[str, str]:
    if isinstance(pair, dict):
        return str(pair.get("left_id") or pair.get("left")), str(pair.get("right_id") or pair.get("right"))
    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
        return str(pair[0]), str(pair[1])
    return str(pair), ""


def _score_pairs(puzzle: dict[str, Any], learner_answer: Any) -> tuple[float, dict[str, Any]]:
    expected = {_pair_key(pair) for pair in _as_list(puzzle.get("correct_answer"))}
    submitted = {_pair_key(pair) for pair in _as_list(_extract_answer(learner_answer, "pairs", "matches", "answer"))}
    total = max(1, len(expected))
    correct = len(expected.intersection(submitted))
    return correct / total, {"correct_pairs": correct, "total_pairs": total}


def _score_code_puzzle(puzzle: dict[str, Any], learner_answer: Any) -> tuple[float, dict[str, Any]]:
    expected_answer = puzzle.get("correct_answer")
    submitted = _extract_answer(learner_answer, "code", "answer", "completion")
    expected_output = puzzle.get("expected_output")
    code_snippet = puzzle.get("code_snippet") or ""

    normalized_match = _normalize(submitted) == _normalize(expected_answer)
    details: dict[str, Any] = {"normalized_answer_match": normalized_match}
    if expected_output and "____" in code_snippet:
        candidate_code = code_snippet.replace("____", str(submitted))
        try:
            from tutor.evaluation.code_runner import SafeCodeRunner

            run_result = SafeCodeRunner().run(candidate_code, expected_output=str(expected_output))
            details["safe_code_runner"] = run_result
            return float(run_result.get("score", 0.0)), details
        except Exception as exc:
            details["safe_code_runner_error"] = f"{type(exc).__name__}: {exc}"

    return (1.0 if normalized_match else 0.0), details


def _score_syntax_completion(puzzle: dict[str, Any], learner_answer: Any) -> tuple[float, dict[str, Any]]:
    expected = puzzle.get("correct_answer")
    submitted = _extract_answer(learner_answer, "completion", "answer", "syntax")
    match = _normalize(submitted) == _normalize(expected)
    return (1.0 if match else 0.0), {"normalized_completion_match": match}


SCORERS = {
    "fill_blank": _score_fill_blank,
    "arrange_steps": _score_order,
    "drag_order": _score_order,
    "match_pairs": _score_pairs,
    "code_puzzle": _score_code_puzzle,
    "syntax_completion": _score_syntax_completion,
}


def evaluate_puzzle_answer(puzzle: dict[str, Any], learner_answer: Any) -> dict[str, Any]:
    puzzle_type = str(puzzle.get("puzzle_type") or puzzle.get("question_type") or "")
    scorer = SCORERS.get(puzzle_type)
    if scorer is None:
        return {
            "status": "error",
            "question_type": "puzzle",
            "puzzle_type": puzzle_type,
            "score": 0.0,
            "label": "weak",
            "correct": False,
            "feedback": f"Unsupported puzzle type: {puzzle_type}",
            "mistake_type": "unsupported_puzzle_type",
            "details": {},
        }

    raw_score, details = scorer(puzzle, learner_answer)
    score = _clamp(raw_score)
    label = _label(score)
    return {
        "status": "success",
        "question_type": "puzzle",
        "puzzle_type": puzzle_type,
        "score": score,
        "label": label,
        "correct": score >= 0.8,
        "feedback": _feedback(puzzle_type, score),
        "mistake_type": None if score >= 0.8 else f"{puzzle_type}_structured_error",
        "details": details,
    }
