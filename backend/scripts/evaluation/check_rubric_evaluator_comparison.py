import json
from pathlib import Path

from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


OUTPUT_JSON = Path("evaluation_outputs/json/rubric_evaluator_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rubric_evaluator_comparison_report.md")


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


def _safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _extract_baseline_summary(evaluator_output: dict) -> dict:
    evaluation = evaluator_output.get("evaluation", {})
    return {
        "status": evaluation.get("status"),
        "overall_score": _safe_float(evaluation.get("overall_score")),
        "verdict": evaluation.get("verdict"),
        "learning_signal": evaluator_output.get("learning_signal"),
    }


def _extract_rubric_summary(evaluator_output: dict) -> dict:
    rubric = evaluator_output.get("rubric_evaluation_output", {})
    return {
        "status": rubric.get("status"),
        "overall_score": _safe_float(rubric.get("overall_score")),
        "verdict": rubric.get("verdict"),
        "weak_assessment_types": rubric.get("weak_assessment_types", []),
        "strong_assessment_types": rubric.get("strong_assessment_types", []),
    }


def _extract_mistake_summary(evaluator_output: dict) -> dict:
    mistake = evaluator_output.get("mistake_analysis_output", {})
    return {
        "status": mistake.get("status"),
        "dominant_mistake_type": mistake.get("dominant_mistake_type"),
        "mistake_type_counts": mistake.get("mistake_type_counts", {}),
        "high_severity_count": mistake.get("high_severity_count"),
    }


def _score_gap_label(baseline_score: float, rubric_score: float) -> str:
    gap = abs(baseline_score - rubric_score)

    if gap >= 0.35:
        return "large_gap"
    if gap >= 0.15:
        return "medium_gap"
    return "small_gap"


def _build_markdown(data: dict) -> str:
    lines = []

    lines.append("# Baseline Evaluator vs Rubric Evaluator Comparison Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report compares the existing baseline evaluator with the new "
        "rubric-based evaluator. The rubric evaluator is currently running in "
        "comparison-only mode and does not replace the final evaluation decision yet."
    )
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- Concept: {data['concept_name']}")
    lines.append(f"- Difficulty: {data['difficulty']}")
    lines.append(f"- Question count: {data['question_count']}")
    lines.append(f"- Rubric mode: {data['rubric_mode']}")
    lines.append("")
    lines.append("## Profile-Level Comparison")
    lines.append("")
    lines.append(
        "| Profile | Baseline Score | Baseline Verdict | Rubric Score | Rubric Verdict | Score Gap | Dominant Mistake | High Severity |"
    )
    lines.append("|---|---:|---|---:|---|---|---|---:|")

    for item in data["profile_results"]:
        lines.append(
            f"| {item['profile']} | "
            f"{item['baseline']['overall_score']} | "
            f"{item['baseline']['verdict']} | "
            f"{item['rubric']['overall_score']} | "
            f"{item['rubric']['verdict']} | "
            f"{item['score_gap_label']} | "
            f"{item['mistake']['dominant_mistake_type']} | "
            f"{item['mistake']['high_severity_count']} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- The baseline evaluator gives the current final score used by the pipeline."
    )
    lines.append(
        "- The rubric evaluator adds dimension-wise judgement through correctness, "
        "concept coverage, specificity, code reasoning, and clarity."
    )
    lines.append(
        "- Large score gaps identify cases where the baseline evaluator may be too strict "
        "or too lenient compared with the rubric evaluator."
    )
    lines.append(
        "- The rubric evaluator remains comparison-only until more logs and validation are available."
    )
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("Rubric evaluator comparison audit completed successfully.")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    concept_resource = _build_concept_resource()

    assessment_output = generate_assessment_bundle(
        concept_resource=concept_resource,
        difficulty="medium",
        requested_types=[
            "mcq",
            "debug",
            "output_prediction",
            "short_explanation",
            "transfer",
        ],
    )

    evaluator = EvaluatorAgent()
    profiles = ["strong", "average", "weak", "debug_weak", "low_confidence"]

    profile_results = []

    for profile in profiles:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        evaluator_output = evaluator.run(
            assessment_bundle=assessment_output,
            learner_answers=learner_answers,
        )

        baseline = _extract_baseline_summary(evaluator_output)
        rubric = _extract_rubric_summary(evaluator_output)
        mistake = _extract_mistake_summary(evaluator_output)

        baseline_score = baseline["overall_score"]
        rubric_score = rubric["overall_score"]
        score_gap = round(abs(baseline_score - rubric_score), 4)

        profile_results.append(
            {
                "profile": profile,
                "baseline": baseline,
                "rubric": rubric,
                "mistake": mistake,
                "score_gap": score_gap,
                "score_gap_label": _score_gap_label(
                    baseline_score=baseline_score,
                    rubric_score=rubric_score,
                ),
            }
        )

    report = {
        "status": "success",
        "module": "RubricEvaluatorComparisonAudit",
        "concept_id": concept_resource["concept_id"],
        "concept_name": concept_resource["concept_name"],
        "difficulty": "medium",
        "question_count": assessment_output.get("question_count"),
        "rubric_mode": "comparison_only_not_replacing_final_evaluation",
        "profile_results": profile_results,
    }

    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    OUTPUT_MD.write_text(
        _build_markdown(report),
        encoding="utf-8",
    )

    print("\nRUBRIC EVALUATOR COMPARISON AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("concept:", report["concept_name"])
    print("question_count:", report["question_count"])
    print("rubric_mode:", report["rubric_mode"])

    print("\nPROFILE COMPARISON")
    for item in profile_results:
        print(
            item["profile"],
            "| baseline:",
            item["baseline"]["overall_score"],
            item["baseline"]["verdict"],
            "| rubric:",
            item["rubric"]["overall_score"],
            item["rubric"]["verdict"],
            "| gap:",
            item["score_gap"],
            item["score_gap_label"],
            "| dominant_mistake:",
            item["mistake"]["dominant_mistake_type"],
        )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: rubric_evaluator_comparison_audit")


if __name__ == "__main__":
    main()