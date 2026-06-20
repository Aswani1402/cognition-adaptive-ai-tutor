import re
from typing import Any, Dict, List


TEACHING = {
    "explanation", "definition_view", "simple_example_view", "step_by_step_view", "analogy_view",
    "code_view", "misconception_view", "debug_view", "output_prediction_view", "transfer_view",
    "challenge_view", "revision_summary_view", "comparison_view", "real_world_connection_view",
    "revision_summary",
}
ASSESSMENT = {
    "mcq", "debug_task", "output_prediction", "transfer_question", "challenge_question",
    "explanation_check", "syntax_completion", "coding_prompt", "code_reasoning_task",
    "fill_in_the_blank", "true_or_false", "practice_question", "transfer_task",
    "real_world_application_question", "debug_challenge", "output_prediction_challenge",
    "multi_step_challenge",
}
SUPPORT = {
    "flashcard", "concept_recall_flashcard", "misconception_flashcard", "example_flashcard",
    "debug_flashcard", "personal_flashcards", "syntax_flashcard", "mindmap", "concept_mindmap",
    "comparison_mindmap", "hint", "feedback", "doubt_answer", "notebook_summary",
    "mistake_summary", "revision_plan", "voice_script", "teaching_voice_script",
    "revision_voice_script", "mistake_feedback_voice_script", "doubt_explanation_voice_script",
    "encouragement_script", "next_step_guidance_script", "concept_intro_voice_script",
}
SUPPORTED_TASKS = TEACHING | ASSESSMENT | SUPPORT


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return str(value or "")


def _has_any(data: Dict[str, Any], names: List[str]) -> bool:
    return any(str(data.get(name) or "").strip() for name in names)


def _loop_detect(text: str) -> bool:
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < 16:
        return False
    chunks = [" ".join(words[i : i + 4]) for i in range(0, len(words) - 3)]
    return any(chunks.count(chunk) >= 4 for chunk in set(chunks))


def _contains_bad_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(x in lowered for x in ["todo", "placeholder", "n/a", "lorem ipsum", "undefined"])


