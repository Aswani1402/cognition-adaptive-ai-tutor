from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tutor.RL.bandit_policy import BanditPolicy
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.policy.rl.double_dqn_policy import DoubleDQNPolicy
from tutor.policy.rl.dueling_dqn_policy import DuelingDQNPolicy
from tutor.policy.rl.state_action_space import STATE_FEATURES, id_to_action
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask, detect_rl_action_violations


DATA_PATH = Path("evaluation_outputs/csv/rl_training_dataset.csv")
DOUBLE_DQN_PATH = Path("models/rl/double_dqn_policy.pt")
DUELING_DQN_PATH = Path("models/rl/dueling_dqn_policy.pt")
OUTPUT_JSON = Path("evaluation_outputs/json/rl_model_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rl_model_comparison_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_from_row(row: pd.Series) -> dict[str, Any]:
    return {
        "mastery_score": float(row["mastery_score"]),
        "behaviour_risk": float(row["behaviour_risk"]),
        "fused_score": float(row["fused_score"]),
        "review_due": bool(row["review_due"]),
        "promotion_confidence": float(row["promotion_confidence"]),
        "difficulty": "hard" if row["difficulty_encoded"] >= 0.75 else "medium" if row["difficulty_encoded"] >= 0.25 else "easy",
        "weakest_skill": "output_prediction" if row["weakest_skill_encoded"] >= 0.5 else "none",
        "behaviour_risk_label": "high_risk" if row["behaviour_risk_label_encoded"] >= 0.75 else "medium_risk" if row["behaviour_risk_label_encoded"] >= 0.25 else "low_risk",
        "concept_dependency_valid": bool(row["concept_dependency_valid"]),
        "concept_domain_match": bool(row["concept_dependency_valid"]),
        "view_reward": float(row["view_reward"]),
    }


def _legacy_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "mastery_score": state["mastery_score"],
        "behavior_score": state["behaviour_risk"],
        "review_due": state["review_due"],
        "evaluation_score": state["fused_score"],
        "learning_signal": "mastered" if state["fused_score"] >= 0.75 else "partial" if state["fused_score"] >= 0.5 else "weak",
    }


def _action_from_output(output: dict[str, Any] | None) -> str | None:
    if not isinstance(output, dict) or output.get("status") != "success":
        return None
    if output.get("action_label"):
        return str(output["action_label"])
    if output.get("strategy") and output.get("difficulty"):
        return f"{output['strategy']}_{output['difficulty']}"
    return None


def _predict_actions(df: pd.DataFrame) -> dict[str, list[str | None]]:
    states = [_state_from_row(row) for _, row in df.iterrows()]
    vectors = df[STATE_FEATURES].astype(float).to_numpy(dtype=np.float32)
    actions: dict[str, list[str | None]] = {
        "baseline_policy": [id_to_action(int(row["action_id"])) for _, row in df.iterrows()],
        "contextual_bandit": [],
        "current_dqn": [],
        "double_dqn": [],
        "dueling_dqn": [],
    }

    bandit = BanditPolicy()
    dqn = DQNPolicy()
    double = DoubleDQNPolicy.load(DOUBLE_DQN_PATH) if DOUBLE_DQN_PATH.exists() else None
    dueling = DuelingDQNPolicy.load(DUELING_DQN_PATH) if DUELING_DQN_PATH.exists() else None

    for state, vector in zip(states, vectors):
        try:
            actions["contextual_bandit"].append(_action_from_output(bandit.predict(_legacy_state(state))) if bandit.is_available() else None)
        except Exception:
            actions["contextual_bandit"].append(None)
        try:
            actions["current_dqn"].append(_action_from_output(dqn.predict(_legacy_state(state))) if dqn.is_available() else None)
        except Exception:
            actions["current_dqn"].append(None)
        try:
            actions["double_dqn"].append(double.predict_action(vector)["action_label"] if double else None)
        except Exception:
            actions["double_dqn"].append(None)
        try:
            actions["dueling_dqn"].append(dueling.predict_action(vector)["action_label"] if dueling else None)
        except Exception:
            actions["dueling_dqn"].append(None)
    return actions


