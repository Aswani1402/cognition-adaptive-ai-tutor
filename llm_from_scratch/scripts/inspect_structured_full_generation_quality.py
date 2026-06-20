import json
from collections import Counter
from typing import Any, Dict, List

from scripts.inspect_structured_generation_quality import (
    concept_relevant,
    has_domain_noise,
    inspect_json_task,
    inspect_mcq,
    inspect_text_task,
    norm,
    style_match,
)
from scripts.structured_generation_common import ROOT_DIR


IN_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full.json"
FULL_REPORT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_quality_report.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_quality_report.md"

JSON_BASE_TASKS = {"flashcard", "debug_task", "output_prediction", "challenge_question", "mindmap"}
REQUIRED_FIELDS = {
    "item_id",
    "concept_id",
    "concept_name",
    "domain",
    "task_type",
    "base_task_type",
    "generation_source",
    "model_used",
    "prompt",
    "output",
    "valid",
    "quality_score",
    "issues",
    "created_at",
}


def avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 1.0


def as_core_item(item: Dict[str, Any]) -> Dict[str, Any]:
    mapped = dict(item)
    mapped["task_type"] = item.get("base_task_type") or item.get("task_type")
    return mapped


def website_ready(item: Dict[str, Any]) -> bool:
    return (
        REQUIRED_FIELDS.issubset(item)
        and item.get("generation_source") == "cognitutor_lm_from_scratch_structured_model"
        and item.get("model_used") == "CogniTutorLM-from-scratch-structured"
        and bool(str(item.get("output", "")).strip())
        and item.get("valid") is True
        and float(item.get("quality_score", 0.0) or 0.0) >= 0.85
    )


def main() -> None:
    items = json.loads(IN_JSON.read_text(encoding="utf-8")) if IN_JSON.exists() else []
    output_counts = Counter(norm(item.get("output")) for item in items)
    repeated_outputs = sum(count for output, count in output_counts.items() if output and count > 1)
    duplicate_output_count = sum(1 for output, count in output_counts.items() if output and count > 1)
    repetition_rate = round(repeated_outputs / len(items), 4) if items else 0.0

    semantic_scores = []
    logical_scores = []
    domain_scores = []
    mcq_scores = []
    option_scores = []
    item_reports = []

    for item in items:
        base_item = as_core_item(item)
        base_task = base_item.get("task_type")
        option_score = None
        if base_task == "mcq":
            semantic_score, option_score, issues = inspect_mcq(base_item)
            mcq_scores.append(semantic_score)
            option_scores.append(option_score)
        elif base_task in JSON_BASE_TASKS:
            semantic_score, issues = inspect_json_task(base_item)
        else:
            semantic_score, issues = inspect_text_task(base_item)

        output = str(item.get("output", ""))
        logical_score = semantic_score if item.get("valid") else 0.0
        domain_score = 1.0 if concept_relevant(base_item, output) and not has_domain_noise(output, item.get("domain", "")) else 0.0
        semantic_scores.append(semantic_score)
        logical_scores.append(logical_score)
        domain_scores.append(domain_score)

        passed = (
            website_ready(item)
            and semantic_score >= 0.85
            and logical_score >= 0.85
            and domain_score >= 0.85
            and style_match(base_item)
        )
        if base_task == "mcq" and (semantic_score < 0.85 or (option_score or 0.0) < 0.85):
            passed = False
        item_reports.append(
            {
                "item_id": item.get("item_id"),
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": item.get("task_type"),
                "base_task_type": base_task,
                "valid": item.get("valid"),
                "website_ready": website_ready(item),
                "semantic_score": semantic_score,
                "logical_score": logical_score,
                "domain_score": domain_score,
                "option_score": option_score,
                "issues": issues,
                "validation_issues": item.get("issues", []),
                "passed_quality": passed,
                "output": item.get("output", ""),
            }
        )

    attempted = len(items)
    valid = sum(1 for item in items if item.get("valid") is True)
    website_ready_count = sum(1 for item in items if website_ready(item))
    failed = [item for item in item_reports if not item["passed_quality"]]
    summary = {
        "full_attempted": attempted,
        "full_valid": valid,
        "full_valid_rate": round(valid / attempted, 4) if attempted else 0.0,
        "full_avg_quality_score": round(sum(float(item.get("quality_score", 0.0) or 0.0) for item in items) / attempted, 4) if attempted else 0.0,
        "full_website_ready_rate": round(website_ready_count / attempted, 4) if attempted else 0.0,
        "full_semantic_quality_score": avg(semantic_scores),
        "full_mcq_quality_score": avg(mcq_scores),
        "full_option_quality_score": avg(option_scores),
        "full_logical_consistency_score": avg(logical_scores),
        "full_domain_relevance_score": avg(domain_scores),
        "full_repetition_rate": repetition_rate,
        "full_duplicate_output_count": duplicate_output_count,
        "full_failed_quality_items": len(failed),
    }
    pass_rule = (
        summary["full_valid_rate"] >= 0.85
        and summary["full_avg_quality_score"] >= 0.85
        and summary["full_website_ready_rate"] >= 0.85
        and summary["full_mcq_quality_score"] >= 0.85
        and summary["full_option_quality_score"] >= 0.85
        and summary["full_logical_consistency_score"] >= 0.85
        and summary["full_domain_relevance_score"] >= 0.85
        and summary["full_repetition_rate"] <= 0.15
    )
    summary["full_quality_status"] = "PASS" if pass_rule else ("WARN" if attempted else "FAIL")

    report = {"summary": summary, "failed_quality_examples": failed[:60], "item_reports": item_reports}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if FULL_REPORT_JSON.exists():
        full_report = json.loads(FULL_REPORT_JSON.read_text(encoding="utf-8"))
        full_report.update(summary)
        FULL_REPORT_JSON.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Structured Full Generation Quality Report", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Failed Quality Examples"])
    if failed:
        for item in failed[:60]:
            lines.extend(
                [
                    "",
                    f"### {item['domain']} {item['concept_name']} - {item['task_type']}",
                    f"- item_id: {item['item_id']}",
                    f"- base_task_type: {item['base_task_type']}",
                    f"- issues: {item['issues']}",
                    f"- validation_issues: {item['validation_issues']}",
                    f"- semantic_score: {item['semantic_score']}",
                    f"- logical_score: {item['logical_score']}",
                    "",
                    "```text",
                    str(item["output"]),
                    "```",
                ]
            )
    else:
        lines.append("- None")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
