from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from typing import Any

from tutor.evaluation.semantic_evaluator import (
    evaluate_semantic_explanation,
    evaluate_semantic_transfer,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().strip().split())


def keyword_overlap_score(answer: str, expected_points: list[str]) -> tuple[float, list[str], list[str]]:
    answer_norm = normalize_text(answer)
    if not answer_norm or not expected_points:
        return 0.0, [], expected_points or []

    matched_points: list[str] = []
    missing_points: list[str] = []

    for point in expected_points:
        point_norm = normalize_text(point)
        point_words = [w for w in point_norm.split() if len(w) > 2]

        if not point_words:
            missing_points.append(point)
            continue

        hit_count = sum(1 for w in point_words if w in answer_norm)
        required_hits = max(1, len(point_words) // 2)

        if hit_count >= required_hits:
            matched_points.append(point)
        else:
            missing_points.append(point)

    score = len(matched_points) / max(1, len(expected_points))
    return round(score, 3), matched_points, missing_points


def text_similarity(a: Any, b: Any) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def mcq_semantic_similarity(learner_answer: Any, expected_answer: Any) -> float:
    learner = normalize_text(learner_answer)
    expected = normalize_text(expected_answer)
    if not learner or not expected:
        return 0.0

    learner_tokens = set(re.findall(r"[a-z0-9_]+", learner))
    expected_tokens = set(re.findall(r"[a-z0-9_]+", expected))
    if not learner_tokens or not expected_tokens:
        return 0.0

    synonyms = {
        "store": {"store", "stores", "stored", "storage", "hold", "holds", "holding"},
        "value": {"value", "values", "data", "information"},
        "name": {"name", "named", "label", "variable"},
        "variable": {"variable", "variables", "name", "named"},
    }

    def has_family(tokens: set[str], family: set[str]) -> bool:
        return bool(tokens & family)

    family_hits = 0
    family_total = 0
    for family in synonyms.values():
        if has_family(expected_tokens, family):
            family_total += 1
            if has_family(learner_tokens, family):
                family_hits += 1

    overlap = len(learner_tokens & expected_tokens) / max(1, len(expected_tokens))
    family_score = family_hits / max(1, family_total)
    return max(overlap, family_score)


def ensure_expected_points(expected_answer: Any) -> list[str]:
    if expected_answer is None:
        return []

    if isinstance(expected_answer, list):
        return [str(x).strip() for x in expected_answer if str(x).strip()]

    if isinstance(expected_answer, dict):
        values = []
        for v in expected_answer.values():
            if isinstance(v, list):
                values.extend(str(x).strip() for x in v if str(x).strip())
            elif v is not None and str(v).strip():
                values.append(str(v).strip())
        return values

    text = str(expected_answer).strip()
    if not text:
        return []

    # split on newline first, fallback to sentences
    if "\n" in text:
        parts = [p.strip("-• ").strip() for p in text.splitlines() if p.strip()]
        return [p for p in parts if p]

    if " - " in text or "; " in text:
        parts = re.split(r"\s*;\s+|\s+-\s+", text)
        parts = [p.strip("-• ").strip() for p in parts if p.strip()]
        if len(parts) > 1:
            return parts

    if ". " in text:
        parts = [p.strip() for p in text.split(". ") if p.strip()]
        return [p for p in parts if p]

    return [text]


def evaluate_mcq(
    learner_answer: str,
    expected_answer: str,
    options: list[str] | None = None,
    correct_option_index: int | None = None,
) -> dict[str, Any]:
    sim = text_similarity(learner_answer, expected_answer)
    semantic_sim = mcq_semantic_similarity(learner_answer, expected_answer)

    if sim >= 0.75 or semantic_sim >= 0.75:
        return {
            "score": 1.0,
            "is_correct": True,
            "quality_label": "correct",
            "feedback": "Correct answer."
        }

    elif sim >= 0.5 or semantic_sim >= 0.5:
        return {
            "score": 0.5,
            "is_correct": False,
            "quality_label": "partial",
            "feedback": f"Partially correct. Expected: {expected_answer}"
        }

    else:
        return {
            "score": 0.0,
            "is_correct": False,
            "quality_label": "incorrect",
            "feedback": f"Expected answer: {expected_answer}"
        }


def evaluate_output_prediction(learner_answer: str, expected_answer: str) -> dict[str, Any]:
    learner = normalize_text(learner_answer)
    expected = normalize_text(expected_answer)

    is_correct = learner == expected

    return {
        "score": 1.0 if is_correct else 0.0,
        "is_correct": is_correct,
        "quality_label": "correct" if is_correct else "incorrect",
        "feedback": "Correct output." if is_correct else f"Expected output: {expected_answer}",
    }


def evaluate_explanation(learner_answer: str, expected_points: list[str]) -> dict[str, Any]:
    if expected_points:
        return evaluate_semantic_explanation(learner_answer, expected_points)

    return {
        "score": 0.0,
        "is_correct": False,
        "quality_label": "insufficient_reference",
        "feedback": "No expected explanation points available.",
    }


def evaluate_transfer(learner_answer: str, expected_points: list[str]) -> dict[str, Any]:
    if expected_points:
        return evaluate_semantic_transfer(learner_answer, expected_points)

    return {
        "score": 0.0,
        "is_correct": False,
        "quality_label": "insufficient_reference",
        "feedback": "No expected transfer points available.",
    }


def evaluate_debug(learner_answer: str, expected_answer: Any) -> dict[str, Any]:
    if isinstance(expected_answer, dict):
        expected_text = expected_answer.get("fix_text", "")
    else:
        expected_text = str(expected_answer)

    sim = text_similarity(learner_answer, expected_text)

    if sim >= 0.75:
        score = 1.0
        label = "correct"
        feedback = "Correct debugging answer."
    elif sim >= 0.4:
        score = 0.5
        label = "partial"
        feedback = f"Partially correct. Expected fix: {expected_text}"
    else:
        score = 0.0
        label = "incorrect"
        feedback = f"Expected fix: {expected_text}"

    return {
        "score": score,
        "is_correct": score >= 0.75,
        "quality_label": label,
        "feedback": feedback,
    }


def evaluate_assessment_item(item: dict[str, Any], learner_answer: str) -> dict[str, Any]:
    assessment_type = item.get("assessment_type", "")

    if assessment_type == "mcq":
        result = evaluate_mcq(
            learner_answer=learner_answer,
            expected_answer=item.get("expected_answer", ""),
            options=item.get("options"),
            correct_option_index=item.get("correct_option_index"),
        )

    elif assessment_type == "output_prediction":
        result = evaluate_output_prediction(
            learner_answer,
            item.get("expected_answer", ""),
        )

    elif assessment_type == "explanation":
        expected_points = item.get("expected_points")
        if not expected_points:
            expected_points = ensure_expected_points(item.get("expected_answer", ""))
        result = evaluate_explanation(learner_answer, expected_points)

    elif assessment_type == "transfer":
        expected_points = item.get("expected_points")
        if not expected_points:
            expected_points = ensure_expected_points(item.get("expected_answer", ""))
        result = evaluate_transfer(learner_answer, expected_points)

    elif assessment_type == "debug":
        result = evaluate_debug(learner_answer, item.get("expected_answer", ""))

    else:
        result = {
            "score": 0.0,
            "is_correct": False,
            "quality_label": "unsupported",
            "feedback": f"Unsupported assessment type: {assessment_type}",
        }

    return {
        "assessment_type": assessment_type,
        "prompt": item.get("prompt", item.get("question", "")),
        "learner_answer": learner_answer,
        "expected_answer": item.get("expected_answer", ""),
        **result,
    }


def derive_bundle_verdict(overall_score: float) -> str:
    if overall_score >= 0.8:
        return "ready_to_progress"
    if overall_score >= 0.5:
        return "needs_light_review"
    return "needs_reteaching"


def build_feedback_summary(results: list[dict[str, Any]]) -> str:
    weak_types = [
        r.get("assessment_type", "")
        for r in results
        if float(r.get("score", 0.0)) < 0.5
    ]

    if not weak_types:
        return "Good overall performance across the assessment."

    weak_types = list(dict.fromkeys(weak_types))
    return "Needs improvement in: " + ", ".join(weak_types)


def evaluate_assessment_bundle(
    assessment_bundle: dict[str, Any],
    learner_answers: dict[str, str],
) -> dict[str, Any]:
    """
    Supports BOTH:
    - old format: assessment_bundle["assessment_items"]
    - new format: assessment_bundle["questions"]
    """

    items = assessment_bundle.get("assessment_items")
    if items is None:
        items = assessment_bundle.get("questions", [])

    results: list[dict[str, Any]] = []
    total_score = 0.0

    for item in items:
        item_type = item.get("assessment_type", "")

        # map explanation key correctly
        learner_answer = learner_answers.get(item_type, "")

        # fallback aliases
        if not learner_answer and item_type == "explanation":
            learner_answer = learner_answers.get("short_explanation", "")
        if not learner_answer and item_type == "debug":
            learner_answer = learner_answers.get("debug", "")

        evaluated_item = evaluate_assessment_item(item, learner_answer)
        results.append(evaluated_item)
        total_score += float(evaluated_item.get("score", 0.0))

    max_score = float(len(items)) if items else 1.0
    overall_score = round(total_score / max_score, 3) if max_score > 0 else 0.0
    verdict = derive_bundle_verdict(overall_score)
    feedback_summary = build_feedback_summary(results)

    return {
        "status": "success",
        "system_concept_id": assessment_bundle.get("system_concept_id", assessment_bundle.get("concept_id", "")),
        "concept_name": assessment_bundle.get("concept_name", ""),
        "domain": assessment_bundle.get("domain", ""),
        "difficulty": assessment_bundle.get("difficulty", ""),
        "results": results,
        "total_score": round(total_score, 3),
        "max_score": round(max_score, 3),
        "overall_score": overall_score,
        "verdict": verdict,
        "feedback_summary": feedback_summary,
        "evaluated_at": now_iso(),
    }


if __name__ == "__main__":
    sample_bundle = {
        "concept_id": "1",
        "concept_name": "Variables",
        "difficulty": "easy",
        "questions": [
            {
                "assessment_type": "mcq",
                "prompt": "What is a variable in Python?",
                "expected_answer": "A named place used to store a value",
                "options": [
                    "A named place used to store a value",
                    "A loop statement",
                    "A file path",
                    "A class object",
                ],
                "correct_option_index": 0,
            },
            {
                "assessment_type": "explanation",
                "prompt": "Explain variables in Python in your own words.",
                "expected_answer": "A variable stores a value and can be reused later in a program.",
            },
            {
                "assessment_type": "output_prediction",
                "prompt": "What is the output of: x = 5; print(x)",
                "expected_answer": "5",
            },
            {
                "assessment_type": "transfer",
                "prompt": "How would you apply variables in a real program?",
                "expected_answer": "Variables can be used to store names, marks, prices, and settings in a program.",
            },
            {
                "assessment_type": "debug",
                "prompt": "Find the mistake.",
                "expected_answer": {"fix_text": "Use the correct variable name x instead of x1."},
            },
        ],
    }

    sample_answers = {
        "mcq": "A named place used to store a value",
        "explanation": "A variable stores a value and can be used later. Example: x = 5",
        "output_prediction": "5",
        "transfer": "We can use variables to store marks, names, and prices in a program.",
        "debug": "Use x instead of x1.",
    }

    import json
    print(json.dumps(evaluate_assessment_bundle(sample_bundle, sample_answers), indent=2))
