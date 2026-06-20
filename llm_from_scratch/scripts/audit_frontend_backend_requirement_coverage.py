import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
STRUCTURED_CORE_PATH = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
WEBSITE_MODE_REPORT_PATH = ROOT_DIR / "outputs" / "service_tests" / "structured_model_website_mode_report.json"
BACKEND_REPORT_PATH = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_lm_backend_report.json"
ARTIFACTS_PATH = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"
TRAINING_DIR = ROOT_DIR / "training_data" / "structured_generation"

OUTPUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "frontend_backend_requirement_coverage_audit.json"
OUTPUT_MD = ROOT_DIR / "outputs" / "final_reports" / "frontend_backend_requirement_coverage_audit.md"

EXPECTED_SOURCE = "cognitutor_lm_from_scratch_structured_model"
REQUIRED_METADATA_FIELDS = [
    "item_id",
    "concept_id",
    "concept_name",
    "domain",
    "task_type",
    "generation_source",
    "model_used",
    "output",
    "valid",
    "quality_score",
    "issues",
]

REQUIRED_FRONTEND_TASKS = [
    "explanation",
    "definition_view OR explanation",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view OR debug_task",
    "output_prediction_view OR output_prediction",
    "transfer_view OR transfer_question",
    "challenge_view OR challenge_question",
    "revision_summary_view OR revision_summary",
    "mcq",
    "syntax_completion",
    "coding_prompt",
    "flashcard",
    "mindmap",
    "feedback",
    "hint",
    "doubt_answer",
    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "weakness_review",
    "daily_review",
    "personal_flashcards",
    "comeback_summary",
    "returning_learner_summary",
    "practice_question",
    "transfer_task",
    "voice_script",
]

CRITICAL_TASKS = [
    "explanation",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "revision_summary",
    "flashcard",
    "mindmap",
    "hint",
    "feedback",
    "doubt_answer",
    "voice_script",
]

FETCH_TESTS = [
    {"domain": "Python", "concept": "Loops", "task_type": "debug_task"},
    {"domain": "Python", "concept": "Variables", "task_type": "explanation"},
    {"domain": "SQL", "concept": "SELECT", "task_type": "mcq"},
    {"domain": "HTML", "concept": "Tags", "task_type": "flashcard"},
    {"domain": "Git", "concept": "Commits", "task_type": "revision_summary"},
    {"domain": "Data Structures", "concept": "Linked List", "task_type": "challenge_question"},
    {"domain": "Data Structures", "concept": "Stack", "task_type": "mindmap"},
    {"domain": "Python", "concept": "Functions", "task_type": "hint"},
    {"domain": "SQL", "concept": "WHERE", "task_type": "output_prediction"},
    {"domain": "Git", "concept": "Branches", "task_type": "doubt_answer"},
    {"domain": "HTML", "concept": "Forms", "task_type": "voice_script"},
]

