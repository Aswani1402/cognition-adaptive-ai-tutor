import json
from pathlib import Path

from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


OUTPUT_JSON = Path("evaluation_outputs/json/full_evaluation_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/full_evaluation_upgrade_report.md")


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


def _first_result(output: dict) -> dict:
    results = output.get("results", [])
    if results and isinstance(results[0], dict):
        return results[0]
    return {}


def _extract_profile_summary(profile: str, evaluator_output: dict) -> dict:
    baseline = evaluator_output.get("evaluation", {})
    rubric = evaluator_output.get("rubric_evaluation_output", {})
    debug = evaluator_output.get("debug_evaluation_output", {})
    output_prediction = evaluator_output.get("output_prediction_evaluation_output", {})
    mistake = evaluator_output.get("mistake_analysis_output", {})
    fusion = evaluator_output.get("evaluation_fusion_output", {})

    debug_first = _first_result(debug)
    output_first = _first_result(output_prediction)

    return {
        "profile": profile,
        "agent_status": evaluator_output.get("status"),
        "baseline": {
            "status": baseline.get("status"),
            "overall_score": _safe_float(baseline.get("overall_score")),
            "verdict": baseline.get("verdict"),
            "learning_signal": evaluator_output.get("learning_signal"),
        },
        "rubric": {
            "status": rubric.get("status"),
            "mode": evaluator_output.get("rubric_mode"),
            "overall_score": _safe_float(rubric.get("overall_score")),
            "verdict": rubric.get("verdict"),
            "weak_assessment_types": rubric.get("weak_assessment_types", []),
            "strong_assessment_types": rubric.get("strong_assessment_types", []),
        },
        "debug": {
            "status": debug.get("status"),
            "mode": evaluator_output.get("debug_evaluation_mode"),
            "overall_score": _safe_float(debug.get("overall_score")),
            "quality_label": debug.get("quality_label"),
            "debug_question_count": debug.get("debug_question_count"),
            "debug_scores": debug_first.get("debug_scores", {}),
        },
        "output_prediction": {
            "status": output_prediction.get("status"),
            "mode": evaluator_output.get("output_prediction_evaluation_mode"),
            "overall_score": _safe_float(output_prediction.get("overall_score")),
            "quality_label": output_prediction.get("quality_label"),
            "output_prediction_question_count": output_prediction.get(
                "output_prediction_question_count"
            ),
            "dominant_output_error_type": output_prediction.get(
                "dominant_output_error_type"
            ),
            "output_scores": output_first.get("output_scores", {}),
        },
        "mistake_analysis": {
            "status": mistake.get("status"),
            "dominant_mistake_type": mistake.get("dominant_mistake_type"),
            "mistake_type_counts": mistake.get("mistake_type_counts", {}),
            "high_severity_count": mistake.get("high_severity_count"),
            "medium_or_high_count": mistake.get("medium_or_high_count"),
        },
        "fusion": {
            "status": fusion.get("status"),
            "mode": evaluator_output.get("evaluation_fusion_mode"),
            "fused_score": fusion.get("fused_score"),
            "fused_label": fusion.get("fused_label"),
            "recommended_learning_signal": fusion.get("recommended_learning_signal"),
            "fusion_confidence": fusion.get("fusion_confidence"),
            "fusion_confidence_label": fusion.get("fusion_confidence_label"),
            "evaluator_agreement": fusion.get("evaluator_agreement"),
            "weakest_skill": (
                fusion.get("weakest_skill_signal", {}).get("weakest_skill")
                if isinstance(fusion.get("weakest_skill_signal"), dict)
                else None
            ),
            "weakest_skill_signal": fusion.get("weakest_skill_signal", {}),
        },
    }