def validate_model_output(
    parsed_output: Any,
    task_type: str,
    domain: str,
    concept_name: str,
    difficulty: str = "easy",
    teaching_view: str | None = None,
    context: Dict[str, Any] | None = None,
    parser_repair_applied: bool = False,
) -> Dict[str, Any]:
    issues: List[str] = []
    schema_valid = isinstance(parsed_output, dict)
    if not schema_valid:
        issues.append("output_not_dict")
        parsed_output = {}
    data: Dict[str, Any] = parsed_output if isinstance(parsed_output, dict) else {}
    full_text = _text(data).strip()
    lowered_full = full_text.lower()

    if task_type not in SUPPORTED_TASKS:
        issues.append("unsupported_task_type")
    if not full_text:
        issues.append("empty_output")
    if len(full_text) < 8:
        issues.append("too_short_or_broken")
    if _contains_bad_placeholder(full_text):
        issues.append("placeholder_text")
    if _loop_detect(full_text):
        issues.append("repeated_text_loop")
    hard_issues = set()
    if re.search(r'"\s*:\s*"', full_text) or full_text.count("{") != full_text.count("}") or full_text.count("[") != full_text.count("]"):
        issues.append("malformed_structural_artifact")

    domain_terms = {
        "python": {"python", "variable", "function", "loop", "print", "list", "dictionary"},
        "sql": {"sql", "select", "join", "table", "query", "database", "where"},
        "html": {"html", "tag", "element", "form", "input", "browser", "<"},
        "git": {"git", "commit", "branch", "merge", "repository", "checkout"},
        "data structures": {"data structure", "tree", "stack", "queue", "node", "graph", "array"},
    }
    concept_tokens = {t for t in re.findall(r"[a-z0-9]+", str(concept_name).lower()) if len(t) > 2}
    concept_tokens |= {t[:-1] for t in list(concept_tokens) if t.endswith("s") and len(t) > 4}
    domain_key = str(domain).lower()
    concept_match = str(concept_name).lower() in lowered_full or any(token in lowered_full for token in concept_tokens)
    domain_match = domain_key in lowered_full or any(term in lowered_full for term in domain_terms.get(domain_key, set()))
    if not concept_match:
        issues.append("concept_not_grounded")
    if not domain_match:
        issues.append("domain_not_grounded")

    task_match = True
    tt = task_type
    if tt == "mcq":
        task_match = _has_any(data, ["question", "prompt"]) and isinstance(data.get("options"), list) and len(data.get("options") or []) == 4 and _has_any(data, ["answer", "correctAnswer"]) and _has_any(data, ["explanation", "reason"])
    elif tt == "debug_task":
        task_match = _has_any(data, ["buggy_code", "buggy_example", "buggyCode"]) and _has_any(data, ["expected_fix", "fix", "expectedFix"]) and _has_any(data, ["explanation", "hint"])
    elif tt == "output_prediction":
        task_match = _has_any(data, ["code", "example"]) and _has_any(data, ["expected_output", "answer", "expectedOutput"]) and _has_any(data, ["explanation", "reason"])
    elif tt == "fill_in_the_blank":
        task_match = _has_any(data, ["blank", "question", "prompt"]) and _has_any(data, ["answer"])
    elif tt == "true_or_false":
        task_match = _has_any(data, ["statement", "question"]) and isinstance(data.get("answer"), bool) or str(data.get("answer")).lower() in {"true", "false"}
    elif "flashcard" in tt:
        task_match = _has_any(data, ["front", "question"]) and _has_any(data, ["back", "answer"])
    elif "mindmap" in tt:
        task_match = _has_any(data, ["center", "title"]) and bool(data.get("branches") or data.get("nodes"))
    elif "hint" in tt:
        task_match = _has_any(data, ["hint", "content", "text"]) and len(full_text) < 700
    elif "feedback" in tt:
        task_match = _has_any(data, ["feedback", "content", "correct", "partial", "wrong"])
    elif "voice" in tt or tt.endswith("_script"):
        task_match = _has_any(data, ["script", "content", "voice_script"])
    elif tt in TEACHING:
        task_match = _has_any(data, ["content", "definition", "summary"]) or (_has_any(data, ["title"]) and _has_any(data, ["example", "key_points", "quick_check"]))
    if not task_match:
        issues.append("task_specific_schema_failed")

    frontend_renderable = schema_valid and bool(full_text) and not isinstance(data.get("branches"), str)
    if not frontend_renderable:
        issues.append("not_frontend_renderable")

    unrelated_domains = {"python", "sql", "html", "git", "data structures"} - {domain_key}
    if any(d in lowered_full for d in unrelated_domains) and domain_key not in lowered_full:
        issues.append("unrelated_subject_mixing")
    wrong_concept_markers = {
        "commits and history": "git",
        "branches": "git",
        "forms and inputs": "html",
        "join operations": "sql",
        "trees": "data structures",
        "variables": "python",
    }
    for marker, marker_domain in wrong_concept_markers.items():
        if marker in lowered_full and marker != str(concept_name).lower() and marker_domain != domain_key:
            issues.append("wrong_concept_leakage")

    hard_issues.update(
        issue for issue in issues
        if issue in {
            "empty_output",
            "too_short_or_broken",
            "placeholder_text",
            "repeated_text_loop",
            "malformed_structural_artifact",
            "concept_not_grounded",
            "domain_not_grounded",
            "task_specific_schema_failed",
            "not_frontend_renderable",
            "unrelated_subject_mixing",
            "wrong_concept_leakage",
            "output_not_dict",
            "unsupported_task_type",
        }
    )
    checks = [
        schema_valid,
        concept_match,
        domain_match,
        task_match,
        frontend_renderable,
        bool(full_text),
        not _contains_bad_placeholder(full_text),
        not _loop_detect(full_text),
    ]
    quality_score = round(sum(1 for x in checks if x) / len(checks), 3)
    valid = not hard_issues and quality_score >= 0.70
    if "empty_output" in issues:
        rejection_category = "empty_output"
    elif "output_not_dict" in issues:
        rejection_category = "parse_failed"
    elif "repeated_text_loop" in issues:
        rejection_category = "repetition"
    elif "concept_not_grounded" in issues or "domain_not_grounded" in issues or "wrong_concept_leakage" in issues or "unrelated_subject_mixing" in issues:
        rejection_category = "concept_mismatch"
    elif "task_specific_schema_failed" in issues:
        rejection_category = "task_mismatch"
    elif "not_frontend_renderable" in issues:
        rejection_category = "frontend_unrenderable"
    elif any(i in issues for i in ["too_short_or_broken", "placeholder_text", "malformed_structural_artifact"]):
        rejection_category = "schema_missing_fields"
    elif not valid and quality_score >= 0.70:
        rejection_category = "validator_too_strict"
    elif not valid:
        rejection_category = "unknown"
    else:
        rejection_category = None
    return {
        "valid": valid,
        "quality_score": quality_score,
        "schema_valid": schema_valid,
        "concept_match": concept_match,
        "domain_match": domain_match,
        "task_match": task_match,
        "frontend_renderable": frontend_renderable,
        "accepted_after_repair": bool(valid and parser_repair_applied),
        "rejection_category": rejection_category,
        "issues": issues,
    }
