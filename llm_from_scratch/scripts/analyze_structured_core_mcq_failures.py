import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from scripts.structured_generation_common import ROOT_DIR
from scripts.inspect_structured_generation_quality import has_domain_noise, inspect_mcq
from src.model_content_validator import normalize_choice, parse_json_object


CORE_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
QUALITY_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_core_mcq_failure_analysis.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_core_mcq_failure_analysis.md"


def analyze_item(item: Dict[str, Any]) -> Dict[str, Any]:
    output = item.get("output", "")
    parsed = parse_json_object(output)
    options = parsed.get("options") if parsed else None
    answer = parsed.get("answer") if parsed else None
    explanation = parsed.get("explanation") if parsed else None
    semantic_score, option_score, quality_issues = inspect_mcq(item)

    reasons: List[str] = []
    if parsed is None:
        reasons.append("json_format_issue")
    if not isinstance(options, list):
        reasons.append("options_missing_or_not_list")
    else:
        if len(options) != 4:
            reasons.append("fewer_or_more_than_4_options")
        normalized = [normalize_choice(option) for option in options]
        if len(set(normalized)) != len(normalized):
            reasons.append("duplicate_options")
        if answer and normalize_choice(answer) not in set(normalized):
            reasons.append("answer_not_in_options")
    if not answer:
        reasons.append("missing_answer")
    if not explanation:
        reasons.append("missing_explanation")
    if any("explanation" in issue for issue in quality_issues):
        reasons.append("answer_explanation_mismatch_or_weak")
    if any("question_not_target" in issue for issue in quality_issues):
        reasons.append("concept_mismatch")
    if has_domain_noise(str(output), item.get("domain", "")):
        reasons.append("domain_mismatch")

    return {
        "item_id": item.get("item_id"),
        "domain": item.get("domain"),
        "concept_name": item.get("concept_name"),
        "raw_output": output,
        "parsed_json_status": "parsed" if parsed else "invalid_json",
        "options": options,
        "answer": answer,
        "answer_in_options": bool(
            isinstance(options, list)
            and answer
            and normalize_choice(answer) in {normalize_choice(option) for option in options}
        ),
        "duplicate_options": bool(
            isinstance(options, list)
            and len({normalize_choice(option) for option in options}) != len(options)
        ),
        "distractor_quality_issue": "mcq_options_not_list" in quality_issues
        or "mcq_duplicate_options" in quality_issues
        or option_score < 0.85,
        "explanation_quality_issue": not explanation or any("explanation" in issue for issue in quality_issues),
        "domain_relevance_issue": has_domain_noise(str(output), item.get("domain", "")),
        "semantic_score": semantic_score,
        "option_score": option_score,
        "quality_issues": quality_issues,
        "exact_reasons": reasons,
    }


def main() -> None:
    items = json.loads(CORE_JSON.read_text(encoding="utf-8")) if CORE_JSON.exists() else []
    quality = json.loads(QUALITY_JSON.read_text(encoding="utf-8")) if QUALITY_JSON.exists() else {}
    mcqs = [item for item in items if item.get("task_type") == "mcq"]
    analyses = [analyze_item(item) for item in mcqs]
    failed = [
        item
        for item in analyses
        if item["semantic_score"] < 0.85 or item["option_score"] < 0.85 or item["parsed_json_status"] != "parsed"
    ]
    by_domain = Counter(item["domain"] for item in failed)
    by_concept = Counter(item["concept_name"] for item in failed)
    by_reason = Counter(reason for item in failed for reason in item["exact_reasons"])
    parsed_failures = sum(1 for item in failed if item["parsed_json_status"] != "parsed")
    missing_field_failures = sum(
        1 for item in failed if "missing_answer" in item["exact_reasons"] or "missing_explanation" in item["exact_reasons"]
    )
    duplicate_failures = sum(1 for item in failed if item["duplicate_options"])

    if parsed_failures or missing_field_failures or duplicate_failures:
        cause = "generated_mcqs_are_actually_bad"
    else:
        cause = "evaluator_or_parser_issue"

    report = {
        "total_mcqs_attempted": len(mcqs),
        "mcqs_valid_by_item_flag": sum(1 for item in mcqs if item.get("valid")),
        "mcq_failed_count": len(failed),
        "option_failed_count": sum(1 for item in analyses if item["option_score"] < 0.85),
        "failed_by_domain": dict(by_domain),
        "failed_by_concept": dict(by_concept),
        "failed_by_reason": dict(by_reason),
        "failure_cause": cause,
        "quality_summary": quality.get("summary", {}),
        "mcq_items": analyses,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Structured Core MCQ Failure Analysis",
        "",
        f"- total_mcqs_attempted: {report['total_mcqs_attempted']}",
        f"- mcqs_valid_by_item_flag: {report['mcqs_valid_by_item_flag']}",
        f"- mcq_failed_count: {report['mcq_failed_count']}",
        f"- option_failed_count: {report['option_failed_count']}",
        f"- failure_cause: {report['failure_cause']}",
        f"- failed_by_domain: {report['failed_by_domain']}",
        f"- failed_by_reason: {report['failed_by_reason']}",
        "",
        "## Failed Examples",
    ]
    for item in failed[:20]:
        lines.extend(
            [
                "",
                f"### {item['item_id']} - {item['concept_name']}",
                f"- parsed_json_status: {item['parsed_json_status']}",
                f"- answer_in_options: {item['answer_in_options']}",
                f"- duplicate_options: {item['duplicate_options']}",
                f"- exact_reasons: {item['exact_reasons']}",
                f"- semantic_score: {item['semantic_score']}",
                f"- option_score: {item['option_score']}",
                "",
                "```text",
                str(item["raw_output"]),
                "```",
            ]
        )
    if not failed:
        lines.append("- None")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"total_mcqs_attempted: {report['total_mcqs_attempted']}")
    print(f"mcq_failed_count: {report['mcq_failed_count']}")
    print(f"option_failed_count: {report['option_failed_count']}")
    print(f"failure_cause: {report['failure_cause']}")
    print(f"report_path: {OUT_JSON}")


if __name__ == "__main__":
    main()
