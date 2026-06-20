from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


SUPPORTED_QUESTION_TYPES = [
    "mcq",
    "debug",
    "output_prediction",
    "short_explanation",
    "transfer",
    "syntax_completion",
    "code_writing",
    "arrange_steps",
    "drag_order",
    "match_pairs",
    "fill_blank",
    "code_puzzle",
    "challenge",
]

PUZZLE_QUESTION_TYPES = [
    "fill_blank",
    "arrange_steps",
    "match_pairs",
    "drag_order",
    "code_puzzle",
]


FRONTEND_COMPONENT_MAP = {
    "mcq": "MCQQuestionCard",
    "debug": "DebugQuestionCard",
    "output_prediction": "OutputPredictionCard",
    "short_explanation": "ShortExplanationCard",
    "transfer": "TransferQuestionCard",
    "syntax_completion": "SyntaxCompletionCard",
    "code_writing": "CodeWritingCard",
    "fill_blank": "FillBlankCard",
    "arrange_steps": "ArrangeStepsCard",
    "match_pairs": "MatchPairsCard",
    "drag_order": "DragOrderCard",
    "code_puzzle": "CodePuzzleCard",
    "challenge": "ChallengeQuestionCard",
}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _make_hash(*parts: Any) -> str:
    raw = "|".join(_safe_str(part) for part in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _base_question(
    concept_id: str,
    concept_name: str,
    question_type: str,
    difficulty: str,
    prompt: str,
    expected_answer: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    question_hash = _make_hash(
        concept_id,
        concept_name,
        question_type,
        difficulty,
        prompt,
        expected_answer,
    )

    return {
        "question_id": f"{concept_id}_{question_type}_{question_hash[:6]}",
        "concept_id": str(concept_id),
        "concept_name": str(concept_name),
        "question_type": question_type,
        "assessment_type": question_type,
        "difficulty": str(difficulty),
        "prompt": prompt,
        "expected_answer": expected_answer,
        "options": None,
        "correct_option_index": None,
        "frontend_component": FRONTEND_COMPONENT_MAP.get(question_type, "GenericQuestionCard"),
        "metadata": metadata or {},
        "question_hash": question_hash,
    }


def make_mcq_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    prompt: str,
    options: List[str],
    correct_option_index: int,
    explanation: str = "",
) -> Dict[str, Any]:
    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="mcq",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer=options[correct_option_index] if options else "",
        metadata={
            "explanation": explanation,
            "render_mode": "radio_options",
        },
    )
    question["options"] = options
    question["correct_option_index"] = correct_option_index
    return question


def make_debug_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    buggy_code: str,
    expected_fix: str,
    bug_type: str = "logic_or_syntax",
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = prompt or (
        "Find the mistake in the code below and explain how to fix it:\n\n"
        f"{buggy_code}"
    )

    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="debug",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "bug_type": bug_type,
            "expected_fix": expected_fix,
        },
        metadata={
            "buggy_code": buggy_code,
            "bug_type": bug_type,
            "render_mode": "code_debug",
        },
    )


def make_output_prediction_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    code: str,
    expected_output: str,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = prompt or (
        "What is the output of the following code?\n\n"
        f"{code}"
    )

    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="output_prediction",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer=expected_output,
        metadata={
            "code": code,
            "render_mode": "code_output_prediction",
        },
    )


def make_short_explanation_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    expected_points: List[str],
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = prompt or f"Explain {concept_name} briefly in your own words."

    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="short_explanation",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "expected_points": expected_points,
        },
        metadata={
            "expected_points": expected_points,
            "render_mode": "text_response",
        },
    )


def make_transfer_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    real_world_context: str,
    expected_points: List[str],
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = prompt or (
        f"How would you apply {concept_name} in a real situation?\n\n"
        f"Context: {real_world_context}"
    )

    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="transfer",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "context": real_world_context,
            "expected_points": expected_points,
        },
        metadata={
            "real_world_context": real_world_context,
            "expected_points": expected_points,
            "render_mode": "text_response",
        },
    )


