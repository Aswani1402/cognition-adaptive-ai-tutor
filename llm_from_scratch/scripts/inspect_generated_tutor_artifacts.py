import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from src.cognitutor_lm_config import ALL_TASK_TYPES

ROOT_DIR = Path(__file__).resolve().parents[1]

ARTIFACTS_PATH = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
REPORT_PATH = ROOT_DIR / "outputs" / "artifacts" / "artifact_quality_report.md"
JSON_REPORT_PATH = ROOT_DIR / "outputs" / "artifacts" / "artifact_quality_report.json"

EXPECTED_ARTIFACT_TYPES = list(ALL_TASK_TYPES)

JSON_ARTIFACT_TYPES = {
    "debug_task",
    "output_prediction",
    "mcq",
    "syntax_completion",
    "fill_in_the_blank",
    "true_or_false",
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
    "mindmap",
    "concept_mindmap",
    "comparison_mindmap",
}


def output_to_text(output: Any) -> str:
    if isinstance(output, dict):
        return json.dumps(output, sort_keys=True, ensure_ascii=False)
    return str(output or "")


def normalized_text(output: Any) -> str:
    text = output_to_text(output).lower().strip()
    text = " ".join(text.split())
    return text


def output_length(output: Any) -> int:
    return len(output_to_text(output).strip())


def validate_json_artifact(artifact: Dict[str, Any]) -> List[str]:
    errors = []
    artifact_type = artifact.get("artifact_type")
    output = artifact.get("output")

    if artifact_type not in JSON_ARTIFACT_TYPES:
        return errors

    if not isinstance(output, dict):
        errors.append("Expected JSON/dict output")
        return errors

    if artifact_type == "flashcard_view":
        for field in ["front", "back"]:
            if not output.get(field):
                errors.append(f"flashcard_view missing {field}")
    elif "flashcard" in str(artifact_type):
        cards = output.get("cards") if isinstance(output, dict) else None
        if not isinstance(cards, list) or len(cards) < 2:
            errors.append(f"{artifact_type} missing multiple cards")

    elif artifact_type == "mindmap_view":
        if not output.get("center"):
            errors.append("mindmap_view missing center")
        if not isinstance(output.get("branches"), list) or not output.get("branches"):
            errors.append("mindmap_view missing branches")
    elif "mindmap" in str(artifact_type):
        if not output.get("center"):
            errors.append(f"{artifact_type} missing center")
        if not isinstance(output.get("branches"), list) or len(output.get("branches", [])) < 3:
            errors.append(f"{artifact_type} missing branches")

    elif artifact_type == "debug_view":
        for field in ["buggy_code", "expected_fix", "hint"]:
            if not output.get(field):
                errors.append(f"debug_view missing {field}")
    elif artifact_type == "debug_task":
        for field in ["buggy_code", "expected_fix", "hint", "explanation", "correct_answer"]:
            if field not in output or output.get(field) in ("", None):
                errors.append(f"debug_task missing {field}")

    elif artifact_type == "output_prediction_view":
        for field in ["question", "code", "answer", "explanation"]:
            if not output.get(field):
                errors.append(f"output_prediction_view missing {field}")
    elif artifact_type == "output_prediction":
        for field in ["question", "code", "answer", "correct_answer", "explanation"]:
            if field not in output or output.get(field) in ("", None):
                errors.append(f"output_prediction missing {field}")
    elif artifact_type == "mcq":
        options = output.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append("mcq must have exactly 4 options")
        if output.get("correct_answer") not in (options or []):
            errors.append("mcq correct_answer must be in options")
    elif artifact_type == "fill_in_the_blank":
        if "____" not in output.get("question", ""):
            errors.append("fill_in_the_blank missing blank")
        if not output.get("correct_answer"):
            errors.append("fill_in_the_blank missing correct_answer")
    elif artifact_type == "true_or_false":
        if output.get("correct_answer") not in {True, False}:
            errors.append("true_or_false correct_answer must be boolean")
    elif artifact_type == "syntax_completion":
        for field in ["incomplete_syntax", "completion", "correct_answer", "explanation"]:
            if field not in output or output.get(field) in ("", None):
                errors.append(f"syntax_completion missing {field}")

    return errors


