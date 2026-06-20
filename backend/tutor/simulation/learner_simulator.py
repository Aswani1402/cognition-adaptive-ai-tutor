from __future__ import annotations

import random
from typing import Any


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(str(text).strip().lower().split())


def pick_with_probability(probability_true: float) -> bool:
    return random.random() < probability_true


def build_explanation_from_points(
    expected_points: list[str],
    quality: str = "partial",
) -> str:
    if not expected_points:
        return "I am not sure."

    if quality == "strong":
        return " ".join(expected_points)

    if quality == "partial":
        take_n = max(1, len(expected_points) // 2)
        chosen = expected_points[:take_n]
        return " ".join(chosen)

    return "I do not know clearly."


def build_transfer_from_points(
    expected_points: list[str],
    quality: str = "partial",
) -> str:
    if not expected_points:
        return "I am not sure how to apply it."

    if quality == "strong":
        return " ".join(expected_points)

    if quality == "partial":
        return expected_points[0]

    return "I cannot apply it properly."


def incorrect_mcq_answer(options: list[str], expected_answer: str) -> str:
    expected_norm = normalize_text(expected_answer)
    for option in options:
        if normalize_text(option) != expected_norm:
            return option
    return options[0] if options else ""


def incorrect_output_answer(expected_answer: str) -> str:
    expected_norm = normalize_text(expected_answer)

    simple_map = {
        "5": "10",
        "7": "5",
        "10": "20",
        "15": "5",
        "alice": "Bob",
        "true": "false",
        "false": "true",
    }

    if expected_norm in simple_map:
        return simple_map[expected_norm]

    return "0"


def simulate_item_answer(
    item: dict[str, Any],
    learner_profile: str = "average",
) -> str:
    assessment_type = item.get("assessment_type", "")
    expected_answer = item.get("expected_answer", "")
    expected_points = item.get("expected_points", [])
    options = item.get("options", [])

    profile = normalize_text(learner_profile)

    if profile == "strong":
        correct_prob = 1.0
        partial_prob = 0.0
    elif profile == "weak":
        correct_prob = 0.20
        partial_prob = 0.30
    else:
        correct_prob = 0.55
        partial_prob = 0.30

    if assessment_type == "mcq":
        if pick_with_probability(correct_prob):
            return expected_answer
        return incorrect_mcq_answer(options, expected_answer)

    if assessment_type == "output_prediction":
        if pick_with_probability(correct_prob):
            return expected_answer
        return incorrect_output_answer(expected_answer)

    if assessment_type == "explanation":
        if pick_with_probability(correct_prob):
            return build_explanation_from_points(expected_points, quality="strong")
        if pick_with_probability(partial_prob):
            return build_explanation_from_points(expected_points, quality="partial")
        return build_explanation_from_points(expected_points, quality="weak")

    if assessment_type == "transfer":
        if pick_with_probability(correct_prob):
            return build_transfer_from_points(expected_points, quality="strong")
        if pick_with_probability(partial_prob):
            return build_transfer_from_points(expected_points, quality="partial")
        return build_transfer_from_points(expected_points, quality="weak")

    return ""


def simulate_learner_answers(
    assessment_bundle: dict[str, Any],
    learner_profile: str = "average",
) -> dict[str, str]:
    items = assessment_bundle.get("assessment_items", [])
    answers: dict[str, str] = {}

    for item in items:
        item_type = item.get("assessment_type", "")
        answers[item_type] = simulate_item_answer(item, learner_profile=learner_profile)

    return answers


if __name__ == "__main__":
    import json

    sample_bundle = {
        "assessment_items": [
            {
                "assessment_type": "mcq",
                "prompt": "Which example shows a valid Python variable name?",
                "options": ["class", "2score", "total_score", "my-var"],
                "expected_answer": "total_score",
            },
            {
                "assessment_type": "explanation",
                "prompt": "Explain Variables in Python after revisiting it.",
                "expected_points": ["concept recall", "correct usage", "relevant example"],
            },
            {
                "assessment_type": "output_prediction",
                "prompt": "What is the output of: score = 10; score = 15; print(score)",
                "expected_answer": "15",
            },
            {
                "assessment_type": "transfer",
                "prompt": "Apply Variables in a fresh situation.",
                "expected_points": ["recalled application", "correct usage", "new example"],
            },
        ]
    }

    for profile in ["weak", "average", "strong"]:
        print(f"\n=== {profile.upper()} LEARNER ===")
        print(json.dumps(simulate_learner_answers(sample_bundle, learner_profile=profile), indent=2))