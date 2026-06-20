from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.xai.decision_explainer import DecisionExplainer


OUTPUT_JSON = Path("evaluation_outputs/json/xai_model_explanation_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/xai_model_explanation_report.md")
RAG_GROUNDING_JSON = Path("evaluation_outputs/json/rag_grounding_report.json")
LEARNER_ID = "14"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _nested_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run_integrated_pipeline() -> dict[str, Any]:
    from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once

    return run_integrated_tutor_once(
        learner_id=LEARNER_ID,
        reward_dry_run=True,
    )


def _rag_score() -> float:
    report = _load_json(RAG_GROUNDING_JSON)
    cases = _nested_get(report, "case_status", "cases", default=[])
    if not isinstance(cases, list) or not cases:
        return 0.0
    safe_scores = [
        _safe_float(case.get("grounding_score"), 0.0)
        for case in cases
        if case.get("safe_to_generate")
    ]
    if not safe_scores:
        return 0.0
    return round(sum(safe_scores) / len(safe_scores), 4)


def _extract_evidence(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    strategy = output.get("evidence_aware_teaching_strategy_output", {})
    if not isinstance(strategy, dict):
        strategy = {}

    kt_data = _nested_get(output, "knowledge_state", "data", "data", default={})
    behaviour_data = _nested_get(output, "behaviour_state", "data", default={})
    if not isinstance(kt_data, dict):
        kt_data = {}
    if not isinstance(behaviour_data, dict):
        behaviour_data = {}

    return {
        "learner_id": LEARNER_ID,
        "concept_id": str(summary.get("final_concept") or "1"),
        "concept_name": str(summary.get("final_concept_name") or "Variables"),
        "mastery_score": _safe_float(kt_data.get("predicted_mastery_last"), 0.5),
        "kt_schema_version": kt_data.get("schema_version"),
        "kt_source": kt_data.get("source"),
        "kt_fallback_used": kt_data.get("fallback_used"),
        "behaviour_label": behaviour_data.get("behavior_label"),
        "behaviour_risk": _safe_float(behaviour_data.get("behavior_risk"), 0.0),
        "behaviour_risk_label": behaviour_data.get("behavior_risk_label"),
        "behavior_risk_label": behaviour_data.get("behavior_risk_label"),
        "behaviour_confidence": behaviour_data.get("behavior_confidence"),
        "fused_score": _safe_float(summary.get("fused_score"), 0.5),
        "fused_label": summary.get("fused_label"),
        "weakest_skill": summary.get("weakest_skill"),
        "recommended_learning_signal": summary.get("recommended_learning_signal"),
        "evaluator_agreement": summary.get("evaluator_agreement"),
        "dominant_mistake_type": summary.get("dominant_mistake_type"),
        "mistake_type_counts": summary.get("mistake_type_counts", {}),
        "high_severity_mistake_count": summary.get("high_severity_mistake_count", 0),
        "review_due": bool(_nested_get(output, "forgetting_state", "data", "review_queue", default=[])),
        "promotion_confidence": _safe_float(summary.get("promotion_confidence"), 0.0),
        "promotion_allowed": summary.get("promotion_allowed"),
        "progression_action": summary.get("progression_action"),
        "reward_xp_awarded": summary.get("reward_xp_awarded"),
        "rag_grounding_score": _rag_score(),
        "teaching_view": strategy.get("teaching_view") or summary.get("teaching_view"),
        "assessment_types": strategy.get("assessment_types") or summary.get("assessment_types", []),
        "next_activity": strategy.get("next_activity") or summary.get("next_activity"),
    }


def _build_explanations(evidence: dict[str, Any]) -> dict[str, Any]:
    explainer = DecisionExplainer()
    return {
        "teaching_strategy": explainer.explain(
            decision_type="teaching_strategy",
            decision=str(evidence.get("teaching_view") or "unknown_view"),
            evidence=evidence,
        ),
        "promotion": explainer.explain(
            decision_type="promotion",
            decision="promoted" if evidence.get("promotion_allowed") else "not_promoted",
            evidence=evidence,
        ),
        "revision_need": explainer.explain(
            decision_type="revision_need",
            decision="review" if evidence.get("review_due") else "no_review_due",
            evidence=evidence,
        ),
        "learner_weakness": explainer.explain(
            decision_type="learner_weakness",
            decision=str(evidence.get("weakest_skill") or "unknown_weakness"),
            evidence=evidence,
        ),
    }


def _overall_status(explanations: dict[str, Any]) -> str:
    if all(item.get("status") == "success" and item.get("feature_contributions") for item in explanations.values()):
        return "success"
    return "warning"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XAI Model Explanation Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Status Classification",
        "",
        "XAI is upgraded from evidence summary to transparent feature-contribution explanation. "
        "It is still not SHAP/deep-model attribution unless a trained model is available.",
        "",
        "## Evidence Snapshot",
        "",
        "```json",
        json.dumps(report["evidence"], indent=2, ensure_ascii=False, default=str),
        "```",
        "",
    ]

    for name, explanation in report["explanations"].items():
        lines.extend(
            [
                f"## {name.replace('_', ' ').title()}",
                "",
                f"- Decision: `{explanation.get('decision')}`",
                f"- Confidence: {explanation.get('confidence')}",
                f"- Top factors: {explanation.get('top_factors')}",
                "",
                "| Feature | Value | Contribution | Direction | Explanation |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for item in explanation.get("feature_contributions", []):
            lines.append(
                f"| {item.get('feature')} | {item.get('value')} | {item.get('contribution')} | {item.get('direction')} | {item.get('explanation')} |"
            )
        lines.extend(
            [
                "",
                "Counterfactuals:",
                "",
            ]
        )
        for counterfactual in explanation.get("counterfactuals", []):
            lines.append(f"- {counterfactual}")
        lines.extend(
            [
                "",
                f"Learner explanation: {explanation.get('learner_friendly_explanation')}",
                "",
                f"Teacher dashboard explanation: {explanation.get('teacher_dashboard_explanation')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Limitations",
            "",
            "- Transparent deterministic contribution scoring, not SHAP/deep-model attribution.",
            "- Contribution weights are rule-based until trained decision models are promoted from comparison mode.",
            "- RL action attribution and teacher dashboard charts remain future work.",
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: xai_model_explanation_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    pipeline_output = _run_integrated_pipeline()
    evidence = _extract_evidence(pipeline_output)
    explanations = _build_explanations(evidence)
    return {
        "overall_status": _overall_status(explanations),
        "module": "xai_model_explanation_report",
        "generated_at": _now_iso(),
        "pipeline_status": pipeline_output.get("status", "success"),
        "evidence": evidence,
        "explanations": explanations,
        "status_classification": (
            "XAI is upgraded from evidence summary to transparent feature-contribution explanation. "
            "It is still not SHAP/deep-model attribution unless a trained model is available."
        ),
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: xai_model_explanation_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
