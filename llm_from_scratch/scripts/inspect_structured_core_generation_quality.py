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


IN_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
CORE_REPORT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.md"

REQUIRED_FIELDS = {
    "item_id",
    "concept_id",
    "concept_name",
    "domain",
    "task_type",
    "generation_source",
    "model_used",
    "prompt",
    "output",
    "valid",
    "quality_score",
    "issues",
    "created_at",
    "raw_model_output",
    "extracted_output",
    "raw_valid",
    "final_valid",
    "raw_quality_score",
    "final_quality_score",
    "fallback_applied",
}


def avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 1.0


def website_ready(item: Dict[str, Any]) -> bool:
    return (
        REQUIRED_FIELDS.issubset(item)
        and item.get("generation_source") in {
            "cognitutor_lm_from_scratch_structured_model",
            "cognitutor_lm_from_scratch_structured_model_guarded_pipeline",
        }
        and item.get("model_used") == "CogniTutorLM-from-scratch-structured"
        and bool(str(item.get("output", "")).strip())
        and item.get("final_valid", item.get("valid")) is True
        and float(item.get("final_quality_score", item.get("quality_score", 0.0)) or 0.0) >= 0.85
    )


def main() -> None:
    items = json.loads(IN_JSON.read_text(encoding="utf-8")) if IN_JSON.exists() else []
    output_counts = Counter(norm(item.get("output")) for item in items)
    repeated_outputs = sum(count for output, count in output_counts.items() if output and count > 1)
    duplicate_output_count = sum(1 for output, count in output_counts.items() if output and count > 1)
    repetition_rate = round(repeated_outputs / len(items), 4) if items else 0.0
    teaching_variation_score = round(max(0.0, 1.0 - repetition_rate - (duplicate_output_count / max(1, len(items)))), 4)

    semantic_scores = []
    logical_scores = []
    domain_scores = []
    mcq_scores = []
    option_scores = []
    item_reports = []
    raw_valid_count = 0
    raw_quality_scores = []
    fallback_count = 0

    for item in items:
        raw_valid_count += 1 if item.get("raw_valid") else 0
        raw_quality_scores.append(float(item.get("raw_quality_score", 0.0) or 0.0))
        fallback_count += 1 if item.get("fallback_applied") else 0
        task = item.get("task_type")
        option_score = None
        if task == "mcq":
            semantic_score, option_score, issues = inspect_mcq(item)
            mcq_scores.append(semantic_score)
            option_scores.append(option_score)
        elif task in {"flashcard", "debug_task", "output_prediction", "challenge_question", "mindmap"}:
            semantic_score, issues = inspect_json_task(item)
        else:
            semantic_score, issues = inspect_text_task(item)
        output = str(item.get("output", ""))
        logical_score = semantic_score if item.get("final_valid", item.get("valid")) else 0.0
        domain_score = 1.0 if concept_relevant(item, output) and not has_domain_noise(output, item.get("domain", "")) else 0.0
        semantic_scores.append(semantic_score)
        logical_scores.append(logical_score)
        domain_scores.append(domain_score)
        passed = (
            website_ready(item)
            and semantic_score >= 0.85
            and logical_score >= 0.85
            and domain_score >= 0.85
            and style_match(item)
        )
        if task == "mcq" and (semantic_score < 0.85 or (option_score or 0.0) < 0.85):
            passed = False
        item_reports.append(
            {
                "item_id": item.get("item_id"),
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": task,
                "raw_valid": item.get("raw_valid"),
                "valid": item.get("final_valid", item.get("valid")),
                "website_ready": website_ready(item),
                "semantic_score": semantic_score,
                "logical_score": logical_score,
                "domain_score": domain_score,
                "option_score": option_score,
                "issues": issues,
                "validation_issues": item.get("issues", []),
                "raw_issues": item.get("raw_issues", []),
                "final_issues": item.get("final_issues", item.get("issues", [])),
                "fallback_applied": item.get("fallback_applied"),
                "passed_quality": passed,
                "output": item.get("output", ""),
                "raw_model_output": item.get("raw_model_output", ""),
            }
        )

    attempted = len(items)
    valid = sum(1 for item in items if item.get("final_valid", item.get("valid")))
    website_ready_count = sum(1 for item in items if website_ready(item))
    core_valid_rate = round(valid / attempted, 4) if attempted else 0.0
    raw_valid_rate = round(raw_valid_count / attempted, 4) if attempted else 0.0
    core_avg_quality_score = round(sum(float(item.get("final_quality_score", item.get("quality_score", 0.0)) or 0.0) for item in items) / attempted, 4) if attempted else 0.0
    raw_avg_quality_score = avg(raw_quality_scores)
    core_website_ready_rate = round(website_ready_count / attempted, 4) if attempted else 0.0
    failed = [item for item in item_reports if not item["passed_quality"]]
    summary = {
        "core_attempted": attempted,
        "raw_valid_count": raw_valid_count,
        "raw_valid_rate": raw_valid_rate,
        "raw_avg_quality_score": raw_avg_quality_score,
        "core_valid": valid,
        "core_valid_rate": core_valid_rate,
        "final_valid_count": valid,
        "final_valid_rate": core_valid_rate,
        "core_avg_quality_score": core_avg_quality_score,
        "final_avg_quality_score": core_avg_quality_score,
        "core_website_ready_rate": core_website_ready_rate,
        "website_ready_rate": core_website_ready_rate,
        "fallback_applied_count": fallback_count,
        "fallback_rate": round(fallback_count / attempted, 4) if attempted else 0.0,
        "core_semantic_quality_score": avg(semantic_scores),
        "core_mcq_quality_score": avg(mcq_scores),
        "core_option_quality_score": avg(option_scores),
        "core_logical_consistency_score": avg(logical_scores),
        "core_domain_relevance_score": avg(domain_scores),
        "core_teaching_variation_score": teaching_variation_score,
        "core_repetition_rate": repetition_rate,
        "core_duplicate_output_count": duplicate_output_count,
        "core_failed_quality_items": len(failed),
    }
    pass_rule = (
        core_valid_rate >= 0.85
        and core_avg_quality_score >= 0.85
        and core_website_ready_rate >= 0.85
        and summary["core_mcq_quality_score"] >= 0.85
        and summary["core_option_quality_score"] >= 0.85
        and summary["core_logical_consistency_score"] >= 0.85
        and summary["core_domain_relevance_score"] >= 0.85
        and repetition_rate <= 0.15
    )
    summary["core_quality_status"] = "PASS" if pass_rule else ("WARN" if attempted else "FAIL")
    summary["raw_generation_status"] = "PASS" if raw_valid_rate >= 0.85 and raw_avg_quality_score >= 0.85 else ("WARN" if attempted else "FAIL")
    summary["final_guarded_generation_status"] = summary["core_quality_status"]
    summary["website_mode_allowed"] = bool(pass_rule)
    summary["full_generation_allowed"] = bool(pass_rule)

    report = {"summary": summary, "failed_quality_examples": failed[:40], "item_reports": item_reports}
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    existing_core = json.loads(CORE_REPORT_JSON.read_text(encoding="utf-8")) if CORE_REPORT_JSON.exists() else {}
    existing_core.update(
        {
            "website_ready_count": website_ready_count,
            "website_ready_rate": core_website_ready_rate,
            "quality_inspection_status": summary["core_quality_status"],
            "raw_generation_status": summary["raw_generation_status"],
            "final_guarded_generation_status": summary["final_guarded_generation_status"],
            "raw_valid_count": raw_valid_count,
            "raw_valid_rate": raw_valid_rate,
            "raw_avg_quality_score": raw_avg_quality_score,
            "final_valid_count": valid,
            "final_valid_rate": core_valid_rate,
            "final_avg_quality_score": core_avg_quality_score,
            "fallback_applied_count": fallback_count,
            "fallback_rate": summary["fallback_rate"],
            "quality_report_path": str(OUT_JSON),
            "website_mode_allowed": summary["website_mode_allowed"],
            "full_generation_allowed": summary["full_generation_allowed"],
        }
    )
    CORE_REPORT_JSON.write_text(json.dumps(existing_core, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Structured Core Generation Quality Report", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Failed Quality Examples"])
    if failed:
        for item in failed[:40]:
            lines.extend(
                [
                    "",
                    f"### {item['domain']} {item['concept_name']} - {item['task_type']}",
                    f"- item_id: {item['item_id']}",
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
