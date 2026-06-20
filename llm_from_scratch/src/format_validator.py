import json
import re
from typing import Any, Dict, List, Optional


PLACEHOLDER_MARKERS = ("placeholder", "todo", "n/a", "...", "c2")

ASSESSMENT_TASKS = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
}

FLASHCARD_TASKS = {
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
    "spaced_repetition_card",
}

MINDMAP_TASKS = {"mindmap", "concept_mindmap", "comparison_mindmap"}

DOUBT_TASKS = {
    "doubt_answer",
    "concept_doubt_answer",
    "syntax_doubt_answer",
    "debug_doubt_answer",
    "output_doubt_answer",
    "example_request_answer",
    "revision_doubt_answer",
    "next_step_doubt_answer",
    "comparison_doubt_answer",
}

HINT_TASKS = {
    "hint",
    "small_hint",
    "guided_hint",
    "worked_example_hint",
    "debug_hint",
    "syntax_hint",
    "output_prediction_hint",
    "misconception_hint",
    "next_step_hint",
    "analogy_hint",
}

FEEDBACK_TASKS = {
    "feedback",
    "correct_answer_feedback",
    "wrong_answer_feedback",
    "partial_answer_feedback",
    "debug_feedback",
    "output_prediction_feedback",
    "next_step_feedback",
    "encouragement_feedback",
}

VOICE_TASKS = {
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
}


def _as_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "")


def _parse_if_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return value


def has_repeated_lines(text: str) -> bool:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    return len(lines) != len(set(lines))


def duplicate_rate(lines_or_prompts: List[str]) -> float:
    normalized = [re.sub(r"\s+", " ", str(x).strip().lower()) for x in lines_or_prompts if str(x).strip()]
    if not normalized:
        return 0.0
    return round(1.0 - (len(set(normalized)) / len(normalized)), 4)


def contains_concept_signal(
    text: str,
    concept_name: Optional[str] = None,
    key_points: Optional[List[str]] = None,
) -> bool:
    lowered = text.lower()
    if concept_name and concept_name.lower() in lowered:
        return True
    for point in key_points or []:
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{4,}", str(point))]
        if any(word in lowered for word in words[:10]):
            return True
    return not concept_name and not key_points


def _has_bad_marker(value: Any) -> bool:
    lowered = _as_text(value).lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _require_fields(obj: Dict[str, Any], fields: List[str], errors: List[str]) -> None:
    for field in fields:
        if field not in obj or obj[field] in ("", None, []):
            errors.append(f"missing_or_empty:{field}")


def _validate_assessment(task_type: str, obj: Dict[str, Any], errors: List[str]) -> None:
    _require_fields(obj, ["question_id", "task_type", "question_type", "difficulty", "prompt", "correct_answer", "explanation", "hint"], errors)
    if task_type == "mcq":
        options = obj.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append("mcq_options_must_be_4")
        elif obj.get("correct_answer") not in options:
            errors.append("mcq_correct_answer_not_in_options")
    if task_type in {"debug_task", "debug_challenge"}:
        _require_fields(obj, ["buggy_code", "expected_fix"], errors)
    if task_type in {"output_prediction", "output_prediction_challenge"}:
        _require_fields(obj, ["code", "expected_output"], errors)
    if task_type in {"coding_prompt", "multi_step_challenge"}:
        if not isinstance(obj.get("test_cases"), list) or not obj.get("test_cases"):
            errors.append("coding_task_missing_test_cases")
    if task_type in {"coding_prompt", "code_reasoning_task", "transfer_question", "challenge_question", "explanation_check", "practice_question", "transfer_task", "real_world_application_question", "multi_step_challenge"}:
        if not isinstance(obj.get("expected_points"), list) or not obj.get("expected_points"):
            errors.append("open_answer_missing_expected_points")
    if task_type == "fill_in_the_blank" and "____" not in str(obj.get("prompt", "")):
        errors.append("fill_in_blank_missing_blank_marker")
    if task_type == "true_or_false" and obj.get("correct_answer") not in {True, False, "True", "False"}:
        errors.append("true_false_correct_answer_not_boolean")


