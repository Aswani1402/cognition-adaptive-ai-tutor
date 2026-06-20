"""
ViewPerformanceTracker

Purpose:
- Track which teaching view works best for each learner.
- Convert teaching-view outcome into reward.
- Store/view performance evidence for later RL policy upgrade.

This upgrades the tutor from:
    adaptive difficulty only
to:
    adaptive difficulty + adaptive teaching representation
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


DEFAULT_DB_PATH = Path("external/core_data/tutor.db")


class ViewPerformanceTracker:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._ensure_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_table(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS view_performance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learner_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    teaching_view TEXT NOT NULL,
                    difficulty TEXT,
                    assessment_score REAL,
                    time_taken REAL,
                    hint_usage INTEGER,
                    engagement_score REAL,
                    mastery_before REAL,
                    mastery_after REAL,
                    reward REAL,
                    outcome_label TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    def log_view_result(
        self,
        learner_id: str | int,
        concept_id: str,
        teaching_view: str,
        difficulty: str = "medium",
        assessment_score: Optional[float] = None,
        time_taken: Optional[float] = None,
        hint_usage: Optional[int] = None,
        engagement_score: Optional[float] = None,
        mastery_before: Optional[float] = None,
        mastery_after: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reward = self.compute_reward(
            assessment_score=assessment_score,
            time_taken=time_taken,
            hint_usage=hint_usage,
            engagement_score=engagement_score,
            mastery_before=mastery_before,
            mastery_after=mastery_after,
        )

        outcome_label = self._label_outcome(reward)

        row = {
            "learner_id": str(learner_id),
            "concept_id": str(concept_id),
            "teaching_view": teaching_view,
            "difficulty": difficulty,
            "assessment_score": assessment_score,
            "time_taken": time_taken,
            "hint_usage": hint_usage,
            "engagement_score": engagement_score,
            "mastery_before": mastery_before,
            "mastery_after": mastery_after,
            "reward": reward,
            "outcome_label": outcome_label,
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
            "created_at": datetime.utcnow().isoformat(),
        }

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO view_performance_log (
                    learner_id,
                    concept_id,
                    teaching_view,
                    difficulty,
                    assessment_score,
                    time_taken,
                    hint_usage,
                    engagement_score,
                    mastery_before,
                    mastery_after,
                    reward,
                    outcome_label,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["learner_id"],
                    row["concept_id"],
                    row["teaching_view"],
                    row["difficulty"],
                    row["assessment_score"],
                    row["time_taken"],
                    row["hint_usage"],
                    row["engagement_score"],
                    row["mastery_before"],
                    row["mastery_after"],
                    row["reward"],
                    row["outcome_label"],
                    row["metadata_json"],
                    row["created_at"],
                ),
            )

            conn.commit()
            row["id"] = cursor.lastrowid

        return {
            "status": "success",
            "module": "ViewPerformanceTracker",
            "logged": row,
        }

    def compute_reward(
        self,
        assessment_score: Optional[float],
        time_taken: Optional[float],
        hint_usage: Optional[int],
        engagement_score: Optional[float],
        mastery_before: Optional[float],
        mastery_after: Optional[float],
    ) -> float:
        """
        Reward design:
        - assessment score is strongest signal
        - mastery gain is very important
        - engagement helps
        - too many hints reduce confidence slightly
        - very high time can slightly reduce reward

        This is a baseline reward function.
        Later RL can learn better reward/action value from logs.
        """

        score = self._safe_float(assessment_score, default=0.5)
        engagement = self._safe_float(engagement_score, default=0.5)

        before = self._safe_float(mastery_before, default=None)
        after = self._safe_float(mastery_after, default=None)

        if before is not None and after is not None:
            mastery_gain = max(0.0, after - before)
        else:
            mastery_gain = 0.0

        hints = self._safe_float(hint_usage, default=0.0)
        time_value = self._safe_float(time_taken, default=0.0)

        hint_penalty = min(hints * 0.04, 0.20)

        if time_value <= 0:
            time_penalty = 0.0
        elif time_value > 300:
            time_penalty = 0.10
        elif time_value > 180:
            time_penalty = 0.05
        else:
            time_penalty = 0.0

        reward = (
            0.55 * score
            + 0.25 * mastery_gain
            + 0.20 * engagement
            - hint_penalty
            - time_penalty
        )

        return round(max(0.0, min(1.0, reward)), 4)

    def get_best_view_for_learner(
        self,
        learner_id: str | int,
        concept_id: Optional[str] = None,
        min_attempts: int = 1,
    ) -> Dict[str, Any]:
        """
        Return best teaching view based on average reward.
        Can be concept-specific or learner-wide.
        """

        query = """
            SELECT teaching_view, COUNT(*) as attempts, AVG(reward) as avg_reward
            FROM view_performance_log
            WHERE learner_id = ?
        """

        params: List[Any] = [str(learner_id)]

        if concept_id:
            query += " AND concept_id = ?"
            params.append(str(concept_id))

        query += """
            GROUP BY teaching_view
            HAVING attempts >= ?
            ORDER BY avg_reward DESC, attempts DESC
            LIMIT 1
        """
        params.append(min_attempts)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()

        if not row:
            return {
                "status": "no_data",
                "module": "ViewPerformanceTracker",
                "learner_id": str(learner_id),
                "concept_id": concept_id,
                "best_view": None,
                "message": "No view performance data found yet.",
            }

        teaching_view, attempts, avg_reward = row

        return {
            "status": "success",
            "module": "ViewPerformanceTracker",
            "learner_id": str(learner_id),
            "concept_id": concept_id,
            "best_view": teaching_view,
            "attempts": attempts,
            "avg_reward": round(float(avg_reward), 4),
        }

    def get_view_summary(
        self,
        learner_id: str | int,
        limit: int = 20,
    ) -> Dict[str, Any]:
        query = """
            SELECT
                teaching_view,
                COUNT(*) as attempts,
                AVG(reward) as avg_reward,
                MAX(created_at) as last_used
            FROM view_performance_log
            WHERE learner_id = ?
            GROUP BY teaching_view
            ORDER BY avg_reward DESC, attempts DESC
            LIMIT ?
        """

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(learner_id), limit))
            rows = cursor.fetchall()

        summary = [
            {
                "teaching_view": row[0],
                "attempts": row[1],
                "avg_reward": round(float(row[2]), 4) if row[2] is not None else None,
                "last_used": row[3],
            }
            for row in rows
        ]

        return {
            "status": "success",
            "module": "ViewPerformanceTracker",
            "learner_id": str(learner_id),
            "summary": summary,
        }

    def _label_outcome(self, reward: float) -> str:
        if reward >= 0.75:
            return "high_success"
        if reward >= 0.50:
            return "moderate_success"
        if reward >= 0.30:
            return "weak_success"
        return "poor_success"

    def _safe_float(self, value: Any, default: Optional[float]) -> Optional[float]:
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default