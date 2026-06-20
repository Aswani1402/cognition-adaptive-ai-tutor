from __future__ import annotations

import sqlite3
from datetime import date
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


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class DailyGoalEngine:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def update_goal(
        self,
        learner_id: str,
        goal_date: str | None = None,
        target_xp: int = 20,
        target_questions: int = 3,
        target_revision_cards: int = 1,
        completion_threshold: float = 0.8,
    ) -> dict[str, Any]:
        from scripts.migration.add_badge_goal_unlock_tables import run_migration

        run_migration(self.db_path)
        goal_date = goal_date or date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            earned_xp = self._earned_xp(conn, learner_id, goal_date)
            completed_questions = self._completed_questions(conn, learner_id, goal_date)
            completed_revision_cards = self._completed_revision_cards(conn, learner_id, goal_date)
            xp_progress = _clamp(earned_xp / max(1, target_xp))
            question_progress = _clamp(completed_questions / max(1, target_questions))
            revision_progress = _clamp(completed_revision_cards / max(1, target_revision_cards))
            completion_rate = round(
                0.40 * xp_progress + 0.35 * question_progress + 0.25 * revision_progress,
                6,
            )
            goal_completed = completion_rate >= _clamp(completion_threshold)
            conn.execute(
                """
                INSERT INTO daily_goal_state (
                    learner_id, goal_date, target_xp, earned_xp,
                    target_questions, completed_questions,
                    target_revision_cards, completed_revision_cards,
                    goal_completed, completion_rate, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(learner_id, goal_date) DO UPDATE SET
                    target_xp = excluded.target_xp,
                    earned_xp = excluded.earned_xp,
                    target_questions = excluded.target_questions,
                    completed_questions = excluded.completed_questions,
                    target_revision_cards = excluded.target_revision_cards,
                    completed_revision_cards = excluded.completed_revision_cards,
                    goal_completed = excluded.goal_completed,
                    completion_rate = excluded.completion_rate,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    learner_id,
                    goal_date,
                    target_xp,
                    earned_xp,
                    target_questions,
                    completed_questions,
                    target_revision_cards,
                    completed_revision_cards,
                    1 if goal_completed else 0,
                    completion_rate,
                ),
            )
            conn.commit()
            return {
                "status": "success",
                "module": "DailyGoalEngine",
                "learner_id": learner_id,
                "goal_date": goal_date,
                "completion_rate": completion_rate,
                "goal_completed": goal_completed,
                "components": {
                    "daily_xp_progress": xp_progress,
                    "question_completion_progress": question_progress,
                    "revision_completion_progress": revision_progress,
                    "earned_xp": earned_xp,
                    "completed_questions": completed_questions,
                    "completed_revision_cards": completed_revision_cards,
                    "target_xp": target_xp,
                    "target_questions": target_questions,
                    "target_revision_cards": target_revision_cards,
                },
            }
        except Exception as exc:
            return {
                "status": "warning",
                "module": "DailyGoalEngine",
                "learner_id": learner_id,
                "goal_date": goal_date,
                "completion_rate": 0.0,
                "goal_completed": False,
                "components": {},
                "reason": f"{type(exc).__name__}: {exc}",
            }
        finally:
            conn.close()

    def _earned_xp(self, conn: sqlite3.Connection, learner_id: str, goal_date: str) -> int:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(xp_awarded), 0)
            FROM reward_event_log
            WHERE learner_id = ? AND substr(COALESCE(created_at, ''), 1, 10) = ?
            """,
            (learner_id, goal_date),
        ).fetchone()
        return _safe_int(row[0] if row else 0)

    def _completed_questions(self, conn: sqlite3.Connection, learner_id: str, goal_date: str) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM quiz_results
            WHERE learner_id = ? AND substr(COALESCE(timestamp, ''), 1, 10) = ?
            """,
            (learner_id, goal_date),
        ).fetchone()
        return _safe_int(row[0] if row else 0)

    def _completed_revision_cards(self, conn: sqlite3.Connection, learner_id: str, goal_date: str) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM revision_attempt_log
            WHERE learner_id = ? AND substr(COALESCE(attempted_at, ''), 1, 10) = ?
            """,
            (learner_id, goal_date),
        ).fetchone()
        return _safe_int(row[0] if row else 0)