def _metrics(df: pd.DataFrame, actions: list[str | None]) -> dict[str, Any]:
    valid = [
        (_state_from_row(row), action, float(row["reward"]), id_to_action(int(row["action_id"])))
        for (_, row), action in zip(df.iterrows(), actions)
        if action is not None
    ]
    if not valid:
        return {
            "model_available": False,
            "evaluated_cases": 0,
            "average_predicted_reward": None,
            "unsafe_action_rate_before_mask": None,
            "unsafe_action_rate_after_mask": None,
            "counterfactual_pass_rate": None,
            "agreement_with_safe_bridge": None,
            "promotion_safety": None,
            "action_distribution_before_mask": {},
            "action_distribution_after_mask": {},
            "masked_action_rate": None,
        }
    before_bad = 0
    after_bad = 0
    masked = 0
    reward_values = []
    safe_agreement = 0
    counterfactual_pass = 0
    promotion_unsafe_after = 0
    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()
    for state, action, logged_reward, baseline_action in valid:
        before_counts[str(action)] += 1
        before_violations = detect_rl_action_violations(str(action), state)
        if before_violations:
            before_bad += 1
        mask = apply_rl_safe_action_mask(state, action)
        after_action = mask["masked_action"]
        after_counts[str(after_action)] += 1
        if mask["was_masked"]:
            masked += 1
        after_violations = detect_rl_action_violations(str(after_action), state)
        if after_violations:
            after_bad += 1
        if not after_violations:
            counterfactual_pass += 1
        if after_action == baseline_action or not after_violations:
            safe_agreement += 1
        if any("promotion" in item or "advance" in item for item in after_violations):
            promotion_unsafe_after += 1
        reward_values.append(logged_reward - 0.5 * len(before_violations) + 0.15 * (1 if not after_violations else 0))
    n = len(valid)
    return {
        "model_available": True,
        "evaluated_cases": n,
        "average_predicted_reward": round(sum(reward_values) / n, 4),
        "unsafe_action_rate_before_mask": round(before_bad / n, 4),
        "unsafe_action_rate_after_mask": round(after_bad / n, 4),
        "counterfactual_pass_rate": round(counterfactual_pass / n, 4),
        "agreement_with_safe_bridge": round(safe_agreement / n, 4),
        "promotion_safety": round(1.0 - promotion_unsafe_after / n, 4),
        "action_distribution_before_mask": dict(before_counts),
        "action_distribution_after_mask": dict(after_counts),
        "masked_action_rate": round(masked / n, 4),
    }


def build_report() -> dict[str, Any]:
    df = pd.read_csv(DATA_PATH).head(500)
    actions = _predict_actions(df)
    model_metrics = {name: _metrics(df, preds) for name, preds in actions.items()}
    after_rates = [
        metrics["unsafe_action_rate_after_mask"]
        for metrics in model_metrics.values()
        if metrics["unsafe_action_rate_after_mask"] is not None
    ]
    all_masked_safe = all(rate == 0 for rate in after_rates)
    best_model = max(
        model_metrics.items(),
        key=lambda item: item[1]["average_predicted_reward"] if item[1]["average_predicted_reward"] is not None else -999,
    )[0]
    return {
        "status": "success" if all_masked_safe else "warning",
        "module": "rl_model_comparison_report",
        "generated_at": _now_iso(),
        "dataset_path": str(DATA_PATH),
        "evaluated_cases": len(df),
        "models_compared": list(model_metrics.keys()),
        "model_metrics": model_metrics,
        "safe_action_mask_applied": True,
        "full_rl_replacement_allowed": False,
        "best_comparison_model_by_proxy_reward": best_model,
        "recommendation": (
            "Double DQN and Dueling DQN are now trained from scratch and can be compared in safety-masked mode. "
            "Keep AdaptivePolicyBridge and RLSafeActionMask as final guards; do not enable full RL authority yet."
        ),
        "limitations": [
            "Training uses offline tutor/synthetic logs, not live online RL.",
            "Average predicted reward is a proxy based on logged/offline reward and safety penalties.",
            "Current DQN has a smaller legacy action space, so comparisons are approximate.",
            "Safe action masking is required for all learned policy outputs.",
        ],
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# RL Model Comparison Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        f"Evaluated cases: `{report['evaluated_cases']}`",
        "",
        "## Model Metrics",
        "",
    ]
    for name, metrics in report["model_metrics"].items():
        lines.append(f"### {name}")
        for key, value in metrics.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.extend(
        [
            "## Recommendation",
            "",
            report["recommendation"],
            "",
            "## Limitations",
            "",
        ]
    )
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Status", "", "```text", f"STATUS: {report['status']}", "MODULE: rl_model_comparison_report", "```", ""])
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: rl_model_comparison_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
