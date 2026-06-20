import json
from pathlib import Path

from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


OUTPUT_JSON = Path("evaluation_outputs/json/debug_evaluator_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/debug_evaluator_comparison_report.md")


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


def _extract_baseline_debug_score(evaluator_output: dict) -> dict:
    evaluation = evaluator_output.get("evaluation", {})
    results = evaluation.get("results", [])

    debug_item = None
    for item in results:
        if not isinstance(item, dict):
            continue

        assessment_type = str(item.get("assessment_type", "")).strip().lower()
        if assessment_type in {"debug", "debug_task"}:
            debug_item = item
            break

    return {
        "evaluation_status": evaluation.get("status"),
        "overall_score": _safe_float(evaluation.get("overall_score")),
        "verdict": evaluation.get("verdict"),
        "debug_item_score": _safe_float(debug_item.get("score")) if debug_item else None,
        "debug_item_feedback": debug_item.get("feedback") if debug_item else None,
    }


def _extract_debug_summary(evaluator_output: dict) -> dict:
    debug_output = evaluator_output.get("debug_evaluation_output", {})

    first_result = {}
    results = debug_output.get("results", [])
    if results and isinstance(results[0], dict):
        first_result = results[0]

    return {
        "status": debug_output.get("status"),
        "mode": evaluator_output.get("debug_evaluation_mode"),
        "debug_question_count": debug_output.get("debug_question_count"),
        "overall_score": _safe_float(debug_output.get("overall_score")),
        "quality_label": debug_output.get("quality_label"),
        "debug_scores": first_result.get("debug_scores", {}),
        "feedback": first_result.get("feedback"),
    }


def _extract_mistake_summary(evaluator_output: dict) -> dict:
    mistake = evaluator_output.get("mistake_analysis_output", {})

    debug_mistake = None
    for item in mistake.get("classified_mistakes", []):
        if not isinstance(item, dict):
            continue

        assessment_type = str(item.get("assessment_type", "")).strip().lower()
        canonical_type = str(item.get("canonical_assessment_type", "")).strip().lower()

        if assessment_type in {"debug", "debug_task"} or canonical_type == "debug":
            debug_mistake = item
            break

    return {
        "status": mistake.get("status"),
        "dominant_mistake_type": mistake.get("dominant_mistake_type"),
        "high_severity_count": mistake.get("high_severity_count"),
        "debug_mistake_type": debug_mistake.get("mistake_type") if debug_mistake else None,
        "debug_mistake_severity": debug_mistake.get("severity") if debug_mistake else None,
        "debug_mistake_reason": debug_mistake.get("reason") if debug_mistake else None,
    }


def _gap_label(baseline_debug_score: float | None, specialized_score: float | None) -> str:
    if baseline_debug_score is None or specialized_score is None:
        return "not_comparable"

    gap = abs(float(baseline_debug_score) - float(specialized_score))

    if gap >= 0.35:
        return "large_gap"
    if gap >= 0.15:
        return "medium_gap"
    return "small_gap"


