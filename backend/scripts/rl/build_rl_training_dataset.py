from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tutor.policy.rl.reward_builder import build_reward, infer_action_from_row, infer_next_state, infer_state_from_row
from tutor.policy.rl.state_action_space import STATE_FEATURES, action_to_id, state_to_vector


SYNTHETIC_PATH = Path("evaluation_outputs/csv/synthetic_promotion_confidence_logs.csv")
EXPERIENCE_PATH = Path("evaluation_outputs/csv/rl_experience_dataset.csv")
DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_CSV = Path("evaluation_outputs/csv/rl_training_dataset.csv")
OUTPUT_JSON = Path("evaluation_outputs/json/rl_training_dataset_summary.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _row_from_state(
    source: str,
    row_id: str,
    state: dict[str, Any],
    action_label: str,
    reward: float,
    next_state: dict[str, Any],
    done: bool = False,
) -> dict[str, Any]:
    vector = state_to_vector(state)
    next_vector = state_to_vector(next_state)
    output = {
        "source": source,
        "source_row_id": row_id,
        "action_label": action_label,
        "action_id": action_to_id(action_label),
        "reward": reward,
        "done": int(done),
    }
    for feature, value in zip(STATE_FEATURES, vector):
        output[feature] = float(value)
    for feature, value in zip(STATE_FEATURES, next_vector):
        output[f"next_{feature}"] = float(value)
    return output


def _from_synthetic() -> list[dict[str, Any]]:
    if not SYNTHETIC_PATH.exists():
        return []
    df = pd.read_csv(SYNTHETIC_PATH)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        raw = row.to_dict()
        state = infer_state_from_row(raw)
        action = infer_action_from_row(raw)
        reward = build_reward(state, action, raw)
        next_state = infer_next_state(state, action)
        rows.append(_row_from_state("synthetic_promotion_logs", str(raw.get("row_id", idx)), state, action, reward, next_state))
    return rows


def _from_experience() -> list[dict[str, Any]]:
    if not EXPERIENCE_PATH.exists():
        return []
    df = pd.read_csv(EXPERIENCE_PATH)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        raw = row.to_dict()
        state = {
            "mastery_score": _safe_float(raw.get("mastery_score")),
            "behaviour_risk": _safe_float(raw.get("behavior_score")),
            "fused_score": _safe_float(raw.get("evaluation_score")),
            "review_due": str(raw.get("review_due")).lower() == "true",
            "promotion_confidence": min(0.9, max(0.0, (_safe_float(raw.get("mastery_score")) + _safe_float(raw.get("evaluation_score"))) / 2.0)),
            "difficulty": raw.get("difficulty", "medium"),
            "weakest_skill": "none",
            "behaviour_risk_label": "high_risk" if _safe_float(raw.get("behavior_score")) >= 0.7 else "medium_risk" if _safe_float(raw.get("behavior_score")) >= 0.4 else "low_risk",
            "concept_dependency_valid": True,
            "view_reward": min(1.0, max(0.0, (_safe_float(raw.get("reward")) + 1.0) / 3.0)),
        }
        action = infer_action_from_row(raw)
        reward = build_reward(state, action, raw)
        next_state = {
            **state,
            "mastery_score": _safe_float(raw.get("next_mastery_score"), state["mastery_score"]),
            "behaviour_risk": _safe_float(raw.get("next_behavior_score"), state["behaviour_risk"]),
            "fused_score": _safe_float(raw.get("next_evaluation_score"), state["fused_score"]),
            "review_due": str(raw.get("next_review_due")).lower() == "true",
        }
        rows.append(_row_from_state("rl_experience_dataset", str(idx), state, action, reward, next_state))
    return rows


def _db_summary() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"db_exists": False}
    with sqlite3.connect(DB_PATH) as conn:
        tables = {}
        for table in ["reward_event_log", "quiz_results", "knowledge_state", "behaviour_state", "teaching_strategy_log"]:
            try:
                tables[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                tables[table] = None
    return {"db_exists": True, "tables": tables}


def build_dataset() -> dict[str, Any]:
    rows = _from_synthetic() + _from_experience()
    if not rows:
        fallback_state = {
            "mastery_score": 0.5,
            "behaviour_risk": 0.2,
            "fused_score": 0.5,
            "review_due": False,
            "promotion_confidence": 0.5,
            "difficulty": "medium",
            "weakest_skill": "none",
            "behaviour_risk_label": "low_risk",
            "concept_dependency_valid": True,
            "view_reward": 0.5,
        }
        rows.append(_row_from_state("fallback", "0", fallback_state, "practice_medium", 0.2, fallback_state))
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    summary = {
        "status": "success",
        "module": "rl_training_dataset_builder",
        "generated_at": _now_iso(),
        "output_csv": str(OUTPUT_CSV),
        "row_count": len(df),
        "state_features": STATE_FEATURES,
        "action_distribution": df["action_label"].value_counts().to_dict(),
        "reward_summary": {
            "min": round(float(df["reward"].min()), 4),
            "avg": round(float(df["reward"].mean()), 4),
            "max": round(float(df["reward"].max()), 4),
        },
        "source_distribution": df["source"].value_counts().to_dict(),
        "db_summary": _db_summary(),
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    summary = build_dataset()
    print(f"STATUS: {summary['status']}")
    print("MODULE: rl_training_dataset_builder")
    print(f"CSV_OUTPUT: {OUTPUT_CSV}")
    print(f"JSON_SUMMARY: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
