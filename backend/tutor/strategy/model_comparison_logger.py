import json
import sqlite3
from datetime import datetime, UTC
from typing import Any, Dict, Optional


TABLE_NAME = "teaching_strategy_model_comparison_log"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "json_serialization_failed"})


def ensure_model_comparison_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            concept_id TEXT,
            concept_name TEXT,

            evidence_teaching_view TEXT,
            model_teaching_view TEXT,
            teaching_view_agreement INTEGER,

            evidence_progression_action TEXT,
            model_progression_action TEXT,
            progression_agreement INTEGER,

            model_teaching_view_confidence REAL,
            model_progression_confidence REAL,

            evidence_strategy_json TEXT,
            model_strategy_json TEXT,

            created_at TEXT
        )
        """
    )
    conn.commit()


def log_teaching_strategy_model_comparison(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    concept_name: str,
    evidence_aware_output: Optional[Dict[str, Any]],
    model_based_output: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    ensure_model_comparison_table(conn)

    evidence_aware_output = evidence_aware_output or {}
    model_based_output = model_based_output or {}

    evidence_teaching_view = evidence_aware_output.get("teaching_view")
    model_teaching_view = model_based_output.get("model_teaching_view")

    evidence_progression_action = evidence_aware_output.get("progression_action")
    model_progression_action = model_based_output.get("model_progression_action")

    teaching_view_agreement = (
        evidence_teaching_view == model_teaching_view
        if evidence_teaching_view is not None and model_teaching_view is not None
        else None
    )

    progression_agreement = (
        evidence_progression_action == model_progression_action
        if evidence_progression_action is not None and model_progression_action is not None
        else None
    )

    model_teaching_view_confidence = model_based_output.get("teaching_view_confidence")
    model_progression_confidence = model_based_output.get("progression_confidence")

    created_at = _now_iso()

    conn.execute(
        f"""
        INSERT INTO {TABLE_NAME} (
            learner_id,
            concept_id,
            concept_name,
            evidence_teaching_view,
            model_teaching_view,
            teaching_view_agreement,
            evidence_progression_action,
            model_progression_action,
            progression_agreement,
            model_teaching_view_confidence,
            model_progression_confidence,
            evidence_strategy_json,
            model_strategy_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(learner_id),
            str(concept_id),
            str(concept_name),
            evidence_teaching_view,
            model_teaching_view,
            int(teaching_view_agreement) if teaching_view_agreement is not None else None,
            evidence_progression_action,
            model_progression_action,
            int(progression_agreement) if progression_agreement is not None else None,
            model_teaching_view_confidence,
            model_progression_confidence,
            _to_json(evidence_aware_output),
            _to_json(model_based_output),
            created_at,
        ),
    )

    conn.commit()

    return {
        "status": "success",
        "module": "TeachingStrategyModelComparisonLogger",
        "learner_id": str(learner_id),
        "concept_id": str(concept_id),
        "concept_name": str(concept_name),
        "evidence_teaching_view": evidence_teaching_view,
        "model_teaching_view": model_teaching_view,
        "teaching_view_agreement": teaching_view_agreement,
        "evidence_progression_action": evidence_progression_action,
        "model_progression_action": model_progression_action,
        "progression_agreement": progression_agreement,
        "model_teaching_view_confidence": model_teaching_view_confidence,
        "model_progression_confidence": model_progression_confidence,
        "created_at": created_at,
    }