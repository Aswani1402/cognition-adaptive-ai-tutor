import json
import re
from typing import Any, Dict, List


BAD_MARKERS = ("...", "TODO", "N/A", "placeholder")
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
    "misconception_check",
    "concept_recall",
    "flashcard",
    "real_world_application_question",
    "multi_step_challenge",
}
FRONTEND_REQUIRED = [
    "status",
    "domain",
    "concept_id",
    "concept_name",
    "difficulty",
    "source_level",
    "teaching_view",
    "teaching_content",
    "aligned_assessments",
    "hint",
    "feedback_template",
    "revision_summary",
    "flashcard",
    "mindmap",
    "voice_script",
    "next_step",
    "metadata",
]


def _text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")


def _has_output(item: Dict[str, Any]) -> bool:
    return bool(item.get("output") or item.get("teaching_content") or item.get("aligned_assessments"))


def validate_content_item(item: Dict[str, Any], *, item_type: str = "task") -> Dict[str, Any]:
    issues: List[str] = []
    if item_type not in {"status", "catalog", "assessment", "doubt"} and not _has_output(item):
        issues.append("missing_output")
    if item_type not in {"status", "catalog", "assessment", "doubt"}:
        for field in ["concept_id", "concept_name", "domain"]:
            if not item.get(field):
                issues.append(f"missing_{field}")
    if item_type not in {"website_packet", "status", "catalog", "assessment", "doubt"} and not item.get("task_type") and not item.get("teaching_view"):
        issues.append("missing_task_type")
    if item_type not in {"status", "catalog", "assessment", "doubt"}:
        for field in ["source_level", "difficulty"]:
            if not item.get(field):
                issues.append(f"missing_{field}")
    if item_type == "task" and not item.get("alignment_reason"):
        issues.append("missing_alignment_reason")
    if item_type == "packet":
        assessments = item.get("aligned_assessments") or []
        if not assessments or not all(a.get("alignment_reason") for a in assessments):
            issues.append("missing_alignment_reason")
    if float(item.get("quality_score", 1.0) or 0.0) < 0.85:
        issues.append("low_quality_score")
    text = _text(item)
    if any(marker in text for marker in BAD_MARKERS):
        issues.append("placeholder_marker")
    if re.fullmatch(r"\s*[A-Za-z]\s*", _text(item.get("output"))):
        issues.append("broken_one_letter_output")
    if re.search(r"\b(th|st|becom|elemen|Comp)\.", text):
        issues.append("broken_sentence_ending")

    output = item.get("output") or {}
    task_type = item.get("task_type") or ""
    if task_type == "mcq":
        if len(output.get("options") or []) != 4 or output.get("answer") not in {"A", "B", "C", "D"}:
            issues.append("malformed_mcq")
    if task_type in ASSESSMENT_TASKS and task_type != "true_or_false":
        answer = item.get("answer") or output.get("answer") or output.get("expected_output") or output.get("expected_fix") or output.get("back")
        if answer in (None, "", []):
            issues.append("missing_assessment_answer")
    if item_type in {"packet", "website_packet"} and not item.get("teaching_content"):
        issues.append("empty_teaching_content")
    if item.get("raw_valid") is False and item.get("fallback_applied") is not True:
        issues.append("raw_invalid_without_fallback")
    if item.get("rag_used") and not (item.get("rag_context_count") is not None and item.get("rag_sections") is not None):
        issues.append("missing_rag_grounding_metadata")
    if item_type == "website_packet":
        for field in FRONTEND_REQUIRED:
            if field not in item:
                issues.append(f"missing_frontend_field_{field}")
        tc = item.get("teaching_content") or {}
        fb = item.get("feedback_template") or {}
        for field in ["title", "beginner_explanation", "definition", "example"]:
            if not tc.get(field):
                issues.append(f"missing_teaching_content_{field}")
        for field in ["correct", "partial", "wrong"]:
            if not fb.get(field):
                issues.append(f"missing_feedback_{field}")

    status = "PASS" if not issues else ("WARN" if all(issue.startswith("missing_rag") for issue in issues) else "FAIL")
    return {
        "quality_gate_status": status,
        "website_ready": status == "PASS",
        "issues": issues,
    }


def apply_quality_gate(item: Dict[str, Any], *, item_type: str = "task") -> Dict[str, Any]:
    result = validate_content_item(item, item_type=item_type)
    item.update(result)
    return item