def inspect_artifacts(artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    by_concept = defaultdict(list)
    by_type = Counter()
    duplicates_by_concept = defaultdict(list)
    global_duplicates = defaultdict(list)

    for artifact in artifacts:
        key = (
            artifact.get("domain"),
            artifact.get("concept_id"),
            artifact.get("concept_name"),
        )
        by_concept[key].append(artifact)
        by_type[artifact.get("artifact_type")] += 1

        norm = normalized_text(artifact.get("output"))
        global_duplicates[norm].append(artifact)

    # Concept-level checks.
    for concept_key, items in by_concept.items():
        domain, concept_id, concept_name = concept_key

        found_types = {item.get("artifact_type") for item in items}
        missing_types = [t for t in EXPECTED_ARTIFACT_TYPES if t not in found_types]

        if missing_types:
            issues.append(
                {
                    "level": "concept",
                    "domain": domain,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "issue": "missing_artifact_types",
                    "details": missing_types,
                }
            )

        if len(items) != len(EXPECTED_ARTIFACT_TYPES):
            issues.append(
                {
                    "level": "concept",
                    "domain": domain,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "issue": "unexpected_artifact_count",
                    "details": len(items),
                }
            )

        local_seen = {}
        for item in items:
            norm = normalized_text(item.get("output"))
            if norm in local_seen:
                duplicates_by_concept[concept_key].append(
                    {
                        "artifact_type_1": local_seen[norm].get("artifact_type"),
                        "artifact_type_2": item.get("artifact_type"),
                        "text_preview": norm[:160],
                    }
                )
            else:
                local_seen[norm] = item

    # Artifact-level checks.
    for artifact in artifacts:
        output = artifact.get("output")
        artifact_type = artifact.get("artifact_type")
        length = output_length(output)

        if not artifact.get("valid"):
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "valid_flag_false",
                    "details": "",
                }
            )

        if length == 0:
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "empty_output",
                    "details": "",
                }
            )

        if artifact_type not in JSON_ARTIFACT_TYPES and length < 50:
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "short_text_output",
                    "details": length,
                }
            )

        json_errors = validate_json_artifact(artifact)
        for err in json_errors:
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "json_schema_error",
                    "details": err,
                }
            )

        text = normalized_text(output)
        if "c2" in text or "apply concept" in text or "placeholder" in text:
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "placeholder_or_c2_output",
                    "details": text[:120],
                }
            )

        if not artifact.get("fallback_applied") or artifact.get("raw_valid") is not False:
            issues.append(
                {
                    "level": "artifact",
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact_type,
                    "issue": "fallback_metadata_missing_or_raw_claimed",
                    "details": artifact.get("generation_source"),
                }
            )

    # Count meaningful global duplicates but ignore tiny/common text.
    global_duplicate_groups = []
    for norm, group in global_duplicates.items():
        if len(group) > 1 and len(norm) > 80:
            global_duplicate_groups.append(
                {
                    "count": len(group),
                    "artifact_refs": [
                        {
                            "domain": item.get("domain"),
                            "concept_id": item.get("concept_id"),
                            "concept_name": item.get("concept_name"),
                            "artifact_type": item.get("artifact_type"),
                        }
                        for item in group[:10]
                    ],
                    "preview": norm[:200],
                }
            )

    report = {
        "total_artifacts": len(artifacts),
        "total_concepts": len(by_concept),
        "expected_artifacts_per_concept": len(EXPECTED_ARTIFACT_TYPES),
        "valid_artifacts": sum(1 for item in artifacts if item.get("valid")),
        "artifact_type_counts": dict(by_type),
        "issue_count": len(issues),
        "issues": issues,
        "concept_duplicate_groups": {
            f"{k[0]}::{k[1]}::{k[2]}": v
            for k, v in duplicates_by_concept.items()
            if v
        },
        "global_duplicate_group_count": len(global_duplicate_groups),
        "global_duplicate_groups": global_duplicate_groups[:20],
        "sample_artifacts": artifacts[:10],
    }

    return report


