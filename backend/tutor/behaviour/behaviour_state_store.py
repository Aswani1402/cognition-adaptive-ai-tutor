from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def behavior_risk_label_for_score(risk: float) -> str:
    risk = _clamp(risk)
    if risk >= 0.7:
        return "high_risk"
    if risk >= 0.4:
        return "medium_risk"
    return "low_risk"


def compute_behavior_risk(
    behavior_label: str | None,
    wrong_rate: float = 0.0,
    slow_rate: float = 0.0,
    low_confidence_rate: float = 0.0,
    hint_rate: float = 0.0,
    option_change_rate: float = 0.0,
) -> dict[str, Any]:
    label = (behavior_label or "stable").strip().lower()
    base_risk = {
        "stable": 0.18,
        "confused": 0.55,
        "guessing": 0.78,
        "struggling": 0.88,
    }.get(label, 0.35)

    feature_risk = (
        0.35 * _clamp(wrong_rate)
        + 0.18 * _clamp(low_confidence_rate)
        + 0.16 * _clamp(hint_rate)
        + 0.16 * _clamp(slow_rate)
        + 0.15 * _clamp(option_change_rate)
    )
    risk = _clamp((base_risk * 0.6) + (feature_risk * 0.4))

    if label == "stable":
        risk = _clamp(risk, 0.10, 0.35)
    elif label == "confused":
        risk = _clamp(risk, 0.45, 0.68)
    elif label == "guessing":
        risk = _clamp(risk, 0.70, 0.88)
    elif label == "struggling":
        risk = _clamp(risk, 0.80, 0.95)

    return {
        "behavior_risk": round(risk, 4),
        "behavior_risk_label": behavior_risk_label_for_score(risk),
    }


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def enrich_behaviour_output(output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(output, dict):
        return output

    enriched = dict(output)
    label = enriched.get("behavior_label")
    confidence = _safe_float(
        enriched.get("behavior_confidence", enriched.get("behavior_score")),
        0.0,
    )
    risk = compute_behavior_risk(
        behavior_label=str(label or "stable"),
        wrong_rate=_safe_float(enriched.get("wrong_rate")),
        slow_rate=_safe_float(enriched.get("slow_rate")),
        low_confidence_rate=_safe_float(enriched.get("low_confidence_rate")),
        hint_rate=_safe_float(enriched.get("hint_rate")),
        option_change_rate=_safe_float(enriched.get("option_change_rate")),
    )

    enriched["module"] = enriched.get("module") or "LSTMBehaviourModel"
    enriched["behavior_confidence"] = round(_clamp(confidence), 4)
    enriched["behavior_risk"] = risk["behavior_risk"]
    enriched["behavior_risk_label"] = risk["behavior_risk_label"]
    enriched["behavior_score"] = risk["behavior_risk"]
    enriched["behaviour_state"] = enriched.get("behaviour_state") or enriched.get("behavior_label") or "stable"
    enriched["behaviour_risk"] = enriched.get("behaviour_risk", enriched.get("behavior_risk"))
    enriched["confidence_score"] = enriched.get("confidence_score", enriched.get("behavior_confidence"))
    enriched["model_source"] = enriched.get("model_source") or enriched.get("behavior_source") or "lstm_runtime"
    enriched["behavior_source"] = enriched.get("behavior_source") or enriched.get("model_source")
    enriched["model_used"] = bool(enriched.get("model_used", False))
    enriched["sequence_length"] = _safe_int(enriched.get("sequence_length"), 0)
    return enriched


def persist_behaviour_state(
    behaviour_output: dict[str, Any],
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    output = enrich_behaviour_output(behaviour_output)
    learner_id = str(output.get("learner_id") or "").strip()
    if not learner_id:
        return {
            "status": "error",
            "module": "BehaviourStateStore",
            "error": "learner_id missing from behaviour output.",
        }

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        columns = _table_columns(conn, "behaviour_state")
        learner_column = "learner_id" if "learner_id" in columns else "student_id"
        if learner_column not in columns:
            return {
                "status": "error",
                "module": "BehaviourStateStore",
                "error": "behaviour_state has no learner_id/student_id column.",
            }

        values_by_column = {
            learner_column: learner_id,
            "behavior_label": output.get("behavior_label") or output.get("behaviour_state"),
            "behavior_score": _safe_float(output.get("behavior_score")),
            "behavior_confidence": _safe_float(output.get("behavior_confidence")),
            "behavior_risk": _safe_float(output.get("behavior_risk")),
            "behavior_risk_label": output.get("behavior_risk_label"),
            "wrong_rate": _safe_float(output.get("wrong_rate")),
            "slow_rate": _safe_float(output.get("slow_rate")),
            "low_confidence_rate": _safe_float(output.get("low_confidence_rate")),
            "hint_rate": _safe_float(output.get("hint_rate")),
            "option_change_rate": _safe_float(output.get("option_change_rate")),
            "model_used": 1 if output.get("model_used") else 0,
            "sequence_length": _safe_int(output.get("sequence_length")),
            "behavior_source": output.get("model_source") or output.get("behavior_source"),
            "state_json": json.dumps(
                {
                    "model_source": output.get("model_source") or output.get("behavior_source"),
                    "behaviour_state": output.get("behaviour_state") or output.get("behavior_label"),
                    "behaviour_risk": output.get("behaviour_risk") or output.get("behavior_risk"),
                    "evidence_inputs": output.get("evidence_inputs", {}),
                    "fallback_reason": output.get("fallback_reason"),
                },
                default=str,
            ),
            "timestamp": now_iso(),
        }

        insert_columns = [
            column
            for column in values_by_column.keys()
            if column in columns
        ]
        placeholders = ", ".join(["?"] * len(insert_columns))
        column_sql = ", ".join(insert_columns)
        values = [values_by_column[column] for column in insert_columns]

        cursor = conn.execute(
            f"""
            INSERT INTO behaviour_state ({column_sql})
            VALUES ({placeholders})
            """,
            values,
        )
        conn.commit()

    return {
        "status": "success",
        "module": "BehaviourStateStore",
        "learner_id": learner_id,
        "row_id": cursor.lastrowid,
        "behavior_label": output.get("behavior_label"),
        "behavior_score": output.get("behavior_score"),
        "behavior_confidence": output.get("behavior_confidence"),
        "behavior_risk": output.get("behavior_risk"),
        "behavior_risk_label": output.get("behavior_risk_label"),
        "behavior_source": output.get("behavior_source"),
    }
