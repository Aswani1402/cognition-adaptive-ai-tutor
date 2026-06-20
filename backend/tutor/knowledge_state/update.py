from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from tutor.knowledge_state.dkt.dkt_inference import predict_mastery_dkt_or_fallback


def _normalize_interactions(rows):
    normalized = []

    for row in rows:
        if isinstance(row, dict):
            normalized.append(row)
        elif hasattr(row, "_asdict"):
            normalized.append(row._asdict())
        elif isinstance(row, (list, tuple)):
            normalized.append({
                "correct": row[0] if len(row) > 0 else 0,
                "elapsed_time": row[1] if len(row) > 1 else 0,
                "attempts": row[2] if len(row) > 2 else 1,
                "hint_count": row[3] if len(row) > 3 else 0,
            })
        else:
            continue

    return normalized


def update_knowledge_state(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    try:
        rows = conn.execute(
            """
            SELECT concept_id, is_correct
            FROM quiz_results
            WHERE learner_id = ?
            ORDER BY quiz_id DESC
            LIMIT 20
            """,
            (learner_id,),
        ).fetchall()

        if not rows:
            return {
                "status": "error",
                "module": "knowledge_state",
                "error": "No interactions found",
            }

        interactions = []

        for concept_id, correct in reversed(rows):
            raw_concept_id = str(concept_id).strip()
            normalized_concept_id = raw_concept_id.upper()

            if normalized_concept_id.startswith(("P", "H", "D", "S", "G")):
                # use mapping table
                row = conn.execute("""
                    SELECT system_concept_id
                    FROM concept_id_map
                    WHERE content_concept_id = ?
                """, (normalized_concept_id,)).fetchone()

                if row:
                    cid = int(row[0])
                else:
                    continue  # skip unknown
            else:
                try:
                    cid = int(float(normalized_concept_id))
                except Exception:
                    continue

            interactions.append(
                {
                    "raw_concept_id": raw_concept_id,
                    "concept_id": cid,
                    "correct": int(correct or 0),
                }
            )

        inference = predict_mastery_dkt_or_fallback(
            learner_id=learner_id,
            interactions=interactions,
        )

        if inference.get("status") != "success":
            return {
                "status": "error",
                "module": "knowledge_state",
                "source": inference.get("source"),
                "fallback_used": inference.get("fallback_used"),
                "error": inference.get("error") or "KT inference failed",
            }

        written_state = {
            str(concept_id): float(mastery)
            for concept_id, mastery in inference.get("concept_mastery", {}).items()
        }
        updated_at = datetime.now().isoformat()

        attempts_by_concept: dict[str, int] = {}
        last_correct_by_concept: dict[str, bool | None] = {}
        for interaction in interactions:
            concept_key = str(interaction["concept_id"])
            attempts_by_concept[concept_key] = attempts_by_concept.get(concept_key, 0) + 1
            last_correct_by_concept[concept_key] = bool(interaction.get("correct"))

        concepts = {}
        for concept_id, mastery in written_state.items():
            concepts[concept_id] = {
                "mastery": float(mastery),
                "confidence": float(inference.get("confidence", mastery) or mastery),
                "attempts": int(attempts_by_concept.get(concept_id, 0)),
                "last_correct": last_correct_by_concept.get(concept_id),
                "source": inference.get("source"),
                "kt_source": inference.get("kt_source") or inference.get("source"),
            }

        state = {
            "schema_version": "kt_v2",
            "learner_id": str(learner_id),
            "updated_at": updated_at,
            "source": inference.get("source"),
            "kt_source": inference.get("kt_source") or inference.get("source"),
            "model_used": bool(inference.get("model_used")),
            "fallback_used": bool(inference.get("fallback_used")),
            "sequence_length": int(inference.get("sequence_length", len(interactions)) or 0),
            "predicted_mastery_last": float(inference.get("predicted_mastery_last", 0.0) or 0.0),
            "concepts": concepts,
            "model_path": inference.get("model_path"),
            "id_map_path": inference.get("id_map_path"),
            "inference_error": inference.get("inference_error") or inference.get("error"),
            "fallback_reason": inference.get("inference_error") or inference.get("error") if inference.get("fallback_used") else None,
        }
        latest_concept_id = str(interactions[-1]["concept_id"]) if interactions else None
        mastery_after = float(inference.get("predicted_mastery_last", 0.0) or 0.0)
        prior_values = [
            float(item.get("correct", 0.0) or 0.0)
            for item in interactions[:-1]
        ]
        mastery_before = sum(prior_values) / len(prior_values) if prior_values else 0.0

        conn.execute(
            """
            INSERT INTO knowledge_state(student_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id)
            DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at
            """,
            (
                learner_id,
                json.dumps(state),
                updated_at,
            ),
        )
        conn.commit()

        return {
            "status": "success",
            "learner_id": learner_id,
            "data": {
                "sequence_length": state["sequence_length"],
                "concept_id": latest_concept_id,
                "mastery_before": round(mastery_before, 4),
                "mastery_after": mastery_after,
                "predicted_mastery_last": state["predicted_mastery_last"],
                "written_state": written_state,
                "schema_version": "kt_v2",
                "source": inference.get("source"),
                "kt_source": inference.get("kt_source") or inference.get("source"),
                "model_used": bool(inference.get("model_used")),
                "fallback_used": bool(inference.get("fallback_used")),
                "fallback_reason": state["fallback_reason"],
                "state_json": state,
                "model_path": inference.get("model_path"),
                "id_map_path": inference.get("id_map_path"),
                "inference_error": inference.get("inference_error") or inference.get("error"),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "module": "knowledge_state",
            "error": str(e),
        }
