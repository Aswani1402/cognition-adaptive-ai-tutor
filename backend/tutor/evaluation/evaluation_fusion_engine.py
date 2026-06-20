from __future__ import annotations

from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _score_label(score: float) -> str:
    if score >= 0.85:
        return "mastered"
    if score >= 0.65:
        return "partial_strong"
    if score >= 0.45:
        return "needs_light_review"
    return "needs_reteaching"


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _collect_available_scores(
    baseline_evaluation_output: Dict[str, Any],
    rubric_evaluation_output: Dict[str, Any],
    debug_evaluation_output: Dict[str, Any],
    output_prediction_evaluation_output: Dict[str, Any],
) -> Dict[str, float]:
    scores = {}

    baseline_score = _safe_float(
        baseline_evaluation_output.get("overall_score"),
        default=-1.0,
    )
    if baseline_score >= 0:
        scores["baseline"] = baseline_score

    rubric_score = _safe_float(
        rubric_evaluation_output.get("overall_score"),
        default=-1.0,
    )
    if rubric_score >= 0:
        scores["rubric"] = rubric_score

    debug_score = _safe_float(
        debug_evaluation_output.get("overall_score"),
        default=-1.0,
    )
    if debug_score >= 0:
        scores["debug"] = debug_score

    output_prediction_score = _safe_float(
        output_prediction_evaluation_output.get("overall_score"),
        default=-1.0,
    )
    if output_prediction_score >= 0:
        scores["output_prediction"] = output_prediction_score

    return scores


def _agreement_label(scores: Dict[str, float]) -> str:
    if len(scores) <= 1:
        return "not_enough_evaluators"

    values = list(scores.values())
    score_range = max(values) - min(values)

    if score_range <= 0.15:
        return "high_agreement"
    if score_range <= 0.35:
        return "medium_agreement"
    return "low_agreement"


def _weakest_skill_signal(
    rubric_evaluation_output: Dict[str, Any],
    debug_evaluation_output: Dict[str, Any],
    output_prediction_evaluation_output: Dict[str, Any],
    mistake_analysis_output: Dict[str, Any],
) -> Dict[str, Any]:
    weak_candidates = []

    rubric_weak = rubric_evaluation_output.get("weak_assessment_types", [])
    if isinstance(rubric_weak, list):
        for item in rubric_weak:
            weak_candidates.append(
                {
                    "skill": str(item),
                    "source": "rubric_evaluator",
                    "severity": "medium",
                }
            )

    debug_score = _safe_float(debug_evaluation_output.get("overall_score"), default=1.0)
    if debug_score < 0.65:
        weak_candidates.append(
            {
                "skill": "debug",
                "source": "debug_answer_evaluator",
                "severity": "high" if debug_score < 0.45 else "medium",
            }
        )

    output_prediction_score = _safe_float(
        output_prediction_evaluation_output.get("overall_score"),
        default=1.0,
    )
    if output_prediction_score < 0.65:
        weak_candidates.append(
            {
                "skill": "output_prediction",
                "source": "output_prediction_evaluator",
                "severity": "high" if output_prediction_score < 0.45 else "medium",
            }
        )

    classified_mistakes = mistake_analysis_output.get("classified_mistakes", [])
    if isinstance(classified_mistakes, list):
        for item in classified_mistakes:
            if not isinstance(item, dict):
                continue

            severity = item.get("severity")
            assessment_type = item.get("assessment_type")
            mistake_type = item.get("mistake_type")

            if severity in {"medium", "high"} and assessment_type:
                weak_candidates.append(
                    {
                        "skill": str(assessment_type),
                        "source": "mistake_type_classifier",
                        "severity": severity,
                        "mistake_type": mistake_type,
                    }
                )

    if not weak_candidates:
        return {
            "weakest_skill": None,
            "weakness_source": None,
            "weakness_severity": "none",
            "mistake_type": None,
            "all_weak_candidates": [],
        }

    severity_rank = {
        "high": 3,
        "medium": 2,
        "low": 1,
        "none": 0,
    }

    strongest = sorted(
        weak_candidates,
        key=lambda item: severity_rank.get(str(item.get("severity")), 0),
        reverse=True,
    )[0]

    return {
        "weakest_skill": strongest.get("skill"),
        "weakness_source": strongest.get("source"),
        "weakness_severity": strongest.get("severity"),
        "mistake_type": strongest.get("mistake_type"),
        "all_weak_candidates": weak_candidates,
    }


