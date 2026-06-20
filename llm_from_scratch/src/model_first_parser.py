import ast
import json
import re
from typing import Any, Dict, List


def _dedupe_lines(text: str) -> str:
    seen = set()
    lines: List[str] = []
    for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        clean = " ".join(line.strip().split())
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line.strip())
    return "\n".join(lines).strip()


def _extract_jsonish(text: str) -> str:
    text = str(text or "").strip()
    fence = re.search(r"```(?:json|python)?\s*(.*?)```", text, flags=re.I | re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1].strip()
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        return text[start : end + 1].strip()
    return text


def _parse_structured(raw: str) -> Any:
    candidate = _extract_jsonish(raw)
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(candidate)
        except Exception:
            pass
    repaired = candidate
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = repaired.replace("True", "true").replace("False", "false").replace("None", "null")
    try:
        return json.loads(repaired)
    except Exception:
        return None


def _wrap_text(text: str, task_type: str) -> Dict[str, Any]:
    cleaned = _dedupe_lines(text)
    title = task_type.replace("_", " ").title()
    if "voice" in task_type or task_type.endswith("_script"):
        return {"script": cleaned}
    if "hint" in task_type:
        return {"hint": cleaned}
    if "feedback" in task_type:
        return {"feedback": cleaned}
    if task_type == "doubt_answer":
        return {"answer": cleaned, "reason": "", "example": "", "try_this": ""}
    return {
        "title": title,
        "content": cleaned,
        "key_points": [],
        "example": "",
        "quick_check": "",
    }


def _normalize_options(value: Any) -> List[str]:
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"\s*(?:\||;|\n|,[A-D][).])\s*", str(value or ""))
    out = []
    for item in items:
        text = str(item).strip(" -0123456789.)\t")
        if text and text not in out:
            out.append(text)
    return out


def _parse_mcq_text(text: str) -> Dict[str, Any] | None:
    option_matches = list(re.finditer(r"(?im)^\s*([A-D])[\).:-]\s*(.+)$", text))
    if len(option_matches) < 4:
        return None
    question = text[: option_matches[0].start()].strip(" \n:-")
    options = [f"{m.group(1).upper()}) {m.group(2).strip()}" for m in option_matches[:4]]
    answer_match = re.search(r"(?im)^\s*(?:answer|correct answer)\s*[:=-]\s*([A-D]|.+)$", text)
    explanation_match = re.search(r"(?im)^\s*(?:explanation|reason)\s*[:=-]\s*(.+)$", text)
    answer = answer_match.group(1).strip() if answer_match else ""
    if answer and len(answer) > 1:
        for opt in options:
            if answer.lower() in opt.lower():
                answer = opt[0]
                break
    if not question:
        q_match = re.search(r"(?im)^\s*(?:question|q)\s*[:=-]\s*(.+)$", text)
        question = q_match.group(1).strip() if q_match else "Choose the best answer."
    if not answer:
        return None
    return {
        "question": question,
        "options": options,
        "answer": answer[0].upper(),
        "explanation": explanation_match.group(1).strip() if explanation_match else "The answer follows the concept context.",
    }


def _parse_flashcard_text(text: str) -> Dict[str, Any] | None:
    match = re.search(r"(?is)(?:^|\n)\s*(?:q|front)\s*[:=-]\s*(.+?)\s*(?:\n|$)\s*(?:a|back)\s*[:=-]\s*(.+)", text)
    if not match:
        return None
    return {"front": match.group(1).strip(), "back": match.group(2).strip()}


def _parse_mindmap_text(text: str) -> Dict[str, Any] | None:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip(" -*\t")]
    if len(lines) < 3:
        return None
    center = re.sub(r"(?i)^mind\s*map\s*[:=-]\s*", "", lines[0]).strip()
    branches = [{"label": line.split(":", 1)[0].strip(), "items": [line.split(":", 1)[1].strip()] if ":" in line else [line]} for line in lines[1:6]]
    return {"center": center or "Concept", "branches": branches}


def parse_model_output(raw_text: str, task_type: str) -> Dict[str, Any]:
    issues: List[str] = []
    repair_applied = False
    raw_text = str(raw_text or "").strip()
    if not raw_text:
        return {"parse_status": "FAIL", "parsed_output": None, "repair_applied": False, "issues": ["empty_raw_output"]}

    parsed = _parse_structured(raw_text)
    if parsed is not None:
        if isinstance(parsed, list):
            parsed = {"items": parsed}
            repair_applied = True
            issues.append("wrapped_list_output")
        if isinstance(parsed, dict):
            normalized = dict(parsed)
            if "options" in normalized:
                opts = _normalize_options(normalized.get("options"))
                if opts != normalized.get("options"):
                    normalized["options"] = opts
                    repair_applied = True
                    issues.append("normalized_options")
            if "answer" not in normalized and "correctAnswer" in normalized:
                normalized["answer"] = normalized.get("correctAnswer")
                repair_applied = True
                issues.append("normalized_answer_key")
            if "expected_output" not in normalized and "expectedOutput" in normalized:
                normalized["expected_output"] = normalized.get("expectedOutput")
                repair_applied = True
                issues.append("normalized_expected_output_key")
            for key, value in list(normalized.items()):
                if isinstance(value, str):
                    cleaned = _dedupe_lines(value)
                    if cleaned != value:
                        normalized[key] = cleaned
                        repair_applied = True
                        issues.append(f"deduped_{key}")
            return {
                "parse_status": "PASS" if not issues else "WARN",
                "parsed_output": normalized,
                "repair_applied": repair_applied,
                "issues": issues,
            }

    text = _dedupe_lines(_extract_jsonish(raw_text))
    if len(text) < 2:
        return {"parse_status": "FAIL", "parsed_output": None, "repair_applied": False, "issues": ["unparseable_or_too_short"]}
    if task_type == "mcq":
        mcq = _parse_mcq_text(text)
        if mcq:
            return {"parse_status": "WARN", "parsed_output": mcq, "repair_applied": True, "issues": ["parsed_mcq_text"]}
    if "flashcard" in task_type:
        flashcard = _parse_flashcard_text(text)
        if flashcard:
            return {"parse_status": "WARN", "parsed_output": flashcard, "repair_applied": True, "issues": ["parsed_flashcard_text"]}
    if "mindmap" in task_type:
        mindmap = _parse_mindmap_text(text)
        if mindmap:
            return {"parse_status": "WARN", "parsed_output": mindmap, "repair_applied": True, "issues": ["parsed_mindmap_text"]}
    issues.append("wrapped_plain_text")
    return {
        "parse_status": "WARN",
        "parsed_output": _wrap_text(text, task_type),
        "repair_applied": True,
        "issues": issues,
    }