def _validate_flashcards(obj: Dict[str, Any], errors: List[str]) -> None:
    cards = obj.get("cards")
    if not isinstance(cards, list) or len(cards) < 3:
        errors.append("flashcards_need_multiple_cards")
        return
    for idx, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(f"flashcard_{idx}_not_object")
            continue
        _require_fields(card, ["card_type", "front", "back", "explanation", "difficulty"], errors)


def _validate_mindmap(obj: Dict[str, Any], errors: List[str]) -> None:
    _require_fields(obj, ["mindmap_type", "center", "branches"], errors)
    branches = obj.get("branches")
    if not isinstance(branches, list) or len(branches) < 4:
        errors.append("mindmap_needs_rich_branches")
        return
    for branch in branches:
        if not isinstance(branch, dict) or not branch.get("label") or not isinstance(branch.get("items"), list) or not branch.get("items"):
            errors.append("mindmap_branch_missing_label_or_items")


def validate_task_output(
    task_type: str,
    output: Any,
    concept_name: Optional[str] = None,
    key_points: Optional[List[str]] = None,
) -> Dict[str, Any]:
    parsed = _parse_if_json(output)
    errors: List[str] = []
    warnings: List[str] = []
    text = _as_text(parsed)

    if parsed in ("", None, [], {}):
        errors.append("empty_output")
    if _has_bad_marker(parsed):
        errors.append("placeholder_or_c2_marker")
    if has_repeated_lines(text):
        errors.append("duplicate_lines")
    if not contains_concept_signal(text, concept_name=concept_name, key_points=key_points):
        errors.append("concept_relevance_failed")

    if task_type in ASSESSMENT_TASKS:
        if not isinstance(parsed, dict):
            errors.append("assessment_output_must_be_object")
        else:
            _validate_assessment(task_type, parsed, errors)
    elif task_type in FLASHCARD_TASKS:
        if not isinstance(parsed, dict):
            errors.append("flashcard_output_must_be_object")
        else:
            _validate_flashcards(parsed, errors)
    elif task_type in MINDMAP_TASKS:
        if not isinstance(parsed, dict):
            errors.append("mindmap_output_must_be_object")
        else:
            _validate_mindmap(parsed, errors)
    elif task_type in DOUBT_TASKS:
        if not isinstance(parsed, dict):
            errors.append("doubt_output_must_be_object")
        else:
            _require_fields(parsed, ["answer", "example", "source_context_summary", "follow_up_check", "next_step"], errors)
    elif task_type in HINT_TASKS:
        if not isinstance(parsed, dict):
            errors.append("hint_output_must_be_object")
        else:
            _require_fields(parsed, ["hint_type", "hint", "why_this_helps", "next_step"], errors)
    elif task_type in FEEDBACK_TASKS:
        if not isinstance(parsed, dict):
            errors.append("feedback_output_must_be_object")
        else:
            _require_fields(parsed, ["feedback_type", "message", "correction", "next_step"], errors)
    elif task_type in VOICE_TASKS:
        if not isinstance(parsed, dict):
            errors.append("voice_output_must_be_object")
        else:
            _require_fields(parsed, ["script_type", "script", "voice_ready"], errors)
            if parsed.get("voice_ready") is not True:
                errors.append("voice_ready_not_true")
    elif isinstance(parsed, dict):
        if len(text.split()) < 30:
            warnings.append("short_structured_output")
    else:
        if len(text.split()) < 30:
            errors.append("text_output_too_short")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "parsed": parsed,
        "quality_score": round(max(0.0, 1.0 - (0.12 * len(errors)) - (0.04 * len(warnings))), 4),
    }


def validate_output(
    task_type: str,
    generated_text: Any,
    concept_name: Optional[str] = None,
    key_points: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return validate_task_output(task_type, generated_text, concept_name=concept_name, key_points=key_points)


if __name__ == "__main__":
    sample = {
        "question_id": "P1_mcq_1",
        "task_type": "mcq",
        "question_type": "mcq",
        "difficulty": "easy",
        "prompt": "Which statement best matches Variables?",
        "options": ["A variable is a name bound to an object in memory", "Wrong one", "Wrong two", "Wrong three"],
        "correct_answer": "A variable is a name bound to an object in memory",
        "explanation": "The answer uses the key point for Variables.",
        "hint": "Look for the option that mentions the name-object binding.",
    }
    print(json.dumps(validate_task_output("mcq", sample, "Variables", ["A variable is a name bound to an object in memory"]), indent=2))
