import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


ROOT_DIR = Path(__file__).resolve().parents[1]

ARTIFACTS_PATH = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"

OUTPUT_DIR = ROOT_DIR / "outputs" / "service_tests"
OUTPUT_JSON = OUTPUT_DIR / "variation_diversity_report.json"
OUTPUT_MD = OUTPUT_DIR / "variation_diversity_report.md"


MIN_TEACHING_UNIQUE_RATIO = 0.75
MIN_QUESTION_UNIQUE_RATIO = 0.70
MAX_DUPLICATE_RATIO = 0.30


def normalize_text(value: Any) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    elif isinstance(value, list):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    else:
        text = str(value or "")

    text = text.lower()
    text = " ".join(text.split())

    cleaned = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)

    return " ".join("".join(cleaned).split())


def short_preview(value: Any, max_chars: int = 180) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")

    text = text.replace("\n", " ").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def unique_ratio(values: List[Any]) -> float:
    if not values:
        return 0.0

    normalized = [normalize_text(v) for v in values if normalize_text(v)]
    if not normalized:
        return 0.0

    return round(len(set(normalized)) / len(normalized), 3)


def duplicate_groups(values: List[Any]) -> List[Dict[str, Any]]:
    groups = defaultdict(list)

    for idx, value in enumerate(values):
        norm = normalize_text(value)
        if norm:
            groups[norm].append(
                {
                    "index": idx,
                    "preview": short_preview(value),
                }
            )

    result = []

    for norm, items in groups.items():
        if len(items) > 1:
            result.append(
                {
                    "count": len(items),
                    "preview": norm[:180],
                    "items": items[:8],
                }
            )

    return sorted(result, key=lambda x: x["count"], reverse=True)


