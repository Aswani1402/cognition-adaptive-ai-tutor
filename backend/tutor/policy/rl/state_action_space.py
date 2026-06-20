from __future__ import annotations

from typing import Any

import numpy as np


STATE_FEATURES = [
    "mastery_score",
    "behaviour_risk",
    "fused_score",
    "review_due",
    "promotion_confidence",
    "difficulty_encoded",
    "weakest_skill_encoded",
    "behaviour_risk_label_encoded",
    "concept_dependency_valid",
    "view_reward",
]

ACTIONS = [
    "remedial_easy",
    "practice_easy",
    "practice_medium",
    "practice_hard",
    "advanced_hard",
    "review",
    "reteach",
    "same_level_change_view_or_practice",
    "advance_concept",
    "level_up",
]

ACTION_TO_ID = {label: idx for idx, label in enumerate(ACTIONS)}
ID_TO_ACTION = {idx: label for label, idx in ACTION_TO_ID.items()}

DIFFICULTY_MAP = {"easy": 0.0, "medium": 0.5, "hard": 1.0}
WEAKEST_SKILL_MAP = {
    "none": 0.0,
    "mcq": 0.1,
    "explanation": 0.2,
    "short_explanation": 0.25,
    "output_prediction": 0.5,
    "debug": 0.7,
    "transfer": 0.85,
    "challenge": 1.0,
}
RISK_LABEL_MAP = {
    "low_risk": 0.0,
    "medium_risk": 0.5,
    "high_risk": 1.0,
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def encode_bool(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return 1.0 if str(value).strip().lower() in {"1", "true", "yes", "y"} else 0.0


def encode_difficulty(value: Any) -> float:
    return DIFFICULTY_MAP.get(str(value or "medium").strip().lower(), 0.5)


def encode_weakest_skill(value: Any) -> float:
    return WEAKEST_SKILL_MAP.get(str(value or "none").strip().lower(), 0.0)


def encode_risk_label(value: Any) -> float:
    return RISK_LABEL_MAP.get(str(value or "low_risk").strip().lower(), 0.0)


def action_count() -> int:
    return len(ACTIONS)


def action_to_id(action_label: str) -> int:
    return ACTION_TO_ID.get(str(action_label), ACTION_TO_ID["practice_medium"])


def id_to_action(action_id: int) -> str:
    return ID_TO_ACTION.get(int(action_id), "practice_medium")


def normalize_action(strategy: Any = None, difficulty: Any = None, action: Any = None) -> str:
    raw = str(action or "").strip()
    if raw in ACTION_TO_ID:
        return raw
    if raw in {"advance", "advanced"}:
        return "advance_concept"
    if raw in {"remediate", "remedial"}:
        return "remedial_easy"
    if raw in {"stay_same_level", "reinforce", "practice"}:
        return "practice_medium"
    if raw in {"review", "reteach", "level_up", "advance_concept", "same_level_change_view_or_practice"}:
        return raw

    strategy_s = str(strategy or "").strip().lower()
    difficulty_s = str(difficulty or "medium").strip().lower()
    if strategy_s == "advanced":
        return "advanced_hard" if difficulty_s == "hard" else "advance_concept"
    if strategy_s == "remedial":
        return "remedial_easy"
    if strategy_s == "reteach":
        return "reteach"
    if strategy_s == "review":
        return "review"
    if strategy_s == "practice":
        return f"practice_{difficulty_s}" if difficulty_s in {"easy", "medium", "hard"} else "practice_medium"
    return "practice_medium"


def state_to_vector(state: dict[str, Any]) -> np.ndarray:
    behaviour_risk = safe_float(state.get("behaviour_risk", state.get("behavior_score", state.get("behavior_risk"))))
    fused_score = safe_float(state.get("fused_score", state.get("evaluation_score")), 0.0)
    risk_label = state.get("behaviour_risk_label", state.get("behavior_risk_label"))
    if not risk_label:
        risk_label = "high_risk" if behaviour_risk >= 0.7 else "medium_risk" if behaviour_risk >= 0.4 else "low_risk"
    vector = [
        clamp(safe_float(state.get("mastery_score", state.get("mastery")))),
        clamp(behaviour_risk),
        clamp(fused_score),
        encode_bool(state.get("review_due")),
        clamp(safe_float(state.get("promotion_confidence"), 0.0)),
        encode_difficulty(state.get("difficulty")),
        encode_weakest_skill(state.get("weakest_skill")),
        encode_risk_label(risk_label),
        encode_bool(state.get("concept_dependency_valid", state.get("concept_domain_match", True))),
        clamp(safe_float(state.get("view_reward"), 0.5)),
    ]
    return np.array(vector, dtype=np.float32)


def vector_to_state(vector: list[float] | np.ndarray) -> dict[str, float]:
    arr = np.array(vector, dtype=np.float32).tolist()
    return dict(zip(STATE_FEATURES, arr))


def model_action_dict(action_label: str) -> dict[str, Any]:
    if action_label.startswith("practice_"):
        _, difficulty = action_label.split("_", 1)
        return {"action_label": action_label, "strategy": "practice", "difficulty": difficulty}
    if action_label == "remedial_easy":
        return {"action_label": action_label, "strategy": "remedial", "difficulty": "easy"}
    if action_label == "advanced_hard":
        return {"action_label": action_label, "strategy": "advanced", "difficulty": "hard"}
    if action_label in {"review", "reteach"}:
        return {"action_label": action_label, "strategy": action_label, "difficulty": "easy"}
    if action_label in {"advance_concept", "level_up"}:
        return {"action_label": action_label, "strategy": "advanced", "difficulty": "hard"}
    return {"action_label": action_label, "strategy": "practice", "difficulty": "medium"}

