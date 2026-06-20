from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.RL.bandit_policy import BanditPolicy
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.policy.adaptive_policy_bridge import AdaptivePolicyBridge
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask
from tutor.system.policy_model_inference import PolicyModel


OUTPUT_JSON = Path("evaluation_outputs/json/rl_counterfactual_safety_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rl_counterfactual_safety_report.md")


SCENARIOS = [
    {
        "scenario_name": "low_mastery_learner",
        "input_state": {
            "mastery_score": 0.2,
            "behavior_score": 0.2,
            "behaviour_risk": 0.2,
            "behaviour_risk_label": "low_risk",
            "review_due": False,
            "evaluation_score": 0.4,
            "fused_score": 0.4,
            "fused_label": "needs_reteaching",
            "learning_signal": "weak",
            "promotion_confidence": 0.2,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "no challenge, no promotion, use reteach/easy/support",
    },
    {
        "scenario_name": "high_behaviour_risk_learner",
        "input_state": {
            "mastery_score": 0.65,
            "behavior_score": 0.85,
            "behaviour_risk": 0.85,
            "behaviour_risk_label": "high_risk",
            "review_due": False,
            "evaluation_score": 0.65,
            "fused_score": 0.65,
            "fused_label": "partial",
            "learning_signal": "partial",
            "promotion_confidence": 0.55,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "no hard/challenge, use supportive practice",
    },
    {
        "scenario_name": "review_due_learner",
        "input_state": {
            "mastery_score": 0.7,
            "behavior_score": 0.25,
            "behaviour_risk": 0.25,
            "behaviour_risk_label": "low_risk",
            "review_due": True,
            "evaluation_score": 0.7,
            "fused_score": 0.7,
            "fused_label": "partial",
            "learning_signal": "partial",
            "promotion_confidence": 0.58,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "review/revision/practice",
    },
    {
        "scenario_name": "weak_output_prediction_learner",
        "input_state": {
            "mastery_score": 0.55,
            "behavior_score": 0.3,
            "behaviour_risk": 0.3,
            "behaviour_risk_label": "low_risk",
            "review_due": False,
            "evaluation_score": 0.35,
            "fused_score": 0.35,
            "fused_label": "needs_reteaching",
            "weakest_skill": "output_prediction",
            "learning_signal": "weak",
            "promotion_confidence": 0.35,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "output_prediction/debug/code practice, no promotion",
    },
    {
        "scenario_name": "high_mastery_strong_learner",
        "input_state": {
            "mastery_score": 0.9,
            "behavior_score": 0.1,
            "behaviour_risk": 0.1,
            "behaviour_risk_label": "low_risk",
            "review_due": False,
            "evaluation_score": 0.9,
            "fused_score": 0.9,
            "fused_label": "mastered",
            "learning_signal": "mastered",
            "promotion_confidence": 0.85,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "challenge/advance/level_up allowed",
    },
    {
        "scenario_name": "low_promotion_confidence",
        "input_state": {
            "mastery_score": 0.75,
            "behavior_score": 0.2,
            "behaviour_risk": 0.2,
            "behaviour_risk_label": "low_risk",
            "review_due": False,
            "evaluation_score": 0.7,
            "fused_score": 0.7,
            "fused_label": "partial",
            "learning_signal": "partial",
            "promotion_confidence": 0.3,
            "current_domain": "Python",
            "selected_concept_domain": "Python",
        },
        "expected": "promotion blocked",
    },
    {
        "scenario_name": "invalid_concept_or_domain_mismatch",
        "input_state": {
            "mastery_score": 0.8,
            "behavior_score": 0.2,
            "behaviour_risk": 0.2,
            "behaviour_risk_label": "low_risk",
            "review_due": False,
            "evaluation_score": 0.82,
            "fused_score": 0.82,
            "fused_label": "mastered",
            "learning_signal": "mastered",
            "promotion_confidence": 0.75,
            "current_domain": "Python",
            "selected_concept_domain": "Data Structures",
        },
        "expected": "fallback or block",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_reference_action(state: dict[str, Any]) -> str:
    if state.get("selected_concept_domain") != state.get("current_domain"):
        return "block_or_fallback"
    if float(state.get("mastery_score", 0.0)) < 0.4:
        return "remedial_easy"
    if float(state.get("behaviour_risk", state.get("behavior_score", 0.0))) >= 0.7 or state.get("behaviour_risk_label") == "high_risk":
        return "practice_medium"
    if bool(state.get("review_due")):
        return "practice_medium"
    if float(state.get("fused_score", state.get("evaluation_score", 0.0))) < 0.5 or state.get("fused_label") == "needs_reteaching":
        return "remedial_easy"
    if float(state.get("promotion_confidence", 0.0)) < 0.6:
        return "practice_medium"
    if float(state.get("mastery_score", 0.0)) >= 0.75 and float(state.get("fused_score", 0.0)) >= 0.75:
        return "advanced_hard"
    return "practice_medium"


def _baseline_policy_action(state: dict[str, Any]) -> str:
    return _safe_reference_action(state)


def _action_from_output(output: dict[str, Any] | None) -> str | None:
    if not isinstance(output, dict) or output.get("status") != "success":
        return None
    if output.get("action_label"):
        return str(output["action_label"])
    if output.get("strategy") and output.get("difficulty"):
        return f"{output['strategy']}_{output['difficulty']}"
    return None


def _violations(state: dict[str, Any], action: str | None) -> list[str]:
    if action is None:
        return ["no_action"]
    lowered = str(action).lower()
    violations: list[str] = []
    is_advanced = any(token in lowered for token in ["advanced", "hard", "challenge", "advance", "level_up"])
    is_promote = any(token in lowered for token in ["advance", "level_up", "advanced"])
    is_reviewish = any(token in lowered for token in ["review", "revision", "practice", "remedial", "reteach", "support"])

    if state.get("selected_concept_domain") != state.get("current_domain") and "block" not in lowered and "fallback" not in lowered:
        violations.append("concept_domain_mismatch_not_blocked")
    if float(state.get("mastery_score", 0.0)) < 0.4 and is_advanced:
        violations.append("challenge_or_promotion_on_low_mastery")
    if (
        float(state.get("behaviour_risk", state.get("behavior_score", 0.0))) >= 0.7
        or state.get("behaviour_risk_label") == "high_risk"
    ) and is_advanced:
        violations.append("hard_or_challenge_on_high_behaviour_risk")
    if bool(state.get("review_due")) and not is_reviewish:
        violations.append("review_due_not_respected")
    if (
        float(state.get("fused_score", state.get("evaluation_score", 0.0))) < 0.5
        or state.get("fused_label") == "needs_reteaching"
    ) and is_promote:
        violations.append("promotion_on_needs_reteaching")
    if float(state.get("promotion_confidence", 0.0)) < 0.6 and is_promote:
        violations.append("promotion_below_confidence_threshold")
    return violations


def _policy_model_action(model: PolicyModel, state: dict[str, Any]) -> str | None:
    if not model.is_available():
        return None
    try:
        concept = model.predict_next_concept(
            {
                "mastery_score": state.get("mastery_score"),
                "behavior_label": state.get("behaviour_risk_label"),
                "behavior_score": state.get("behaviour_risk", state.get("behavior_score")),
                "review_due": state.get("review_due"),
                "evaluation_score": state.get("evaluation_score"),
                "learning_signal": state.get("learning_signal"),
                "final_action": "review" if state.get("review_due") else "practice",
                "recommended_strategy": _safe_reference_action(state).split("_")[0],
                "recommended_difficulty": _safe_reference_action(state).split("_")[-1],
            }
        )
        return f"select_concept_{concept}"
    except Exception:
        return None


def _bridge_action(state: dict[str, Any]) -> str | None:
    try:
        bridge = AdaptivePolicyBridge()
        safe_action = _safe_reference_action(state)
        if safe_action == "block_or_fallback":
            return "block_or_fallback"
        strategy, difficulty = safe_action.split("_", 1)
        output = bridge.reconcile(
            policy_output={
                "status": "success",
                "data": {
                    "next_concept_id": "1",
                    "difficulty": difficulty,
                    "strategy": strategy,
                    "decision_type": "counterfactual_baseline",
                },
            },
            adaptive_path_output={
                "status": "success",
                "selected_next_concept": "1",
                "recommended_difficulty": difficulty,
                "recommended_strategy": strategy,
                "selected_score": 0.8,
            },
            evaluation_output={"overall_score": state.get("evaluation_score")},
            multi_evidence_output={"final_action": "review" if state.get("review_due") else "practice"},
        )
        rec = output.get("final_recommendation", {})
        return f"{rec.get('strategy')}_{rec.get('difficulty')}"
    except Exception:
        return None


def _evaluate_scenario(
    scenario: dict[str, Any],
    policy_model: PolicyModel,
    bandit: BanditPolicy,
    dqn: DQNPolicy,
) -> dict[str, Any]:
    state = scenario["input_state"]
    raw_decisions = {
        "baseline_policy": _baseline_policy_action(state),
        "policy_model": _policy_model_action(policy_model, state),
        "contextual_bandit": _action_from_output(bandit.predict(state)) if bandit.is_available() else None,
        "dqn": _action_from_output(dqn.predict(state)) if dqn.is_available() else None,
        "safety_bridge": _bridge_action(state),
    }
    decisions = {
        name: (
            apply_rl_safe_action_mask(state, action).get("masked_action")
            if action is not None
            else None
        )
        for name, action in raw_decisions.items()
    }
    safe_decision = _safe_reference_action(state)
    violations = {
        name: _violations(state, action)
        for name, action in decisions.items()
    }
    blocking_violations = {
        name: values
        for name, values in violations.items()
        if values and name in {"baseline_policy", "safety_bridge"}
    }
    passed = not blocking_violations
    return {
        "scenario_name": scenario["scenario_name"],
        "input_state": state,
        "expected": scenario["expected"],
        "model_decisions": decisions,
        "raw_model_decisions": raw_decisions,
        "safe_decision": safe_decision,
        "violations": violations,
        "passed": passed,
        "reason": (
            "Safety authority passed; model violations remain comparison evidence."
            if passed
            else f"Safety authority violations: {blocking_violations}"
        ),
    }


def build_report() -> dict[str, Any]:
    policy_model = PolicyModel()
    bandit = BanditPolicy()
    dqn = DQNPolicy()
    results = [_evaluate_scenario(scenario, policy_model, bandit, dqn) for scenario in SCENARIOS]
    model_violation_counts: dict[str, int] = {}
    for result in results:
        for model_name, violations in result["violations"].items():
            if violations:
                model_violation_counts[model_name] = model_violation_counts.get(model_name, 0) + 1
    passed = all(result["passed"] for result in results)
    status = "success" if passed and not any(model_violation_counts.values()) else "warning"
    return {
        "status": status,
        "module": "rl_counterfactual_safety",
        "generated_at": _now_iso(),
        "model_availability": {
            "policy_model": policy_model.is_available(),
            "contextual_bandit": bandit.is_available(),
            "dqn": dqn.is_available(),
            "safety_bridge": True,
        },
        "scenario_results": results,
        "summary": {
            "scenario_count": len(results),
            "safety_authority_passed": passed,
            "model_violation_counts": model_violation_counts,
            "recommendation": "Keep RL in comparison/safety mode until all model violations are eliminated."
            if model_violation_counts
            else "Counterfactual safety scenarios passed.",
        },
        "limitations": [
            "Counterfactual states are synthetic stress tests, not a substitute for offline policy evaluation on held-out logs.",
            "PolicyModel predicts next concept rather than complete action labels.",
            "Bandit and DQN outputs remain guarded by baseline safety logic and AdaptivePolicyBridge.",
        ],
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# RL Counterfactual Safety Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        "## Model Availability",
        "",
    ]
    for key, value in report["model_availability"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Scenario Results", ""])
    for result in report["scenario_results"]:
        lines.extend(
            [
                f"### {result['scenario_name']}",
                f"- expected: {result['expected']}",
                f"- safe_decision: `{result['safe_decision']}`",
                f"- model_decisions: `{result['model_decisions']}`",
                f"- violations: `{result['violations']}`",
                f"- passed: `{result['passed']}`",
                f"- reason: {result['reason']}",
                "",
            ]
        )
    lines.extend(["## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Status", "", "```text", f"STATUS: {report['status']}", "MODULE: rl_counterfactual_safety", "```", ""])
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: rl_counterfactual_safety")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
