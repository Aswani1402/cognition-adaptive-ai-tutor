from __future__ import annotations

from typing import Any

from tutor.policy.rl.state_action_space import clamp, normalize_action, safe_float
from tutor.policy.rl_safe_action_mask import detect_rl_action_violations


def infer_state_from_row(row: dict[str, Any]) -> dict[str, Any]:
    mastery = safe_float(row.get("mastery_score", row.get("mastery")), 0.0)
    fused_score = safe_float(row.get("fused_score", row.get("evaluation_score")), 0.0)
    behaviour_risk = safe_float(row.get("behaviour_risk", row.get("behavior_score", row.get("behaviour_score"))), 0.0)
    promotion_allowed = int(safe_float(row.get("target_promotion_allowed", row.get("promotion_allowed")), 0.0))
    promotion_confidence = (
        safe_float(row.get("promotion_confidence"))
        if row.get("promotion_confidence") is not None
        else 0.75 if promotion_allowed else min(0.59, (mastery + fused_score) / 2.0)
    )
    review_due = row.get("review_due")
    if review_due is None:
        review_due = safe_float(row.get("forgetting_priority"), 0.0) >= 0.5
    return {
        "mastery_score": mastery,
        "behaviour_risk": behaviour_risk,
        "behaviour_risk_label": "high_risk" if behaviour_risk >= 0.7 else "medium_risk" if behaviour_risk >= 0.4 else "low_risk",
        "fused_score": fused_score,
        "fused_label": "needs_reteaching" if fused_score < 0.5 else "partial" if fused_score < 0.75 else "mastered",
        "review_due": bool(review_due),
        "promotion_confidence": promotion_confidence,
        "difficulty": row.get("difficulty", "medium"),
        "weakest_skill": row.get("weakest_skill", "output_prediction" if safe_float(row.get("output_prediction_score"), 1.0) < 0.5 else "none"),
        "concept_dependency_valid": bool(row.get("concept_dependency_valid", True)),
        "concept_domain_match": bool(row.get("concept_domain_match", True)),
        "view_reward": safe_float(row.get("view_reward"), 0.5),
    }


def infer_next_state(state: dict[str, Any], action_label: str, logged_next: dict[str, Any] | None = None) -> dict[str, Any]:
    if logged_next:
        merged = {**state}
        for key, value in logged_next.items():
            if value is not None:
                merged[key] = value
        return merged

    next_state = dict(state)
    if action_label in {"review", "reteach", "remedial_easy", "same_level_change_view_or_practice"}:
        next_state["fused_score"] = clamp(safe_float(state.get("fused_score")) + 0.05)
        next_state["view_reward"] = clamp(safe_float(state.get("view_reward"), 0.5) + 0.05)
    elif action_label in {"advanced_hard", "advance_concept", "level_up"}:
        next_state["mastery_score"] = clamp(safe_float(state.get("mastery_score")) + 0.03)
    else:
        next_state["mastery_score"] = clamp(safe_float(state.get("mastery_score")) + 0.02)
        next_state["fused_score"] = clamp(safe_float(state.get("fused_score")) + 0.02)
    return next_state


def build_reward(state: dict[str, Any], action_label: str, row: dict[str, Any] | None = None) -> float:
    row = row or {}
    if row.get("reward") is not None:
        base = safe_float(row.get("reward"), 0.0)
        # Normalize older reward logs roughly into [-1, 1].
        base = max(-1.0, min(1.0, base / 3.0))
    else:
        base = 0.0

    violations = detect_rl_action_violations(action_label, state)
    reward = base + 0.2
    reward -= 0.45 * len(violations)

    mastery = safe_float(state.get("mastery_score"))
    fused_score = safe_float(state.get("fused_score", state.get("evaluation_score")))
    review_due = bool(state.get("review_due"))
    behaviour_risk = safe_float(state.get("behaviour_risk", state.get("behavior_score")))
    promotion_confidence = safe_float(state.get("promotion_confidence"))

    if mastery < 0.4 and action_label in {"remedial_easy", "reteach"}:
        reward += 0.35
    if review_due and action_label in {"review", "practice_easy", "practice_medium", "reteach"}:
        reward += 0.25
    if fused_score < 0.5 and action_label in {"remedial_easy", "same_level_change_view_or_practice", "reteach"}:
        reward += 0.3
    if behaviour_risk >= 0.7 and action_label in {"practice_easy", "remedial_easy", "review"}:
        reward += 0.25
    if promotion_confidence >= 0.75 and mastery >= 0.75 and fused_score >= 0.75 and action_label in {"advanced_hard", "advance_concept", "level_up"}:
        reward += 0.35
    if row.get("reward_xp_awarded") is not None:
        reward += min(0.15, safe_float(row.get("reward_xp_awarded")) / 100.0)
    return round(max(-1.0, min(1.0, reward)), 4)


def infer_action_from_row(row: dict[str, Any]) -> str:
    if row.get("action_label"):
        return normalize_action(action=row.get("action_label"))
    if row.get("target_progression_action"):
        target = str(row.get("target_progression_action"))
        if target in {"remediate", "review"}:
            return "remedial_easy"
        if target in {"advance", "advance_concept", "level_up"}:
            return "advance_concept"
        return "practice_medium"
    return normalize_action(
        strategy=row.get("strategy"),
        difficulty=row.get("difficulty"),
        action=row.get("progression_action"),
    )
