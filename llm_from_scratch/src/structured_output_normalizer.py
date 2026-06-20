import json
import re
from typing import Any, Dict, List, Tuple

from src.model_content_validator import parse_json_object


JSON_TASKS = {
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "mindmap",
}

SCHEMAS = {
    "flashcard": ["front", "back"],
    "mcq": ["question", "options", "answer", "explanation"],
    "debug_task": ["buggy_code", "expected_fix", "hint", "explanation"],
    "output_prediction": ["code", "question", "answer", "explanation"],
    "challenge_question": ["challenge", "solution_outline"],
    "mindmap": ["center", "branches"],
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _strip_fences(text: str) -> str:
    text = str(text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def _label_value(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*(.+?)(?=\n[A-Z][A-Za-z _-]*:|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return _clean(match.group(1)) if match else ""


def _normalize_options(options: Any) -> List[str]:
    if isinstance(options, list):
        raw = options
    else:
        raw = re.split(r"\n|;|\|", str(options or ""))
    cleaned: List[str] = []
    for option in raw:
        value = _clean(option)
        value = re.sub(r"^[A-Da-d][).:-]\s*", "", value)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:4]


def _coerce_from_labels(task_type: str, text: str) -> Dict[str, Any]:
    if task_type == "flashcard":
        front = _label_value(text, "front:")
        back = _label_value(text, "back:")
        return {"front": front, "back": back} if front or back else {}
    if task_type == "debug_task":
        return {
            "buggy_code": _label_value(text, "buggy_code:") or _label_value(text, "Buggy code:"),
            "expected_fix": _label_value(text, "expected_fix:") or _label_value(text, "Expected fix:"),
            "hint": _label_value(text, "hint:"),
            "explanation": _label_value(text, "explanation:"),
        }
    if task_type == "output_prediction":
        return {
            "code": _label_value(text, "code:"),
            "question": _label_value(text, "question:"),
            "answer": _label_value(text, "answer:"),
            "explanation": _label_value(text, "explanation:"),
        }
    if task_type == "challenge_question":
        return {
            "challenge": _label_value(text, "challenge:"),
            "solution_outline": _label_value(text, "solution_outline:") or _label_value(text, "solution outline:"),
        }
    return {}


def normalize_structured_output(task_type: str, extracted_output: str) -> Tuple[str, Dict[str, Any]]:
    text = _strip_fences(extracted_output)
    if task_type not in JSON_TASKS:
        return text, {"normalizer_applied": False, "normalizer_status": "not_json_task", "normalizer_issues": []}

    issues: List[str] = []
    parsed = parse_json_object(text)
    if parsed is None:
        parsed = _coerce_from_labels(task_type, text)
        if parsed:
            issues.append("json_rebuilt_from_clear_labels")
        else:
            return text, {
                "normalizer_applied": False,
                "normalizer_status": "invalid_json",
                "normalizer_issues": ["could_not_parse_or_rebuild_json"],
            }
    else:
        issues.append("json_parsed")

    normalized: Dict[str, Any] = {}
    for field in SCHEMAS[task_type]:
        value = parsed.get(field)
        if task_type == "mcq" and field == "options":
            normalized[field] = _normalize_options(value)
        elif task_type == "mindmap" and field == "branches":
            normalized[field] = _normalize_options(value)
        else:
            normalized[field] = _clean(value)

    if task_type == "mcq" and normalized.get("options"):
        answer = normalized.get("answer")
        options = normalized["options"]
        if answer and answer not in options:
            for option in options:
                if _clean(answer).lower() == _clean(option).lower():
                    normalized["answer"] = option
                    break

    return json.dumps(normalized, ensure_ascii=False), {
        "normalizer_applied": True,
        "normalizer_status": "normalized",
        "normalizer_issues": issues,
    }
