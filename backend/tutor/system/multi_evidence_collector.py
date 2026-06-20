# tutor/system/multi_evidence_collector.py

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class EvidenceSummary:
    mastery_score: float
    behaviour_risk: float
    decay_priority: float
    recent_correctness: float
    evidence_confidence: float


class MultiEvidenceCollector:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def collect(
        self,
        learner_id: str,
        system_concept_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self.connect() as conn:
            target_concept_id = system_concept_id or self._infer_target_concept(conn, learner_id)

            mastery = self._get_knowledge_state(conn, learner_id, target_concept_id)
            behaviour = self._get_behaviour_state(conn, learner_id)
            decay = self._get_decay_state(conn, learner_id, target_concept_id)
            profile = self._get_personalization_state(conn, learner_id)
            quiz = self._get_quiz_evidence(conn, learner_id, target_concept_id)

            summary = self._build_summary(
                mastery=mastery,
                behaviour=behaviour,
                decay=decay,
                profile=profile,
                quiz=quiz,
            )

            return {
                "learner_id": str(learner_id),
                "target_concept_id": str(target_concept_id) if target_concept_id is not None else None,
                "timestamp": utc_now_iso(),
                "evidence": {
                    "mastery": mastery,
                    "behaviour": behaviour,
                    "decay": decay,
                    "profile": profile,
                    "quiz": quiz,
                },
                "summary": asdict(summary),
            }

    def _infer_target_concept(self, conn: sqlite3.Connection, learner_id: str) -> Optional[str]:
        row = conn.execute(
            """
            SELECT concept_id
            FROM quiz_results
            WHERE learner_id = ?
              AND concept_id IS NOT NULL
              AND TRIM(concept_id) != ''
            ORDER BY
                CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                timestamp DESC,
                quiz_id DESC
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()

        if not row:
            return None
        return str(row["concept_id"])

    def _get_knowledge_state(
        self,
        conn: sqlite3.Connection,
        learner_id: str,
        system_concept_id: Optional[str],
    ) -> Dict[str, Any]:
        row = conn.execute(
            """
            SELECT state_json, updated_at
            FROM knowledge_state
            WHERE student_id = ?
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()

        if not row:
            return {
                "concept_id": system_concept_id,
                "mastery_score": 0.0,
                "full_state": {},
                "updated_at": None,
                "available": False,
            }

        state_json = safe_json_load(row["state_json"], {})
        mastery_score = 0.0
        mastery_map = state_json

        if (
            isinstance(state_json, dict)
            and state_json.get("schema_version") == "kt_v2"
            and isinstance(state_json.get("concepts"), dict)
        ):
            mastery_map = state_json.get("concepts", {})

        if system_concept_id is not None:
            concept_data = mastery_map.get(str(system_concept_id), {})
            if isinstance(concept_data, dict):
                mastery_score = float(concept_data.get("mastery", concept_data.get("probability", 0.0)) or 0.0)
            elif isinstance(concept_data, (int, float)):
                mastery_score = float(concept_data)

        return {
            "concept_id": system_concept_id,
            "mastery_score": clamp(mastery_score),
            "full_state": state_json,
            "updated_at": row["updated_at"],
            "available": True,
        }

    def _get_behaviour_state(self, conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='behaviour_state'
            """
        ).fetchone()

        if not table_exists:
            return {
                "label": "unknown",
                "risk_score": 0.0,
                "state": {},
                "timestamp": None,
                "available": False,
                "reason": "behaviour_state table not found",
            }

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(behaviour_state)").fetchall()
        }

        # Case 1: JSON-based behaviour table
        json_col = None
        for candidate in ["behavior_json", "behaviour_json", "state_json", "data_json"]:
            if candidate in columns:
                json_col = candidate
                break

        timestamp_col = None
        for candidate in ["timestamp", "created_at", "updated_at"]:
            if candidate in columns:
                timestamp_col = candidate
                break

        order_parts = []
        if timestamp_col:
            order_parts.append(f"CASE WHEN {timestamp_col} IS NULL THEN 1 ELSE 0 END")
            order_parts.append(f"{timestamp_col} DESC")
        if "id" in columns:
            order_parts.append("id DESC")
        order_sql = ", ".join(order_parts) if order_parts else "ROWID DESC"

        if json_col is not None:
            select_timestamp = f", {timestamp_col} AS ts_value" if timestamp_col else ""

            row = conn.execute(
                f"""
                SELECT {json_col} AS state_value
                {select_timestamp}
                FROM behaviour_state
                WHERE learner_id = ?
                ORDER BY {order_sql}
                LIMIT 1
                """,
                (learner_id,),
            ).fetchone()

            if not row:
                return {
                    "label": "unknown",
                    "risk_score": 0.0,
                    "state": {},
                    "timestamp": None,
                    "available": False,
                }

            state = safe_json_load(row["state_value"], {})
            if not isinstance(state, dict):
                state = {}

            risk_score = float(
                state.get(
                    "behavior_risk",
                    state.get("behaviour_risk", state.get("risk_score", state.get("anomaly_score", 0.0))),
                ) or 0.0
            )
            confidence = state.get("behavior_confidence", state.get("behaviour_confidence"))

            return {
                "label": state.get("label", state.get("behavior_label", state.get("behaviour_label", "unknown"))),
                "risk_score": clamp(risk_score),
                "confidence": clamp(float(confidence)) if confidence is not None else None,
                "risk_label": state.get("behavior_risk_label", state.get("behaviour_risk_label")),
                "state": state,
                "timestamp": row["ts_value"] if "ts_value" in row.keys() else None,
                "available": True,
            }

        # Case 2: Column-based behaviour table
        structured_candidates = {
            "behavior_label",
            "behavior_score",
            "wrong_rate",
            "slow_rate",
            "low_confidence_rate",
            "hint_rate",
            "option_change_rate",
        }

        if structured_candidates.intersection(columns):
            select_fields = []
            for col in [
                "behavior_label",
                "behavior_score",
                "behavior_confidence",
                "behavior_risk",
                "behavior_risk_label",
                "wrong_rate",
                "slow_rate",
                "low_confidence_rate",
                "hint_rate",
                "option_change_rate",
                "model_used",
                "sequence_length",
                "behavior_source",
            ]:
                if col in columns:
                    select_fields.append(col)

            if timestamp_col:
                select_fields.append(f"{timestamp_col} AS ts_value")

            row = conn.execute(
                f"""
                SELECT {", ".join(select_fields)}
                FROM behaviour_state
                WHERE learner_id = ?
                ORDER BY {order_sql}
                LIMIT 1
                """,
                (learner_id,),
            ).fetchone()

            if not row:
                return {
                    "label": "unknown",
                    "risk_score": 0.0,
                    "state": {},
                    "timestamp": None,
                    "available": False,
                }

            wrong_rate = float(row["wrong_rate"]) if "wrong_rate" in row.keys() and row[
                "wrong_rate"] is not None else 0.0
            slow_rate = float(row["slow_rate"]) if "slow_rate" in row.keys() and row["slow_rate"] is not None else 0.0
            low_conf_rate = (
                float(row["low_confidence_rate"])
                if "low_confidence_rate" in row.keys() and row["low_confidence_rate"] is not None
                else 0.0
            )
            hint_rate = float(row["hint_rate"]) if "hint_rate" in row.keys() and row["hint_rate"] is not None else 0.0
            option_change_rate = (
                float(row["option_change_rate"])
                if "option_change_rate" in row.keys() and row["option_change_rate"] is not None
                else 0.0
            )
            behavior_score = (
                float(row["behavior_score"])
                if "behavior_score" in row.keys() and row["behavior_score"] is not None
                else 0.0
            )
            behavior_risk = (
                float(row["behavior_risk"])
                if "behavior_risk" in row.keys() and row["behavior_risk"] is not None
                else None
            )
            behavior_confidence = (
                float(row["behavior_confidence"])
                if "behavior_confidence" in row.keys() and row["behavior_confidence"] is not None
                else None
            )

            fallback_risk = (wrong_rate + slow_rate + low_conf_rate + hint_rate + option_change_rate) / 5.0
            risk_score = behavior_risk if behavior_risk is not None else (behavior_score if behavior_score > 0 else fallback_risk)

            state = {
                "wrong_rate": round(clamp(wrong_rate), 4),
                "slow_rate": round(clamp(slow_rate), 4),
                "low_confidence_rate": round(clamp(low_conf_rate), 4),
                "hint_rate": round(clamp(hint_rate), 4),
                "option_change_rate": round(clamp(option_change_rate), 4),
                "behavior_score": round(clamp(behavior_score), 4),
                "behavior_confidence": round(clamp(behavior_confidence), 4) if behavior_confidence is not None else None,
                "behavior_risk": round(clamp(risk_score), 4),
                "behavior_risk_label": (
                    row["behavior_risk_label"]
                    if "behavior_risk_label" in row.keys() and row["behavior_risk_label"]
                    else None
                ),
                "model_used": (
                    bool(row["model_used"])
                    if "model_used" in row.keys() and row["model_used"] is not None
                    else None
                ),
                "sequence_length": (
                    int(row["sequence_length"])
                    if "sequence_length" in row.keys() and row["sequence_length"] is not None
                    else None
                ),
                "behavior_source": (
                    row["behavior_source"]
                    if "behavior_source" in row.keys() and row["behavior_source"]
                    else None
                ),
            }

            return {
                "label": row["behavior_label"] if "behavior_label" in row.keys() and row[
                    "behavior_label"] else "unknown",
                "risk_score": round(clamp(risk_score), 4),
                "confidence": round(clamp(behavior_confidence), 4) if behavior_confidence is not None else None,
                "risk_label": state.get("behavior_risk_label"),
                "state": state,
                "timestamp": row["ts_value"] if "ts_value" in row.keys() else None,
                "available": True,
            }

        return {
            "label": "unknown",
            "risk_score": 0.0,
            "state": {},
            "timestamp": None,
            "available": False,
            "reason": f"No supported behaviour format found. Columns: {sorted(columns)}",
        }

    def _get_decay_state(
            self,
            conn: sqlite3.Connection,
            learner_id: str,
            system_concept_id: Optional[str],
    ) -> Dict[str, Any]:
        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='decay_state'
            """
        ).fetchone()

        if not table_exists:
            return {
                "concept_id": system_concept_id,
                "decay_score": 0.0,
                "priority_score": 0.0,
                "queue_entry": None,
                "generation": None,
                "available": False,
                "reason": "decay_state table not found",
            }

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(decay_state)").fetchall()
        }

        decay_col = None
        priority_col = None
        queue_col = None
        params_col = None
        generation_col = None

        for candidate in ["decay_json", "decay_state_json", "state_json"]:
            if candidate in columns:
                decay_col = candidate
                break

        for candidate in ["priority_json", "priority_state_json", "review_priority_json"]:
            if candidate in columns:
                priority_col = candidate
                break

        for candidate in ["queue_json", "review_queue_json"]:
            if candidate in columns:
                queue_col = candidate
                break

        for candidate in ["params_json", "parameter_json", "config_json"]:
            if candidate in columns:
                params_col = candidate
                break

        for candidate in ["generation", "version", "updated_at", "timestamp"]:
            if candidate in columns:
                generation_col = candidate
                break

        select_parts = []
        if decay_col:
            select_parts.append(f"{decay_col} AS decay_value")
        if priority_col:
            select_parts.append(f"{priority_col} AS priority_value")
        if queue_col:
            select_parts.append(f"{queue_col} AS queue_value")
        if params_col:
            select_parts.append(f"{params_col} AS params_value")
        if generation_col:
            select_parts.append(f"{generation_col} AS generation_value")

        if not select_parts:
            return {
                "concept_id": system_concept_id,
                "decay_score": 0.0,
                "priority_score": 0.0,
                "queue_entry": None,
                "generation": None,
                "available": False,
                "reason": f"No supported columns found in decay_state. Columns: {sorted(columns)}",
            }

        order_parts = []
        if "updated_at" in columns:
            order_parts.append("CASE WHEN updated_at IS NULL THEN 1 ELSE 0 END")
            order_parts.append("updated_at DESC")
        elif "timestamp" in columns:
            order_parts.append("CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END")
            order_parts.append("timestamp DESC")

        if "id" in columns:
            order_parts.append("id DESC")

        order_sql = ", ".join(order_parts) if order_parts else "ROWID DESC"

        row = conn.execute(
            f"""
            SELECT {", ".join(select_parts)}
            FROM decay_state
            WHERE learner_id = ?
            ORDER BY {order_sql}
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()

        if not row:
            return {
                "concept_id": system_concept_id,
                "decay_score": 0.0,
                "priority_score": 0.0,
                "queue_entry": None,
                "generation": None,
                "available": False,
            }

        decay_json = safe_json_load(row["decay_value"], {}) if "decay_value" in row.keys() else {}
        priority_json = safe_json_load(row["priority_value"], {}) if "priority_value" in row.keys() else {}
        queue_json = safe_json_load(row["queue_value"], {}) if "queue_value" in row.keys() else {}

        if not isinstance(decay_json, dict):
            decay_json = {}
        if not isinstance(priority_json, dict):
            priority_json = {}
        if not isinstance(queue_json, dict):
            queue_json = {}

        concept_key = str(system_concept_id) if system_concept_id is not None else None

        decay_score = 0.0
        priority_score = 0.0
        queue_entry = None

        if concept_key:
            decay_val = decay_json.get(concept_key, {})
            priority_val = priority_json.get(concept_key, {})
            queue_entry = queue_json.get(concept_key)

            if isinstance(decay_val, dict):
                decay_score = float(decay_val.get("decay_score", decay_val.get("value", 0.0)) or 0.0)
            elif isinstance(decay_val, (int, float)):
                decay_score = float(decay_val)

            if isinstance(priority_val, dict):
                priority_score = float(priority_val.get("priority", priority_val.get("score", 0.0)) or 0.0)
            elif isinstance(priority_val, (int, float)):
                priority_score = float(priority_val)

        return {
            "concept_id": system_concept_id,
            "decay_score": clamp(decay_score),
            "priority_score": clamp(priority_score),
            "queue_entry": queue_entry,
            "generation": row["generation_value"] if "generation_value" in row.keys() else None,
            "available": True,
        }



    def _get_personalization_state(self, conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='long_term_personalization'
            """
        ).fetchone()

        if not table_exists:
            return {
                "profile": {},
                "available": False,
            }

        row = conn.execute(
            """
            SELECT *
            FROM long_term_personalization
            WHERE learner_id = ?
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()

        if not row:
            return {
                "profile": {},
                "available": False,
            }

        data = dict(row)
        return {
            "profile": data,
            "available": True,
        }

    def _get_quiz_evidence(
        self,
        conn: sqlite3.Connection,
        learner_id: str,
        system_concept_id: Optional[str],
    ) -> Dict[str, Any]:
        params: List[Any] = [learner_id]
        concept_clause = ""

        if system_concept_id is not None:
            concept_clause = " AND concept_id = ? "
            params.append(system_concept_id)

        rows = conn.execute(
            f"""
            SELECT quiz_id, learner_id, concept_id, question_id, selected_option,
                   is_correct, confidence, time_taken_sec, attempt_no, timestamp,
                   hint_used, hint_count, option_changes_count
            FROM quiz_results
            WHERE learner_id = ?
            {concept_clause}
            ORDER BY
                CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                timestamp DESC,
                quiz_id DESC
            LIMIT 10
            """,
            params,
        ).fetchall()

        attempts = [dict(r) for r in rows]
        if not attempts:
            return {
                "concept_id": system_concept_id,
                "attempt_count": 0,
                "latest_attempt": None,
                "recent_correctness": 0.0,
                "avg_confidence": 0.0,
                "avg_time_taken": 0.0,
                "hint_usage_rate": 0.0,
                "option_change_rate": 0.0,
                "available": False,
            }

        n = len(attempts)
        recent_correctness = sum(int(a.get("is_correct") or 0) for a in attempts) / n
        avg_confidence = sum(float(a.get("confidence") or 0) for a in attempts) / n
        avg_time_taken = sum(float(a.get("time_taken_sec") or 0) for a in attempts) / n
        hint_usage_rate = sum(int(a.get("hint_used") or 0) for a in attempts) / n
        option_change_rate = sum(1 if int(a.get("option_changes_count") or 0) > 0 else 0 for a in attempts) / n

        return {
            "concept_id": system_concept_id,
            "attempt_count": n,
            "latest_attempt": attempts[0],
            "recent_attempts": attempts,
            "recent_correctness": round(recent_correctness, 4),
            "avg_confidence": round(avg_confidence, 4),
            "avg_time_taken": round(avg_time_taken, 4),
            "hint_usage_rate": round(hint_usage_rate, 4),
            "option_change_rate": round(option_change_rate, 4),
            "available": True,
        }

    def _build_summary(
        self,
        mastery: Dict[str, Any],
        behaviour: Dict[str, Any],
        decay: Dict[str, Any],
        profile: Dict[str, Any],
        quiz: Dict[str, Any],
    ) -> EvidenceSummary:
        mastery_score = float(mastery.get("mastery_score", 0.0) or 0.0)
        behaviour_risk = float(behaviour.get("risk_score", 0.0) or 0.0)
        decay_priority = float(decay.get("priority_score", 0.0) or 0.0)
        recent_correctness = float(quiz.get("recent_correctness", 0.0) or 0.0)

        available_count = sum(
            [
                1 if mastery.get("available") else 0,
                1 if behaviour.get("available") else 0,
                1 if decay.get("available") else 0,
                1 if profile.get("available") else 0,
                1 if quiz.get("available") else 0,
            ]
        )
        evidence_confidence = available_count / 5.0

        return EvidenceSummary(
            mastery_score=round(clamp(mastery_score), 4),
            behaviour_risk=round(clamp(behaviour_risk), 4),
            decay_priority=round(clamp(decay_priority), 4),
            recent_correctness=round(clamp(recent_correctness), 4),
            evidence_confidence=round(clamp(evidence_confidence), 4),
        )


def collect_multi_evidence(
    learner_id: str,
    system_concept_id: Optional[str] = None,
    db_path: Path | str = DB_PATH,
) -> Dict[str, Any]:
    collector = MultiEvidenceCollector(db_path=db_path)
    return collector.collect(learner_id=learner_id, system_concept_id=system_concept_id)


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    result = collect_multi_evidence(
        learner_id=str(args.learner_id),
        system_concept_id=str(args.concept_id) if args.concept_id else None,
    )
    pprint.pp(result)