def make_syntax_completion_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    incomplete_code: str,
    missing_part: str,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = prompt or (
        "Complete the missing syntax in the code below:\n\n"
        f"{incomplete_code}"
    )

    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="syntax_completion",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer=missing_part,
        metadata={
            "incomplete_code": incomplete_code,
            "missing_part": missing_part,
            "render_mode": "code_fill",
        },
    )


def make_code_writing_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    task: str,
    expected_features: List[str],
) -> Dict[str, Any]:
    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="code_writing",
        difficulty=difficulty,
        prompt=task,
        expected_answer={
            "expected_features": expected_features,
        },
        metadata={
            "expected_features": expected_features,
            "render_mode": "code_editor",
        },
    )


def make_drag_order_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    prompt: str,
    items: List[str],
    correct_order: List[int],
) -> Dict[str, Any]:
    item_objects = [
        {"id": f"i{idx + 1}", "text": str(item)}
        for idx, item in enumerate(items)
    ]
    correct_ids = [
        f"i{idx + 1}"
        for idx in correct_order
        if isinstance(idx, int) and 0 <= idx < len(items)
    ]

    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="drag_order",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "correct_order": correct_ids,
            "legacy_correct_order_indexes": correct_order,
        },
        metadata={
            "items": item_objects,
            "correct_order": correct_ids,
            "legacy_items": items,
            "legacy_correct_order_indexes": correct_order,
            "render_mode": "drag_order",
        },
    )
    question["items"] = item_objects
    question["correct_order"] = correct_ids
    return question


def make_arrange_steps_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    prompt: str,
    steps: List[str],
    correct_order: List[int],
) -> Dict[str, Any]:
    step_objects = [
        {"id": f"s{idx + 1}", "text": str(step)}
        for idx, step in enumerate(steps)
    ]
    correct_ids = [
        f"s{idx + 1}"
        for idx in correct_order
        if isinstance(idx, int) and 0 <= idx < len(steps)
    ]

    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="arrange_steps",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "correct_order": correct_ids,
            "legacy_correct_order_indexes": correct_order,
        },
        metadata={
            "steps": step_objects,
            "correct_order": correct_ids,
            "legacy_steps": steps,
            "legacy_correct_order_indexes": correct_order,
            "render_mode": "arrange_steps",
        },
    )
    question["steps"] = step_objects
    question["correct_order"] = correct_ids
    return question


def make_match_pairs_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    prompt: str,
    pairs: List[Dict[str, str]],
) -> Dict[str, Any]:
    left_items = []
    right_items = []
    correct_pairs = []
    normalized_pairs = []

    for idx, pair in enumerate(pairs, start=1):
        left_id = f"l{idx}"
        right_id = f"r{idx}"
        left_text = str(pair.get("left", "")) if isinstance(pair, dict) else ""
        right_text = str(pair.get("right", "")) if isinstance(pair, dict) else ""
        left_items.append({"id": left_id, "text": left_text})
        right_items.append({"id": right_id, "text": right_text})
        correct_pairs.append([left_id, right_id])
        normalized_pairs.append({"left": left_text, "right": right_text})

    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="match_pairs",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "pairs": normalized_pairs,
            "correct_pairs": correct_pairs,
        },
        metadata={
            "pairs": normalized_pairs,
            "left_items": left_items,
            "right_items": right_items,
            "correct_pairs": correct_pairs,
            "render_mode": "match_pairs",
        },
    )
    question["left_items"] = left_items
    question["right_items"] = right_items
    question["correct_pairs"] = correct_pairs
    return question


def make_fill_blank_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    sentence: str,
    blanks: List[str],
) -> Dict[str, Any]:
    answer = blanks[0] if blanks else ""
    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="fill_blank",
        difficulty=difficulty,
        prompt="Complete the missing part.",
        expected_answer={
            "blanks": blanks,
            "answer": answer,
        },
        metadata={
            "text_with_blank": sentence,
            "blanks": blanks,
            "answer": answer,
            "render_mode": "fill_blank",
        },
    )
    question["text_with_blank"] = sentence
    question["answer"] = answer
    question["hint"] = "Use the key rule from the current concept."
    return question


