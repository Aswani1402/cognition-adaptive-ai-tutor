import json
import re
from typing import Any, Dict, List, Optional


JSON_TASKS = {"mcq", "flashcard", "debug_task", "output_prediction"}
STRUCTURED_TASKS = JSON_TASKS | {"hint", "revision_summary", "explanation"}

UNSAFE_MARKERS = {
    "ignore previous instructions",
    "system prompt",
    "api key",
    "password",
    "secret key",
    "lorem ipsum",
    "todo",
    "placeholder",
}

SUBJECT_TERMS = {
    "python": {"python", "variable", "function", "loop", "print", "list", "dictionary", "code"},
    "sql": {"sql", "select", "database", "table", "query", "where", "join"},
    "html": {"html", "tag", "element", "browser", "form", "attribute", "<"},
    "git": {"git", "commit", "repository", "branch", "version", "merge"},
    "data structures": {"array", "stack", "queue", "tree", "graph", "node", "data structure"},
}


def as_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(as_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(as_text(v) for v in value)
    return str(value or "")


def parse_json_object(value: Any) -> tuple[Optional[Any], bool]:
    if isinstance(value, (dict, list)):
        return value, True
    text = str(value or "").strip()
    if not text:
        return None, False
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return None, False


def has_repeated_lines(text: str) -> bool:
    lines = [re.sub(r"\s+", " ", line.strip().lower()) for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    return len(lines) != len(set(lines))


def has_repeated_phrase_loop(text: str) -> bool:
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    if len(words) < 20:
        return False
    for size in (3, 4, 5):
        chunks = [" ".join(words[i : i + size]) for i in range(0, len(words) - size + 1)]
        if any(chunks.count(chunk) >= 4 for chunk in set(chunks)):
            return True
    return False


def concept_tokens(concept_name: str) -> set[str]:
    tokens = {t for t in re.findall(r"[a-z0-9]+", str(concept_name).lower()) if len(t) > 2}
    tokens |= {t[:-1] for t in list(tokens) if t.endswith("s") and len(t) > 4}
    aliases = {
        "variables": {"variable", "value", "name"},
        "sql select queries": {"select", "query"},
        "database basics": {"database", "table"},
        "html tags and elements": {"html", "tag", "element"},
        "git repositories": {"git", "repository", "repo"},
        "commits and history": {"commit", "history"},
        "arrays": {"array", "index", "element"},
    }
    tokens |= aliases.get(str(concept_name).lower(), set())
    return tokens


def concept_match(text: str, concept_name: str, rag_context: Any = None) -> bool:
    lowered = text.lower()
    tokens = concept_tokens(concept_name)
    if str(concept_name).lower() in lowered or any(token in lowered for token in tokens):
        return True
    context_text = ""
    if isinstance(rag_context, dict):
        context_text = as_text(rag_context.get("context_text") or rag_context.get("sections") or "")
    else:
        context_text = str(rag_context or "")
    context_tokens = {t for t in re.findall(r"[a-z0-9]+", context_text.lower()) if len(t) > 5}
    return bool(context_tokens and any(token in lowered for token in list(context_tokens)[:25]))


def subject_match(text: str, subject: str) -> bool:
    lowered = text.lower()
    subject_key = str(subject or "").lower()
    if subject_key and subject_key in lowered:
        return True
    return any(term in lowered for term in SUBJECT_TERMS.get(subject_key, set()))


def difficulty_match(text: str, difficulty: str) -> bool:
    lowered = text.lower()
    level = str(difficulty or "").lower()
    advanced_terms = {"advanced", "optimize", "complexity", "edge case", "window function", "rebase"}
    if level == "easy":
        return not any(term in lowered for term in advanced_terms)
    if level == "hard":
        return len(text.split()) >= 8
    return True


def validate_required_fields(task_type: str, data: Any, errors: List[str]) -> None:
    if task_type == "mcq":
        if not isinstance(data, dict):
            errors.append("mcq_not_object")
            return
        question = data.get("question") or data.get("prompt")
        options = data.get("options")
        answer = data.get("answer") or data.get("correct_answer") or data.get("correctAnswer")
        explanation = data.get("explanation") or data.get("reason")
        if not question:
            errors.append("mcq_missing_question")
        if not isinstance(options, list) or len(options) != 4:
            errors.append("mcq_options_must_be_4")
        if not answer:
            errors.append("mcq_missing_answer")
        if answer and isinstance(options, list) and len(options) == 4:
            answer_text = str(answer).strip()
            option_letters = {"A", "B", "C", "D"}
            if answer_text not in [str(o).strip() for o in options] and answer_text.upper() not in option_letters:
                errors.append("mcq_answer_not_in_options_or_letter")
        if not explanation:
            errors.append("mcq_missing_explanation")
    elif task_type == "flashcard":
        if not isinstance(data, dict):
            errors.append("flashcard_not_object")
            return
        if not data.get("front"):
            errors.append("flashcard_missing_front")
        if not data.get("back"):
            errors.append("flashcard_missing_back")
    elif task_type == "debug_task":
        if not isinstance(data, dict):
            errors.append("debug_task_not_object")
            return
        for field in ("buggy_code", "expected_fix"):
            if not data.get(field):
                errors.append(f"debug_task_missing_{field}")
        if not (data.get("hint") or data.get("explanation")):
            errors.append("debug_task_missing_hint_or_explanation")
    elif task_type == "output_prediction":
        if not isinstance(data, dict):
            errors.append("output_prediction_not_object")
            return
        for field in ("question", "code"):
            if not data.get(field):
                errors.append(f"output_prediction_missing_{field}")
        if not (data.get("answer") or data.get("expected_output")):
            errors.append("output_prediction_missing_answer")
        if not data.get("explanation"):
            errors.append("output_prediction_missing_explanation")
    elif task_type == "hint":
        if not as_text(data).strip():
            errors.append("hint_missing_text")
    elif task_type in {"explanation", "revision_summary"}:
        if len(as_text(data).split()) < 8:
            errors.append(f"{task_type}_too_short")


def hint_reveals_full_answer(data: Any, learner_state: Optional[Dict[str, Any]] = None) -> bool:
    if (learner_state or {}).get("hint_level") in {"final", "answer"}:
        return False
    text = as_text(data).lower()
    direct_markers = ["the answer is", "correct answer:", "use this exact answer", "expected fix:"]
    return any(marker in text for marker in direct_markers)


def validate_guarded_tutor_output(
    output: Any,
    task_type: str,
    concept_name: str,
    subject: str,
    difficulty: str,
    learner_state: Optional[Dict[str, Any]] = None,
    rag_context: Any = None,
    raw_text: Optional[str] = None,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    text = as_text(output).strip()
    raw_source = raw_text if raw_text is not None else output
    _, json_valid = parse_json_object(raw_source)

    if not text:
        errors.append("empty_output")
    if has_repeated_lines(str(raw_text if raw_text is not None else text)):
        errors.append("repeated_lines")
    # Raw model text needs loop detection. For validated MCQ objects, repeated
    # concept names across options are normal and should not be treated as loops.
    phrase_loop_source = str(raw_text if raw_text is not None else text)
    if task_type == "mcq" and raw_text is None:
        phrase_loop_source = ""
    if phrase_loop_source and has_repeated_phrase_loop(phrase_loop_source):
        errors.append("repeated_phrase_loop")
    if any(marker in text.lower() for marker in UNSAFE_MARKERS):
        errors.append("unsafe_or_placeholder_text")

    if task_type in JSON_TASKS and not json_valid and raw_text is not None:
        errors.append("json_invalid_for_json_task")

    grounding_pass = bool(text) and concept_match(text, concept_name, rag_context) and subject_match(text, subject)
    if not grounding_pass:
        errors.append("concept_or_subject_grounding_failed")

    difficulty_pass = difficulty_match(text, difficulty)
    if not difficulty_pass:
        errors.append("difficulty_match_failed")

    validate_required_fields(task_type, output, errors)
    if task_type == "hint" and hint_reveals_full_answer(output, learner_state):
        errors.append("hint_reveals_full_answer_before_final_hint")

    repetition_pass = "repeated_lines" not in errors and "repeated_phrase_loop" not in errors
    format_pass = not any(
        error
        for error in errors
        if error.startswith(task_type)
        or error.endswith("_not_object")
        or error.startswith("mcq_")
        or error.startswith("flashcard_")
        or error.startswith("debug_task_")
        or error.startswith("output_prediction_")
        or error == "json_invalid_for_json_task"
    )
    learner_facing_safe = not errors and bool(text)

    return {
        "valid": learner_facing_safe,
        "errors": errors,
        "warnings": warnings,
        "json_valid": json_valid if task_type in JSON_TASKS else True,
        "grounding_pass": grounding_pass,
        "repetition_pass": repetition_pass,
        "format_pass": format_pass,
        "difficulty_match": difficulty_pass,
        "learner_facing_safe": learner_facing_safe,
        "text_length": len(text),
        "word_count": len(text.split()),
    }
