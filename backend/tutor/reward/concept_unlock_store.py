from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: Any) -> float:
    return max(0.0, min(1.0, _safe_float(value, 0.0)))


class ConceptUnlockStore:
    def __init__(self, db_path: Path | str = DB_PATH, unlock_threshold: float = 0.65) -> None:
        self.db_path = Path(db_path)
        self.unlock_threshold = unlock_threshold

    def update_unlock_state(
        self,
        learner_id: str,
        concept_id: str,
        domain: str | None = None,
        concept_name: str | None = None,
        mastery_score: float = 0.0,
        promotion_confidence: float = 0.0,
        prerequisites_met: bool = False,
        fused_score: float = 0.0,
        review_due: bool = False,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from scripts.migration.add_badge_goal_unlock_tables import run_migration

        run_migration(self.db_path)
        mastery_score = _clamp(mastery_score)
        promotion_confidence = _clamp(promotion_confidence)
        fused_score = _clamp(fused_score)
        prerequisites_score = 1.0 if prerequisites_met else 0.0
        unlock_score = round(
            0.45 * mastery_score
            + 0.30 * promotion_confidence
            + 0.15 * fused_score
            + 0.10 * prerequisites_score,
            6,
        )
        unlock_allowed = prerequisites_met and unlock_score >= self.unlock_threshold
        if unlock_allowed:
            unlock_status = "unlocked"
            locked_reason = None
        elif review_due:
            unlock_status = "review"
            locked_reason = "Review is due before moving ahead."
        elif prerequisites_met:
            unlock_status = "recommended"
            locked_reason = "Prerequisites are met, but weighted unlock score is below threshold."
        else:
            unlock_status = "locked"
            locked_reason = "Prerequisites are not met."

        evidence_payload = {
            **(evidence or {}),
            "mastery_score": mastery_score,
            "promotion_confidence": promotion_confidence,
            "fused_score": fused_score,
            "prerequisites_met": prerequisites_met,
            "unlock_score": unlock_score,
            "unlock_threshold": self.unlock_threshold,
            "threshold_note": "unlock_score = 0.45*mastery + 0.30*promotion_confidence + 0.15*fused_score + 0.10*prerequisites_met_score; default threshold 0.65.",
            "parameter_sensitivity_reference": "evaluation_outputs/reports/parameter_sensitivity_report.md",
        }
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO concept_unlock_state (
                    learner_id, concept_id, domain, concept_name, unlock_status,
                    mastery_score, promotion_confidence, prerequisites_met,
                    unlocked_at, locked_reason, evidence_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? = 'unlocked' THEN CURRENT_TIMESTAMP ELSE NULL END, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(learner_id, concept_id) DO UPDATE SET
                    domain = excluded.domain,
                    concept_name = excluded.concept_name,
                    unlock_status = excluded.unlock_status,
                    mastery_score = excluded.mastery_score,
                    promotion_confidence = excluded.promotion_confidence,
                    prerequisites_met = excluded.prerequisites_met,
                    unlocked_at = CASE
                        WHEN excluded.unlock_status = 'unlocked' AND concept_unlock_state.unlocked_at IS NULL
                        THEN CURRENT_TIMESTAMP
                        ELSE concept_unlock_state.unlocked_at
                    END,
                    locked_reason = excluded.locked_reason,
                    evidence_json = excluded.evidence_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    learner_id,
                    concept_id,
                    domain,
                    concept_name,
                    unlock_status,
                    mastery_score,
                    promotion_confidence,
                    1 if prerequisites_met else 0,
                    unlock_status,
                    locked_reason,
                    json.dumps(evidence_payload, default=str),
                ),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT unlock_status, unlocked_at, locked_reason
                FROM concept_unlock_state
                WHERE learner_id = ? AND concept_id = ?
                """,
                (learner_id, concept_id),
            ).fetchone()
            return {
                "status": "success",
                "module": "ConceptUnlockStore",
                "learner_id": learner_id,
                "concept_id": concept_id,
                "unlock_status": row[0] if row else unlock_status,
                "unlock_score": unlock_score,
                "evidence": evidence_payload,
                "reason": row[2] if row and row[2] else "Unlock criteria met.",
                "unlocked_at": row[1] if row else None,
            }
        except Exception as exc:
            return {
                "status": "warning",
                "module": "ConceptUnlockStore",
                "learner_id": learner_id,
                "concept_id": concept_id,
                "unlock_status": "locked",
                "unlock_score": unlock_score,
                "evidence": evidence_payload,
                "reason": f"{type(exc).__name__}: {exc}",
            }
        finally:
            conn.close()
