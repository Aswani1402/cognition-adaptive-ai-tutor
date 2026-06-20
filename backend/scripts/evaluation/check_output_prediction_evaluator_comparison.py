import json
from pathlib import Path

from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


OUTPUT_JSON = Path("evaluation_outputs/json/output_prediction_evaluator_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/output_prediction_evaluator_comparison_report.md")


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


def _extract_baseline_output_prediction_score(evaluator_output: dict) -> dict:
    evaluation = evaluator_output.get("evaluation", {})
    results = evaluation.get("results", [])

    output_item = None

    for item in results:
        if not isinstance(item, dict):
            continue

        assessment_type = str(item.get("assessment_type", "")).strip().lower()

        if assessment_type == "output_prediction":
            output_item = item
            break

    return {
        "evaluation_status": evaluation.get("status"),
        "overall_score": _safe_float(evaluation.get("overall_score")),
        "verdict": evaluation.get("verdict"),
        "output_prediction_item_score": (
            _safe_float(output_item.get("score")) if output_item else None
        ),
        "output_prediction_item_feedback": (
            output_item.get("feedback") if output_item else None
        ),
    }


def _extract_output_prediction_summary(evaluator_output: dict) -> dict:
    output_prediction = evaluator_output.get("output_prediction_evaluation_output", {})

    first_result = {}
    results = output_prediction.get("results", [])

    if results and isinstance(results[0], dict):
        first_result = results[0]

    return {
        "status": output_prediction.get("status"),
        "mode": evaluator_output.get("output_prediction_evaluation_mode"),
        "output_prediction_question_count": output_prediction.get(
            "output_prediction_question_count"
        ),
        "overall_score": _safe_float(output_prediction.get("overall_score")),
        "quality_label": output_prediction.get("quality_label"),
        "dominant_output_error_type": output_prediction.get(
            "dominant_output_error_type"
        ),
        "output_error_type_counts": output_prediction.get(
            "output_error_type_counts", {}
        ),
        "output_scores": first_result.get("output_scores", {}),
        "output_error_type": first_result.get("output_error_type"),
        "feedback": first_result.get("feedback"),
    }


def _extract_mistake_summary(evaluator_output: dict) -> dict:
    mistake = evaluator_output.get("mistake_analysis_output", {})

    output_mistake = None

    for item in mistake.get("classified_mistakes", []):
        if not isinstance(item, dict):
            continue

        assessment_type = str(item.get("assessment_type", "")).strip().lower()
        canonical_type = str(item.get("canonical_assessment_type", "")).strip().lower()

        if assessment_type == "output_prediction" or canonical_type == "output_prediction":
            output_mistake = item
            break

    return {
        "status": mistake.get("status"),
        "dominant_mistake_type": mistake.get("dominant_mistake_type"),
        "high_severity_count": mistake.get("high_severity_count"),
        "output_prediction_mistake_type": (
            output_mistake.get("mistake_type") if output_mistake else None
        ),
        "output_prediction_mistake_severity": (
            output_mistake.get("severity") if output_mistake else None
        ),
        "output_prediction_mistake_reason": (
            output_mistake.get("reason") if output_mistake else None
        ),
    }


def _gap_label(
    baseline_output_prediction_score: float | None,
    specialized_score: float | None,
) -> str:
    if baseline_output_prediction_score is None or specialized_score is None:
        return "not_comparable"

    gap = abs(float(baseline_output_prediction_score) - float(specialized_score))

    if gap >= 0.35:
        return "large_gap"
    if gap >= 0.15:
        return "medium_gap"
    return "small_gap"


