from __future__ import annotations

from typing import Any, Dict, List, Optional
from tutor.progression.model_based_promotion_predictor import predict_promotion_with_model

DIFFICULTY_ORDER = ["easy", "medium", "hard"]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _extract_scores_by_type(evaluation_output: Dict[str, Any]) -> Dict[str, float]:
    scores: Dict[str, float] = {}

    for result in _as_list(evaluation_output.get("results", [])):
        if not isinstance(result, dict):
            continue

        assessment_type = (
            result.get("assessment_type")
            or result.get("question_type")
            or "unknown"
        )

        scores[str(assessment_type)] = _safe_float(result.get("score"), 0.0)

    return scores


def _extract_structured_score(structured_evaluation_output: Dict[str, Any]) -> Optional[float]:
    evaluation = _as_dict(structured_evaluation_output.get("evaluation"))

    if not evaluation:
        return None

    return _safe_float(evaluation.get("overall_score"), 0.0)


def _next_difficulty(current_difficulty: str) -> str:
    current = _safe_str(current_difficulty, "easy").lower()

    if current not in DIFFICULTY_ORDER:
        return "medium"

    index = DIFFICULTY_ORDER.index(current)

    if index + 1 < len(DIFFICULTY_ORDER):
        return DIFFICULTY_ORDER[index + 1]

    return "hard"


def _previous_difficulty(current_difficulty: str) -> str:
    current = _safe_str(current_difficulty, "easy").lower()

    if current not in DIFFICULTY_ORDER:
        return "easy"

    index = DIFFICULTY_ORDER.index(current)

    if index - 1 >= 0:
        return DIFFICULTY_ORDER[index - 1]

    return "easy"


def _build_celebration(
    show: bool,
    celebration_type: str,
    concept_name: str,
    message: str,
    xp_awarded: int,
    streak_updated: bool,
    next_unlock: Optional[str] = None,
    mascot_emotion: str = "happy",
    animation: str = "confetti",
) -> Dict[str, Any]:
    return {
        "show": show,
        "type": celebration_type,
        "message": message,
        "mascot_emotion": mascot_emotion,
        "animation": animation,
        "xp_awarded": xp_awarded,
        "streak_updated": streak_updated,
        "next_unlock": next_unlock,
        "concept_name": concept_name,
    }


def compute_promotion_confidence_baseline(
    evaluation_output: Dict[str, Any],
    structured_evaluation_output: Optional[Dict[str, Any]] = None,
    behaviour_state: Optional[Dict[str, Any]] = None,
    view_performance_output: Optional[Dict[str, Any]] = None,
    guess_probability: float = 0.0,
) -> Dict[str, Any]:
    """
    Baseline promotion confidence.

    Later this will be replaced/compared with an ML model:
    LogisticRegression / RandomForest / DecisionTree.
    """
    structured_evaluation_output = structured_evaluation_output or {}
    behaviour_state = behaviour_state or {}
    view_performance_output = view_performance_output or {}

    overall_score = _safe_float(evaluation_output.get("overall_score"), 0.0)
    scores_by_type = _extract_scores_by_type(evaluation_output)

    structured_score = _extract_structured_score(structured_evaluation_output)

    behaviour_data = _as_dict(behaviour_state.get("data"))
    if isinstance(behaviour_data.get("data"), dict):
        behaviour_data = behaviour_data.get("data", {})

    behaviour_score = _safe_float(behaviour_data.get("behavior_score"), 0.5)
    wrong_rate = _safe_float(behaviour_data.get("wrong_rate"), 0.0)
    low_confidence_rate = _safe_float(behaviour_data.get("low_confidence_rate"), 0.0)

    logged_view = _as_dict(view_performance_output.get("logged"))
    view_reward = _safe_float(logged_view.get("reward"), 0.5)

    debug_score = scores_by_type.get("debug")
    output_score = scores_by_type.get("output_prediction")
    explanation_score = scores_by_type.get("explanation") or scores_by_type.get("short_explanation")
    transfer_score = scores_by_type.get("transfer")

    skill_scores = [
        score
        for score in [
            debug_score,
            output_score,
            explanation_score,
            transfer_score,
            structured_score,
        ]
        if score is not None
    ]

    skill_average = (
        sum(skill_scores) / len(skill_scores)
        if skill_scores
        else overall_score
    )

    reliability_penalty = 0.0

    if guess_probability >= 0.6:
        reliability_penalty += 0.25

    if low_confidence_rate >= 0.7:
        reliability_penalty += 0.1

    if wrong_rate >= 0.5:
        reliability_penalty += 0.15

    confidence = (
        0.45 * overall_score
        + 0.25 * skill_average
        + 0.15 * view_reward
        + 0.15 * behaviour_score
        - reliability_penalty
    )

    confidence = max(0.0, min(1.0, round(confidence, 4)))

    if confidence >= 0.82:
        label = "high"
    elif confidence >= 0.62:
        label = "medium"
    else:
        label = "low"

    promotion_allowed = confidence >= 0.75 and guess_probability < 0.6

    blocking_reasons = []

    if confidence < 0.75:
        blocking_reasons.append("promotion confidence below threshold")

    if guess_probability >= 0.6:
        blocking_reasons.append("possible guessing detected")

    if debug_score is not None and debug_score < 0.5:
        blocking_reasons.append("debug skill still weak")

    if output_score is not None and output_score < 0.5:
        blocking_reasons.append("output prediction still weak")

    return {
        "status": "success",
        "module": "PromotionConfidenceBaseline",
        "promotion_confidence": confidence,
        "promotion_confidence_label": label,
        "promotion_allowed": promotion_allowed,
        "blocking_reasons": blocking_reasons,
        "features": {
            "overall_score": overall_score,
            "skill_average": round(skill_average, 4),
            "structured_score": structured_score,
            "behaviour_score": behaviour_score,
            "wrong_rate": wrong_rate,
            "low_confidence_rate": low_confidence_rate,
            "view_reward": view_reward,
            "guess_probability": guess_probability,
            "debug_score": debug_score,
            "output_prediction_score": output_score,
            "explanation_score": explanation_score,
            "transfer_score": transfer_score,
        },
        "model_status": "baseline_rules_now_ml_later",
        "next_upgrade": "Train LogisticRegression, DecisionTreeClassifier, and RandomForestClassifier on promotion logs.",

    }


