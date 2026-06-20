from __future__ import annotations

import hashlib
from typing import Any


PUZZLE_TYPES = [
    "fill_blank",
    "arrange_steps",
    "match_pairs",
    "drag_order",
    "code_puzzle",
    "syntax_completion",
]

PUZZLE_FRONTEND_COMPONENT_MAP = {
    "fill_blank": "FillBlankPuzzleCard",
    "arrange_steps": "ArrangeStepsPuzzleCard",
    "match_pairs": "MatchPairsPuzzleCard",
    "drag_order": "DragOrderPuzzleCard",
    "code_puzzle": "CodePuzzleCard",
    "syntax_completion": "SyntaxCompletionCard",
}

PUZZLE_VALIDATION_MODES = {
    "fill_blank": "normalized_blank_match",
    "arrange_steps": "position_accuracy",
    "match_pairs": "pair_accuracy",
    "drag_order": "position_accuracy",
    "code_puzzle": "code_output_or_order_match",
    "syntax_completion": "normalized_completion_match",
}


def _puzzle_id(concept_id: str, puzzle_type: str, prompt: str) -> str:
    raw = f"{concept_id}|{puzzle_type}|{prompt}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"{concept_id}_{puzzle_type}_{digest}"


def make_puzzle(
    puzzle_type: str,
    concept_id: str,
    concept_name: str,
    domain: str,
    difficulty: str,
    prompt: str,
    instructions: str,
    options: list[Any] | None = None,
    correct_answer: Any = None,
    correct_order: list[Any] | None = None,
    pairs: list[dict[str, Any]] | None = None,
    blanks: list[str] | None = None,
    code_snippet: str | None = None,
    expected_output: str | None = None,
    hints: list[str] | None = None,
    max_score: float = 1.0,
) -> dict[str, Any]:
    if puzzle_type not in PUZZLE_TYPES:
        raise ValueError(f"Unsupported puzzle_type: {puzzle_type}")

    return {
        "puzzle_id": _puzzle_id(str(concept_id), puzzle_type, prompt),
        "question_type": "puzzle",
        "puzzle_type": puzzle_type,
        "concept_id": str(concept_id),
        "concept_name": str(concept_name),
        "domain": str(domain),
        "difficulty": str(difficulty),
        "prompt": prompt,
        "instructions": instructions,
        "options": options or [],
        "correct_answer": correct_answer,
        "correct_order": correct_order or [],
        "pairs": pairs or [],
        "blanks": blanks or [],
        "code_snippet": code_snippet,
        "expected_output": expected_output,
        "hints": hints or [],
        "max_score": float(max_score),
        "frontend_component": PUZZLE_FRONTEND_COMPONENT_MAP[puzzle_type],
        "validation_mode": PUZZLE_VALIDATION_MODES[puzzle_type],
    }


def compact_puzzle_for_frontend(puzzle: dict[str, Any]) -> dict[str, Any]:
    puzzle_type = puzzle.get("puzzle_type") or puzzle.get("question_type")
    return {
        "puzzle_id": puzzle.get("puzzle_id") or puzzle.get("question_id"),
        "question_type": "puzzle",
        "puzzle_type": puzzle_type,
        "frontend_component": (
            puzzle.get("frontend_component")
            or PUZZLE_FRONTEND_COMPONENT_MAP.get(str(puzzle_type), "PuzzleCard")
        ),
        "prompt": puzzle.get("prompt"),
        "instructions": puzzle.get("instructions"),
        "options": puzzle.get("options", []),
        "blanks": puzzle.get("blanks", []),
        "pairs": puzzle.get("pairs", []),
        "correct_order": puzzle.get("correct_order", []),
        "code_snippet": puzzle.get("code_snippet"),
        "expected_output": puzzle.get("expected_output"),
        "hints": puzzle.get("hints", []),
        "difficulty": puzzle.get("difficulty"),
        "concept_id": puzzle.get("concept_id"),
        "concept_name": puzzle.get("concept_name"),
        "domain": puzzle.get("domain"),
        "validation_mode": puzzle.get("validation_mode"),
        "max_score": puzzle.get("max_score", 1.0),
    }
