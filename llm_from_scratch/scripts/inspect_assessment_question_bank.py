import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]

QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"
QUALITY_REPORT_PATH = ROOT_DIR / "outputs" / "question_bank" / "question_bank_inspection_report.json"
QUALITY_REPORT_MD = ROOT_DIR / "outputs" / "question_bank" / "question_bank_inspection_report.md"

EXPECTED_QUESTION_TYPES = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
}

MIN_QUESTIONS_PER_CONCEPT = 15


def normalize_text(value: Any) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    else:
        text = str(value or "")

    text = text.lower()
    text = " ".join(text.split())

    cleaned = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)

    return "".join(cleaned).strip()


def get_question_preview(item: Dict[str, Any], max_chars: int = 180) -> str:
    qjson = item.get("question_json")
    qtext = item.get("question_text")

    if isinstance(qjson, dict):
        if qjson.get("question"):
            text = qjson.get("question")
        elif qjson.get("buggy_code"):
            text = qjson.get("buggy_code")
        else:
            text = json.dumps(qjson, ensure_ascii=False)
    else:
        text = qtext or ""

    text = str(text).replace("\n", " ").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def validate_row(item: Dict[str, Any]) -> List[str]:
    errors = []

    required_base = [
        "concept_id",
        "concept_name",
        "domain",
        "question_type",
        "difficulty",
        "valid",
        "answer_key_json",
        "rubric_json",
    ]

    for field in required_base:
        if field not in item:
            errors.append(f"missing field: {field}")

    qtype = item.get("question_type")

    if qtype not in EXPECTED_QUESTION_TYPES:
        errors.append(f"unknown question_type: {qtype}")

    if item.get("valid") is not True:
        errors.append("valid is not True")

    if qtype in {"mcq", "debug_task", "output_prediction", "explanation_check"}:
        if not isinstance(item.get("question_json"), dict):
            errors.append(f"{qtype} should have question_json dict")

    if qtype in {"transfer_question", "challenge_question"}:
        if not isinstance(item.get("question_text"), str) or len(item.get("question_text", "").strip()) < 20:
            errors.append(f"{qtype} should have non-empty question_text")

    if qtype == "mcq":
        q = item.get("question_json") or {}
        options = q.get("options", [])
        answer = q.get("answer")

        if not q.get("question"):
            errors.append("mcq missing question")

        if not isinstance(options, list) or len(options) != 4:
            errors.append("mcq options must be exactly 4")

        if isinstance(options, list) and len(set(options)) != len(options):
            errors.append("mcq options contain duplicates")

        if answer not in options:
            errors.append("mcq answer not in options")

    elif qtype == "debug_task":
        q = item.get("question_json") or {}
        for field in ["buggy_code", "expected_fix", "hint"]:
            if not q.get(field):
                errors.append(f"debug_task missing {field}")

    elif qtype == "output_prediction":
        q = item.get("question_json") or {}
        for field in ["question", "code", "answer", "explanation"]:
            if not q.get(field):
                errors.append(f"output_prediction missing {field}")

    elif qtype == "explanation_check":
        q = item.get("question_json") or {}
        for field in ["question", "expected_key_points", "rubric"]:
            if not q.get(field):
                errors.append(f"explanation_check missing {field}")

    return errors