def build_progression_reward_output(
    learner_id: str,
    concept_id: str,
    concept_name: str,
    current_difficulty: str,
    evaluation_output: Dict[str, Any],
    structured_evaluation_output: Optional[Dict[str, Any]] = None,
    behaviour_state: Optional[Dict[str, Any]] = None,
    view_performance_output: Optional[Dict[str, Any]] = None,
    teaching_strategy_output: Optional[Dict[str, Any]] = None,
    next_concept_name: Optional[str] = None,
    guess_probability: float = 0.0,
) -> Dict[str, Any]:
    """
    Creates Duolingo-style progression + XP/streak/celebration output.

    This does not change policy yet.
    It gives frontend a clean progression/reward object.
    """
    structured_evaluation_output = structured_evaluation_output or {}
    behaviour_state = behaviour_state or {}
    view_performance_output = view_performance_output or {}
    teaching_strategy_output = teaching_strategy_output or {}

    current_difficulty = _safe_str(current_difficulty, "easy").lower()
    concept_name = _safe_str(concept_name, "Concept")

    overall_score = _safe_float(evaluation_output.get("overall_score"), 0.0)
    verdict = _safe_str(evaluation_output.get("verdict"), "unknown")

    scores_by_type = _extract_scores_by_type(evaluation_output)

    weak_types = [
        assessment_type
        for assessment_type, score in scores_by_type.items()
        if score < 0.5
    ]

    strong_types = [
        assessment_type
        for assessment_type, score in scores_by_type.items()
        if score >= 0.85
    ]

    promotion_confidence_output = compute_promotion_confidence_baseline(
        evaluation_output=evaluation_output,
        structured_evaluation_output=structured_evaluation_output,
        behaviour_state=behaviour_state,
        view_performance_output=view_performance_output,
        guess_probability=guess_probability,
    )

    promotion_allowed = bool(promotion_confidence_output.get("promotion_allowed"))
    confidence = _safe_float(promotion_confidence_output.get("promotion_confidence"), 0.0)

    concept_cleared = False
    level_up_allowed = False
    next_difficulty = current_difficulty
    progression_action = "stay_same_level"
    xp_awarded = 5
    streak_updated = True

    if promotion_allowed:
        if current_difficulty == "hard":
            concept_cleared = True
            level_up_allowed = False
            next_difficulty = "hard"
            progression_action = "move_to_next_concept"
            xp_awarded = 30
        else:
            level_up_allowed = True
            next_difficulty = _next_difficulty(current_difficulty)
            progression_action = f"level_up_to_{next_difficulty}"
            xp_awarded = 20
    else:
        if overall_score >= 0.6:
            progression_action = "same_level_change_view_or_practice"
            next_difficulty = current_difficulty
            xp_awarded = 10
        else:
            progression_action = "same_or_lower_level_change_view"
            next_difficulty = _previous_difficulty(current_difficulty)
            xp_awarded = 5

    if concept_cleared:
        message = f"Great work! You cleared {concept_name}. Next concept unlocked."
        celebration_type = "concept_cleared"
        mascot_emotion = "excited"
        animation = "confetti"
        next_unlock = next_concept_name
    elif level_up_allowed:
        message = f"Nice work! {current_difficulty.title()} level cleared. {next_difficulty.title()} level unlocked."
        celebration_type = "level_up"
        mascot_emotion = "happy"
        animation = "sparkle"
        next_unlock = None
    elif overall_score >= 0.6:
        message = f"Good effort! You are close. Let’s practice {concept_name} once more with a different view."
        celebration_type = "encouragement"
        mascot_emotion = "supportive"
        animation = "soft_glow"
        next_unlock = None
    else:
        message = f"No worries. Let’s try a simpler version of {concept_name} and build confidence."
        celebration_type = "support"
        mascot_emotion = "kind"
        animation = "none"
        next_unlock = None

    celebration = _build_celebration(
        show=True,
        celebration_type=celebration_type,
        concept_name=concept_name,
        message=message,
        xp_awarded=xp_awarded,
        streak_updated=streak_updated,
        next_unlock=next_unlock,
        mascot_emotion=mascot_emotion,
        animation=animation,
    )

    reward_state = {
        "xp_awarded": xp_awarded,
        "streak_updated": streak_updated,
        "daily_goal_progress_note": "Add this XP to learner daily goal in future streak_state table.",
        "reward_reason": celebration_type,
        "model_status": "baseline_reward_rules_now_ml_later",
    }

    progression_result = {
        "learner_id": str(learner_id),
        "current_concept_id": str(concept_id),
        "current_concept": concept_name,
        "current_difficulty": current_difficulty,
        "passed": promotion_allowed,
        "promotion_allowed": promotion_allowed,
        "level_up_allowed": level_up_allowed,
        "next_difficulty": next_difficulty,
        "concept_cleared": concept_cleared,
        "next_concept_unlocked": next_concept_name if concept_cleared else None,
        "progression_action": progression_action,
        "promotion_confidence": confidence,
        "promotion_confidence_label": promotion_confidence_output.get("promotion_confidence_label"),
        "weak_assessment_types": weak_types,
        "strong_assessment_types": strong_types,
        "blocking_reasons": promotion_confidence_output.get("blocking_reasons", []),
        "message": message,
    }
    promotion_features = promotion_confidence_output.get("features", {})

    model_comparison_output = predict_promotion_with_model(
        {
            "mastery": promotion_features.get("overall_score", overall_score),
            "evaluation_score": promotion_features.get("overall_score", overall_score),
            "structured_score": promotion_features.get("structured_score", 0.0),
            "debug_score": promotion_features.get("debug_score", 0.0),
            "output_prediction_score": promotion_features.get("output_prediction_score", 0.0),
            "explanation_score": promotion_features.get("explanation_score", 0.0),
            "transfer_score": promotion_features.get("transfer_score", 0.0),
            "behaviour_score": promotion_features.get("behaviour_score", 0.5),
            "wrong_rate": promotion_features.get("wrong_rate", 0.0),
            "low_confidence_rate": promotion_features.get("low_confidence_rate", 0.0),
            "view_reward": promotion_features.get("view_reward", 0.5),
            "forgetting_priority": 0.0,
            "guess_probability": promotion_features.get("guess_probability", guess_probability),
        }
    )
    return {
        "status": "success",
        "module": "ProgressionRewardEngine",
        "learner_id": str(learner_id),
        "concept_id": str(concept_id),
        "concept_name": concept_name,
        "model_comparison_status": "comparison_only_not_used_for_final_decision",
        "model_comparison_output": model_comparison_output,
        "progression_result": progression_result,
        "promotion_confidence_output": promotion_confidence_output,
        "reward_state": reward_state,
        "celebration": celebration,
        "frontend_contract": {
            "show_celebration_modal": celebration.get("show"),
            "show_xp_popup": xp_awarded > 0,
            "update_streak_widget": streak_updated,
            "update_path_node": True,
            "mascot_emotion": celebration.get("mascot_emotion"),
        },
        "reason": (
            f"Progression action={progression_action}. "
            f"Promotion confidence={confidence}. "
            f"Evaluation score={overall_score}, verdict={verdict}."
            f"ML comparison action={model_comparison_output.get('model_progression_action')}."
        ),
    }