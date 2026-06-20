from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tutor.RL.bandit_policy import BanditPolicy
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.policy.adaptive_policy_bridge import AdaptivePolicyBridge
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask
from tutor.system.policy_model_inference import PolicyModel
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


CSV_PATH = Path("evaluation_outputs/csv/synthetic_promotion_confidence_logs.csv")
OUTPUT_JSON = Path("evaluation_outputs/json/rl_offline_policy_evaluation_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rl_offline_policy_evaluation_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _learning_signal(score: float) -> str:
    if score >= 0.75:
        return "mastered"
    if score >= 0.50:
        return "partial"
    return "weak"


def _baseline_action(row: dict[str, Any]) -> str:
    target = str(row.get("target_progression_action", "")).strip()
    difficulty = str(row.get("difficulty", "medium")).strip().lower() or "medium"
    if target in {"advance", "level_up", "advance_concept"}:
        return "advanced_hard"
    if target in {"remediate", "reteach", "review"}:
        return "remedial_easy"
    return f"practice_{difficulty if difficulty in {'easy', 'medium', 'hard'} else 'medium'}"


def _state_from_row(row: dict[str, Any]) -> dict[str, Any]:
    evaluation_score = _safe_float(row.get("evaluation_score"))
    behaviour_risk = _safe_float(row.get("behaviour_score", row.get("behavior_score", 0.0)))
    return {
        "learner_id": str(row.get("learner_id", "")),
        "concept_id": str(row.get("concept_id", "")),
        "mastery_score": _safe_float(row.get("mastery")),
        "behavior_score": behaviour_risk,
        "behaviour_risk": behaviour_risk,
        "behaviour_risk_label": "high_risk" if behaviour_risk >= 0.7 else "medium_risk" if behaviour_risk >= 0.4 else "low_risk",
        "review_due": _safe_float(row.get("forgetting_priority")) >= 0.5,
        "evaluation_score": evaluation_score,
        "fused_score": evaluation_score,
        "fused_label": "needs_reteaching" if evaluation_score < 0.5 else "partial" if evaluation_score < 0.75 else "mastered",
        "learning_signal": _learning_signal(evaluation_score),
        "promotion_confidence": (
            0.75
            if int(_safe_float(row.get("target_promotion_allowed"), 0.0)) == 1
            else min(0.59, max(0.0, (_safe_float(row.get("mastery")) + evaluation_score) / 2.0))
        ),
        "difficulty": str(row.get("difficulty", "medium")),
        "view_reward": _safe_float(row.get("view_reward"), 0.5),
        "target_promotion_allowed": int(_safe_float(row.get("target_promotion_allowed"), 0.0)),
    }


def _action_from_output(output: dict[str, Any] | None) -> str | None:
    if not isinstance(output, dict) or output.get("status") != "success":
        return None
    action_label = output.get("action_label")
    if action_label:
        return str(action_label)
    strategy = output.get("strategy")
    difficulty = output.get("difficulty")
    if strategy and difficulty:
        return f"{strategy}_{difficulty}"
    return None


def _safe_reference_action(state: dict[str, Any]) -> str:
    if state["mastery_score"] < 0.4:
        return "remedial_easy"
    if state["behaviour_risk"] >= 0.7 or state["behaviour_risk_label"] == "high_risk":
        return "practice_medium"
    if state["review_due"]:
        return "practice_medium"
    if state["fused_score"] < 0.5 or state["fused_label"] == "needs_reteaching":
        return "remedial_easy"
    if state["promotion_confidence"] < 0.6:
        return "practice_medium"
    if state["mastery_score"] >= 0.75 and state["fused_score"] >= 0.75:
        return "advanced_hard"
    return "practice_medium"


def _violations(state: dict[str, Any], action: str | None) -> list[str]:
    if action is None:
        return ["no_action"]
    lowered = action.lower()
    violations: list[str] = []
    is_advanced = "advanced" in lowered or "hard" in lowered or "challenge" in lowered or "level_up" in lowered
    is_promote = "advance" in lowered or "level_up" in lowered or "advanced" in lowered
    is_reviewish = any(token in lowered for token in ["review", "revision", "practice", "remedial", "reteach"])
    if state["mastery_score"] < 0.4 and is_advanced:
        violations.append("challenge_or_advance_on_low_mastery")
    if (state["behaviour_risk"] >= 0.7 or state["behaviour_risk_label"] == "high_risk") and is_advanced:
        violations.append("hard_or_challenge_on_high_behaviour_risk")
    if state["review_due"] and not is_reviewish:
        violations.append("review_due_but_not_review")
    if (state["fused_score"] < 0.5 or state["fused_label"] == "needs_reteaching") and is_promote:
        violations.append("promotion_on_needs_reteaching")
    if state["promotion_confidence"] < 0.6 and is_promote:
        violations.append("promotion_below_confidence_threshold")
    return violations


def _empty_metrics(available: bool) -> dict[str, Any]:
    return {
        "model_available": available,
        "evaluated_cases": 0,
        "action_agreement_with_baseline": None,
        "action_agreement_with_safe_bridge": None,
        "bad_action_rate": None,
        "unsafe_promotion_rate": None,
        "challenge_on_low_mastery_rate": None,
        "hard_on_high_behaviour_risk_rate": None,
        "review_due_but_not_review_rate": None,
        "average_predicted_reward": None,
        "action_distribution": {},
        "recommendation_summary": "No available actions to evaluate.",
    }


def _summarize(actions: list[str | None], states: list[dict[str, Any]], baseline: list[str], safe: list[str], available: bool) -> dict[str, Any]:
    valid = [(a, s, b, sf) for a, s, b, sf in zip(actions, states, baseline, safe) if a is not None]
    if not valid:
        return _empty_metrics(available)
    violations_by_case = [_violations(state, action) for action, state, _, _ in valid]
    n = len(valid)
    total_violations = sum(1 for violations in violations_by_case if violations)
    action_counts = Counter(str(action) for action, _, _, _ in valid)
    reward_values = []
    for action, state, _, _ in valid:
        violation_count = len(_violations(state, action))
        reward = 1.0 - min(1.0, 0.5 * violation_count)
        if action == _safe_reference_action(state):
            reward += 0.1
        reward_values.append(max(0.0, min(1.0, reward)))
    return {
        "model_available": available,
        "evaluated_cases": n,
        "action_agreement_with_baseline": round(sum(1 for a, _, b, _ in valid if a == b) / n, 4),
        "action_agreement_with_safe_bridge": round(sum(1 for a, _, _, sf in valid if a == sf) / n, 4),
        "bad_action_rate": round(total_violations / n, 4),
        "unsafe_promotion_rate": round(
            sum(1 for violations in violations_by_case if any("promotion" in v for v in violations)) / n,
            4,
        ),
        "challenge_on_low_mastery_rate": round(
            sum(1 for violations in violations_by_case if "challenge_or_advance_on_low_mastery" in violations) / n,
            4,
        ),
        "hard_on_high_behaviour_risk_rate": round(
            sum(1 for violations in violations_by_case if "hard_or_challenge_on_high_behaviour_risk" in violations) / n,
            4,
        ),
        "review_due_but_not_review_rate": round(
            sum(1 for violations in violations_by_case if "review_due_but_not_review" in violations) / n,
            4,
        ),
        "average_predicted_reward": round(sum(reward_values) / len(reward_values), 4),
        "action_distribution": dict(action_counts),
        "recommendation_summary": (
            "Offline safety check passed without violations."
            if total_violations == 0
            else "Offline safety check found potential unsafe actions; keep RL in safety/comparison mode."
        ),
    }


def _policy_model_predictions(states: list[dict[str, Any]]) -> list[str | None]:
    model = PolicyModel()
    if not model.is_available():
        return [None for _ in states]
    actions: list[str | None] = []
    for state in states:
        try:
            predicted_concept = model.predict_next_concept(
                {
                    "mastery_score": state["mastery_score"],
                    "behavior_label": state["behaviour_risk_label"],
                    "behavior_score": state["behaviour_risk"],
                    "review_due": state["review_due"],
                    "evaluation_score": state["evaluation_score"],
                    "learning_signal": state["learning_signal"],
                    "final_action": "review" if state["review_due"] else "practice",
                    "recommended_strategy": _safe_reference_action(state).split("_")[0],
                    "recommended_difficulty": _safe_reference_action(state).split("_")[-1],
                }
            )
            actions.append(f"select_concept_{predicted_concept}")
        except Exception:
            actions.append(None)
    return actions


def _bandit_predictions(states: list[dict[str, Any]]) -> tuple[bool, list[str | None]]:
    model = BanditPolicy()
    available = model.is_available()
    actions: list[str | None] = []
    for state in states:
        try:
            actions.append(_action_from_output(model.predict(state)) if available else None)
        except Exception:
            actions.append(None)
    return available, actions


def _dqn_predictions(states: list[dict[str, Any]]) -> tuple[bool, list[str | None]]:
    model = DQNPolicy()
    available = model.is_available()
    actions: list[str | None] = []
    for state in states:
        try:
            actions.append(_action_from_output(model.predict(state)) if available else None)
        except Exception:
            actions.append(None)
    return available, actions


def _mask_actions(states: list[dict[str, Any]], actions: list[str | None]) -> list[str | None]:
    masked: list[str | None] = []
    for state, action in zip(states, actions):
        if action is None:
            masked.append(None)
            continue
        masked.append(apply_rl_safe_action_mask(state, action).get("masked_action"))
    return masked


def _bridge_status() -> dict[str, Any]:
    try:
        output = run_integrated_tutor_once(learner_id="14", reward_dry_run=True)
        bridge = output.get("adaptive_policy_bridge_output", {})
        return {
            "status": bridge.get("status"),
            "agreement": bridge.get("agreement"),
            "override_allowed": bridge.get("override_allowed"),
            "recommendation": bridge.get("final_recommendation"),
            "reason": bridge.get("reason"),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def build_report() -> dict[str, Any]:
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH).head(500)
    else:
        df = pd.DataFrame()
    states = [_state_from_row(row) for row in df.to_dict(orient="records")]
    baseline_actions = [_baseline_action(row) for row in df.to_dict(orient="records")]
    safe_actions = [_safe_reference_action(state) for state in states]

    policy_model = PolicyModel()
    bandit_available, bandit_actions = _bandit_predictions(states)
    dqn_available, dqn_actions = _dqn_predictions(states)
    policy_model_actions = _policy_model_predictions(states)

    masked_baseline_actions = _mask_actions(states, baseline_actions)
    masked_policy_model_actions = _mask_actions(states, policy_model_actions)
    masked_bandit_actions = _mask_actions(states, bandit_actions)
    masked_dqn_actions = _mask_actions(states, dqn_actions)

    baseline_metrics = _summarize(masked_baseline_actions, states, baseline_actions, safe_actions, available=bool(states))
    policy_model_metrics = _summarize(masked_policy_model_actions, states, baseline_actions, safe_actions, policy_model.is_available())
    bandit_metrics = _summarize(masked_bandit_actions, states, baseline_actions, safe_actions, bandit_available)
    dqn_metrics = _summarize(masked_dqn_actions, states, baseline_actions, safe_actions, dqn_available)

    status = "success"
    if any(
        metrics.get("bad_action_rate") not in {None, 0, 0.0}
        for metrics in [policy_model_metrics, bandit_metrics, dqn_metrics]
    ):
        status = "warning"
    if dqn_available or bandit_available:
        status = "warning"

    return {
        "status": status,
        "module": "rl_offline_policy_evaluation",
        "generated_at": _now_iso(),
        "dataset_status": {
            "csv_path": str(CSV_PATH),
            "csv_exists": CSV_PATH.exists(),
            "evaluated_cases": len(states),
        },
        "model_status": {
            "baseline_policy_status": "backend_ready",
            "policy_model_status": "available" if policy_model.is_available() else "missing",
            "contextual_bandit_status": "prototype_comparison_mode" if bandit_available else "missing",
            "dqn_status": "prototype_comparison_mode" if dqn_available else "missing",
            "full_rl_replacement_status": "pending",
        },
        "adaptive_bridge_status": _bridge_status(),
        "metrics": {
            "baseline_policy": baseline_metrics,
            "policy_model": policy_model_metrics,
            "contextual_bandit": bandit_metrics,
            "dqn": dqn_metrics,
        },
        "masking_status": {
            "safe_action_mask_applied": True,
            "note": "Metrics use RLSafeActionMask-filtered actions. Raw before/after rates are in rl_safe_action_masking_report.",
        },
        "policy_action_distribution": baseline_metrics.get("action_distribution", {}),
        "bandit_action_distribution": bandit_metrics.get("action_distribution", {}),
        "dqn_action_distribution": dqn_metrics.get("action_distribution", {}),
        "recommendation_summary": [
            "Keep baseline policy and AdaptivePolicyBridge as safety authority.",
            "Keep contextual bandit and DQN in prototype/comparison mode until offline violations are zero and reward metrics beat baseline.",
            "Add stronger logged rewards and counterfactual safety tests before any full RL replacement.",
        ],
        "limitations": [
            "Evaluation uses available synthetic promotion logs and transparent safety heuristics.",
            "PolicyModel predicts next concept rather than a full action label, so action-level comparison is approximate.",
            "Average predicted reward is a safety proxy, not an environment reward estimate.",
        ],
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# RL Offline Policy Evaluation Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        "## Dataset",
        "",
        f"- CSV exists: `{report['dataset_status']['csv_exists']}`",
        f"- evaluated cases: `{report['dataset_status']['evaluated_cases']}`",
        "",
        "## Model Status",
        "",
    ]
    for key, value in report["model_status"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Metrics", ""])
    for model_name, metrics in report["metrics"].items():
        lines.append(f"### {model_name}")
        for key, value in metrics.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.extend(["## Adaptive Bridge", ""])
    for key, value in report["adaptive_bridge_status"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Recommendation Summary", ""])
    for item in report["recommendation_summary"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Status", "", "```text", f"STATUS: {report['status']}", "MODULE: rl_offline_policy_evaluation", "```", ""])
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: rl_offline_policy_evaluation")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