SERVICE_OUTPUT_CHECKS = {
    "teaching_card_output": ["explanation"],
    "assessment_output": ["mcq", "output_prediction", "challenge_question"],
    "debug_code_output": ["debug_task", "output_prediction"],
    "flashcard_output": ["flashcard"],
    "mindmap_output": ["mindmap"],
    "hint_output": ["hint"],
    "revision_output": ["revision_summary"],
    "doubt_answer_output": ["doubt_answer"],
    "voice_script_output": ["voice_script"],
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def concept_matches(concept_name: str, query: str) -> bool:
    concept = norm(concept_name)
    query_norm = norm(query)
    if query_norm in concept:
        return True
    return all(token in concept for token in query_norm.split())


def task_expr_covered(expr: str, task_types: set[str]) -> bool:
    return any(part.strip() in task_types for part in expr.split(" OR "))


def preferred_missing_name(expr: str) -> str:
    parts = [part.strip() for part in expr.split(" OR ")]
    return parts[-1] if len(parts) > 1 else parts[0]


def collect_training_task_types() -> set[str]:
    task_types: set[str] = set()
    for path in TRAINING_DIR.glob("*.jsonl"):
        for row in load_jsonl(path):
            if row.get("task_type"):
                task_types.add(str(row["task_type"]))
            text = " ".join(str(row.get(key, "")) for key in ("input", "training_text"))
            for match in re.findall(r"<task_([a-zA-Z0-9_]+)>", text):
                task_types.add(match)
                if match == "revision":
                    task_types.add("revision_summary")
    return task_types


def collect_baseline_task_types() -> set[str]:
    task_types: set[str] = set()
    for row in load_json(ARTIFACTS_PATH, []):
        if row.get("artifact_type"):
            task_types.add(str(row["artifact_type"]))
    for row in load_json(QUESTION_BANK_PATH, []):
        if row.get("question_type"):
            task_types.add(str(row["question_type"]))
    return task_types


def find_fetch_item(items: list[dict[str, Any]], domain: str, concept: str, task_type: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("domain") != domain:
            continue
        if item.get("task_type") != task_type:
            continue
        if concept_matches(str(item.get("concept_name", "")), concept) or norm(concept) == norm(item.get("concept_id")):
            return item
    return None


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Frontend Backend Requirement Coverage Audit",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Final status: **{report['final_status']}**",
        "",
        "## Summary",
        "",
        f"- Required task types: {report['required_task_types_count']}",
        f"- Covered task types: {report['covered_task_types_count']}",
        f"- Frontend ready rate: {report['frontend_ready_rate']:.4f}",
        f"- Website mode supported: {report['website_mode_supported']}",
        f"- Metadata field status: {report['metadata_field_status']['status']}",
        f"- Fetch test status: {report['fetch_test_status']['status']}",
        f"- Template fallback used: {report['template_fallback_used']}",
        f"- Generation source OK: {report['generation_source_status']['status']}",
        "",
        "## Covered Task Types",
        "",
        ", ".join(report["covered_task_types"]) or "None",
        "",
        "## Missing Task Types",
        "",
        ", ".join(report["missing_task_types"]) or "None",
        "",
        "## Critical Missing Task Types",
        "",
        ", ".join(report["critical_missing_task_types"]) or "None",
        "",
        "## Fetch Tests",
        "",
        "| Domain | Concept | Task Type | Status | Matched Item |",
        "|---|---|---|---|---|",
    ]
    for test in report["fetch_tests"]:
        lines.append(
            f"| {test['domain']} | {test['concept']} | {test['task_type']} | {test['status']} | {test.get('matched_item_id') or ''} |"
        )

    lines.extend([
        "",
        "## Missing Backend Items For Frontend",
        "",
        "| Missing task type | Training dataset | Baseline/template | Needs full generation | Needs generator support |",
        "|---|---:|---:|---:|---:|",
    ])
    for item in report["missing_backend_items_for_frontend"]:
        lines.append(
            f"| {item['missing_task_type']} | {item['exists_in_training_dataset']} | {item['exists_only_in_baseline_template_outputs']} | {item['needs_full_generation']} | {item['needs_new_generator_support']} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        "- Coverage is measured against `outputs/model_generated/structured_model_generated_core.json` for generated structured outputs.",
        "- Training dataset and baseline/template banks are used only to diagnose missing generated task types.",
        "- PASS is only assigned when all critical task types, fetch tests, metadata, website mode, source, ready-rate, and no-template-fallback gates pass.",
        "",
    ])

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    core_items = load_json(STRUCTURED_CORE_PATH, [])
    website_report = load_json(WEBSITE_MODE_REPORT_PATH, {})
    backend_report = load_json(BACKEND_REPORT_PATH, {})

    task_types = {str(item.get("task_type")) for item in core_items if item.get("task_type")}
    task_counts = Counter(str(item.get("task_type")) for item in core_items if item.get("task_type"))
    required_status = {
        expr: {
            "covered": task_expr_covered(expr, task_types),
            "matched_task_types": [part.strip() for part in expr.split(" OR ") if part.strip() in task_types],
        }
        for expr in REQUIRED_FRONTEND_TASKS
    }
    missing_task_exprs = [expr for expr, status in required_status.items() if not status["covered"]]
    missing_task_types = [preferred_missing_name(expr) for expr in missing_task_exprs]
    critical_missing = [task for task in CRITICAL_TASKS if task not in task_types]

    metadata_missing_by_item = []
    for item in core_items:
        missing_fields = [field for field in REQUIRED_METADATA_FIELDS if field not in item]
        if missing_fields:
            metadata_missing_by_item.append({"item_id": item.get("item_id"), "missing_fields": missing_fields})
    metadata_status = {
        "status": "PASS" if not metadata_missing_by_item else "FAIL",
        "required_fields": REQUIRED_METADATA_FIELDS,
        "missing_item_count": len(metadata_missing_by_item),
        "missing_by_item_sample": metadata_missing_by_item[:25],
    }

    source_bad = [
        item.get("item_id")
        for item in core_items
        if item.get("generation_source") != EXPECTED_SOURCE
    ]
    source_status = {
        "status": "PASS" if not source_bad else "FAIL",
        "expected_generation_source": EXPECTED_SOURCE,
        "bad_item_count": len(source_bad),
        "bad_item_sample": source_bad[:25],
    }

    fetch_tests = []
    for test in FETCH_TESTS:
        match = find_fetch_item(core_items, test["domain"], test["concept"], test["task_type"])
        fetch_tests.append(
            {
                **test,
                "status": "PASS" if match else "FAIL",
                "matched_item_id": match.get("item_id") if match else None,
                "valid": match.get("valid") if match else None,
                "quality_score": match.get("quality_score") if match else None,
            }
        )
    fetch_status = {
        "status": "PASS" if all(test["status"] == "PASS" for test in fetch_tests) else "FAIL",
        "passed": sum(1 for test in fetch_tests if test["status"] == "PASS"),
        "total": len(fetch_tests),
    }

    frontend_api_checks = {
        name: {
            "status": "PASS" if all(task in task_types for task in required_tasks) else "FAIL",
            "required_task_types": required_tasks,
            "missing_task_types": [task for task in required_tasks if task not in task_types],
        }
        for name, required_tasks in SERVICE_OUTPUT_CHECKS.items()
    }

    training_task_types = collect_training_task_types()
    baseline_task_types = collect_baseline_task_types()
    missing_backend_items = []
    for missing in missing_task_types:
        in_training = missing in training_task_types
        in_baseline = missing in baseline_task_types
        missing_backend_items.append(
            {
                "missing_task_type": missing,
                "exists_in_training_dataset": in_training,
                "exists_only_in_baseline_template_outputs": in_baseline and not in_training,
                "needs_full_generation": in_training or in_baseline,
                "needs_new_generator_support": not in_training,
            }
        )

    frontend_ready_rate = float(
        website_report.get(
            "website_ready_rate",
            sum(1 for item in core_items if item.get("valid") is True) / len(core_items) if core_items else 0.0,
        )
    )
    template_fallback_used = bool(website_report.get("template_fallback_used", True))
    service_mode = website_report.get("service_mode")
    website_mode_supported = (
        website_report.get("status") == "PASS"
        and service_mode == "structured_model_generated"
        and not template_fallback_used
    )

    pass_gates = {
        "critical_task_types_present": not critical_missing,
        "frontend_ready_rate_at_least_0_85": frontend_ready_rate >= 0.85,
        "exact_fetch_tests_pass": fetch_status["status"] == "PASS",
        "no_template_fallback_used": not template_fallback_used,
        "generation_source_is_structured_model": source_status["status"] == "PASS",
        "metadata_fields_present": metadata_status["status"] == "PASS",
        "website_mode_supported": website_mode_supported,
    }

    if all(pass_gates.values()) and not missing_task_types:
        final_status = "PASS"
    elif all(pass_gates.values()):
        final_status = "WARN"
    else:
        final_status = "FAIL"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_files": {
            "structured_core": str(STRUCTURED_CORE_PATH),
            "website_mode_report": str(WEBSITE_MODE_REPORT_PATH),
            "backend_report": str(BACKEND_REPORT_PATH),
        },
        "required_task_types_count": len(REQUIRED_FRONTEND_TASKS),
        "covered_task_types_count": sum(1 for status in required_status.values() if status["covered"]),
        "covered_task_types": sorted(task_types),
        "task_type_counts": dict(sorted(task_counts.items())),
        "required_task_type_status": required_status,
        "missing_task_types": missing_task_types,
        "critical_task_types": CRITICAL_TASKS,
        "critical_missing_task_types": critical_missing,
        "metadata_field_status": metadata_status,
        "generation_source_status": source_status,
        "fetch_test_status": fetch_status,
        "fetch_tests": fetch_tests,
        "frontend_api_readiness": frontend_api_checks,
        "frontend_ready_rate": frontend_ready_rate,
        "website_mode_supported": website_mode_supported,
        "service_mode": service_mode,
        "template_fallback_used": template_fallback_used,
        "missing_backend_items_for_frontend": missing_backend_items,
        "training_task_types": sorted(training_task_types),
        "baseline_template_task_types": sorted(baseline_task_types),
        "pass_gates": pass_gates,
        "backend_report_structured_generation_status": backend_report.get("summary", {}).get("structured_generation_upgrade", {}),
        "final_status": final_status,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)

    print(f"required_task_types_count: {report['required_task_types_count']}")
    print(f"covered_task_types_count: {report['covered_task_types_count']}")
    print(f"missing_task_types: {report['missing_task_types']}")
    print(f"metadata_field_status: {report['metadata_field_status']['status']}")
    print(f"fetch_test_status: {report['fetch_test_status']['status']}")
    print(f"frontend_ready_rate: {report['frontend_ready_rate']:.4f}")
    print(f"website_mode_supported: {report['website_mode_supported']}")
    print(f"missing_backend_items_for_frontend: {report['missing_backend_items_for_frontend']}")
    print(f"final_status: {report['final_status']}")


if __name__ == "__main__":
    main()