def _build_markdown(data: dict) -> str:
    lines = []

    lines.append("# Baseline Output Prediction vs Specialized Output Prediction Evaluator Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report compares the baseline evaluator's output prediction score "
        "with the specialized OutputPredictionEvaluator. The specialized evaluator "
        "checks exact output match, normalized output match, line count, partial "
        "line match, trace reasoning, and output error type."
    )
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- Concept: {data['concept_name']}")
    lines.append(f"- Difficulty: {data['difficulty']}")
    lines.append(f"- Question count: {data['question_count']}")
    lines.append(f"- Output prediction evaluator mode: {data['output_prediction_evaluation_mode']}")
    lines.append("")
    lines.append("## Profile-Level Comparison")
    lines.append("")
    lines.append(
        "| Profile | Baseline Output Score | Specialized Output Score | Label | Gap | Output Error Type | Mistake Type | Exact Match | Normalized Match | Line Count | Partial Line | Trace Reasoning |"
    )
    lines.append("|---|---:|---:|---|---|---|---|---:|---:|---:|---:|---:|")

    for item in data["profile_results"]:
        baseline_score = item["baseline"].get("output_prediction_item_score")
        specialized = item["output_prediction_evaluator"]
        output_scores = specialized.get("output_scores", {})
        mistake = item["mistake"]

        lines.append(
            f"| {item['profile']} | "
            f"{baseline_score} | "
            f"{specialized.get('overall_score')} | "
            f"{specialized.get('quality_label')} | "
            f"{item.get('score_gap_label')} | "
            f"{specialized.get('dominant_output_error_type')} | "
            f"{mistake.get('output_prediction_mistake_type')} | "
            f"{output_scores.get('exact_output_match')} | "
            f"{output_scores.get('normalized_output_match')} | "
            f"{output_scores.get('line_count_match')} | "
            f"{output_scores.get('partial_line_match')} | "
            f"{output_scores.get('trace_reasoning_quality')} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- The baseline evaluator provides a general score for output prediction.")
    lines.append(
        "- The specialized OutputPredictionEvaluator shows whether the learner gave the exact output, "
        "matched after normalization, matched line count, or made a specific output error."
    )
    lines.append(
        "- This helps the tutor distinguish wrong value errors, line-count mistakes, and partial tracing errors."
    )
    lines.append(
        "- The specialized evaluator remains comparison-only until more logs and validation are available."
    )
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("Output prediction evaluator comparison audit completed successfully.")
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

        baseline = _extract_baseline_output_prediction_score(evaluator_output)
        output_prediction_evaluator = _extract_output_prediction_summary(evaluator_output)
        mistake = _extract_mistake_summary(evaluator_output)

        baseline_score = baseline.get("output_prediction_item_score")
        specialized_score = output_prediction_evaluator.get("overall_score")

        score_gap = None

        if baseline_score is not None and specialized_score is not None:
            score_gap = round(abs(float(baseline_score) - float(specialized_score)), 4)

        profile_results.append(
            {
                "profile": profile,
                "baseline": baseline,
                "output_prediction_evaluator": output_prediction_evaluator,
                "mistake": mistake,
                "score_gap": score_gap,
                "score_gap_label": _gap_label(
                    baseline_output_prediction_score=baseline_score,
                    specialized_score=specialized_score,
                ),
            }
        )

    report = {
        "status": "success",
        "module": "OutputPredictionEvaluatorComparisonAudit",
        "concept_id": concept_resource["concept_id"],
        "concept_name": concept_resource["concept_name"],
        "difficulty": "medium",
        "question_count": assessment_output.get("question_count"),
        "output_prediction_evaluation_mode": (
            "comparison_only_not_replacing_final_evaluation"
        ),
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

    print("\nOUTPUT PREDICTION EVALUATOR COMPARISON AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("concept:", report["concept_name"])
    print("question_count:", report["question_count"])
    print("output_prediction_evaluation_mode:", report["output_prediction_evaluation_mode"])

    print("\nPROFILE COMPARISON")
    for item in profile_results:
        output_scores = item["output_prediction_evaluator"].get("output_scores", {})

        print(
            item["profile"],
            "| baseline_output:",
            item["baseline"].get("output_prediction_item_score"),
            "| specialized_output:",
            item["output_prediction_evaluator"].get("overall_score"),
            item["output_prediction_evaluator"].get("quality_label"),
            "| gap:",
            item["score_gap"],
            item["score_gap_label"],
            "| error_type:",
            item["output_prediction_evaluator"].get("dominant_output_error_type"),
            "| exact:",
            output_scores.get("exact_output_match"),
            "| normalized:",
            output_scores.get("normalized_output_match"),
        )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: output_prediction_evaluator_comparison_audit")


if __name__ == "__main__":
    main()