def _build_markdown(data: dict) -> str:
    lines = []

    lines.append("# Baseline Debug Evaluation vs Specialized Debug Evaluator Report")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report compares the baseline evaluator's debug score with the "
        "specialized DebugAnswerEvaluator. The specialized evaluator checks whether "
        "the learner detected the bug, identified the bug type, explained the fix, "
        "provided corrected code, and gave clear debugging reasoning."
    )
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- Concept: {data['concept_name']}")
    lines.append(f"- Difficulty: {data['difficulty']}")
    lines.append(f"- Question count: {data['question_count']}")
    lines.append(f"- Debug evaluator mode: {data['debug_evaluation_mode']}")
    lines.append("")
    lines.append("## Profile-Level Comparison")
    lines.append("")
    lines.append(
        "| Profile | Baseline Debug Score | Specialized Debug Score | Debug Label | Gap | Debug Mistake | Bug Detected | Bug Type | Fix Explained | Corrected Code | Reasoning |"
    )
    lines.append("|---|---:|---:|---|---|---|---:|---:|---:|---:|---:|")

    for item in data["profile_results"]:
        baseline_debug_score = item["baseline"].get("debug_item_score")
        debug = item["debug_evaluator"]
        debug_scores = debug.get("debug_scores", {})
        mistake = item["mistake"]

        lines.append(
            f"| {item['profile']} | "
            f"{baseline_debug_score} | "
            f"{debug.get('overall_score')} | "
            f"{debug.get('quality_label')} | "
            f"{item.get('score_gap_label')} | "
            f"{mistake.get('debug_mistake_type')} | "
            f"{debug_scores.get('bug_detected')} | "
            f"{debug_scores.get('bug_type_identified')} | "
            f"{debug_scores.get('fix_explained')} | "
            f"{debug_scores.get('corrected_code_present')} | "
            f"{debug_scores.get('debug_reasoning_quality')} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- The baseline evaluator provides a general score for debug answers."
    )
    lines.append(
        "- The specialized DebugAnswerEvaluator provides more granular debug-specific evidence."
    )
    lines.append(
        "- This helps the tutor distinguish between learners who detect a bug but fail to explain the fix, "
        "learners who misdiagnose the bug, and learners who provide a complete correction."
    )
    lines.append(
        "- The specialized evaluator remains comparison-only until more logs and validation are available."
    )
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("```text")
    lines.append("Debug evaluator comparison audit completed successfully.")
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

        baseline = _extract_baseline_debug_score(evaluator_output)
        debug_evaluator = _extract_debug_summary(evaluator_output)
        mistake = _extract_mistake_summary(evaluator_output)

        baseline_debug_score = baseline.get("debug_item_score")
        specialized_score = debug_evaluator.get("overall_score")

        score_gap = None
        if baseline_debug_score is not None and specialized_score is not None:
            score_gap = round(abs(float(baseline_debug_score) - float(specialized_score)), 4)

        profile_results.append(
            {
                "profile": profile,
                "baseline": baseline,
                "debug_evaluator": debug_evaluator,
                "mistake": mistake,
                "score_gap": score_gap,
                "score_gap_label": _gap_label(
                    baseline_debug_score=baseline_debug_score,
                    specialized_score=specialized_score,
                ),
            }
        )

    report = {
        "status": "success",
        "module": "DebugEvaluatorComparisonAudit",
        "concept_id": concept_resource["concept_id"],
        "concept_name": concept_resource["concept_name"],
        "difficulty": "medium",
        "question_count": assessment_output.get("question_count"),
        "debug_evaluation_mode": "comparison_only_not_replacing_final_evaluation",
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

    print("\nDEBUG EVALUATOR COMPARISON AUDIT")
    print("status:", report["status"])
    print("module:", report["module"])
    print("concept:", report["concept_name"])
    print("question_count:", report["question_count"])
    print("debug_evaluation_mode:", report["debug_evaluation_mode"])

    print("\nPROFILE COMPARISON")
    for item in profile_results:
        debug_scores = item["debug_evaluator"].get("debug_scores", {})
        print(
            item["profile"],
            "| baseline_debug:",
            item["baseline"].get("debug_item_score"),
            "| specialized_debug:",
            item["debug_evaluator"].get("overall_score"),
            item["debug_evaluator"].get("quality_label"),
            "| gap:",
            item["score_gap"],
            item["score_gap_label"],
            "| debug_mistake:",
            item["mistake"].get("debug_mistake_type"),
            "| bug_detected:",
            debug_scores.get("bug_detected"),
            "| bug_type:",
            debug_scores.get("bug_type_identified"),
        )

    print("\nSaved JSON:", OUTPUT_JSON)
    print("Saved Markdown:", OUTPUT_MD)

    print("\nSTATUS: success")
    print("MODULE: debug_evaluator_comparison_audit")


if __name__ == "__main__":
    main()