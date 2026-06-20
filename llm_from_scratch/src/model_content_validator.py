import json
import re
from typing import Any, Dict, List, Optional


JSON_TASKS = {
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "mindmap",
    "syntax_completion",
}

DOMAIN_FORBIDDEN = {
    "Python": ["git commit", "submodule", "stack follows lifo", "queue is fifo", "sql select"],
    "SQL": ["html", "image", "git", "stack follows lifo"],
    "HTML": ["git commit", "stack follows lifo", "sql select"],
    "Git": ["sql select", "stack follows lifo", "html tag"],
    "Data Structures": ["sql select", "select query", "git commit"],
}


def words(value: Any) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def _first_balanced_json(text: str) -> str:
    text = str(text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1].strip()
    return text[start:].strip()


def normalize_choice(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def parse_json_object(text: Any) -> Optional[Dict[str, Any]]:
    if isinstance(text, dict):
        return text
    cleaned = _first_balanced_json(str(text or ""))
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def has_repeated_nonsense(text: str) -> bool:
    tokens = words(text)
    if len(tokens) < 8:
        return False
    most_common = max(tokens.count(token) for token in set(tokens))
    if most_common / len(tokens) > 0.35:
        return True
    lines = [line.strip().lower() for line in str(text).splitlines() if line.strip()]
    return len(lines) >= 4 and len(set(lines)) <= 2


def has_prompt_echo(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(
        marker in lowered
        for marker in [
            "<bos>",
            "<instruction>",
            "<task_",
            "<concept>",
            "<domain>",
            "<context>",
            "<answer>",
        ]
    )


def has_placeholder_content(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in ["...", "lorem", "todo", "<unk>"])


def has_broken_ending(text: str) -> bool:
    stripped = str(text or "").strip()
    if not stripped:
        return False
    if parse_json_object(stripped) is not None:
        return False
    return stripped.endswith(("\\", ",", " and", " or", " the", " to"))


def wrong_task_format(task_type: str, text: str, parsed: Optional[Dict[str, Any]]) -> bool:
    lowered = str(text or "").strip().lower()
    if task_type not in JSON_TASKS and parsed is not None:
        return True
    if task_type == "explanation" and lowered.startswith("{"):
        return True
    if task_type == "hint" and lowered.startswith("{"):
        return True
    if task_type == "feedback" and lowered.startswith(("{", "voice script:", "notebook summary:")):
        return True
    if task_type == "doubt_answer" and lowered.startswith(("{", "notebook summary:", "voice script:")):
        return True
    if task_type == "revision_summary" and lowered.startswith("{"):
        return True
    return False


def concept_relevant(text: str, concept_name: str, domain: str, context_text: str = "") -> bool:
    text_lower = str(text or "").lower()
    concept_tokens = [token for token in words(concept_name) if len(token) >= 4]
    domain_tokens = [token for token in words(domain) if len(token) >= 3]
    context_tokens = [token for token in words(context_text) if len(token) >= 6][:10]
    signals = concept_tokens + domain_tokens + context_tokens
    for signal in signals:
        if signal in text_lower:
            return True
        if signal.endswith("s") and signal[:-1] in text_lower:
            return True
        if f"{signal}s" in text_lower:
            return True
    return False


def score_from_issues(issues: List[str], blocking_issues: List[str]) -> float:
    if blocking_issues:
        return round(max(0.0, 0.72 - 0.16 * len(blocking_issues) - 0.04 * len(issues)), 4)
    return round(max(0.0, 1.0 - 0.08 * len(issues)), 4)


def validate_model_output(
    task_type: str,
    generated_text: Any,
    concept_name: str = "",
    domain: str = "",
    context_text: str = "",
    grounding_score: Optional[float] = None,
) -> Dict[str, Any]:
    text = str(generated_text or "").strip()
    issues: List[str] = []
    blocking: List[str] = []
    parsed = None

    if not text:
        blocking.append("output_empty")
    if len(words(text)) < 6:
        blocking.append("output_too_short")
    if text and has_repeated_nonsense(text):
        blocking.append("repeated_nonsense")
    if text and has_prompt_echo(text):
        blocking.append("prompt_echo")
    if text and has_placeholder_content(text):
        blocking.append("placeholder_content")
    if text and has_broken_ending(text):
        blocking.append("broken_ending")
    if text and not concept_relevant(text, concept_name, domain, context_text):
        blocking.append("concept_or_domain_irrelevant")
    if grounding_score is not None and grounding_score < 0.5:
        blocking.append("grounding_score_below_0_5")

    lowered = text.lower()
    parsed_for_task_check = parse_json_object(text) if text else None
    if text and wrong_task_format(task_type, text, parsed_for_task_check):
        blocking.append("task_format_mismatch")
    for forbidden in DOMAIN_FORBIDDEN.get(domain, []):
        if forbidden in lowered:
            blocking.append(f"wrong_domain_term:{forbidden}")
    concept_lower = str(concept_name or "").lower()
    if domain == "SQL":
        sql_required_terms = {
            "join": ["join"],
            "index": ["index"],
            "window": ["window", "over", "partition"],
            "cte": ["cte", "with", "common table"],
            "common table": ["cte", "with", "common table"],
        }
        for concept_marker, required_terms in sql_required_terms.items():
            if concept_marker in concept_lower and not any(term in lowered for term in required_terms):
                blocking.append(f"sql_concept_missing_required_term:{concept_marker}")

    if task_type in JSON_TASKS:
        parsed = parse_json_object(text)
        if parsed is None:
            blocking.append(f"{task_type}_invalid_json")
        elif task_type == "flashcard":
            if text.lstrip().lower().startswith("hint"):
                blocking.append("flashcard_starts_with_hint")
            for field in ["front", "back"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"flashcard_missing_{field}")
        elif task_type == "mcq":
            if text.lstrip().lower().startswith("hint"):
                blocking.append("mcq_plain_hint_text")
            for field in ["question", "answer", "explanation"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"mcq_missing_{field}")
            options = parsed.get("options")
            if not isinstance(options, list):
                blocking.append("mcq_options_not_list")
            elif len(options) != 4:
                blocking.append("mcq_options_not_exactly_4")
            elif len({normalize_choice(option) for option in options}) != 4:
                blocking.append("mcq_duplicate_options")
            elif normalize_choice(parsed.get("answer")) not in {normalize_choice(option) for option in options}:
                issues.append("mcq_answer_not_in_options")
        elif task_type == "debug_task":
            for field in ["buggy_code", "expected_fix", "hint", "explanation"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"debug_task_missing_{field}")
        elif task_type == "output_prediction":
            for field in ["code", "question", "answer", "explanation"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"output_prediction_missing_{field}")
        elif task_type == "challenge_question":
            for field in ["challenge", "solution_outline"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"challenge_question_missing_{field}")
        elif task_type == "mindmap":
            if not str(parsed.get("center", "")).strip():
                blocking.append("mindmap_missing_center")
            branches = parsed.get("branches")
            if not isinstance(branches, list) or not branches:
                blocking.append("mindmap_missing_branches")
            elif any(not str(branch).strip() for branch in branches):
                blocking.append("mindmap_empty_branch")
        elif task_type == "syntax_completion":
            for field in ["incomplete_code", "completion", "explanation"]:
                if not str(parsed.get(field, "")).strip():
                    blocking.append(f"syntax_completion_missing_{field}")

    elif task_type == "explanation":
        for heading in ["Concept:", "Definition:", "Example:", "Why it matters:"]:
            if heading.lower() not in lowered:
                blocking.append(f"explanation_missing_{heading}")
    elif task_type == "revision_summary":
        for heading in ["Summary:", "Remember:", "Avoid this mistake:"]:
            if heading.lower() not in lowered:
                blocking.append(f"revision_summary_missing_{heading}")
    elif task_type == "voice_script":
        if len(words(text)) < 18:
            blocking.append("voice_script_not_readable")
    elif task_type in {"hint", "feedback", "doubt_answer"}:
        if len(words(text)) < 8:
            blocking.append(f"{task_type}_too_short")
        expected = {
            "hint": ["Hint:"],
            "feedback": ["What was correct:", "What to improve:", "Next step:"],
            "doubt_answer": ["Answer:", "Reason:", "Example:", "Try this:"],
        }[task_type]
        for heading in expected:
            if heading.lower() not in lowered:
                blocking.append(f"{task_type}_missing_{heading}")
    elif task_type == "coding_prompt":
        for heading in ["Task:", "Starter Code:", "Expected Outcome:"]:
            if heading.lower() not in lowered:
                blocking.append(f"coding_prompt_missing_{heading}")
    elif task_type == "transfer_question":
        for heading in ["Scenario:", "Question:", "Expected Idea:"]:
            if heading.lower() not in lowered:
                blocking.append(f"transfer_question_missing_{heading}")
    elif task_type == "notebook_summary":
        for heading in ["Notebook Summary:", "Strength:", "Focus:"]:
            if heading.lower() not in lowered:
                blocking.append(f"notebook_summary_missing_{heading}")
    elif task_type == "comeback_summary":
        for heading in ["Welcome Back:", "Last Topic:", "Next Step:"]:
            if heading.lower() not in lowered:
                blocking.append(f"comeback_summary_missing_{heading}")
    else:
        issues.append(f"unknown_task_type:{task_type}")

    seen = []
    for item in blocking:
        if item not in seen:
            seen.append(item)
    blocking = seen

    quality_score = score_from_issues(issues, blocking)
    return {
        "valid": not blocking,
        "quality_score": quality_score,
        "issues": issues + blocking,
        "blocking_issues": blocking,
        "parsed": parsed,
    }


def validate_output(*args, **kwargs) -> Dict[str, Any]:
    return validate_model_output(*args, **kwargs)