def inspect_teaching_diversity(artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_concept = defaultdict(list)

    for item in artifacts:
        key = (item.get("domain"), item.get("concept_id"), item.get("concept_name"))
        by_concept[key].append(item)

    concept_reports = []
    issues = []

    for key, items in by_concept.items():
        domain, concept_id, concept_name = key

        outputs = [item.get("output") for item in items]
        artifact_types = [item.get("artifact_type") for item in items]

        ratio = unique_ratio(outputs)
        duplicates = duplicate_groups(outputs)

        type_count = len(set(artifact_types))
        total = len(items)
        duplicate_ratio = round(1.0 - ratio, 3)

        concept_issues = []

        if total < 13:
            concept_issues.append(f"low_artifact_count_{total}")

        if type_count < 13:
            concept_issues.append(f"missing_artifact_types_count_{type_count}")

        if ratio < MIN_TEACHING_UNIQUE_RATIO:
            concept_issues.append(f"low_teaching_unique_ratio_{ratio}")

        if duplicate_ratio > MAX_DUPLICATE_RATIO:
            concept_issues.append(f"high_teaching_duplicate_ratio_{duplicate_ratio}")

        for issue in concept_issues:
            issues.append(
                {
                    "domain": domain,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "section": "teaching",
                    "issue": issue,
                }
            )

        concept_reports.append(
            {
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "total_artifacts": total,
                "artifact_type_count": type_count,
                "unique_ratio": ratio,
                "duplicate_ratio": duplicate_ratio,
                "duplicate_group_count": len(duplicates),
                "duplicate_groups": duplicates[:5],
                "issues": concept_issues,
                "sample_views": [
                    {
                        "artifact_type": item.get("artifact_type"),
                        "preview": short_preview(item.get("output")),
                    }
                    for item in items[:5]
                ],
            }
        )

    return {
        "total_concepts": len(by_concept),
        "concept_reports": sorted(
            concept_reports,
            key=lambda x: (x["domain"], x["concept_id"]),
        ),
        "issue_count": len(issues),
        "issues": issues,
    }


def get_question_content(item: Dict[str, Any]) -> Any:
    return item.get("question_json") if item.get("question_json") is not None else item.get("question_text")


def get_mcq_question_text(item: Dict[str, Any]) -> str:
    qjson = item.get("question_json") or {}
    return str(qjson.get("question") or "")


def get_mcq_options(item: Dict[str, Any]) -> List[str]:
    qjson = item.get("question_json") or {}
    options = qjson.get("options") or []
    return options if isinstance(options, list) else []


def get_debug_code(item: Dict[str, Any]) -> str:
    qjson = item.get("question_json") or {}
    return str(qjson.get("buggy_code") or "")


def get_output_prediction_code(item: Dict[str, Any]) -> str:
    qjson = item.get("question_json") or {}
    return str(qjson.get("code") or "")


def inspect_question_diversity(question_bank: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_concept = defaultdict(list)

    for item in question_bank:
        key = (item.get("domain"), item.get("concept_id"), item.get("concept_name"))
        by_concept[key].append(item)

    concept_reports = []
    issues = []

    for key, items in by_concept.items():
        domain, concept_id, concept_name = key

        by_type = defaultdict(list)
        for item in items:
            by_type[item.get("question_type")].append(item)

        type_reports = {}
        concept_issues = []

        for qtype, qitems in by_type.items():
            contents = [get_question_content(item) for item in qitems]
            ratio = unique_ratio(contents)
            duplicate_ratio = round(1.0 - ratio, 3)
            duplicates = duplicate_groups(contents)

            extra = {}

            if qtype == "mcq":
                mcq_questions = [get_mcq_question_text(item) for item in qitems]
                all_options = []
                for item in qitems:
                    all_options.extend(get_mcq_options(item))

                extra["mcq_question_unique_ratio"] = unique_ratio(mcq_questions)
                extra["mcq_option_unique_ratio"] = unique_ratio(all_options)

                if extra["mcq_question_unique_ratio"] < 0.6:
                    concept_issues.append(f"low_mcq_question_unique_ratio_{extra['mcq_question_unique_ratio']}")

                if extra["mcq_option_unique_ratio"] < 0.5:
                    concept_issues.append(f"low_mcq_option_unique_ratio_{extra['mcq_option_unique_ratio']}")

            elif qtype == "debug_task":
                debug_codes = [get_debug_code(item) for item in qitems]
                extra["debug_code_unique_ratio"] = unique_ratio(debug_codes)

                if extra["debug_code_unique_ratio"] < 0.7:
                    concept_issues.append(f"low_debug_code_unique_ratio_{extra['debug_code_unique_ratio']}")

            elif qtype == "output_prediction":
                output_codes = [get_output_prediction_code(item) for item in qitems]
                extra["output_code_unique_ratio"] = unique_ratio(output_codes)

                if extra["output_code_unique_ratio"] < 0.7:
                    concept_issues.append(f"low_output_code_unique_ratio_{extra['output_code_unique_ratio']}")

            if ratio < MIN_QUESTION_UNIQUE_RATIO:
                concept_issues.append(f"{qtype}_low_unique_ratio_{ratio}")

            if duplicate_ratio > MAX_DUPLICATE_RATIO:
                concept_issues.append(f"{qtype}_high_duplicate_ratio_{duplicate_ratio}")

            type_reports[qtype] = {
                "count": len(qitems),
                "unique_ratio": ratio,
                "duplicate_ratio": duplicate_ratio,
                "duplicate_group_count": len(duplicates),
                "duplicate_groups": duplicates[:5],
                "extra": extra,
                "samples": [
                    {
                        "variant_id": item.get("variant_id"),
                        "preview": short_preview(get_question_content(item)),
                    }
                    for item in qitems[:3]
                ],
            }

        question_types_present = set(by_type.keys())
        expected = {
            "mcq",
            "debug_task",
            "output_prediction",
            "transfer_question",
            "challenge_question",
            "explanation_check",
        }

        missing_types = sorted(expected - question_types_present)

        if missing_types:
            concept_issues.append(f"missing_question_types_{missing_types}")

        for issue in concept_issues:
            issues.append(
                {
                    "domain": domain,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "section": "questions",
                    "issue": issue,
                }
            )

        concept_reports.append(
            {
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "total_questions": len(items),
                "question_type_counts": dict(Counter(item.get("question_type") for item in items)),
                "type_reports": type_reports,
                "issues": concept_issues,
            }
        )

    return {
        "total_concepts": len(by_concept),
        "concept_reports": sorted(
            concept_reports,
            key=lambda x: (x["domain"], x["concept_id"]),
        ),
        "issue_count": len(issues),
        "issues": issues,
    }


def summarize_global(report: Dict[str, Any]) -> Dict[str, Any]:
    teaching = report["teaching_diversity"]
    questions = report["question_diversity"]

    teaching_ratios = [
        item["unique_ratio"] for item in teaching["concept_reports"]
    ]

    question_ratios = []
    for concept in questions["concept_reports"]:
        for _, type_report in concept["type_reports"].items():
            question_ratios.append(type_report["unique_ratio"])

    avg_teaching_unique = round(sum(teaching_ratios) / len(teaching_ratios), 3) if teaching_ratios else 0.0
    avg_question_unique = round(sum(question_ratios) / len(question_ratios), 3) if question_ratios else 0.0

    total_issues = teaching["issue_count"] + questions["issue_count"]

    status = "PASS"
    if total_issues > 0:
        status = "CHECK"

    return {
        "status": status,
        "avg_teaching_unique_ratio": avg_teaching_unique,
        "avg_question_unique_ratio": avg_question_unique,
        "teaching_issue_count": teaching["issue_count"],
        "question_issue_count": questions["issue_count"],
        "total_issue_count": total_issues,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]

    lines = []

    lines.append("# CogniTutorLM Variation Diversity Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: **{summary['status']}**")
    lines.append(f"- Average teaching unique ratio: **{summary['avg_teaching_unique_ratio']}**")
    lines.append(f"- Average question unique ratio: **{summary['avg_question_unique_ratio']}**")
    lines.append(f"- Teaching issue count: **{summary['teaching_issue_count']}**")
    lines.append(f"- Question issue count: **{summary['question_issue_count']}**")
    lines.append(f"- Total issue count: **{summary['total_issue_count']}**")
    lines.append("")

    lines.append("## Teaching Diversity Issues")
    lines.append("")
    teaching_issues = report["teaching_diversity"]["issues"]

    if not teaching_issues:
        lines.append("No teaching diversity issues found.")
    else:
        for issue in teaching_issues[:80]:
            lines.append(
                f"- {issue['domain']} {issue['concept_id']} — {issue['concept_name']}: {issue['issue']}"
            )
    lines.append("")

    lines.append("## Question Diversity Issues")
    lines.append("")
    question_issues = report["question_diversity"]["issues"]

    if not question_issues:
        lines.append("No question diversity issues found.")
    else:
        for issue in question_issues[:120]:
            lines.append(
                f"- {issue['domain']} {issue['concept_id']} — {issue['concept_name']}: {issue['issue']}"
            )
    lines.append("")

    lines.append("## Teaching Concept Summary")
    lines.append("")
    for item in report["teaching_diversity"]["concept_reports"]:
        lines.append(
            f"- **{item['domain']} {item['concept_id']} — {item['concept_name']}**: "
            f"artifacts={item['total_artifacts']}, unique_ratio={item['unique_ratio']}, "
            f"duplicate_groups={item['duplicate_group_count']}, issues={item['issues']}"
        )
    lines.append("")

    lines.append("## Question Concept Summary")
    lines.append("")
    for item in report["question_diversity"]["concept_reports"]:
        lines.append(
            f"- **{item['domain']} {item['concept_id']} — {item['concept_name']}**: "
            f"questions={item['total_questions']}, types={item['question_type_counts']}, "
            f"issues={item['issues']}"
        )
    lines.append("")

    lines.append("## Sample Detail")
    lines.append("")
    for item in report["teaching_diversity"]["concept_reports"][:5]:
        lines.append(f"### Teaching samples — {item['domain']} {item['concept_id']} {item['concept_name']}")
        for sample in item["sample_views"]:
            lines.append(f"- **{sample['artifact_type']}**: {sample['preview']}")
        lines.append("")

    for item in report["question_diversity"]["concept_reports"][:5]:
        lines.append(f"### Question samples — {item['domain']} {item['concept_id']} {item['concept_name']}")
        for qtype, type_report in item["type_reports"].items():
            lines.append(
                f"- **{qtype}**: count={type_report['count']}, unique_ratio={type_report['unique_ratio']}, "
                f"duplicate_ratio={type_report['duplicate_ratio']}"
            )
            for sample in type_report["samples"][:2]:
                lines.append(f"  - v{sample['variant_id']}: {sample['preview']}")
        lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nRunning CogniTutorLM variation diversity test...")
    print("=" * 80)

    artifacts = load_json(ARTIFACTS_PATH)
    question_bank = load_json(QUESTION_BANK_PATH)

    teaching_report = inspect_teaching_diversity(artifacts)
    question_report = inspect_question_diversity(question_bank)

    report = {
        "teaching_diversity": teaching_report,
        "question_diversity": question_report,
    }
    report["summary"] = summarize_global(report)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    summary = report["summary"]

    print("\nVariation diversity test complete.")
    print(f"Status: {summary['status']}")
    print(f"Average teaching unique ratio: {summary['avg_teaching_unique_ratio']}")
    print(f"Average question unique ratio: {summary['avg_question_unique_ratio']}")
    print(f"Teaching issue count: {summary['teaching_issue_count']}")
    print(f"Question issue count: {summary['question_issue_count']}")
    print(f"Total issue count: {summary['total_issue_count']}")
    print(f"Output JSON: {OUTPUT_JSON}")
    print(f"Output Markdown: {OUTPUT_MD}")

    if summary["total_issue_count"] > 0:
        print("\nTop issues:")
        for issue in (teaching_report["issues"] + question_report["issues"])[:30]:
            print(issue)

    print(f"\nSTATUS: {summary['status']}")


if __name__ == "__main__":
    main()