def build_markdown_report(report: Dict[str, Any]) -> str:
    lines = []

    lines.append("# Generated Tutor Artifact Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total artifacts: **{report['total_artifacts']}**")
    lines.append(f"- Total concepts: **{report['total_concepts']}**")
    lines.append(f"- Expected artifacts per concept: **{report['expected_artifacts_per_concept']}**")
    lines.append(f"- Valid artifacts: **{report['valid_artifacts']} / {report['total_artifacts']}**")
    lines.append(f"- Issue count: **{report['issue_count']}**")
    lines.append(f"- Global duplicate groups: **{report['global_duplicate_group_count']}**")
    lines.append("")

    lines.append("## Artifact Type Counts")
    lines.append("")
    for artifact_type, count in sorted(report["artifact_type_counts"].items()):
        lines.append(f"- {artifact_type}: {count}")
    lines.append("")

    lines.append("## Issues")
    lines.append("")
    if not report["issues"]:
        lines.append("No issues found.")
    else:
        for issue in report["issues"][:50]:
            lines.append(
                f"- `{issue.get('issue')}` | "
                f"{issue.get('concept_id')} | "
                f"{issue.get('concept_name')} | "
                f"{issue.get('artifact_type', '')} | "
                f"{issue.get('details')}"
            )
    lines.append("")

    lines.append("## Concept Duplicate Groups")
    lines.append("")
    if not report["concept_duplicate_groups"]:
        lines.append("No within-concept duplicate artifact outputs found.")
    else:
        for concept, groups in list(report["concept_duplicate_groups"].items())[:20]:
            lines.append(f"### {concept}")
            for group in groups:
                lines.append(
                    f"- {group['artifact_type_1']} duplicates {group['artifact_type_2']}: "
                    f"{group['text_preview']}"
                )
            lines.append("")

    lines.append("## Sample Artifacts")
    lines.append("")
    for item in report["sample_artifacts"]:
        lines.append(f"### {item['domain']} — {item['concept_id']} — {item['artifact_type']}")
        lines.append("")
        output = item["output"]
        if isinstance(output, dict):
            lines.append("```json")
            lines.append(json.dumps(output, indent=2, ensure_ascii=False))
            lines.append("```")
        else:
            lines.append(str(output))
        lines.append("")

    return "\n".join(lines)


def main():
    if not ARTIFACTS_PATH.exists():
        raise FileNotFoundError(
            f"Artifacts file not found: {ARTIFACTS_PATH}\n"
            "Run: python -m scripts.generate_tutor_artifacts"
        )

    with ARTIFACTS_PATH.open("r", encoding="utf-8") as f:
        artifacts = json.load(f)

    report = inspect_artifacts(artifacts)

    with JSON_REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(report))

    print("\nArtifact inspection complete.")
    print(f"Total artifacts: {report['total_artifacts']}")
    print(f"Total concepts: {report['total_concepts']}")
    print(f"Valid artifacts: {report['valid_artifacts']}/{report['total_artifacts']}")
    print(f"Issue count: {report['issue_count']}")
    print(f"Global duplicate groups: {report['global_duplicate_group_count']}")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {REPORT_PATH}")

    if (
        report["total_artifacts"] == report["total_concepts"] * len(EXPECTED_ARTIFACT_TYPES)
        and report["valid_artifacts"] == report["total_artifacts"]
        and report["issue_count"] == 0
    ):
        print("STATUS: PASS")
    else:
        print("STATUS: CHECK")


if __name__ == "__main__":
    main()
