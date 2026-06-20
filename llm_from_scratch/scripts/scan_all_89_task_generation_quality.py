import json
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List

from src.cognitutor_lm_config import ALL_TASK_GENERATED_OUTPUT, ALL_TASK_TYPES, REPORTS_DIR


OUT_JSON = REPORTS_DIR / "all_89_task_generation_quality_scan.json"
OUT_MD = REPORTS_DIR / "all_89_task_generation_quality_scan.md"
BAD_MARKERS = ("...", "TODO", "N/A", "placeholder")


def txt(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")


def has_bad_marker(value: Any) -> bool:
    text = txt(value)
    return any(marker in text for marker in BAD_MARKERS)


def schema_issues(row: Dict[str, Any]) -> List[str]:
    out = row.get("output")
    task = row.get("task_type")
    issues = []
    if not isinstance(out, dict) or not out:
        return ["missing_output_object"]
    if task == "mcq":
        if len(out.get("options") or []) != 4:
            issues.append("mcq_option_count")
        if out.get("answer") not in {"A", "B", "C", "D"}:
            issues.append("mcq_answer_key")
    if task == "fill_in_the_blank" and "____" not in out.get("question", ""):
        issues.append("fill_blank_missing_blank")
    if task == "true_or_false" and not isinstance(out.get("answer"), bool):
        issues.append("true_false_answer_not_boolean")
    if task in {"debug_task", "debug_challenge"} and not (out.get("buggy_code") and out.get("expected_fix")):
        issues.append("debug_schema")
    if task in {"output_prediction", "output_prediction_challenge"} and not (out.get("code") and out.get("expected_output")):
        issues.append("output_prediction_schema")
    if row.get("task_family") == "hint" and not out.get("hint"):
        issues.append("hint_empty")
    if row.get("task_family") == "feedback" and not all(out.get(k) for k in ["correct", "partial", "wrong"]):
        issues.append("feedback_schema")
    if row.get("task_family") == "flashcard" and not (out.get("front") and out.get("back")):
        issues.append("flashcard_schema")
    if row.get("task_family") == "mindmap" and not (out.get("center") and out.get("branches")):
        issues.append("mindmap_schema")
    if row.get("task_family") == "doubt" and not all(out.get(k) for k in ["answer", "reason", "example", "try_this"]):
        issues.append("doubt_schema")
    if row.get("task_family") == "notebook" and not all(out.get(k) for k in ["summary", "strengths", "weaknesses", "next_revision"]):
        issues.append("notebook_schema")
    if row.get("task_family") == "voice" and not out.get("script"):
        issues.append("voice_schema")
    if has_bad_marker(out):
        issues.append("bad_marker")
    if re.fullmatch(r"\s*[A-Za-z]\s*", txt(out)):
        issues.append("one_letter_output")
    if re.search(r"\b(th|st|becom|elemen|Comp)\.", txt(out)):
        issues.append("broken_sentence_ending")
    return issues


def main() -> None:
    rows = json.loads(ALL_TASK_GENERATED_OUTPUT.read_text(encoding="utf-8")) if ALL_TASK_GENERATED_OUTPUT.exists() else []
    task_set = {r.get("task_type") for r in rows}
    concepts = {(r.get("domain"), r.get("concept_id"), r.get("concept_name")) for r in rows}
    by_concept = defaultdict(list)
    for row in rows:
        by_concept[(row.get("domain"), row.get("concept_id"), row.get("concept_name"))].append(row)

    missing_tasks_by_concept = {
        " | ".join(k): sorted(set(ALL_TASK_TYPES) - {r.get("task_type") for r in v})
        for k, v in by_concept.items()
        if set(ALL_TASK_TYPES) - {r.get("task_type") for r in v}
    }
    extra_tasks = sorted(task_set - set(ALL_TASK_TYPES))
    missing_global = sorted(set(ALL_TASK_TYPES) - task_set)

    schema_failures = []
    invalid_rows = []
    low_quality_rows = []
    for idx, row in enumerate(rows):
        issues = []
        for required in ["output", "source_level", "task_family", "alignment_reason"]:
            if not row.get(required):
                issues.append(f"missing_{required}")
        if row.get("valid") is not True:
            invalid_rows.append(row)
            issues.append("valid_not_true")
        if float(row.get("quality_score", 0.0) or 0.0) < 0.85:
            low_quality_rows.append(row)
            issues.append("low_quality")
        issues.extend(schema_issues(row))
        if issues:
            schema_failures.append({"index": idx, "domain": row.get("domain"), "concept_id": row.get("concept_id"), "task_type": row.get("task_type"), "issues": issues})

    average_quality = round(sum(float(r.get("quality_score", 0.0) or 0.0) for r in rows) / len(rows), 4) if rows else 0.0
    expected_total = 38 * len(ALL_TASK_TYPES)
    pass_rule = (
        len(rows) == expected_total
        and len(concepts) == 38
        and len(task_set) == len(ALL_TASK_TYPES)
        and not missing_tasks_by_concept
        and not missing_global
        and not extra_tasks
        and not invalid_rows
        and not schema_failures
        and average_quality >= 0.95
    )
    report = {
        "file_exists": ALL_TASK_GENERATED_OUTPUT.exists(),
        "total_items": len(rows),
        "expected_total_items": expected_total,
        "concept_count": len(concepts),
        "task_type_count": len(task_set),
        "expected_task_type_count": len(ALL_TASK_TYPES),
        "missing_task_count": sum(len(v) for v in missing_tasks_by_concept.values()) + len(missing_global),
        "missing_tasks": missing_global,
        "missing_tasks_by_concept": missing_tasks_by_concept,
        "extra_tasks": extra_tasks,
        "invalid_count": len(invalid_rows),
        "low_quality_count": len(low_quality_rows),
        "bad_schema_count": len(schema_failures),
        "average_quality": average_quality,
        "failure_counts": dict(Counter(issue for item in schema_failures for issue in item["issues"])),
        "schema_failures_sample": schema_failures[:50],
        "status": "PASS" if pass_rule else "FAIL",
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# All-89 Task Generation Quality Scan\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"schema_failures_sample", "missing_tasks_by_concept"})
        + "\n",
        encoding="utf-8",
    )
    for key in ["total_items", "concept_count", "task_type_count", "missing_task_count", "invalid_count", "low_quality_count", "bad_schema_count", "status"]:
        print(f"{key}: {report[key]}")


if __name__ == "__main__":
    main()
