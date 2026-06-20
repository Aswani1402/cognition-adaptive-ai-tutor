from typing import Dict, Any

def explain_state(state: Dict[str, Any], skill_id: str) -> str:
    mastery = float(state.get("mastery", {}).get(skill_id, state.get("overall_mastery", 0.5)))
    beh = state.get("behaviour", {}) or {}
    label = beh.get("label", "normal")
    mse = float(beh.get("mse", 0.0))

    parts = [f"Mastery for {skill_id}: {mastery:.2f}."]
    if label == "warmup":
        parts.append("Behaviour model is warming up (needs ~20 events).")
    else:
        parts.append(f"Behaviour: {label} (mse={mse:.4f}).")
    return " ".join(parts)