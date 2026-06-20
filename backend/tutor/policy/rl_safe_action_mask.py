from __future__ import annotations

from typing import Any


PROMOTION_TOKENS = ("advanced", "advance", "level_up", "challenge")
HARD_TOKENS = ("advanced", "hard", "challenge")
REVIEWISH_TOKENS = ("review", "revision", "practice", "remedial", "reteach", "support")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _action_label(action: dict[str, Any] | str | None) -> str:
    if action is None:
        return ""
    if isinstance(action, str):
        return action
    if action.get("action_label"):
        return str(action["action_label"])
    strategy = action.get("strategy")
    difficulty = action.get("difficulty")
    if strategy and difficulty:
        return f"{strategy}_{difficulty}"
    return str(action.get("progression_action") or action.get("action") or "")


def _action_parts(action_label: str) -> tuple[str, str]:
    lowered = action_label.lower()
    if "_" in lowered:
        strategy, difficulty = lowered.rsplit("_", 1)
        return strategy, difficulty
    if lowered in {"review", "reteach"}:
        return lowered, "easy"
    if lowered in {"advance_concept", "level_up"}:
        return "advanced", "hard"
    return lowered or "practice", "medium"


def is_promotion_action(action_label: str) -> bool:
    lowered = action_label.lower()
    return any(token in lowered for token in PROMOTION_TOKENS)


def is_hard_or_challenge_action(action_label: str) -> bool:
    lowered = action_label.lower()
    return any(token in lowered for token in HARD_TOKENS)


def _domain_matches(state: dict[str, Any]) -> bool:
    if "concept_domain_match" in state:
        return bool(state.get("concept_domain_match"))
    current = state.get("current_domain")
    selected = state.get("selected_domain") or state.get("selected_concept_domain")
    if current is None or selected is None:
        return True
    return str(current).lower() == str(selected).lower()


def detect_rl_action_violations(action_label: str, state: dict[str, Any]) -> list[str]:
    mastery = _safe_float(state.get("mastery_score"))
    behaviour_risk = _safe_float(state.get("behaviour_risk", state.get("behavior_score")))
    behaviour_risk_label = str(state.get("behaviour_risk_label", state.get("behavior_risk_label", ""))).lower()
    fused_score = _safe_float(state.get("fused_score", state.get("evaluation_score")), 1.0)
    fused_label = str(state.get("fused_label", "")).lower()
    promotion_confidence = _safe_float(state.get("promotion_confidence"), 1.0)
    review_due = bool(state.get("review_due"))
    weakest_skill = str(state.get("weakest_skill", "")).lower()

    violations: list[str] = []
    if not _domain_matches(state):
        violations.append("concept_domain_mismatch_blocks_selection")
    if mastery < 0.4 and (is_promotion_action(action_label) or is_hard_or_challenge_action(action_label)):
        violations.append("low_mastery_blocks_advanced")
    if (fused_score < 0.5 or fused_label == "needs_reteaching") and is_promotion_action(action_label):
        violations.append("needs_reteaching_blocks_advance")
    if promotion_confidence < 0.6 and is_promotion_action(action_label):
        violations.append("low_promotion_confidence_blocks_promotion")
    if (behaviour_risk >= 0.7 or behaviour_risk_label == "high_risk") and is_hard_or_challenge_action(action_label):
        violations.append("high_behaviour_risk_blocks_hard")
    if review_due and not any(token in action_label.lower() for token in REVIEWISH_TOKENS):
        violations.append("review_due_blocks_advance")
    if weakest_skill in {"output_prediction", "debug"} and is_promotion_action(action_label):
        violations.append("weakest_skill_requires_targeted_practice")
    return violations


def choose_safe_fallback_action(state: dict[str, Any]) -> str:
    if not _domain_matches(state):
        return "block_or_fallback"
    mastery = _safe_float(state.get("mastery_score"))
    behaviour_risk = _safe_float(state.get("behaviour_risk", state.get("behavior_score")))
    behaviour_risk_label = str(state.get("behaviour_risk_label", state.get("behavior_risk_label", ""))).lower()
    fused_score = _safe_float(state.get("fused_score", state.get("evaluation_score")), 1.0)
    fused_label = str(state.get("fused_label", "")).lower()
    review_due = bool(state.get("review_due"))

    if review_due:
        return "review"
    if mastery < 0.4:
        return "remedial_easy"
    if fused_score < 0.5 or fused_label == "needs_reteaching":
        return "same_level_change_view_or_practice"
    if behaviour_risk >= 0.7 or behaviour_risk_label == "high_risk":
        return "practice_easy"
    return "practice_medium"


def apply_rl_safe_action_mask(
    state: dict[str, Any],
    model_action: dict[str, Any] | str | None,
) -> dict[str, Any]:
    original = _action_label(model_action)
    violations = detect_rl_action_violations(original, state)
    masked = choose_safe_fallback_action(state) if violations else original
    strategy, difficulty = _action_parts(masked)
    reason = (
        f"Action {original} blocked by safety rules: {', '.join(violations)}."
        if violations
        else f"Action {original} passed RL safety mask."
    )
    return {
        "status": "success",
        "module": "RLSafeActionMask",
        "original_action": original,
        "masked_action": masked,
        "strategy": strategy,
        "difficulty": difficulty,
        "was_masked": bool(violations),
        "violations": violations,
        "safe": not detect_rl_action_violations(masked, {**state, "concept_domain_match": True})
        if masked != "block_or_fallback"
        else True,
        "reason": reason,
    }


__all__ = [
    "apply_rl_safe_action_mask",
    "choose_safe_fallback_action",
    "detect_rl_action_violations",
    "is_promotion_action",
    "is_hard_or_challenge_action",
]
