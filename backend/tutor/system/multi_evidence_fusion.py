from __future__ import annotations

from typing import Any

from tutor.system.fusion_model_inference import FusionModel


def safe_get(d: dict[str, Any], *keys: str, default=None):
    current: Any = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def fuse_evidence(
    knowledge_state: dict[str, Any],
    behaviour_state: dict[str, Any],
    forgetting_state: dict[str, Any],
    evaluation_output: dict[str, Any],
    learning_signal: str,
) -> dict[str, Any]:
    mastery = float(
        safe_get(
            knowledge_state,
            "data", "data", "predicted_mastery_last",
            default=0.0
        ) or 0.0
    )

    behavior_label = safe_get(
        behaviour_state,
        "data", "behavior_label",
        default="unknown"
    )

    behavior_score = float(
        safe_get(
            behaviour_state,
            "data", "behavior_score",
            default=0.0
        ) or 0.0
    )

    review_queue = safe_get(
        forgetting_state,
        "data", "review_queue",
        default=[]
    )

    review_due = bool(review_queue)

    evaluation_score = float(evaluation_output.get("score", 0.0) or 0.0)
    evaluation_quality = evaluation_output.get("quality_label", "unknown")

    evidence_summary = {
        "mastery_score": mastery,
        "behavior_label": behavior_label,
        "behavior_score": behavior_score,
        "review_due": review_due,
        "evaluation_score": evaluation_score,
        "evaluation_quality": evaluation_quality,
        "learning_signal": learning_signal,
    }

    fusion_model = FusionModel()
    model_action = None
    model_metadata = fusion_model.get_metadata()

    if fusion_model.is_available():
        try:
            model_action = fusion_model.predict(evidence_summary)
            model_metadata = fusion_model.get_metadata()
        except Exception:
            model_action = None
            model_metadata = fusion_model.get_metadata()

    # -------------------------
    # Rule-based decision
    # -------------------------
    if learning_signal == "weak" or evaluation_score < 0.4:
        final_action = "reinforce_current"

    elif review_due:
        if learning_signal == "weak":
            final_action = "review_current"
        elif learning_signal == "partial":
            final_action = "light_review"
        else:
            final_action = "progress_with_review_later"

    elif learning_signal == "partial":
        final_action = "guided_practice"

    elif learning_signal == "mastered" and evaluation_score >= 0.8:
        final_action = "promote_next"

    elif mastery >= 0.75 and evaluation_score >= 0.8:
        final_action = "promote_next"

    else:
        final_action = "continue_current"

    # -------------------------
    # Model override (safe mode)
    # -------------------------
    if model_action:
        final_action = model_action
        decision_source = "model"
    else:
        decision_source = "rule"

    # -------------------------
    # Strategy mapping
    # -------------------------
    if final_action in {"reinforce_current", "review_current"}:
        recommended_strategy = "remedial"
        recommended_difficulty = "easy"

    elif final_action in {"light_review", "guided_practice"}:
        recommended_strategy = "practice"
        recommended_difficulty = "medium"

    elif final_action in {"promote_next", "progress_with_review_later"}:
        recommended_strategy = "advanced"
        recommended_difficulty = "hard"

    else:
        recommended_strategy = "practice"
        recommended_difficulty = "medium"

    return {
        "status": "success",
        "evidence_summary": evidence_summary,
        "final_action": final_action,
        "decision_source": decision_source,
        "recommended_strategy": recommended_strategy,
        "recommended_difficulty": recommended_difficulty,
        "model_metadata": model_metadata,
        "model_status": model_metadata.get("model_status"),
        "model_loaded": model_metadata.get("model_loaded", False),
        "fallback_used": model_metadata.get("fallback_used", decision_source == "rule"),
        "fallback_reason": model_metadata.get("fallback_reason"),
    }
