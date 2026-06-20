from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_JSON = Path("evaluation_outputs/json/xai_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/xai_upgrade_report.md")
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


def _kt_data(output: dict[str, Any]) -> dict[str, Any]:
    data = _nested_get(output, "knowledge_state", "data", "data", default={})
    if not isinstance(data, dict):
        data = {}
    return {
        "predicted_mastery_last": data.get("predicted_mastery_last"),
        "schema_version": data.get("schema_version"),
        "source": data.get("source"),
        "fallback_used": data.get("fallback_used"),
        "model_used": data.get("model_used"),
    }


def _behaviour_data(output: dict[str, Any]) -> dict[str, Any]:
    data = _nested_get(output, "behaviour_state", "data", default={})
    if not isinstance(data, dict):
        data = {}
    return {
        "behavior_label": data.get("behavior_label"),
        "behavior_confidence": data.get("behavior_confidence"),
        "behavior_risk": data.get("behavior_risk"),
        "behavior_risk_label": data.get("behavior_risk_label"),
    }


def _evaluation_data(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    eval_fusion = _nested_get(output, "evaluator_agent_output", "evaluation_fusion_output", default={})
    if not isinstance(eval_fusion, dict):
        eval_fusion = {}
    return {
        "fused_score": summary.get("fused_score", eval_fusion.get("fused_score")),
        "fused_label": summary.get("fused_label", eval_fusion.get("fused_label")),
        "weakest_skill": summary.get(
            "weakest_skill",
            _nested_get(eval_fusion, "weakest_skill_signal", "weakest_skill"),
        ),
        "recommended_learning_signal": summary.get(
            "recommended_learning_signal",
            eval_fusion.get("recommended_learning_signal"),
        ),
        "evaluator_agreement": summary.get("evaluator_agreement", eval_fusion.get("evaluator_agreement")),
    }


def _mistake_data(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    mistake = _nested_get(output, "evaluator_agent_output", "mistake_analysis_output", default={})
    if not isinstance(mistake, dict):
        mistake = {}
    return {
        "dominant_mistake_type": summary.get("dominant_mistake_type", mistake.get("dominant_mistake_type")),
        "mistake_type_counts": summary.get("mistake_type_counts", mistake.get("mistake_type_counts", {})),
        "high_severity_mistake_count": summary.get(
            "high_severity_mistake_count",
            mistake.get("high_severity_count"),
        ),
    }


def _reward_data(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    return {
        "promotion_confidence": summary.get("promotion_confidence"),
        "promotion_allowed": summary.get("promotion_allowed"),
        "progression_action": summary.get("progression_action"),
        "reward_xp_awarded": summary.get("reward_xp_awarded"),
        "concept_cleared": summary.get("concept_cleared"),
    }


def _teaching_strategy_data(output: dict[str, Any]) -> dict[str, Any]:
    strategy = output.get("evidence_aware_teaching_strategy_output", {})
    if not isinstance(strategy, dict):
        strategy = {}
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    return {
        "teaching_view": strategy.get("teaching_view", summary.get("teaching_view")),
        "progression_action": strategy.get("progression_action", summary.get("progression_action")),
        "next_activity": strategy.get("next_activity", summary.get("next_activity")),
        "fallback_views": strategy.get("fallback_views", summary.get("fallback_views", [])),
        "assessment_types": strategy.get("assessment_types", summary.get("assessment_types", [])),
        "reason": strategy.get("reason"),
        "confidence": strategy.get("confidence"),
        "evidence_used": strategy.get("evidence_used", {}),
    }


def _rag_grounding_summary() -> dict[str, Any]:
    report = _load_json(RAG_GROUNDING_JSON)
    case_status = report.get("case_status", {}) if isinstance(report, dict) else {}
    return {
        "report_exists": RAG_GROUNDING_JSON.exists(),
        "overall_status": report.get("overall_status"),
        "case_count": case_status.get("case_count"),
        "safe_case_count": case_status.get("safe_case_count"),
        "fallback_case_count": case_status.get("fallback_case_count"),
        "failures": case_status.get("failures", []),
    }


def _top_factors(
    *,
    summary: dict[str, Any],
    kt: dict[str, Any],
    behaviour: dict[str, Any],
    evaluation: dict[str, Any],
) -> list[dict[str, Any]]:
    mastery = _safe_float(kt.get("predicted_mastery_last"), 0.0)
    behaviour_risk = _safe_float(behaviour.get("behavior_risk"), 0.0)
    fused_score = _safe_float(evaluation.get("fused_score"), 0.0)
    raw_factors = summary.get("xai_top_factors") or []

    factors = [
        {
            "factor": "evaluation_need",
            "value": round(fused_score, 4),
            "direction": "support_needed" if fused_score < 0.55 else "progress_possible",
            "explanation": f"Evaluation fusion labelled the learner as {evaluation.get('fused_label')}.",
        },
        {
            "factor": "behaviour_risk",
            "value": round(behaviour_risk, 4),
            "direction": behaviour.get("behavior_risk_label") or "unknown",
            "explanation": (
                f"Behaviour model classified the learner as {behaviour.get('behavior_label')} "
                f"with risk label {behaviour.get('behavior_risk_label')}."
            ),
        },
        {
            "factor": "mastery_need",
            "value": round(mastery, 4),
            "direction": "partial_mastery" if mastery < 0.75 else "strong_mastery",
            "explanation": "KT mastery is not yet high enough for automatic promotion.",
        },
    ]

    for factor in raw_factors:
        if factor not in {item["factor"] for item in factors}:
            factors.append(
                {
                    "factor": str(factor),
                    "value": None,
                    "direction": "observed",
                    "explanation": f"{factor} appeared in the pipeline XAI top factor list.",
                }
            )

    return factors[:5]


def _dashboard_object(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    kt = _kt_data(output)
    behaviour = _behaviour_data(output)
    evaluation = _evaluation_data(output)
    mistake = _mistake_data(output)
    reward = _reward_data(output)
    strategy = _teaching_strategy_data(output)
    rag = _rag_grounding_summary()

    concept_id = str(summary.get("final_concept") or output.get("concept_id") or "1")
    concept_name = str(summary.get("final_concept_name") or "Variables")
    teaching_view = strategy.get("teaching_view") or "current teaching view"
    weakest_skill = evaluation.get("weakest_skill") or "current weak skill"
    fused_label = evaluation.get("fused_label") or "unknown"
    progression_action = strategy.get("progression_action") or reward.get("progression_action")

    decision_summary = (
        f"The tutor selected {teaching_view} for {concept_name} because evaluation fusion is "
        f"{fused_label}, weakest skill is {weakest_skill}, KT mastery is "
        f"{kt.get('predicted_mastery_last')}, and behaviour risk is "
        f"{behaviour.get('behavior_risk_label')}."
    )

    why_not_promoted = (
        "Promotion was not allowed because current evidence still shows reteaching/revision need."
        if not reward.get("promotion_allowed")
        else "Promotion is allowed by current reward/progression evidence."
    )

    top_factors = _top_factors(summary=summary, kt=kt, behaviour=behaviour, evaluation=evaluation)

    return {
        "status": "success",
        "module": "XAIUpgradeReport",
        "learner_id": LEARNER_ID,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "decision_summary": decision_summary,
        "top_factors": top_factors,
        "why_this_teaching_view": strategy.get("reason") or f"{teaching_view} was selected from available evidence.",
        "why_this_assessment": (
            f"Assessment types {strategy.get('assessment_types')} target the weakest skill "
            f"{weakest_skill} and current teaching view {teaching_view}."
        ),
        "why_not_promoted": why_not_promoted,
        "what_to_improve_next": (
            f"Focus next on {weakest_skill}, then re-check mastery, mistakes, and promotion confidence."
        ),
        "frontend_dashboard_fields": {
            "learner_state_card": {
                "mastery": kt.get("predicted_mastery_last"),
                "kt_schema_version": kt.get("schema_version"),
                "behaviour_label": behaviour.get("behavior_label"),
                "behaviour_risk": behaviour.get("behavior_risk"),
                "behaviour_risk_label": behaviour.get("behavior_risk_label"),
            },
            "decision_reason_card": {
                "teaching_view": teaching_view,
                "progression_action": progression_action,
                "next_activity": strategy.get("next_activity"),
                "reason": strategy.get("reason"),
            },
            "weakness_card": {
                "weakest_skill": weakest_skill,
                "dominant_mistake_type": mistake.get("dominant_mistake_type"),
                "mistake_type_counts": mistake.get("mistake_type_counts"),
                "high_severity_mistake_count": mistake.get("high_severity_mistake_count"),
            },
            "next_action_card": {
                "assessment_types": strategy.get("assessment_types"),
                "fallback_views": strategy.get("fallback_views"),
                "reward_xp_awarded": reward.get("reward_xp_awarded"),
                "promotion_allowed": reward.get("promotion_allowed"),
            },
            "evidence_breakdown": top_factors,
        },
        "source_evidence": {
            "xai_pressure": summary.get("xai_pressure"),
            "xai_top_factors": summary.get("xai_top_factors", []),
            "notebook_summary": summary.get("notebook_summary"),
            "reflection": _nested_get(output, "reflection_output", "reflection", default={}),
            "learner_insight_output": output.get("learner_insight_output", {}),
            "teaching_strategy": strategy,
            "kt": kt,
            "behaviour": behaviour,
            "evaluation": evaluation,
            "mistake": mistake,
            "reward": reward,
            "rag_grounding": rag,
        },
        "limitations": [
            "Current XAI is evidence aggregation and rule explanation, not SHAP-based attribution.",
            "Model-based teaching strategy remains shadow/comparison-only.",
            "RAG grounding checker is keyword/section based rather than semantic entailment.",
        ],
    }


def _overall_status(dashboard: dict[str, Any]) -> str:
    evidence = dashboard.get("source_evidence", {})
    required = [
        evidence.get("xai_pressure"),
        evidence.get("teaching_strategy", {}).get("teaching_view"),
        evidence.get("kt", {}).get("predicted_mastery_last"),
        evidence.get("behaviour", {}).get("behavior_risk"),
        evidence.get("evaluation", {}).get("fused_score"),
        evidence.get("mistake", {}).get("dominant_mistake_type"),
    ]
    if all(item is not None for item in required):
        return "success"
    return "warning"


def _build_markdown(report: dict[str, Any]) -> str:
    dashboard = report["dashboard_ready_xai"]
    evidence = dashboard["source_evidence"]
    lines = [
        "# XAI Upgrade Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## XAI Status",
        "",
        f"- Module: `{dashboard['module']}`",
        f"- Learner: `{dashboard['learner_id']}`",
        f"- Concept: `{dashboard['concept_id']}` / {dashboard['concept_name']}",
        "",
        "## What XAI Currently Explains",
        "",
        "- Why a teaching view was selected.",
        "- Why assessment types were selected.",
        "- Why promotion was or was not allowed.",
        "- What the learner should improve next.",
        "- Which evidence sources drove the decision.",
        "",
        "## Evidence Sources Used",
        "",
        f"- XAI pressure: {evidence.get('xai_pressure')}",
        f"- XAI top factors: {evidence.get('xai_top_factors')}",
        f"- KT: {evidence.get('kt')}",
        f"- Behaviour: {evidence.get('behaviour')}",
        f"- Evaluation fusion: {evidence.get('evaluation')}",
        f"- Mistake analysis: {evidence.get('mistake')}",
        f"- Reward/promotion: {evidence.get('reward')}",
        f"- RAG grounding: {evidence.get('rag_grounding')}",
        "",
        "## Example Learner 14 Explanation",
        "",
        dashboard["decision_summary"],
        "",
        f"- Why this teaching view: {dashboard['why_this_teaching_view']}",
        f"- Why this assessment: {dashboard['why_this_assessment']}",
        f"- Why not promoted: {dashboard['why_not_promoted']}",
        f"- What to improve next: {dashboard['what_to_improve_next']}",
        "",
        "## Top Factors",
        "",
    ]
    for factor in dashboard["top_factors"]:
        lines.append(
            f"- `{factor['factor']}`: value={factor['value']}, direction={factor['direction']}. {factor['explanation']}"
        )

    lines.extend(
        [
            "",
            "## Dashboard-Ready Fields",
            "",
            "```json",
            json.dumps(dashboard["frontend_dashboard_fields"], indent=2, ensure_ascii=False, default=str),
            "```",
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in dashboard["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Future Upgrades",
            "",
            "- SHAP/permutation importance.",
            "- Decision tree path explanation.",
            "- RL action explanation.",
            "- Promotion model explanation.",
            "- Teacher dashboard XAI charts.",
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: xai_upgrade_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    pipeline_output = _run_integrated_pipeline()
    dashboard = _dashboard_object(pipeline_output)
    report = {
        "overall_status": _overall_status(dashboard),
        "module": "xai_upgrade_report",
        "generated_at": _now_iso(),
        "pipeline_status": pipeline_output.get("status", "success"),
        "dashboard_ready_xai": dashboard,
        "future_upgrades": [
            "SHAP/permutation importance",
            "decision tree path explanation",
            "RL action explanation",
            "promotion model explanation",
            "teacher dashboard XAI charts",
        ],
    }
    return report


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: xai_upgrade_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
