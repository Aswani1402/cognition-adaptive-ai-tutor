from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.RL.bandit_policy import BanditPolicy
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


OUTPUT_JSON = Path("evaluation_outputs/json/policy_rl_upgrade_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/policy_rl_upgrade_report.md")

POLICY_MODEL_PATH = Path("models/policy/policy_model.joblib")
POLICY_MODEL_META_PATH = Path("models/policy/policy_model_meta.json")
PROMOTION_MODEL_DIR = Path("models/promotion_confidence")
BANDIT_MODEL_PATH = Path("models/rl/bandit_policy_model.pkl")
BANDIT_ENCODER_PATH = Path("models/rl/bandit_label_encoders.pkl")
BANDIT_META_PATH = Path("models/rl/bandit_policy_metadata.json")
DQN_MODEL_PATH = Path("models/rl/dqn/dqn_policy_model.pt")
DQN_META_PATH = Path("models/rl/dqn/dqn_policy_metadata.json")
SYNTHETIC_PROMOTION_LOGS = Path("evaluation_outputs/csv/synthetic_promotion_confidence_logs.csv")
SEARCH_ROOTS = [
    Path("tutor/policy"),
    Path("tutor/RL"),
    Path("scripts/rl"),
    Path("scripts/training"),
    Path("models"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _safe_get(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _build_rl_state(output: dict[str, Any]) -> dict[str, Any]:
    evidence_summary = _safe_get(
        output,
        "decision_agent_output",
        "multi_evidence_output",
        "evidence_summary",
        default={},
    )
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    return {
        "mastery_score": evidence_summary.get("mastery_score", 0.0),
        "behavior_score": evidence_summary.get(
            "behavior_score",
            summary.get("behavior_risk", summary.get("behaviour_risk", 0.0)),
        ),
        "review_due": evidence_summary.get("review_due", bool(summary.get("adaptive_path_fallback_used"))),
        "evaluation_score": evidence_summary.get("evaluation_score", summary.get("evaluation_score", 0.0)),
        "learning_signal": evidence_summary.get(
            "learning_signal",
            summary.get("recommended_learning_signal", "weak"),
        ),
    }


def _inspect_bandit(state: dict[str, Any]) -> dict[str, Any]:
    status = {
        "model_path": str(BANDIT_MODEL_PATH),
        "encoder_path": str(BANDIT_ENCODER_PATH),
        "model_exists": BANDIT_MODEL_PATH.exists(),
        "encoder_exists": BANDIT_ENCODER_PATH.exists(),
        "metadata_path": str(BANDIT_META_PATH),
        "metadata": _load_json(BANDIT_META_PATH),
        "available": False,
        "prediction": None,
        "runtime_role": "comparison_or_prototype",
    }
    try:
        policy = BanditPolicy()
        status["available"] = policy.is_available()
        status["prediction"] = policy.predict(state)
    except Exception as exc:
        status["available"] = False
        status["prediction"] = {"status": "error", "reason": str(exc)}
    return status


def _inspect_dqn(state: dict[str, Any], integrated_output: dict[str, Any]) -> dict[str, Any]:
    decision_agent_dqn = _safe_get(integrated_output, "decision_agent_output", "dqn_output", default=None)
    status = {
        "model_path": str(DQN_MODEL_PATH),
        "model_exists": DQN_MODEL_PATH.exists(),
        "metadata_path": str(DQN_META_PATH),
        "metadata": _load_json(DQN_META_PATH),
        "available": False,
        "standalone_prediction": None,
        "integrated_decision_agent_output": decision_agent_dqn,
        "runtime_role": "active_strategy_difficulty_override_when_available",
    }
    try:
        policy = DQNPolicy()
        status["available"] = policy.is_available()
        status["standalone_prediction"] = policy.predict(state)
    except Exception as exc:
        status["available"] = False
        status["standalone_prediction"] = {"status": "error", "reason": str(exc)}
    return status


def _inspect_artifacts() -> dict[str, Any]:
    discovered = _discover_policy_rl_files()
    return {
        "policy_model": {
            "path": str(POLICY_MODEL_PATH),
            "exists": POLICY_MODEL_PATH.exists(),
            "metadata_path": str(POLICY_MODEL_META_PATH),
            "metadata": _load_json(POLICY_MODEL_META_PATH),
            "runtime_role": "can predict next_concept_id inside DecisionAgent when artifact loads",
        },
        "promotion_confidence_models": {
            "directory": str(PROMOTION_MODEL_DIR),
            "exists": PROMOTION_MODEL_DIR.exists(),
            "files": sorted(str(path) for path in PROMOTION_MODEL_DIR.glob("*") if path.is_file()),
            "synthetic_log_path": str(SYNTHETIC_PROMOTION_LOGS),
            "synthetic_log_exists": SYNTHETIC_PROMOTION_LOGS.exists(),
            "runtime_role": "comparison/model evidence for promotion confidence and progression status",
        },
        "discovered_policy_rl_files": discovered,
    }


def _discover_policy_rl_files() -> dict[str, Any]:
    keywords = ("bandit", "dqn", "promotion", "policy")
    found: dict[str, list[str]] = {keyword: [] for keyword in keywords}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lowered = str(path).lower()
            for keyword in keywords:
                if keyword in lowered:
                    found[keyword].append(str(path))
    return {
        keyword: sorted(paths)[:100]
        for keyword, paths in found.items()
    }


def _extract_pipeline_status(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    policy_data = _safe_get(output, "policy_output", "data", default={})
    bridge = output.get("adaptive_policy_bridge_output", {})
    decision_agent = output.get("decision_agent_output", {})
    dqn_output = decision_agent.get("dqn_output") if isinstance(decision_agent, dict) else None

    return {
        "learner_id": output.get("learner_id", "14"),
        "baseline_policy_output": output.get("baseline_policy_output") or output.get("current_policy_output"),
        "policy_output": output.get("policy_output"),
        "strategy": policy_data.get("strategy"),
        "difficulty": policy_data.get("difficulty"),
        "next_concept_id": policy_data.get("next_concept_id"),
        "content_type": policy_data.get("content_type"),
        "decision_type": policy_data.get("decision_type"),
        "final_policy_decision_type": policy_data.get("decision_type"),
        "final_next_concept_id": policy_data.get("next_concept_id"),
        "final_strategy": policy_data.get("strategy"),
        "final_difficulty": policy_data.get("difficulty"),
        "promotion_confidence": summary.get("promotion_confidence"),
        "promotion_allowed": summary.get("promotion_allowed"),
        "level_up_allowed": summary.get("level_up_allowed"),
        "concept_cleared": summary.get("concept_cleared"),
        "final_action": summary.get("final_action"),
        "progression_action": summary.get("progression_action"),
        "model_progression_action": summary.get("model_progression_action"),
        "model_comparison_status": summary.get("model_comparison_status")
        or summary.get("progression_model_status"),
        "model_comparison_output": summary.get("model_comparison_output")
        or summary.get("model_comparison_log_status"),
        "progression_model_status": summary.get("progression_model_status"),
        "progression_model_reason": summary.get("progression_model_reason"),
        "model_teaching_view": summary.get("model_teaching_view"),
        "model_teaching_view_confidence": summary.get("model_teaching_view_confidence"),
        "model_comparison_log_status": summary.get("model_comparison_log_status"),
        "teaching_strategy_agreement": summary.get("teaching_strategy_agreement"),
        "policy_bridge_status": bridge.get("status") if isinstance(bridge, dict) else None,
        "policy_bridge_agreement": bridge.get("agreement") if isinstance(bridge, dict) else None,
        "policy_bridge_override_allowed": bridge.get("override_allowed") if isinstance(bridge, dict) else None,
        "policy_bridge_recommendation": bridge.get("final_recommendation") if isinstance(bridge, dict) else None,
        "policy_bridge_reason": bridge.get("reason") if isinstance(bridge, dict) else None,
        "dqn_output": dqn_output,
        "adaptive_path_original_selected": summary.get("adaptive_path_original_selected"),
        "adaptive_path_selected": summary.get("adaptive_path_selected"),
        "adaptive_path_validation_status": summary.get("adaptive_path_validation_status"),
    }


def _status_from_report(report: dict[str, Any]) -> str:
    pipeline = report["pipeline_status"]
    if pipeline.get("final_policy_decision_type") is None:
        return "error"
    # Warning is the honest status: baseline policy is backend-ready, but RL is
    # not a full replacement until stronger algorithms and offline evaluation pass.
    return "warning"


def build_report() -> dict[str, Any]:
    integrated_output = run_integrated_tutor_once(learner_id="14", reward_dry_run=True)
    rl_state = _build_rl_state(integrated_output)
    report = {
        "overall_status": "warning",
        "module": "policy_rl_upgrade_report",
        "generated_at": _now_iso(),
        "learner_id": "14",
        "pipeline_status": _extract_pipeline_status(integrated_output),
        "rl_state_used_for_artifact_checks": rl_state,
        "artifact_status": _inspect_artifacts(),
        "bandit_status": _inspect_bandit(rl_state),
        "dqn_status": _inspect_dqn(rl_state, integrated_output),
        "active_vs_shadow_status": {
            "baseline_policy": "active input policy and fallback",
            "policy_model": "active if artifact loads; predicts next_concept_id inside DecisionAgent",
            "dqn": "prototype baseline can override strategy/difficulty when artifact loads; not full final RL replacement",
            "adaptive_policy_bridge": "active comparison/safety bridge; does not blindly override final policy",
            "promotion_confidence": "active evidence for reward/progression safety",
            "contextual_bandit": "artifact available but treated as comparison/prototype, not final policy authority",
            "teaching_strategy_model_comparison": "shadow/comparison only",
        },
        "status_classification": {
            "baseline_policy": "backend_ready",
            "promotion_model": "backend_ready"
            if PROMOTION_MODEL_DIR.exists()
            else "pending",
            "contextual_bandit": "prototype_comparison_mode"
            if BANDIT_MODEL_PATH.exists()
            else "pending",
            "dqn": "prototype_comparison_mode"
            if DQN_MODEL_PATH.exists()
            else "pending",
            "double_dqn": "pending",
            "dueling_dqn": "pending",
            "ppo": "pending",
            "full_rl_replacement": "pending",
        },
        "dashboard_ready_policy_rl_object": {},
        "upgrade_status": {
            "backend_ready": [
                "Baseline dependency policy remains available as fallback.",
                "Policy model artifact is present for next-concept prediction.",
                "AdaptivePolicyBridge records agreement, override allowance, and recommendation source.",
                "Promotion confidence and reward/progression safety signals are exposed in the main pipeline.",
            ],
            "comparison_or_prototype_mode": [
                "Contextual bandit model is available but remains comparison/prototype mode.",
                "DQN artifact exists and can be exercised, but metadata indicates supervised_q_vector_baseline rather than full online RL.",
                "Teaching strategy model output remains shadow/comparison mode.",
            ],
            "future_research_upgrades": [
                "Define a clean state vector: mastery_score, behaviour_risk, fused_score, weakest_skill, review_due, promotion_confidence, difficulty, view_reward, concept_dependency_status.",
                "Define policy actions: reteach, review, practice, advance_concept, level_up, change_view, select_debug, select_output_prediction, select_challenge.",
                "Define reward: mastery gain, evaluation improvement, reduced mistakes, engagement, correct promotion, retention.",
                "Train and evaluate contextual bandit, DQN, Double DQN, Dueling DQN, and PPO where feasible.",
                "Compare every learned policy against the baseline policy.",
                "Keep safe fallback and shadow mode until RL consistently outperforms baseline offline.",
                "Double DQN.",
                "Dueling DQN.",
                "Prioritized replay and target-network evaluation metrics.",
                "PPO or other policy-gradient comparison.",
                "Offline policy evaluation and counterfactual safety testing.",
                "Constrained safe exploration before any online policy learning.",
            ],
        },
        "known_limitations": [
            "Current DQN artifact is a baseline supervised Q-vector policy, not a full production RL replacement.",
            "Bandit/DQN artifacts are trained from logged/synthetic experience data and need stronger offline evaluation before becoming final authority.",
            "AdaptivePolicyBridge is safety-first and logs disagreement instead of automatically accepting every adaptive/RL suggestion.",
            "Promotion confidence is evidence-aware and model-assisted, but final promotion remains guarded by progression safety rules.",
            "Double DQN, Dueling DQN, PPO, and teacher-facing RL diagnostics remain future work.",
        ],
    }
    report["overall_status"] = _status_from_report(report)
    report["dashboard_ready_policy_rl_object"] = _build_dashboard_object(report)
    return report


def _build_dashboard_object(report: dict[str, Any]) -> dict[str, Any]:
    pipeline = report["pipeline_status"]
    return {
        "status": "success" if report["overall_status"] in {"success", "warning"} else "error",
        "module": "PolicyRLUpgradeReport",
        "current_policy_status": "backend_ready",
        "rl_status": "prototype_comparison_mode",
        "active_decision_source": pipeline.get("final_policy_decision_type"),
        "baseline_policy": {
            "strategy": pipeline.get("strategy"),
            "difficulty": pipeline.get("difficulty"),
            "next_concept_id": pipeline.get("next_concept_id"),
            "content_type": pipeline.get("content_type"),
            "decision_type": pipeline.get("decision_type"),
        },
        "promotion_model": {
            "promotion_confidence": pipeline.get("promotion_confidence"),
            "promotion_allowed": pipeline.get("promotion_allowed"),
            "level_up_allowed": pipeline.get("level_up_allowed"),
            "concept_cleared": pipeline.get("concept_cleared"),
            "final_action": pipeline.get("final_action"),
            "progression_action": pipeline.get("progression_action"),
        },
        "adaptive_bridge": {
            "adaptive_path_selected": pipeline.get("adaptive_path_selected"),
            "adaptive_path_original_selected": pipeline.get("adaptive_path_original_selected"),
            "adaptive_path_validation_status": pipeline.get("adaptive_path_validation_status"),
            "bridge_agreement": pipeline.get("policy_bridge_agreement"),
            "bridge_override_allowed": pipeline.get("policy_bridge_override_allowed"),
            "bridge_recommendation": pipeline.get("policy_bridge_recommendation"),
        },
        "model_comparison": {
            "model_comparison_status": pipeline.get("model_comparison_status"),
            "model_comparison_output": pipeline.get("model_comparison_output"),
            "model_progression_action": pipeline.get("model_progression_action"),
            "progression_model_status": pipeline.get("progression_model_status"),
            "progression_model_reason": pipeline.get("progression_model_reason"),
            "model_teaching_view": pipeline.get("model_teaching_view"),
            "model_teaching_view_confidence": pipeline.get("model_teaching_view_confidence"),
        },
        "rl_models": {
            "contextual_bandit": report["status_classification"]["contextual_bandit"],
            "dqn": report["status_classification"]["dqn"],
            "double_dqn": report["status_classification"]["double_dqn"],
            "dueling_dqn": report["status_classification"]["dueling_dqn"],
            "ppo": report["status_classification"]["ppo"],
        },
        "safe_fallback": True,
        "frontend_dashboard_fields": {
            "policy_card": [
                "active_decision_source",
                "strategy",
                "difficulty",
                "next_concept_id",
            ],
            "promotion_card": [
                "promotion_confidence",
                "promotion_allowed",
                "progression_action",
            ],
            "rl_status_card": [
                "contextual_bandit",
                "dqn",
                "double_dqn",
                "dueling_dqn",
                "ppo",
            ],
            "safety_card": [
                "safe_fallback",
                "bridge_agreement",
                "bridge_override_allowed",
            ],
        },
    }


def _build_markdown(report: dict[str, Any]) -> str:
    pipeline = report["pipeline_status"]
    artifact = report["artifact_status"]
    bandit = report["bandit_status"]
    dqn = report["dqn_status"]
    lines = [
        "# Policy/RL Upgrade Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Runtime Pipeline Evidence",
        "",
        f"- final policy decision type: `{pipeline.get('final_policy_decision_type')}`",
        f"- final next concept: `{pipeline.get('final_next_concept_id')}`",
        f"- final strategy/difficulty: `{pipeline.get('final_strategy')}` / `{pipeline.get('final_difficulty')}`",
        f"- promotion confidence: `{pipeline.get('promotion_confidence')}`",
        f"- promotion allowed: `{pipeline.get('promotion_allowed')}`",
        f"- progression action: `{pipeline.get('progression_action')}`",
        f"- model progression action: `{pipeline.get('model_progression_action')}`",
        f"- progression model status: `{pipeline.get('progression_model_status')}`",
        f"- model comparison log status: `{pipeline.get('model_comparison_log_status')}`",
        "",
        "## Adaptive Policy Bridge",
        "",
        f"- status: `{pipeline.get('policy_bridge_status')}`",
        f"- agreement: `{pipeline.get('policy_bridge_agreement')}`",
        f"- override allowed: `{pipeline.get('policy_bridge_override_allowed')}`",
        f"- recommendation: `{pipeline.get('policy_bridge_recommendation')}`",
        f"- reason: {pipeline.get('policy_bridge_reason')}",
        "",
        "## Artifact Status",
        "",
        f"- policy model exists: `{artifact['policy_model']['exists']}`",
        f"- policy model metadata: `{artifact['policy_model']['metadata']}`",
        f"- promotion model files: `{artifact['promotion_confidence_models']['files']}`",
        f"- contextual bandit available: `{bandit.get('available')}`",
        f"- contextual bandit prediction: `{bandit.get('prediction')}`",
        f"- DQN available: `{dqn.get('available')}`",
        f"- DQN integrated output: `{dqn.get('integrated_decision_agent_output')}`",
        f"- DQN standalone prediction: `{dqn.get('standalone_prediction')}`",
        "",
        "## Active vs Shadow/Comparison Mode",
        "",
    ]
    for key, value in report["active_vs_shadow_status"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Backend-Ready Pieces", ""])
    for item in report["upgrade_status"]["backend_ready"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Comparison/Prototype Mode", ""])
    for item in report["upgrade_status"]["comparison_or_prototype_mode"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Future RL Upgrade Path", ""])
    for item in report["upgrade_status"]["future_research_upgrades"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Known Limitations", ""])
    for item in report["known_limitations"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: policy_rl_upgrade_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['overall_status']}")
    print("MODULE: policy_rl_upgrade_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