def make_code_puzzle_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    starter_code: str,
    answer: str,
    expected_output: str,
    prompt: str | None = None,
) -> Dict[str, Any]:
    prompt = prompt or "Fix the missing line/code block."
    question = _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="code_puzzle",
        difficulty=difficulty,
        prompt=prompt,
        expected_answer={
            "answer": answer,
            "expected_output": expected_output,
        },
        metadata={
            "starter_code": starter_code,
            "answer": answer,
            "expected_output": expected_output,
            "render_mode": "code_puzzle",
        },
    )
    question["starter_code"] = starter_code
    question["answer"] = answer
    question["expected_output"] = expected_output
    return question


def make_challenge_question(
    concept_id: str,
    concept_name: str,
    difficulty: str,
    challenge_prompt: str,
    success_criteria: List[str],
) -> Dict[str, Any]:
    return _base_question(
        concept_id=concept_id,
        concept_name=concept_name,
        question_type="challenge",
        difficulty=difficulty,
        prompt=challenge_prompt,
        expected_answer={
            "success_criteria": success_criteria,
        },
        metadata={
            "success_criteria": success_criteria,
            "render_mode": "challenge",
        },
    )


def normalize_question_for_frontend(question: Dict[str, Any]) -> Dict[str, Any]:
    question = dict(question)

    question_type = question.get("question_type") or question.get("assessment_type") or "short_explanation"

    question["question_type"] = question_type
    question["assessment_type"] = question_type
    question["frontend_component"] = question.get("frontend_component") or FRONTEND_COMPONENT_MAP.get(
        question_type,
        "GenericQuestionCard",
    )

    metadata = question.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    if not metadata.get("render_mode") or metadata.get("render_mode") == "generic":
        if question_type == "debug":
            metadata["render_mode"] = "code_debug"
        elif question_type == "output_prediction":
            metadata["render_mode"] = "code_output_prediction"
        elif question_type == "syntax_completion":
            metadata["render_mode"] = "code_fill"
        elif question_type == "code_writing":
            metadata["render_mode"] = "code_editor"
        elif question_type == "arrange_steps":
            metadata["render_mode"] = "arrange_steps"
        elif question_type == "drag_order":
            metadata["render_mode"] = "drag_order"
        elif question_type == "match_pairs":
            metadata["render_mode"] = "match_pairs"
        elif question_type == "fill_blank":
            metadata["render_mode"] = "fill_blank"
        elif question_type == "code_puzzle":
            metadata["render_mode"] = "code_puzzle"
        elif question_type == "challenge":
            metadata["render_mode"] = "challenge"
        elif question_type in {"short_explanation", "transfer"}:
            metadata["render_mode"] = "text_response"
        elif question_type == "mcq":
            metadata["render_mode"] = "radio_options"
        else:
            metadata["render_mode"] = "generic"

    question["metadata"] = metadata

    return question


def normalize_assessment_bundle_for_frontend(bundle: Dict[str, Any]) -> Dict[str, Any]:
    bundle = dict(bundle) if isinstance(bundle, dict) else {}

    questions = bundle.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    normalized_questions = [
        normalize_question_for_frontend(q)
        for q in questions
        if isinstance(q, dict)
    ]

    bundle["questions"] = normalized_questions
    bundle["question_count"] = len(normalized_questions)
    bundle["frontend_ready"] = True
    bundle["supported_question_types"] = SUPPORTED_QUESTION_TYPES
    bundle["supported_interactive_types"] = PUZZLE_QUESTION_TYPES
    bundle["frontend_component_map"] = FRONTEND_COMPONENT_MAP
    bundle["puzzle_questions"] = [
        q for q in normalized_questions
        if q.get("question_type") in PUZZLE_QUESTION_TYPES
    ]
    bundle["frontend_components_used"] = sorted(
        {
            q.get("frontend_component")
            for q in normalized_questions
            if q.get("frontend_component")
        }
    )

    return bundle