def _recommended_learning_signal(
    fused_score: float,
    weakest_skill: Dict[str, Any],
    mistake_analysis_output: Dict[str, Any],
) -> str:
    high_severity_count = int(
        _safe_float(mistake_analysis_output.get("high_severity_count"), 0.0)
    )

    weakest_skill_name = weakest_skill.get("weakest_skill")
    weakness_severity = weakest_skill.get("weakness_severity")

    if high_severity_count >= 2:
        return "focused_remediation"

    if weakness_severity == "high":
        return "targeted_reteaching"

    if fused_score >= 0.85 and not weakest_skill_name:
        return "ready_to_progress"

    if fused_score >= 0.65:
        return "light_review_then_progress"

    if fused_score >= 0.45:
        return "guided_practice"

    return "reteach_with_support"


def fuse_evaluation_outputs(
    baseline_evaluation_output: Dict[str, Any],
    rubric_evaluation_output: Dict[str, Any] | None = None,
    debug_evaluation_output: Dict[str, Any] | None = None,
    output_prediction_evaluation_output: Dict[str, Any] | None = None,
    mistake_analysis_output: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Combines baseline, rubric, debug, output prediction, and mistake analysis
    into one comparison-level evaluation fusion output.

    Current role:
    - Comparison mode only.
    - Does not replace final baseline evaluation yet.
    - Gives stronger report/demo intelligence.
    """

    baseline_evaluation_output = _safe_dict(baseline_evaluation_output)
    rubric_evaluation_output = _safe_dict(rubric_evaluation_output)
    debug_evaluation_output = _safe_dict(debug_evaluation_output)
    output_prediction_evaluation_output = _safe_dict(
        output_prediction_evaluation_output
    )
    mistake_analysis_output = _safe_dict(mistake_analysis_output)

    scores = _collect_available_scores(
        baseline_evaluation_output=baseline_evaluation_output,
        rubric_evaluation_output=rubric_evaluation_output,
        debug_evaluation_output=debug_evaluation_output,
        output_prediction_evaluation_output=output_prediction_evaluation_output,
    )

    if not scores:
        return {
            "status": "error",
            "module": "EvaluationFusionEngine",
            "reason": "No evaluator scores were available.",
        }

    weights = {
        "baseline": 0.30,
        "rubric": 0.30,
        "debug": 0.20,
        "output_prediction": 0.20,
    }

    available_weight_sum = sum(
        weights.get(name, 0.0)
        for name in scores
    )

    fused_score = sum(
        score * weights.get(name, 0.0)
        for name, score in scores.items()
    ) / max(available_weight_sum, 1e-8)

    fused_score = round(max(0.0, min(1.0, fused_score)), 4)

    agreement = _agreement_label(scores)
    weakest_skill = _weakest_skill_signal(
        rubric_evaluation_output=rubric_evaluation_output,
        debug_evaluation_output=debug_evaluation_output,
        output_prediction_evaluation_output=output_prediction_evaluation_output,
        mistake_analysis_output=mistake_analysis_output,
    )

    recommended_signal = _recommended_learning_signal(
        fused_score=fused_score,
        weakest_skill=weakest_skill,
        mistake_analysis_output=mistake_analysis_output,
    )

    high_severity_count = int(
        _safe_float(mistake_analysis_output.get("high_severity_count"), 0.0)
    )

    confidence_base = 0.75
    if agreement == "high_agreement":
        confidence_base += 0.15
    elif agreement == "medium_agreement":
        confidence_base += 0.05
    elif agreement == "low_agreement":
        confidence_base -= 0.20

    if high_severity_count >= 2:
        confidence_base += 0.05

    fusion_confidence = round(max(0.0, min(1.0, confidence_base)), 4)

    reason = (
        f"Fusion used evaluator scores {scores}. "
        f"Evaluator agreement is {agreement}. "
        f"Weakest skill signal is {weakest_skill.get('weakest_skill')} "
        f"from {weakest_skill.get('weakness_source')}. "
        f"Recommended learning signal is {recommended_signal}."
    )

    return {
        "status": "success",
        "module": "EvaluationFusionEngine",
        "mode": "comparison_only_not_replacing_final_evaluation",
        "fused_score": fused_score,
        "fused_label": _score_label(fused_score),
        "recommended_learning_signal": recommended_signal,
        "fusion_confidence": fusion_confidence,
        "fusion_confidence_label": _confidence_label(fusion_confidence),
        "evaluator_scores": scores,
        "evaluator_agreement": agreement,
        "weakest_skill_signal": weakest_skill,
        "dominant_mistake_type": mistake_analysis_output.get("dominant_mistake_type"),
        "high_severity_mistake_count": high_severity_count,
        "reason": reason,
    }