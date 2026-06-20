from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return bool(row)


class BadgeEngine:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def evaluate_and_award(self, learner_id: str) -> dict[str, Any]:
        from scripts.migration.add_badge_goal_unlock_tables import run_migration

        run_migration(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            evidence = self._collect_evidence(conn, learner_id)
            badge_rows = conn.execute(
                "SELECT badge_id, badge_name, badge_type, description, criteria_json FROM achievement_badges"
            ).fetchall()
            existing_rows = conn.execute(
                """
                SELECT b.badge_id, b.badge_name, b.badge_type, lb.awarded_at, lb.evidence_json
                FROM learner_badges lb
                JOIN achievement_badges b ON b.badge_id = lb.badge_id
                WHERE lb.learner_id = ?
                ORDER BY lb.awarded_at
                """,
                (learner_id,),
            ).fetchall()
            existing_ids = {row["badge_id"] for row in existing_rows}
            new_badges = []
            for row in badge_rows:
                badge_id = row["badge_id"]
                if badge_id in existing_ids:
                    continue
                if self._criteria_met(badge_id, evidence):
                    payload = {
                        "badge_id": badge_id,
                        "badge_name": row["badge_name"],
                        "badge_type": row["badge_type"],
                        "description": row["description"],
                        "evidence": evidence,
                    }
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO learner_badges
                        (learner_id, badge_id, evidence_json)
                        VALUES (?, ?, ?)
                        """,
                        (learner_id, badge_id, json.dumps(evidence, default=str)),
                    )
                    new_badges.append(payload)
            conn.commit()
            existing_badges = [dict(row) for row in existing_rows]
            refreshed_count = conn.execute(
                "SELECT COUNT(*) FROM learner_badges WHERE learner_id = ?",
                (learner_id,),
            ).fetchone()[0]
            return {
                "status": "success",
                "module": "BadgeEngine",
                "learner_id": learner_id,
                "new_badges": new_badges,
                "existing_badges": existing_badges,
                "badge_count": int(refreshed_count),
                "evidence": evidence,
            }
        except Exception as exc:
            return {
                "status": "warning",
                "module": "BadgeEngine",
                "learner_id": learner_id,
                "new_badges": [],
                "existing_badges": [],
                "badge_count": 0,
                "evidence": {},
                "reason": f"{type(exc).__name__}: {exc}",
            }
        finally:
            conn.close()

    def _collect_evidence(self, conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
        reward_count = self._count(conn, "reward_event_log", "learner_id = ?", (learner_id,))
        total_xp = self._scalar(conn, "SELECT COALESCE(SUM(xp_awarded), 0) FROM reward_event_log WHERE learner_id = ?", (learner_id,))
        quiz_count = self._count(conn, "quiz_results", "learner_id = ?", (learner_id,))
        correct_quiz_count = self._count(conn, "quiz_results", "learner_id = ? AND is_correct = 1", (learner_id,))
        debug_count = self._activity_count(conn, learner_id, "debug")
        output_count = self._activity_count(conn, learner_id, "output_prediction")
        challenge_count = self._activity_count(conn, learner_id, "challenge")
        revision_count = self._count(conn, "revision_attempt_log", "learner_id = ? AND COALESCE(correct, 0) = 1", (learner_id,))
        current_streak = _safe_int(self._scalar(conn, "SELECT current_streak FROM learner_streak_state WHERE learner_id = ?", (learner_id,)))
        mastery_score = self._mastery_score(conn, learner_id)
        practice_events = reward_count + quiz_count
        return {
            "reward_event_count": reward_count,
            "total_xp": _safe_int(total_xp),
            "quiz_count": quiz_count,
            "correct_quiz_count": correct_quiz_count,
            "debug_activity_count": debug_count,
            "output_prediction_activity_count": output_count,
            "challenge_activity_count": challenge_count,
            "revision_completed_count": revision_count,
            "current_streak": current_streak,
            "mastery_score": mastery_score,
            "practice_event_count": practice_events,
        }

    def _criteria_met(self, badge_id: str, evidence: dict[str, Any]) -> bool:
        criteria = {
            "first_step": evidence["reward_event_count"] >= 1 or evidence["correct_quiz_count"] >= 1,
            "debug_detective": evidence["debug_activity_count"] >= 1,
            "output_predictor": evidence["output_prediction_activity_count"] >= 1,
            "revision_hero": evidence["revision_completed_count"] >= 1,
            "streak_starter": evidence["current_streak"] >= 2,
            "consistent_learner": evidence["practice_event_count"] >= 5,
            "concept_climber": evidence["mastery_score"] >= 0.65,
            "challenge_solver": evidence["challenge_activity_count"] >= 1,
        }
        return bool(criteria.get(badge_id, False))

    def _count(self, conn: sqlite3.Connection, table: str, where: str, params: tuple[Any, ...]) -> int:
        if not _table_exists(conn, table):
            return 0
        return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0])

    def _scalar(self, conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> Any:
        try:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _activity_count(self, conn: sqlite3.Connection, learner_id: str, activity: str) -> int:
        reward = self._count(
            conn,
            "reward_event_log",
            "learner_id = ? AND (LOWER(COALESCE(reward_reason, '')) LIKE ? OR LOWER(COALESCE(progression_action, '')) LIKE ?)",
            (learner_id, f"%{activity}%", f"%{activity}%"),
        )
        mistakes = self._count(
            conn,
            "learner_mistake_log",
            "learner_id = ? AND LOWER(COALESCE(task_type, '')) LIKE ?",
            (learner_id, f"%{activity}%"),
        )
        return reward + mistakes

    def _mastery_score(self, conn: sqlite3.Connection, learner_id: str) -> float:
        if not _table_exists(conn, "knowledge_state"):
            return 0.0
        row = conn.execute(
            "SELECT state_json FROM knowledge_state WHERE student_id = ?",
            (learner_id,),
        ).fetchone()
        if not row:
            return 0.0
        try:
            state = json.loads(row["state_json"])
            concepts = state.get("concepts", {})
            scores = [_safe_float(item.get("mastery")) for item in concepts.values() if isinstance(item, dict)]
            return round(max(scores) if scores else _safe_float(state.get("predicted_mastery_last")), 6)
        except Exception:
            return 0.0
