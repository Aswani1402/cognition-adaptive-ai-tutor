import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from scripts.structured_generation_common import ROOT_DIR


CORE_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
QUALITY_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_core_failure_analysis.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_core_failure_analysis.md"
MCQ_OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_core_mcq_failure_analysis.json"
MCQ_OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_core_mcq_failure_analysis.md"


def classify(item: Dict[str, Any]) -> List[str]:
    task = item.get("task_type")
    issues = item.get("issues", []) + item.get("validation_issues", [])
    reasons = []
    if not item.get("valid") or any("broken_json" in issue or "invalid_json" in issue for issue in issues):
        reasons.append("model output format/json failure")
    if task == "mcq" and (item.get("option_score") or 0.0) < 0.85:
        reasons.append("MCQ option quality below threshold")
    if task == "mcq" and (item.get("semantic_score") or 0.0) < 0.85:
        reasons.append("MCQ semantic quality below threshold")
    if (item.get("domain_score") or 0.0) < 0.85:
        reasons.append("domain/concept relevance weakness")
    if (item.get("logical_score") or 0.0) < 0.85:
        reasons.append("logical consistency weakness")
    if any("duplicate" in issue for issue in issues):
        reasons.append("duplicate/repetition issue")
    if task in {"output_prediction", "debug_task", "mcq"} and reasons:
        reasons.append("training data weakness likely")
    if reasons and task in {"mcq", "output_prediction"}:
        reasons.append("prompt/checkpoint generalization issue")
    return reasons or ["quality threshold failure"]


def classify_mcq(item: Dict[str, Any]) -> List[str]:
    reasons = []
    output = str(item.get("output", ""))
    issues = item.get("issues", []) + item.get("validation_issues", [])
    if "mcq_broken_json" in issues or "mcq_invalid_json" in issues:
        reasons.append("JSON format issue")
    if "mcq_not_exactly_4_options" in issues or "mcq_options_not_exactly_4" in issues:
        reasons.append("fewer/more than 4 options")
    if "mcq_duplicate_options" in issues:
        reasons.append("duplicate options")
    if "mcq_answer_not_in_options" in issues:
        reasons.append("answer not in options")
    if (item.get("option_score") or 0.0) < 0.85:
        reasons.append("weak/random distractors")
    if "mcq_explanation_weak_or_unrelated" in issues:
        reasons.append("answer/explanation mismatch")
    if "mcq_question_not_target_concept" in issues:
        reasons.append("concept mismatch")
    if (item.get("domain_score") or 0.0) < 0.85:
        reasons.append("domain mismatch")
    return reasons or ["quality threshold failure"]


