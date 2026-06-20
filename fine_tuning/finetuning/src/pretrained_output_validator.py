import re
from typing import Any, Dict, List, Optional


TASK_HINTS = {
    "mcq": ["question", "option", "answer", "explanation"],
    "flashcard": ["front", "back", "question", "answer"],
    "mindmap": ["center", "branch", "node", "topic"],
    "debug_task": ["buggy", "fix", "explanation", "code"],
    "output_prediction": ["code", "output", "explanation"],
}


def _text_from_output(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        return " ".join(_text_from_output(v) for v in output.values())
    if isinstance(output, list):
        return " ".join(_text_from_output(v) for v in output)
    return str(output)


def _has_repetition_problem(text: str) -> bool:
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < 20:
        return False
    for size in (3, 4, 5):
        chunks = [" ".join(words[i : i + size]) for i in range(0, len(words) - size + 1, size)]
        if chunks:
            most_common = max(chunks.count(chunk) for chunk in set(chunks))
            if most_common >= 4:
                return True
    return False


def _concept_terms(concept_name: Optional[str]) -> List[str]:
    if not concept_name:
        return []
    return [term for term in re.split(r"[^a-zA-Z0-9]+", concept_name.lower()) if len(term) > 2]


def validate_task_output(
    task_type: str,
    output: Any,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    text = _text_from_output(output).strip()
    lowered = text.lower()
    issues: List[str] = []

    if not text:
        issues.append("output is empty")
    if len(text) > 12000:
        issues.append("output is too long for safe frontend rendering")
    if _has_repetition_problem(text):
        issues.append("output has repeated phrase patterns")

    concept_terms = _concept_terms(concept_name)
    if concept_terms and not any(term in lowered for term in concept_terms):
        issues.append("output does not mention the requested concept")
    if domain and domain.lower().split()[0] not in lowered:
        issues.append("output does not mention the requested domain")

    task = (task_type or "").lower()
    if task == "mcq":
        option_count = len(re.findall(r"(^|\n|\s)([A-Da-d][\).:]|option\s+[1-4a-d])", text))
        if "question" not in lowered and "?" not in text:
            issues.append("mcq question is missing")
        if option_count and option_count != 4:
            issues.append("mcq does not contain exactly 4 detected options")
        if not option_count and len(re.findall(r"\n\s*[-*]\s+", text)) < 4:
            issues.append("mcq options are missing or not structured")
        if "answer" not in lowered and "correct" not in lowered:
            issues.append("mcq answer is missing")
        if "explanation" not in lowered and "because" not in lowered:
            issues.append("mcq explanation is missing")
    elif task == "flashcard":
        if not (("front" in lowered and "back" in lowered) or ("question" in lowered and "answer" in lowered)):
            issues.append("flashcard front/back or question/answer is missing")
    elif task == "mindmap":
        branch_signals = ["branch", "center", "node", "->", "- "]
        if not any(signal in lowered for signal in branch_signals):
            issues.append("mindmap center/branches or equivalent structure is missing")
    elif task == "debug_task":
        for needed in ("code", "fix", "explanation"):
            if needed not in lowered:
                issues.append(f"debug_task {needed} is missing")
    elif task == "output_prediction":
        for needed in ("code", "output", "explanation"):
            if needed not in lowered:
                issues.append(f"output_prediction {needed} is missing")
    else:
        if len(text) < 30:
            issues.append("output is too short")

    score = 1.0
    score -= min(0.8, 0.14 * len(issues))
    if text and len(text) >= 80:
        score += 0.05
    score = max(0.0, min(1.0, round(score, 3)))
    return {"valid": not issues, "score": score, "issues": issues}

