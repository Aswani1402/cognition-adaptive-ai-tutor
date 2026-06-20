from typing import Any, Dict

from tutor.long_term_personalization.utils import safe_float, safe_int


def _preferred_difficulty(avg_correctness: float) -> str:
    if avg_correctness < 0.45:
        return "easy"
    if avg_correctness < 0.75:
        return "medium"
    return "hard"


def _support_level(avg_anomaly_score: float, struggle_score: float) -> str:
    composite = max(avg_anomaly_score, struggle_score)
    if composite >= 0.7:
        return "high"
    if composite >= 0.4:
        return "medium"
    return "low"


def _practice_need(weak_concept_count: int, repeated_failure_count: int) -> str:
    pressure = weak_concept_count + repeated_failure_count
    if pressure >= 10:
        return "high"
    if pressure >= 4:
        return "medium"
    return "low"


def _explanation_need(avg_correctness: float, struggle_score: float) -> str:
    if avg_correctness < 0.5 and struggle_score >= 0.5:
        return "high"
    if avg_correctness < 0.65 or struggle_score >= 0.35:
        return "medium"
    return "low"


def _challenge_readiness(avg_mastery: float, avg_anomaly_score: float) -> str:
    if avg_mastery >= 0.75 and avg_anomaly_score < 0.4:
        return "high"
    if avg_mastery >= 0.5:
        return "medium"
    return "low"


def _consistency_label(consistency_score: float) -> str:
    if consistency_score >= 0.75:
        return "regular"
    if consistency_score >= 0.4:
        return "moderate"
    return "irregular"


def _learning_speed(avg_correctness: float, avg_time_taken_sec: float) -> str:
    if avg_correctness >= 0.75 and (0 < avg_time_taken_sec <= 30):
        return "fast"
    if avg_correctness >= 0.5:
        return "medium"
    return "slow"


def _engagement_level(total_attempts: int, consistency_score: float) -> str:
    if total_attempts >= 80 and consistency_score >= 0.7:
        return "high"
    if total_attempts >= 20 or consistency_score >= 0.4:
        return "medium"
    return "low"


def _teaching_bias(
    support_level: str, explanation_need: str, challenge_readiness: str, practice_need: str
) -> str:
    if support_level == "high" or explanation_need == "high":
        return "worked_example_first"
    if challenge_readiness == "high" and practice_need == "low":
        return "challenge_first"
    return "practice_first"


def _preferred_flow(recommended_teaching_bias: str) -> str:
    if recommended_teaching_bias == "worked_example_first":
        return "explanation_first"
    return "practice_first"


def build_profile_from_features(features: Dict[str, Any]) -> Dict[str, Any]:
    avg_correctness = safe_float(features.get("avg_correctness"))
    avg_mastery = safe_float(features.get("avg_mastery"))
    avg_anomaly_score = safe_float(features.get("avg_anomaly_score"))
    struggle_score = safe_float(features.get("struggle_score"))
    weak_concept_count = safe_int(features.get("weak_concept_count"))
    strong_concept_count = safe_int(features.get("strong_concept_count"))
    repeated_failure_count = safe_int(features.get("repeated_failure_count"))
    consistency_score = safe_float(features.get("consistency_score"))
    avg_time_taken_sec = safe_float(features.get("avg_time_taken_sec"))
    total_attempts = safe_int(features.get("total_attempts"))

    preferred_difficulty = _preferred_difficulty(avg_correctness)
    support_level = _support_level(avg_anomaly_score, struggle_score)
    practice_need = _practice_need(weak_concept_count, repeated_failure_count)
    explanation_need = _explanation_need(avg_correctness, struggle_score)
    challenge_readiness = _challenge_readiness(avg_mastery, avg_anomaly_score)
    consistency = _consistency_label(consistency_score)
    learning_speed = _learning_speed(avg_correctness, avg_time_taken_sec)
    engagement_level = _engagement_level(total_attempts, consistency_score)
    recommended_teaching_bias = _teaching_bias(
        support_level=support_level,
        explanation_need=explanation_need,
        challenge_readiness=challenge_readiness,
        practice_need=practice_need,
    )
    preferred_flow = _preferred_flow(recommended_teaching_bias)

    return {
        "learner_id": str(features.get("learner_id", "")),
        "learning_speed": learning_speed,
        "support_level": support_level,
        "preferred_difficulty": preferred_difficulty,
        "engagement_level": engagement_level,
        "consistency": consistency,
        "challenge_readiness": challenge_readiness,
        "practice_need": practice_need,
        "explanation_need": explanation_need,
        "strength_areas": features.get("strength_areas", []),
        "weak_areas": features.get("weak_areas", []),
        "preferred_flow": preferred_flow,
        "recommended_teaching_bias": recommended_teaching_bias,
        "relative_strength_signal": "strong" if strong_concept_count > weak_concept_count else "mixed_or_weak",
        "feature_snapshot": features,
    }