def _build_markdown(report: dict) -> str:
    lines = []

    lines.append("# Full Evaluation Upgrade Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report summarizes the May 5 assessment and evaluation intelligence "
        "upgrade. The system now compares the baseline evaluator with rubric-based, "
        "debug-specific, output-prediction-specific, mistake-analysis, and fusion-level "
        "evaluation outputs."
    )
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- Concept: {report['concept_name']}")
    lines.append(f"- Difficulty: {report['difficulty']}")
    lines.append(f"- Question count: {report['question_count']}")
    lines.append(f"- Profiles tested: {', '.join(report['profiles'])}")
    lines.append("")
    lines.append("## Evaluation Modules Included")
    lines.append("")
    for module in report["modules_included"]:
        lines.append(f"- {module}")
    lines.append("")
    lines.append("## Profile Summary")
    lines.append("")
    lines.append(
        "| Profile | Baseline Score | Baseline Verdict | Rubric Score | Debug Score | Output Score | Fused Score | Fused Label | Recommended Signal | Dominant Mistake | Weakest Skill | Agreement |"
    )
    lines.append("|---|---:|---|---:|---:|---:|---:|---|---|---|---|---|")

    for item in report["profile_results"]:
        lines.append(
            f"| {item['profile']} | "
            f"{item['baseline']['overall_score']} | "
            f"{item['baseline']['verdict']} | "
            f"{item['rubric']['overall_score']} | "
            f"{item['debug']['overall_score']} | "
            f"{item['output_prediction']['overall_score']} | "
            f"{item['fusion']['fused_score']} | "
            f"{item['fusion']['fused_label']} | "
            f"{item['fusion']['recommended_learning_signal']} | "
            f"{item['mistake_analysis']['dominant_mistake_type']} | "
            f"{item['fusion']['weakest_skill']} | "
            f"{item['fusion']['evaluator_agreement']} |"
        )

    lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    lines.append(
        "- The baseline evaluator remains the final decision source for now."
    )
    lines.append(
        "- The rubric evaluator adds dimension-wise scoring across correctness, "
        "concept coverage, specificity, code reasoning, and clarity."
    )
    lines.append(
        "- The debug evaluator gives bug-specific evidence such as bug detection, "
        "bug type identification, fix explanation, corrected code presence, and reasoning quality."
    )
    lines.append(
        "- The output prediction evaluator identifies exact match, normalized match, "
        "line-count match, partial line match, trace reasoning, and output error type."
    )
    lines.append(
        "- The mistake classifier now avoids selecting `correct` as dominant when serious "
        "non-correct mistake patterns exist."
    )
    lines.append(
        "- The fusion engine combines all evaluator signals into fused score, agreement, "
        "weakest skill, confidence, and recommended learning signal."
    )
    lines.append("")
    lines.append("## Frontend Readiness")
    lines.append("")
    lines.append(
        "The frontend response now exposes rubric evaluation, debug evaluation, "
        "output prediction evaluation, and evaluation fusion outputs in comparison mode."
    )
    lines.append("")
    lines.append("## Current Mode")
    lines.append("")
    lines.append("```text")
    lines.append("comparison_only_not_replacing_final_evaluation")
    lines.append("```")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("Full evaluation upgrade report generated successfully.")
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

        profile_results.append(
            _extract_profile_summary(
                profile=profile,
                evaluator_output=evaluator_output,
            )
        )

    report = {
        "status": "success",
        "module": "FullEvaluationUpgradeReport",
        "concept_id": concept_resource["concept_id"],
        "concept_name": concept_resource["concept_name"],
        "difficulty": "medium",
        "question_count": assessment_output.get("question_count"),
        "profiles": profiles,
        "mode": "comparison_only_not_replacing_final_evaluation",
        "modules_included": [
            "Baseline Evaluator",
            "RubricEvaluator",
            "DebugAnswerEvaluator",
            "OutputPredictionEvaluator",
            "MistakeTypeClassifier",
            "EvaluationFusionEngine",
        ],
        "frontend_ready_outputs": [
            "rubric_evaluation",
            "debug_evaluation",
            "output_prediction_evaluation",
            "evaluation_fusion",
            "mistake_analysis",
        ],
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

    print("\nFULL EVALUATION UPGRADE REPORT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("concept:", report["concept_name"])
    print("question_count:", report["question_count"])
    print("mode:", report["mode"])

    print("\nPROFILE SUMMARY")
    for item in profile_results:
        print(
            item["profile"],
            "| baseline:",
            item["baseline"]["overall_score"],
            item["baseline"]["verdict"],
            "| rubric:",
            item["rubric"]["overall_score"],
            "| debug:",
            item["debug"]["overall_score"],
            "| output:",
            item["output_prediction"]["overall_score"],
            "| fused:",
            item["fusion"]["fused_score"],
            item["fusion"]["fused_label"],
            "| signal:",
            item["fusion"]["recommended_learning_signal"],
            "| weakest:",
            item["fusion"]["weakest_skill"],
            "| mistake:",
            item["mistake_analysis"]["dominant_mistake_type"],
        )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: full_evaluation_upgrade_report")


if __name__ == "__main__":
    main()