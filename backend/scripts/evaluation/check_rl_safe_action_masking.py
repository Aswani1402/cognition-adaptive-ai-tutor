from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tutor.RL.bandit_policy import BanditPolicy
from tutor.RL.dqn.dqn_policy import DQNPolicy
from tutor.policy.rl_safe_action_mask import apply_rl_safe_action_mask, detect_rl_action_violations
from tutor.system.policy_model_inference import PolicyModel


CSV_PATH = Path("evaluation_outputs/csv/synthetic_promotion_confidence_logs.csv")
OUTPUT_JSON = Path("evaluation_outputs/json/rl_safe_action_masking_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rl_safe_action_masking_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _learning_signal(score: float) -> str:
    if score >= 0.75:
        return "mastered"
    if score >= 0.50:
        return "partial"
    return "weak"


def _state_from_row(row: dict[str, Any]) -> dict[str, Any]:
    evaluation_score = _safe_float(row.get("evaluation_score"))
    behaviour_risk = _safe_float(row.get("behaviour_score", row.get("behavior_score", 0.0)))
    return {
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
        "concept_domain_match": True,
    }


def _baseline_action(row: dict[str, Any]) -> str:
    target = str(row.get("target_progression_action", "")).strip()
    difficulty = str(row.get("difficulty", "medium")).strip().lower() or "medium"
    if target in {"advance", "level_up", "advance_concept"}:
        return "advanced_hard"
    if target in {"remediate", "reteach", "review"}:
        return "remedial_easy"
    return f"practice_{difficulty if difficulty in {'easy', 'medium', 'hard'} else 'medium'}"


def _action_from_output(output: dict[str, Any] | None) -> str | None:
    if not isinstance(output, dict) or output.get("status") != "success":
        return None
    if output.get("action_label"):
        return str(output["action_label"])
    if output.get("strategy") and output.get("difficulty"):
        return f"{output['strategy']}_{output['difficulty']}"
    return None


def _policy_model_action(model: PolicyModel, state: dict[str, Any]) -> str | None:
    if not model.is_available():
        return None
    try:
        concept = model.predict_next_concept(
            {
                "mastery_score": state["mastery_score"],
                "behavior_label": state["behaviour_risk_label"],
                "behavior_score": state["behaviour_risk"],
                "review_due": state["review_due"],
                "evaluation_score": state["evaluation_score"],
                "learning_signal": state["learning_signal"],
                "final_action": "review" if state["review_due"] else "practice",
                "recommended_strategy": "practice",
                "recommended_difficulty": "medium",
            }
        )
        return f"select_concept_{concept}"
    except Exception:
        return None


def _raw_actions(states: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, list[str | None]]:
    policy_model = PolicyModel()
    bandit = BanditPolicy()
    dqn = DQNPolicy()
    actions: dict[str, list[str | None]] = {
        "baseline_policy": [_baseline_action(row) for row in rows],
        "policy_model": [_policy_model_action(policy_model, state) for state in states],
        "contextual_bandit": [],
        "dqn": [],
    }
    for state in states:
        try:
            actions["contextual_bandit"].append(_action_from_output(bandit.predict(state)) if bandit.is_available() else None)
        except Exception:
            actions["contextual_bandit"].append(None)
        try:
            actions["dqn"].append(_action_from_output(dqn.predict(state)) if dqn.is_available() else None)
        except Exception:
            actions["dqn"].append(None)
    return actions


def _metric_block(states: list[dict[str, Any]], actions: list[str | None]) -> dict[str, Any]:
    valid = [(state, action) for state, action in zip(states, actions) if action]
    if not valid:
        return {
            "evaluated_cases": 0,
            "bad_action_rate": None,
            "unsafe_promotion_rate": None,
            "challenge_on_low_mastery_rate": None,
            "hard_on_high_behaviour_risk_rate": None,
            "review_due_but_not_review_rate": None,
            "action_distribution": {},
        }
    n = len(valid)
    violation_lists = [detect_rl_action_violations(str(action), state) for state, action in valid]
    return {
        "evaluated_cases": n,
        "bad_action_rate": round(sum(1 for v in violation_lists if v) / n, 4),
        "unsafe_promotion_rate": round(sum(1 for v in violation_lists if any("promotion" in x or "advance" in x for x in v)) / n, 4),
        "challenge_on_low_mastery_rate": round(sum(1 for v in violation_lists if "low_mastery_blocks_advanced" in v) / n, 4),
        "hard_on_high_behaviour_risk_rate": round(sum(1 for v in violation_lists if "high_behaviour_risk_blocks_hard" in v) / n, 4),
        "review_due_but_not_review_rate": round(sum(1 for v in violation_lists if "review_due_blocks_advance" in v) / n, 4),
        "action_distribution": dict(Counter(str(action) for _, action in valid)),
    }


def _evaluate_model(states: list[dict[str, Any]], actions: list[str | None]) -> dict[str, Any]:
    masked_outputs = [
        apply_rl_safe_action_mask(state, action)
        for state, action in zip(states, actions)
        if action is not None
    ]
    masked_actions = [output["masked_action"] for output in masked_outputs]
    masked_count = sum(1 for output in masked_outputs if output["was_masked"])
    return {
        "before": _metric_block(states, actions),
        "after": _metric_block(states[: len(masked_actions)], masked_actions),
        "masked_action_count": masked_count,
        "masked_action_rate": round(masked_count / len(masked_outputs), 4) if masked_outputs else None,
        "sample_masks": masked_outputs[:10],
    }


def build_report() -> dict[str, Any]:
    df = pd.read_csv(CSV_PATH).head(500) if CSV_PATH.exists() else pd.DataFrame()
    rows = df.to_dict(orient="records")
    states = [_state_from_row(row) for row in rows]
    raw = _raw_actions(states, rows)
    results = {
        model_name: _evaluate_model(states, actions)
        for model_name, actions in raw.items()
    }
    any_after_bad = any(
        (result["after"].get("bad_action_rate") or 0.0) > 0.0
        for result in results.values()
    )
    return {
        "status": "warning" if any_after_bad else "success",
        "module": "rl_safe_action_masking",
        "generated_at": _now_iso(),
        "dataset_status": {
            "csv_path": str(CSV_PATH),
            "csv_exists": CSV_PATH.exists(),
            "evaluated_cases": len(states),
        },
        "model_results": results,
        "summary": {
            "unsafe_rates_reduced_to_zero": not any_after_bad,
            "recommendation": "Masked outputs can be logged as safety-filtered comparison recommendations; raw RL should remain non-authoritative."
            if not any_after_bad
            else "Some masked actions still violate safety rules; keep RL guarded and inspect mask logic.",
        },
        "limitations": [
            "Masking reduces unsafe action labels but does not make RL a trained safe policy.",
            "Offline data is synthetic promotion evidence and should be expanded with real logged rewards.",
            "Policy model predicts concepts, so masking concept outputs is approximated through action safety labels.",
        ],
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# RL Safe Action Masking Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        f"Evaluated cases: `{report['dataset_status']['evaluated_cases']}`",
        "",
        "## Before/After Metrics",
        "",
    ]
    for model_name, result in report["model_results"].items():
        lines.append(f"### {model_name}")
        lines.append(f"- before: `{result['before']}`")
        lines.append(f"- after: `{result['after']}`")
        lines.append(f"- masked_action_count: `{result['masked_action_count']}`")
        lines.append(f"- masked_action_rate: `{result['masked_action_rate']}`")
        lines.append("")
    lines.extend(["## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Status", "", "```text", f"STATUS: {report['status']}", "MODULE: rl_safe_action_masking", "```", ""])
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: rl_safe_action_masking")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