def main() -> None:
    core_items = json.loads(CORE_JSON.read_text(encoding="utf-8")) if CORE_JSON.exists() else []
    quality = json.loads(QUALITY_JSON.read_text(encoding="utf-8")) if QUALITY_JSON.exists() else {}
    reports = quality.get("item_reports", [])
    failed = [item for item in reports if not item.get("passed_quality")]

    by_task = Counter(item.get("task_type") for item in failed)
    by_domain = Counter(item.get("domain") for item in failed)
    by_concept = Counter(f"{item.get('domain')}:{item.get('concept_id')}:{item.get('concept_name')}" for item in failed)
    mcq_failures = [item for item in failed if item.get("task_type") == "mcq"]
    option_failures = [item for item in failed if item.get("task_type") == "mcq" and (item.get("option_score") or 0.0) < 0.85]
    duplicate_failures = [item for item in failed if any("duplicate" in issue for issue in item.get("issues", []))]

    detailed = []
    for item in failed:
        detailed.append(
            {
                "item_id": item.get("item_id"),
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": item.get("task_type"),
                "valid": item.get("valid"),
                "semantic_score": item.get("semantic_score"),
                "logical_score": item.get("logical_score"),
                "domain_score": item.get("domain_score"),
                "option_score": item.get("option_score"),
                "issues": item.get("issues", []),
                "validation_issues": item.get("validation_issues", []),
                "failure_reasons": classify(item),
                "issue_origin": sorted(set(reason for reason in classify(item) if reason.endswith("issue") or reason.endswith("weakness") or "model" in reason or "training" in reason or "prompt" in reason)),
                "output": item.get("output", ""),
            }
        )

    analysis = {
        "failed_item_count": len(failed),
        "failed_by_task_type": dict(by_task),
        "failed_by_domain": dict(by_domain),
        "failed_by_concept": dict(by_concept),
        "mcq_failure_count": len(mcq_failures),
        "option_failure_count": len(option_failures),
        "duplicate_repetition_failure_count": len(duplicate_failures),
        "core_quality_summary": quality.get("summary", {}),
        "mcq_failures": detailed[:],
        "example_failed_outputs": detailed[:30],
        "all_failed_items": detailed,
    }
    analysis["mcq_failures"] = [item for item in detailed if item["task_type"] == "mcq"]

    mcq_reports = [item for item in reports if item.get("task_type") == "mcq"]
    mcq_failed_reports = [item for item in mcq_reports if not item.get("passed_quality")]
    mcq_analysis = {
        "total_mcqs_attempted": len(mcq_reports),
        "mcqs_valid": sum(1 for item in mcq_reports if item.get("valid")),
        "mcq_failed_count": len(mcq_failed_reports),
        "option_failed_count": sum(1 for item in mcq_failed_reports if (item.get("option_score") or 0.0) < 0.85),
        "failed_by_domain": dict(Counter(item.get("domain") for item in mcq_failed_reports)),
        "failed_by_concept": dict(Counter(f"{item.get('domain')}:{item.get('concept_id')}:{item.get('concept_name')}" for item in mcq_failed_reports)),
        "failed_examples": [
            {
                "item_id": item.get("item_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "raw_output": item.get("output", ""),
                "validation_issues": item.get("validation_issues", []),
                "quality_issues": item.get("issues", []),
                "semantic_score": item.get("semantic_score"),
                "option_score": item.get("option_score"),
                "failure_reasons": classify_mcq(item),
            }
            for item in mcq_failed_reports
        ],
    }
    MCQ_OUT_JSON.write_text(json.dumps(mcq_analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    mcq_lines = [
        "# Structured Core MCQ Failure Analysis",
        "",
        f"- total_mcqs_attempted: {mcq_analysis['total_mcqs_attempted']}",
        f"- mcqs_valid: {mcq_analysis['mcqs_valid']}",
        f"- mcq_failed_count: {mcq_analysis['mcq_failed_count']}",
        f"- option_failed_count: {mcq_analysis['option_failed_count']}",
        f"- failed_by_domain: {mcq_analysis['failed_by_domain']}",
        f"- failed_by_concept: {mcq_analysis['failed_by_concept']}",
        "",
        "## Failed Examples",
    ]
    for item in mcq_analysis["failed_examples"]:
        mcq_lines.extend([
            "",
            f"### {item['item_id']}",
            f"- concept_name: {item['concept_name']}",
            f"- domain: {item['domain']}",
            f"- validation_issues: {item['validation_issues']}",
            f"- quality_issues: {item['quality_issues']}",
            f"- semantic_score: {item['semantic_score']}",
            f"- option_score: {item['option_score']}",
            f"- failure_reasons: {item['failure_reasons']}",
            "",
            "```text",
            str(item["raw_output"]),
            "```",
        ])
    if not mcq_analysis["failed_examples"]:
        mcq_lines.append("- None")
    MCQ_OUT_MD.write_text("\n".join(mcq_lines) + "\n", encoding="utf-8")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Structured Core Failure Analysis",
        "",
        f"- failed_item_count: {analysis['failed_item_count']}",
        f"- failed_by_task_type: {analysis['failed_by_task_type']}",
        f"- failed_by_domain: {analysis['failed_by_domain']}",
        f"- mcq_failure_count: {analysis['mcq_failure_count']}",
        f"- option_failure_count: {analysis['option_failure_count']}",
        f"- duplicate_repetition_failure_count: {analysis['duplicate_repetition_failure_count']}",
        "",
        "## Failed Examples",
    ]
    for item in detailed[:30]:
        lines.extend(
            [
                "",
                f"### {item['item_id']}",
                f"- task_type: {item['task_type']}",
                f"- domain: {item['domain']}",
                f"- concept_name: {item['concept_name']}",
                f"- valid: {item['valid']}",
                f"- scores: semantic={item['semantic_score']}, logical={item['logical_score']}, domain={item['domain_score']}, option={item['option_score']}",
                f"- validation_issues: {item['validation_issues']}",
                f"- quality_issues: {item['issues']}",
                f"- failure_reasons: {item['failure_reasons']}",
                "",
                "```text",
                str(item["output"]),
                "```",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"failed_item_count: {analysis['failed_item_count']}")
    print(f"failed_by_task_type: {analysis['failed_by_task_type']}")
    print(f"failed_by_domain: {analysis['failed_by_domain']}")
    print(f"mcq_failure_count: {analysis['mcq_failure_count']}")
    print(f"option_failure_count: {analysis['option_failure_count']}")
    print(f"duplicate_repetition_failure_count: {analysis['duplicate_repetition_failure_count']}")


if __name__ == "__main__":
    main()
