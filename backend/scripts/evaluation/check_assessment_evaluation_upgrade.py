import json
from pathlib import Path
from statistics import mean

from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


OUTPUT_DIR = Path("evaluation_outputs/reports")
JSON_DIR = Path("evaluation_outputs/json")

REPORT_PATH = OUTPUT_DIR / "assessment_evaluation_upgrade_report.md"
JSON_PATH = JSON_DIR / "assessment_evaluation_upgrade_report.json"


def _safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _build_concept_resource() -> dict:
    return {
        "concept_id": "1",
        "concept_name": "Variables",
        "definition": "A variable is a named storage location that holds a value.",
        "examples": ['name = "Alice"\nprint(name)'],
        "key_points": [
            "A variable is a name bound to an object in memory",
            "Python uses dynamic typing",
            "Variables are case-sensitive",
            "Names must start with a letter or underscore",
        ],
        "misconceptions": [
            "Variables can be used before assignment",
            "Python variables always have fixed types",
            "Variables store values directly instead of referring to objects",
        ],
        "real_world_use": (
            "Variables store names, prices, counters, configuration values, "
            "and API response data."
        ),
    }


def _profile_summary(profile: str, output: dict) -> dict:
    evaluation = output.get("evaluation", {})
    mistake = output.get("mistake_analysis_output", {})

    results = evaluation.get("results", [])
    scores = [_safe_float(item.get("score")) for item in results if isinstance(item, dict)]

    weak_types = [
        item.get("assessment_type")
        for item in results
        if isinstance(item, dict) and _safe_float(item.get("score")) < 0.75
    ]

    return {
        "profile": profile,
        "status": output.get("status"),
        "learning_signal": output.get("learning_signal"),
        "overall_score": evaluation.get("overall_score"),
        "average_item_score": round(mean(scores), 4) if scores else 0.0,
        "weak_assessment_types": weak_types,
        "dominant_mistake_type": mistake.get("dominant_mistake_type"),
        "mistake_type_counts": mistake.get("mistake_type_counts", {}),
        "high_severity_count": mistake.get("high_severity_count"),
        "medium_or_high_count": mistake.get("medium_or_high_count"),
        "classified_mistakes": mistake.get("classified_mistakes", []),
    }


def _markdown_report(data: dict) -> str:
    lines = []

    lines.append("# Assessment + Evaluation Upgrade Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report validates the upgraded assessment/evaluation layer using "
        "simulated learner profiles, EvaluatorAgent, and MistakeTypeClassifier."
    )
    lines.append("")
    lines.append("## Assessment Setup")
    lines.append("")
    lines.append(f"- Concept: {data['concept']['concept_name']}")
    lines.append(f"- Difficulty: {data['difficulty']}")
    lines.append(f"- Question count: {data['assessment_question_count']}")
    lines.append(f"- Requested types: {', '.join(data['requested_types'])}")
    lines.append("")
    lines.append("## Profile Results")
    lines.append("")

    lines.append(
        "| Profile | Learning Signal | Overall Score | Dominant Mistake | High Severity Count | Weak Types |"
    )
    lines.append("|---|---|---:|---|---:|---|")

    for item in data["profile_summaries"]:
        weak_types = ", ".join([str(x) for x in item.get("weak_assessment_types", [])])
        lines.append(
            f"| {item['profile']} | {item.get('learning_signal')} | "
            f"{item.get('overall_score')} | {item.get('dominant_mistake_type')} | "
            f"{item.get('high_severity_count')} | {weak_types} |"
        )

    lines.append("")
    lines.append("## Mistake Type Counts")
    lines.append("")

    for item in data["profile_summaries"]:
        lines.append(f"### {item['profile']}")
        lines.append("")
        counts = item.get("mistake_type_counts", {})
        if not counts:
            lines.append("- No mistake types found.")
        else:
            for key, value in counts.items():
                lines.append(f"- {key}: {value}")
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- Strong learners should mostly produce correct classifications."
    )
    lines.append(
        "- Weak learners should show high-severity mistakes such as wrong output, "
        "debug misdiagnosis, no answer, or misconception."
    )
    lines.append(
        "- Low-confidence learners should show low_confidence patterns even when "
        "some answers are partially correct."
    )
    lines.append(
        "- This module improves the tutor because it identifies why the learner "
        "failed, not only whether the learner failed."
    )
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("Assessment/evaluation upgrade audit completed successfully.")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    concept_resource = _build_concept_resource()
    requested_types = [
        "mcq",
        "debug",
        "output_prediction",
        "short_explanation",
        "transfer",
    ]

    assessment_output = generate_assessment_bundle(
        concept_resource=concept_resource,
        difficulty="medium",
        requested_types=requested_types,
    )

    evaluator = EvaluatorAgent()
    profiles = ["strong", "average", "weak", "debug_weak", "low_confidence"]

    profile_summaries = []
    raw_outputs = {}

    for profile in profiles:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        output = evaluator.run(
            assessment_bundle=assessment_output,
            learner_answers=learner_answers,
        )

        summary = _profile_summary(profile, output)
        profile_summaries.append(summary)

        raw_outputs[profile] = {
            "learner_answers": learner_answers,
            "evaluator_output": output,
        }

    report_data = {
        "status": "success",
        "module": "AssessmentEvaluationUpgradeAudit",
        "concept": {
            "concept_id": concept_resource["concept_id"],
            "concept_name": concept_resource["concept_name"],
        },
        "difficulty": "medium",
        "requested_types": requested_types,
        "assessment_question_count": assessment_output.get("question_count"),
        "profile_summaries": profile_summaries,
        "raw_outputs": raw_outputs,
    }

    JSON_PATH.write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    REPORT_PATH.write_text(
        _markdown_report(report_data),
        encoding="utf-8",
    )

    print("\nASSESSMENT + EVALUATION UPGRADE AUDIT")
    print("status:", report_data["status"])
    print("module:", report_data["module"])
    print("assessment_question_count:", report_data["assessment_question_count"])
    print("profiles:", profiles)

    print("\nPROFILE SUMMARY")
    for item in profile_summaries:
        print(
            item["profile"],
            "| signal:", item.get("learning_signal"),
            "| score:", item.get("overall_score"),
            "| dominant_mistake:", item.get("dominant_mistake_type"),
            "| high_severity:", item.get("high_severity_count"),
        )

    print("\nSaved JSON:", JSON_PATH)
    print("Saved Markdown:", REPORT_PATH)

    print("\nSTATUS: success")
    print("MODULE: assessment_evaluation_upgrade_audit")


if __name__ == "__main__":
    main()