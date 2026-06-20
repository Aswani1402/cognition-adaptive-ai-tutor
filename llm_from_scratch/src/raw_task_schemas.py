from typing import Any, Dict, List


TEACHING_TASKS = [
    "explanation",
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "comparison_view",
    "real_world_connection_view",
]

ASSESSMENT_TASKS = [
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
]

SUPPORT_TASKS = [
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
    "mindmap",
    "concept_mindmap",
    "comparison_mindmap",
    "hint",
    "feedback",
    "doubt_answer",
    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "voice_script",
    "teaching_voice_script",
]

JSON_TASKS = {
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
    "mindmap",
    "concept_mindmap",
    "comparison_mindmap",
    "voice_script",
    "teaching_voice_script",
}


def field(name: str, expected_type: type | tuple[type, ...], min_length: int = 1, optional: bool = False, renderable: str = "") -> Dict[str, Any]:
    return {
        "name": name,
        "type": expected_type,
        "min_length": min_length,
        "optional": optional,
        "frontend_renderable": renderable or f"{name} must be displayable as text.",
    }


RAW_TASK_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "mcq": {
        "required": [
            field("question", str, 12),
            field("options", list, 4, renderable="Exactly four non-empty options."),
            field("answer", (str, bool), 1),
            field("explanation", str, 12),
        ],
        "optional": [field("hint", str, 8, True)],
    },
    "debug_task": {"required": [field("buggy_code", str, 6), field("expected_fix", str, 6), field("explanation", str, 12)], "optional": [field("hint", str, 6, True)]},
    "output_prediction": {"required": [field("code", str, 6), field("expected_output", (str, int, float, bool), 1), field("explanation", str, 12)], "optional": [field("question", str, 8, True)]},
    "transfer_question": {"required": [field("scenario", str, 12), field("question", str, 10), field("expected_idea", str, 10)], "optional": []},
    "challenge_question": {"required": [field("challenge", str, 12), field("solution_outline", str, 12)], "optional": []},
    "explanation_check": {"required": [field("question", str, 10), field("expected_points", list, 1)], "optional": [field("rubric", str, 8, True)]},
    "syntax_completion": {"required": [field("incomplete_code", str, 4), field("completion", str, 2), field("explanation", str, 10)], "optional": []},
    "coding_prompt": {"required": [field("task", str, 12), field("starter_code", str, 2), field("expected_outcome", str, 10)], "optional": []},
    "code_reasoning_task": {"required": [field("code", str, 6), field("question", str, 10), field("explanation", str, 12)], "optional": [field("answer", str, 1, True)]},
    "fill_in_the_blank": {"required": [field("prompt", str, 10), field("answer", str, 1)], "optional": [field("explanation", str, 8, True)]},
    "true_or_false": {"required": [field("statement", str, 10), field("answer", bool, 1), field("explanation", str, 8)], "optional": []},
    "flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "concept_recall_flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "misconception_flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "example_flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "debug_flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "personal_flashcards": {"required": [field("cards", list, 1, renderable="List of flashcard objects with front/back.")], "optional": []},
    "syntax_flashcard": {"required": [field("front", str, 8), field("back", str, 8)], "optional": []},
    "mindmap": {"required": [field("center", str, 2), field("branches", list, 2)], "optional": []},
    "concept_mindmap": {"required": [field("center", str, 2), field("branches", list, 2)], "optional": []},
    "comparison_mindmap": {"required": [field("center", str, 2), field("branches", list, 2)], "optional": []},
    "hint": {"required": [field("hint", str, 8)], "optional": []},
    "feedback": {"required": [field("message", str, 12)], "optional": [field("result", str, 4, True), field("next_step", str, 8, True)]},
    "doubt_answer": {"required": [field("answer", str, 12), field("reason", str, 10)], "optional": [field("example", str, 8, True), field("try_this", str, 8, True)]},
    "notebook_summary": {"required": [field("summary", str, 12)], "optional": [field("strengths", list, 1, True), field("focus", list, 1, True)]},
    "mistake_summary": {"required": [field("mistakes", list, 1), field("correction", str, 10)], "optional": []},
    "revision_plan": {"required": [field("steps", list, 1), field("goal", str, 8)], "optional": []},
    "voice_script": {"required": [field("script", str, 20), field("audio_ready", bool, 1)], "optional": [field("voice_ready", bool, 1, True)]},
    "teaching_voice_script": {"required": [field("script", str, 20), field("audio_ready", bool, 1)], "optional": [field("voice_ready", bool, 1, True)]},
}

for _task in TEACHING_TASKS:
    RAW_TASK_SCHEMAS.setdefault(
        _task,
        {
            "required": [field("title", str, 3), field("content", str, 24)],
            "optional": [field("example", str, 8, True), field("key_point", str, 8, True)],
        },
    )


def get_task_schema(task_type: str) -> Dict[str, Any]:
    return RAW_TASK_SCHEMAS.get(task_type, {"required": [field("content", str, 16)], "optional": []})


def task_expects_json(task_type: str) -> bool:
    return task_type in JSON_TASKS


def supported_task_types() -> List[str]:
    return sorted(RAW_TASK_SCHEMAS)


def validate_schema_shape(task_type: str, value: Any) -> Dict[str, Any]:
    schema = get_task_schema(task_type)
    issues: List[str] = []
    if task_expects_json(task_type) and not isinstance(value, dict):
        return {"schema_valid": False, "frontend_renderable": False, "issues": [f"{task_type}_expected_object"]}
    obj = value if isinstance(value, dict) else {"content": str(value or "")}
    for spec in schema["required"]:
        name = spec["name"]
        field_value = obj.get(name)
        if field_value is None and task_type == "output_prediction" and name == "expected_output":
            field_value = obj.get("answer")
        if field_value is None:
            issues.append(f"missing_required_field:{name}")
            continue
        expected_type = spec["type"]
        if not isinstance(field_value, expected_type):
            issues.append(f"wrong_type:{name}")
            continue
        if isinstance(field_value, str) and len(field_value.strip()) < spec["min_length"]:
            issues.append(f"field_too_short:{name}")
        if isinstance(field_value, list):
            if len(field_value) < spec["min_length"]:
                issues.append(f"list_too_short:{name}")
            if any(not str(item).strip() for item in field_value):
                issues.append(f"empty_list_item:{name}")
    return {"schema_valid": not issues, "frontend_renderable": not issues, "issues": issues}
