from typing import Dict, Any

def learning_priority_score(state: Dict[str, Any], skill_id: str) -> float:
    """
    Higher score = needs attention.
    Combines low mastery + behaviour anomaly (small weight).
    """
    mastery = float(state.get("mastery", {}).get(skill_id, 0.5))
    beh = state.get("behaviour", {}) or {}
    mse = float(beh.get("mse", 0.0))
    label = beh.get("label", "normal")

    need = 1.0 - mastery  # low mastery => higher need

    beh_penalty = 0.0
    if label == "anomaly":
        beh_penalty = 0.10
    elif mse > 0.02:
        beh_penalty = 0.05

    return float(need + beh_penalty)