def inspect_question_bank(question_bank: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    by_concept = defaultdict(list)
    by_type = Counter()
    duplicates = defaultdict(list)

    for item in question_bank:
        concept_key = (
            item.get("domain"),
            item.get("concept_id"),
            item.get("concept_name"),
        )

        by_concept[concept_key].append(item)
        by_type[item.get("question_type")] += 1

        norm = item.get("duplicate_group") or normalize_text(
            item.get("question_json") if item.get("question_json") is not None else item.get("question_text")
        )
        duplicates[norm].append(item)

        row_errors = validate_row(item)
        for err in row_errors:
            issues.append(
                {
                    "level": "row",
                    "concept_id": item.get("concept_id"),
                    "concept_name": item.get("concept_name"),
                    "question_type": item.get("question_type"),
                    "variant_id": item.get("variant_id"),
                    "issue": err,
                    "preview": get_question_preview(item),
                }
            )

    concept_reports = []

    for concept_key, items in by_concept.items():
        domain, concept_id, concept_name = concept_key
        type_counts = Counter(item.get("question_type") for item in items)

        missing_types = sorted(EXPECTED_QUESTION_TYPES - set(type_counts.keys()))

        if len(items) < MIN_QUESTIONS_PER_CONCEPT:
            issues.append(
                {
                    "level": "concept",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "question_type": None,
                    "variant_id": None,
                    "issue": f"low question count: {len(items)}",
                    "preview": "",
                }
            )

        if missing_types:
            issues.append(
                {
                    "level": "concept",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "question_type": None,
                    "variant_id": None,
                    "issue": f"missing question types: {missing_types}",
                    "preview": "",
                }
            )

        concept_reports.append(
            {
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "total_questions": len(items),
                "type_counts": dict(type_counts),
                "missing_types": missing_types,
            }
        )

    duplicate_groups = []

    for norm, group in duplicates.items():
        if len(group) > 1 and len(norm) > 40:
            duplicate_groups.append(
                {
                    "count": len(group),
                    "preview": norm[:220],
                    "items": [
                        {
                            "domain": item.get("domain"),
                            "concept_id": item.get("concept_id"),
                            "concept_name": item.get("concept_name"),
                            "question_type": item.get("question_type"),
                            "variant_id": item.get("variant_id"),
                            "question_preview": get_question_preview(item, 100),
                        }
                        for item in group[:12]
                    ],
                }
            )

    duplicate_groups = sorted(duplicate_groups, key=lambda x: x["count"], reverse=True)

    samples_by_type = {}

    for qtype in EXPECTED_QUESTION_TYPES:
        samples = [item for item in question_bank if item.get("question_type") == qtype]
        samples_by_type[qtype] = samples[:3]

    report = {
        "total_questions": len(question_bank),
        "total_concepts": len(by_concept),
        "valid_questions": sum(1 for item in question_bank if item.get("valid") is True),
        "question_type_counts": dict(by_type),
        "issue_count": len(issues),
        "issues": issues,
        "concept_reports": sorted(
            concept_reports,
            key=lambda x: (x["domain"], x["concept_id"]),
        ),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups": duplicate_groups[:30],
        "samples_by_type": samples_by_type,
    }

    return report


def build_markdown_report(report: Dict[str, Any]) -> str:
    lines = []

    lines.append("# Assessment Question Bank Inspection Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total questions: **{report['total_questions']}**")
    lines.append(f"- Total concepts: **{report['total_concepts']}**")
    lines.append(f"- Valid questions: **{report['valid_questions']} / {report['total_questions']}**")
    lines.append(f"- Issue count: **{report['issue_count']}**")
    lines.append(f"- Duplicate groups: **{report['duplicate_group_count']}**")
    lines.append("")

    lines.append("## Question Type Counts")
    lines.append("")
    for qtype, count in sorted(report["question_type_counts"].items()):
        lines.append(f"- {qtype}: {count}")
    lines.append("")

    lines.append("## Concept Coverage")
    lines.append("")
    for concept in report["concept_reports"]:
        lines.append(
            f"- **{concept['domain']} {concept['concept_id']} — {concept['concept_name']}**: "
            f"{concept['total_questions']} questions | {concept['type_counts']}"
        )
    lines.append("")

    lines.append("## Issues")
    lines.append("")
    if not report["issues"]:
        lines.append("No issues found.")
    else:
        for issue in report["issues"][:80]:
            lines.append(
                f"- `{issue['issue']}` | "
                f"{issue.get('concept_id')} | "
                f"{issue.get('concept_name')} | "
                f"{issue.get('question_type')} | "
                f"v{issue.get('variant_id')} | "
                f"{issue.get('preview')}"
            )
    lines.append("")

    lines.append("## Duplicate Groups")
    lines.append("")
    if not report["duplicate_groups"]:
        lines.append("No meaningful duplicate groups found.")
    else:
        for group in report["duplicate_groups"][:20]:
            lines.append(f"### Duplicate group count: {group['count']}")
            lines.append(f"Preview: `{group['preview']}`")
            for item in group["items"]:
                lines.append(
                    f"- {item['domain']} | {item['concept_id']} | "
                    f"{item['concept_name']} | {item['question_type']} | "
                    f"v{item['variant_id']} | {item['question_preview']}"
                )
            lines.append("")

    lines.append("## Sample Questions By Type")
    lines.append("")
    for qtype, samples in sorted(report["samples_by_type"].items()):
        lines.append(f"### {qtype}")
        lines.append("")
        for item in samples:
            lines.append(
                f"**{item['domain']} — {item['concept_id']} — {item['concept_name']} — v{item.get('variant_id')}**"
            )
            lines.append("")
            if item.get("question_json") is not None:
                lines.append("```json")
                lines.append(json.dumps(item["question_json"], indent=2, ensure_ascii=False))
                lines.append("```")
            else:
                lines.append(str(item.get("question_text")))
            lines.append("")

    return "\n".join(lines)


def main():
    if not QUESTION_BANK_PATH.exists():
        raise FileNotFoundError(
            f"Question bank not found: {QUESTION_BANK_PATH}\n"
            "Run: python -m scripts.generate_assessment_question_bank"
        )

    with QUESTION_BANK_PATH.open("r", encoding="utf-8") as f:
        question_bank = json.load(f)

    report = inspect_question_bank(question_bank)

    with QUALITY_REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with QUALITY_REPORT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(report))

    print("\nAssessment question bank inspection complete.")
    print(f"Total questions: {report['total_questions']}")
    print(f"Total concepts: {report['total_concepts']}")
    print(f"Valid questions: {report['valid_questions']}/{report['total_questions']}")
    print(f"Issue count: {report['issue_count']}")
    print(f"Duplicate groups: {report['duplicate_group_count']}")
    print(f"Question type counts: {report['question_type_counts']}")
    print(f"JSON report: {QUALITY_REPORT_PATH}")
    print(f"Markdown report: {QUALITY_REPORT_MD}")

    if (
        report["total_questions"] == 760
        and report["valid_questions"] == report["total_questions"]
        and report["issue_count"] == 0
        and report["total_concepts"] == 38
    ):
        print("STATUS: PASS")
    else:
        print("STATUS: CHECK")


if __name__ == "__main__":
    main()