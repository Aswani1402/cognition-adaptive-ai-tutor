from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(data: Any) -> str:
    return json.dumps(data if data is not None else {}, default=str)


def ensure_teaching_strategy_training_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teaching_strategy_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT,
            concept_name TEXT,
            teaching_view TEXT,
            final_strategy TEXT,
            difficulty TEXT,
            assessment_difficulty TEXT,
            assessment_types_json TEXT,
            fallback_views_json TEXT,
            next_activity TEXT,
            progression_action TEXT,
            evaluation_score REAL,
            evaluation_verdict TEXT,
            behavior_label TEXT,
            view_reward REAL,
            policy_output_json TEXT,
            evidence_strategy_json TEXT,
            learner_memory_json TEXT,
            xai_json TEXT,
            adaptive_path_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def log_teaching_strategy_training_session(
    conn: sqlite3.Connection,
    learner_id: str,
    concept_id: str,
    concept_name: str,
    policy_output: dict[str, Any],
    evaluation_output: dict[str, Any],
    behaviour_state: dict[str, Any],
    view_performance_output: dict[str, Any],
    learner_notebook_memory_output: dict[str, Any],
    xai_output: dict[str, Any],
    adaptive_path_output: dict[str, Any],
    evidence_aware_teaching_strategy_output: dict[str, Any],
) -> dict[str, Any]:
    ensure_teaching_strategy_training_log_table(conn)

    behaviour_data = behaviour_state.get("data", {}) if isinstance(behaviour_state, dict) else {}
    if isinstance(behaviour_data, dict) and isinstance(behaviour_data.get("data"), dict):
        behaviour_data = behaviour_data.get("data", {})

    logged_view = (
        view_performance_output.get("logged", {})
        if isinstance(view_performance_output, dict)
        else {}
    )

    row = {
        "learner_id": str(learner_id),
        "concept_id": str(concept_id),
        "concept_name": str(concept_name or ""),
        "teaching_view": evidence_aware_teaching_strategy_output.get("teaching_view"),
        "final_strategy": evidence_aware_teaching_strategy_output.get("final_strategy"),
        "difficulty": evidence_aware_teaching_strategy_output.get("difficulty"),
        "assessment_difficulty": evidence_aware_teaching_strategy_output.get("assessment_difficulty"),
        "assessment_types_json": _json(evidence_aware_teaching_strategy_output.get("assessment_types", [])),
        "fallback_views_json": _json(evidence_aware_teaching_strategy_output.get("fallback_views", [])),
        "next_activity": evidence_aware_teaching_strategy_output.get("next_activity"),
        "progression_action": evidence_aware_teaching_strategy_output.get("progression_action"),
        "evaluation_score": evaluation_output.get("overall_score") if isinstance(evaluation_output, dict) else None,
        "evaluation_verdict": evaluation_output.get("verdict") if isinstance(evaluation_output, dict) else None,
        "behavior_label": behaviour_data.get("behavior_label"),
        "view_reward": logged_view.get("reward"),
        "policy_output_json": _json(policy_output),
        "evidence_strategy_json": _json(evidence_aware_teaching_strategy_output),
        "learner_memory_json": _json(learner_notebook_memory_output),
        "xai_json": _json(xai_output),
        "adaptive_path_json": _json(adaptive_path_output),
        "created_at": _now_iso(),
    }

    cursor = conn.execute(
        """
        INSERT INTO teaching_strategy_training_log (
            learner_id,
            concept_id,
            concept_name,
            teaching_view,
            final_strategy,
            difficulty,
            assessment_difficulty,
            assessment_types_json,
            fallback_views_json,
            next_activity,
            progression_action,
            evaluation_score,
            evaluation_verdict,
            behavior_label,
            view_reward,
            policy_output_json,
            evidence_strategy_json,
            learner_memory_json,
            xai_json,
            adaptive_path_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["learner_id"],
            row["concept_id"],
            row["concept_name"],
            row["teaching_view"],
            row["final_strategy"],
            row["difficulty"],
            row["assessment_difficulty"],
            row["assessment_types_json"],
            row["fallback_views_json"],
            row["next_activity"],
            row["progression_action"],
            row["evaluation_score"],
            row["evaluation_verdict"],
            row["behavior_label"],
            row["view_reward"],
            row["policy_output_json"],
            row["evidence_strategy_json"],
            row["learner_memory_json"],
            row["xai_json"],
            row["adaptive_path_json"],
            row["created_at"],
        ),
    )
    conn.commit()

    return {
        "status": "success",
        "module": "TeachingStrategyTrainingLogger",
        "log_id": cursor.lastrowid,
        "teaching_view": row["teaching_view"],
        "assessment_types": evidence_aware_teaching_strategy_output.get("assessment_types", []),
        "progression_action": row["progression_action"],
    }
