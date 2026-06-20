"""
LearnerNotebookMemory

Purpose:
- NotebookLM-style learner memory for the tutor.
- Stores learner mistakes, weak assessment types, weak concepts,
  revision notes, view performance signals, XAI signals, mistake analysis,
  and next practice queue.
- This is not frontend memory. This is backend learning memory.

Current role:
    evaluation_output + reflection_output + learner_insight_output
    + view_performance + xai + mistake_analysis
    -> notebook_summary + mistake_patterns + revision_plan + next_practice_queue
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = Path("external/core_data/tutor.db")


class LearnerNotebookMemory:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS learner_notebook_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learner_id TEXT NOT NULL,
                    concept_id TEXT,
                    concept_name TEXT,
                    notebook_summary TEXT,
                    mistake_patterns_json TEXT,
                    weak_assessment_types_json TEXT,
                    strengths_json TEXT,
                    revision_plan_json TEXT,
                    next_practice_queue_json TEXT,
                    view_memory_json TEXT,
                    xai_summary_json TEXT,
                    source_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_learner_notebook_memory_learner
                ON learner_notebook_memory (learner_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_learner_notebook_memory_concept
                ON learner_notebook_memory (concept_id)
                """
            )

            conn.commit()

    def update_memory(
        self,
        learner_id: str | int,
        concept_id: str,
        concept_name: str,
        evaluation_output: Dict[str, Any],
        reflection_output: Optional[Dict[str, Any]] = None,
        learner_insight_output: Optional[Dict[str, Any]] = None,
        view_performance_output: Optional[Dict[str, Any]] = None,
        xai_output: Optional[Dict[str, Any]] = None,
        mistake_analysis_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reflection_output = reflection_output or {}
        learner_insight_output = learner_insight_output or {}
        view_performance_output = view_performance_output or {}
        xai_output = xai_output or {}
        mistake_analysis_output = mistake_analysis_output or {}

        dominant_mistake_type = mistake_analysis_output.get("dominant_mistake_type")
        mistake_type_counts = mistake_analysis_output.get("mistake_type_counts", {})
        high_severity_mistake_count = mistake_analysis_output.get(
            "high_severity_count", 0
        )
        classified_mistakes = mistake_analysis_output.get("classified_mistakes", [])

        weak_assessment_types = self._extract_weak_assessment_types(evaluation_output)
        strengths = self._extract_strengths(evaluation_output)
        mistake_patterns = self._build_mistake_patterns(evaluation_output)

        reflection = reflection_output.get("reflection", {})
        learner_profile = learner_insight_output.get("learner_profile_live", {})

        diagnosis = (
            reflection.get("diagnosis")
            or learner_profile.get("learning_pattern")
            or "Learner performance was analyzed from the latest session."
        )

        recommended_focus = (
            learner_profile.get("recommended_focus")
            or reflection.get("what_next")
            or self._default_focus(weak_assessment_types)
        )

        view_memory = self._extract_view_memory(view_performance_output)
        xai_summary = self._extract_xai_summary(xai_output)

        mistake_focus = self._extract_mistake_focus(classified_mistakes)

        if not dominant_mistake_type:
            dominant_mistake_type = learner_profile.get(
                "dominant_mistake_type"
            ) or reflection.get("dominant_mistake_type")

        if not mistake_type_counts:
            mistake_type_counts = learner_profile.get(
                "mistake_type_counts", {}
            ) or reflection.get("mistake_type_counts", {})

        if not high_severity_mistake_count:
            high_severity_mistake_count = (
                learner_profile.get("high_severity_mistake_count")
                or reflection.get("high_severity_mistake_count")
                or reflection.get("high_severity_mistake_count", 0)
            )

        if not mistake_focus:
            mistake_focus = (
                learner_profile.get("mistake_focus", [])
                or reflection.get("mistake_focus", [])
            )

        revision_plan = self._build_revision_plan(
            concept_id=concept_id,
            concept_name=concept_name,
            weak_assessment_types=weak_assessment_types,
            mistake_patterns=mistake_patterns,
            recommended_focus=recommended_focus,
            dominant_mistake_type=dominant_mistake_type,
            mistake_focus=mistake_focus,
        )

        next_practice_queue = self._build_next_practice_queue(
            concept_id=concept_id,
            weak_assessment_types=weak_assessment_types,
            mistake_focus=mistake_focus,
        )

        notebook_summary = self._build_notebook_summary(
            concept_name=concept_name,
            diagnosis=diagnosis,
            weak_assessment_types=weak_assessment_types,
            strengths=strengths,
            recommended_focus=recommended_focus,
            view_memory=view_memory,
            xai_summary=xai_summary,
            dominant_mistake_type=dominant_mistake_type,
            high_severity_mistake_count=high_severity_mistake_count,
            mistake_focus=mistake_focus,
        )

        source_payload = {
            "evaluation_verdict": evaluation_output.get("verdict"),
            "evaluation_score": evaluation_output.get("overall_score"),
            "reflection_status": reflection_output.get("status"),
            "xai_status": xai_output.get("status"),
            "mistake_analysis_status": mistake_analysis_output.get("status"),
            "dominant_mistake_type": dominant_mistake_type,
            "mistake_type_counts": mistake_type_counts,
            "high_severity_mistake_count": high_severity_mistake_count,
            "mistake_focus": mistake_focus,
        }

        row = {
            "learner_id": str(learner_id),
            "concept_id": str(concept_id),
            "concept_name": concept_name,
            "notebook_summary": notebook_summary,
            "mistake_patterns_json": json.dumps(mistake_patterns, ensure_ascii=False),
            "weak_assessment_types_json": json.dumps(
                weak_assessment_types, ensure_ascii=False
            ),
            "strengths_json": json.dumps(strengths, ensure_ascii=False),
            "revision_plan_json": json.dumps(revision_plan, ensure_ascii=False),
            "next_practice_queue_json": json.dumps(
                next_practice_queue, ensure_ascii=False
            ),
            "view_memory_json": json.dumps(view_memory, ensure_ascii=False),
            "xai_summary_json": json.dumps(xai_summary, ensure_ascii=False),
            "source_json": json.dumps(source_payload, ensure_ascii=False),
            "created_at": self._now(),
        }

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learner_notebook_memory (
                    learner_id,
                    concept_id,
                    concept_name,
                    notebook_summary,
                    mistake_patterns_json,
                    weak_assessment_types_json,
                    strengths_json,
                    revision_plan_json,
                    next_practice_queue_json,
                    view_memory_json,
                    xai_summary_json,
                    source_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["learner_id"],
                    row["concept_id"],
                    row["concept_name"],
                    row["notebook_summary"],
                    row["mistake_patterns_json"],
                    row["weak_assessment_types_json"],
                    row["strengths_json"],
                    row["revision_plan_json"],
                    row["next_practice_queue_json"],
                    row["view_memory_json"],
                    row["xai_summary_json"],
                    row["source_json"],
                    row["created_at"],
                ),
            )

            conn.commit()
            memory_id = cursor.lastrowid

        return {
            "status": "success",
            "module": "LearnerNotebookMemory",
            "memory_id": memory_id,
            "learner_id": str(learner_id),
            "concept_id": str(concept_id),
            "concept_name": concept_name,
            "notebook_summary": notebook_summary,
            "mistake_patterns": mistake_patterns,
            "weak_assessment_types": weak_assessment_types,
            "strengths": strengths,
            "revision_plan": revision_plan,
            "next_practice_queue": next_practice_queue,
            "view_memory": view_memory,
            "xai_summary": xai_summary,
            "dominant_mistake_type": dominant_mistake_type,
            "mistake_type_counts": mistake_type_counts,
            "high_severity_mistake_count": high_severity_mistake_count,
            "mistake_focus": mistake_focus,
            "source": source_payload,
        }

    def get_latest_memory(
        self,
        learner_id: str | int,
        limit: int = 5,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    concept_id,
                    concept_name,
                    notebook_summary,
                    mistake_patterns_json,
                    weak_assessment_types_json,
                    strengths_json,
                    revision_plan_json,
                    next_practice_queue_json,
                    view_memory_json,
                    xai_summary_json,
                    source_json,
                    created_at
                FROM learner_notebook_memory
                WHERE learner_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(learner_id), limit),
            )

            rows = cursor.fetchall()

        memories = []

        for row in rows:
            source = self._loads(row[11], {})

            memories.append(
                {
                    "id": row[0],
                    "concept_id": row[1],
                    "concept_name": row[2],
                    "notebook_summary": row[3],
                    "mistake_patterns": self._loads(row[4], []),
                    "weak_assessment_types": self._loads(row[5], []),
                    "strengths": self._loads(row[6], []),
                    "revision_plan": self._loads(row[7], []),
                    "next_practice_queue": self._loads(row[8], []),
                    "view_memory": self._loads(row[9], {}),
                    "xai_summary": self._loads(row[10], {}),
                    "source": source,
                    "dominant_mistake_type": source.get("dominant_mistake_type"),
                    "mistake_type_counts": source.get("mistake_type_counts", {}),
                    "high_severity_mistake_count": source.get(
                        "high_severity_mistake_count"
                    ),
                    "mistake_focus": source.get("mistake_focus", []),
                    "created_at": row[12],
                }
            )

        return {
            "status": "success",
            "module": "LearnerNotebookMemory",
            "learner_id": str(learner_id),
            "memory_count": len(memories),
            "memories": memories,
        }

    def _extract_weak_assessment_types(
        self,
        evaluation_output: Dict[str, Any],
    ) -> List[str]:
        weak = []

        for item in evaluation_output.get("results", []):
            if not isinstance(item, dict):
                continue

            score = self._safe_float(item.get("score"), 0.0)
            assessment_type = item.get("assessment_type")

            if assessment_type and score < 0.75:
                weak.append(str(assessment_type))

        return self._unique(weak)

    def _extract_strengths(
        self,
        evaluation_output: Dict[str, Any],
    ) -> List[str]:
        strengths = []

        for item in evaluation_output.get("results", []):
            if not isinstance(item, dict):
                continue

            score = self._safe_float(item.get("score"), 0.0)
            assessment_type = item.get("assessment_type")

            if assessment_type and score >= 0.75:
                strengths.append(str(assessment_type))

        return self._unique(strengths)

    def _build_mistake_patterns(
        self,
        evaluation_output: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        patterns = []

        for item in evaluation_output.get("results", []):
            if not isinstance(item, dict):
                continue

            score = self._safe_float(item.get("score"), 0.0)

            if score >= 0.75:
                continue

            patterns.append(
                {
                    "assessment_type": item.get("assessment_type"),
                    "prompt": item.get("prompt"),
                    "learner_answer": item.get("learner_answer"),
                    "expected_answer": item.get("expected_answer"),
                    "feedback": item.get("feedback"),
                    "score": score,
                }
            )

        return patterns

    def _extract_mistake_focus(
        self,
        classified_mistakes: List[Dict[str, Any]],
    ) -> List[str]:
        mistake_focus = []

        for item in classified_mistakes:
            if not isinstance(item, dict):
                continue

            assessment_type = item.get("assessment_type")
            mistake_type = item.get("mistake_type")
            severity = item.get("severity")

            if severity in {"medium", "high"} and assessment_type and mistake_type:
                mistake_focus.append(f"{assessment_type}:{mistake_type}")

        return self._unique(mistake_focus)

    def _extract_view_memory(
        self,
        view_performance_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        logged = view_performance_output.get("logged", {})

        return {
            "teaching_view": logged.get("teaching_view"),
            "reward": logged.get("reward"),
            "outcome_label": logged.get("outcome_label"),
            "difficulty": logged.get("difficulty"),
        }

    def _extract_xai_summary(
        self,
        xai_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = xai_output.get("data", {})
        evidence = data.get("evidence", {})
        feature_contributions = evidence.get("feature_contributions", {})

        return {
            "decision_pressure_label": feature_contributions.get(
                "decision_pressure_label"
            ),
            "total_decision_pressure": feature_contributions.get(
                "total_decision_pressure"
            ),
            "top_factors": [
                factor.get("feature")
                for factor in feature_contributions.get("top_factors", [])
                if isinstance(factor, dict)
            ],
            "reason": data.get("reason"),
        }

    def _build_revision_plan(
        self,
        concept_id: str,
        concept_name: str,
        weak_assessment_types: List[str],
        mistake_patterns: List[Dict[str, Any]],
        recommended_focus: str,
        dominant_mistake_type: str | None = None,
        mistake_focus: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        plan = []
        mistake_focus = mistake_focus or []

        if "output_prediction" in weak_assessment_types:
            plan.append(
                {
                    "task_type": "code_tracing",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Practice predicting exact program output.",
                }
            )

        if "debug" in weak_assessment_types:
            plan.append(
                {
                    "task_type": "debug_practice",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Identify syntax/logic mistakes and explain the fix.",
                }
            )

        if "explanation" in weak_assessment_types:
            plan.append(
                {
                    "task_type": "short_explanation",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Explain the concept clearly using key points.",
                }
            )

        if "transfer" in weak_assessment_types:
            plan.append(
                {
                    "task_type": "transfer_practice",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Apply the concept in a real-world or unfamiliar context.",
                }
            )

        if dominant_mistake_type == "wrong_output":
            plan.append(
                {
                    "task_type": "mistake_review",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Review wrong output predictions using line-by-line tracing.",
                    "mistake_type": dominant_mistake_type,
                    "mistake_focus": mistake_focus,
                }
            )

        elif dominant_mistake_type == "syntax_misunderstanding":
            plan.append(
                {
                    "task_type": "syntax_review",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Review syntax rules and fix quote/assignment mistakes.",
                    "mistake_type": dominant_mistake_type,
                    "mistake_focus": mistake_focus,
                }
            )

        elif dominant_mistake_type == "debug_misdiagnosis":
            plan.append(
                {
                    "task_type": "debug_diagnosis_review",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Practice identifying the actual bug before suggesting a fix.",
                    "mistake_type": dominant_mistake_type,
                    "mistake_focus": mistake_focus,
                }
            )

        elif dominant_mistake_type == "low_confidence":
            plan.append(
                {
                    "task_type": "confidence_practice",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": "Use short guided checks to build confidence.",
                    "mistake_type": dominant_mistake_type,
                    "mistake_focus": mistake_focus,
                }
            )

        if not plan:
            plan.append(
                {
                    "task_type": "light_review",
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "goal": recommended_focus,
                }
            )

        return plan

    def _build_next_practice_queue(
        self,
        concept_id: str,
        weak_assessment_types: List[str],
        mistake_focus: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        mistake_focus = mistake_focus or []

        if not weak_assessment_types and not mistake_focus:
            return [
                {
                    "concept_id": concept_id,
                    "practice_type": "mixed_review",
                    "priority": "low",
                }
            ]

        queue = []

        for weak_type in weak_assessment_types:
            priority = "high" if weak_type in {"debug", "output_prediction"} else "medium"

            queue.append(
                {
                    "concept_id": concept_id,
                    "practice_type": weak_type,
                    "priority": priority,
                }
            )

        for focus in mistake_focus:
            if ":" not in focus:
                continue

            assessment_type, mistake_type = focus.split(":", 1)

            queue.append(
                {
                    "concept_id": concept_id,
                    "practice_type": assessment_type,
                    "mistake_type": mistake_type,
                    "priority": "high",
                }
            )

        return queue

    def _build_notebook_summary(
        self,
        concept_name: str,
        diagnosis: str,
        weak_assessment_types: List[str],
        strengths: List[str],
        recommended_focus: str,
        view_memory: Dict[str, Any],
        xai_summary: Dict[str, Any],
        dominant_mistake_type: str | None = None,
        high_severity_mistake_count: int | None = None,
        mistake_focus: Optional[List[str]] = None,
    ) -> str:
        weak_text = ", ".join(weak_assessment_types) if weak_assessment_types else "none"
        strength_text = ", ".join(strengths) if strengths else "none"
        focus_text = str(recommended_focus or "").strip().rstrip(".")
        mistake_focus = mistake_focus or []

        view_text = ""
        if view_memory.get("teaching_view"):
            view_text = (
                f" Teaching view used: {view_memory.get('teaching_view')} "
                f"with reward {view_memory.get('reward')}."
            )

        xai_text = ""
        if xai_summary.get("top_factors"):
            xai_text = (
                f" Main decision factors: {', '.join(xai_summary.get('top_factors'))}."
            )

        mistake_text = ""
        if dominant_mistake_type:
            mistake_text += (
                f" Dominant mistake type: {dominant_mistake_type}."
            )

        if high_severity_mistake_count is not None:
            mistake_text += (
                f" High severity mistakes: {high_severity_mistake_count}."
            )

        if mistake_focus:
            mistake_text += (
                f" Mistake focus: {', '.join(mistake_focus[:4])}."
            )

        return (
            f"For {concept_name}, {diagnosis} "
            f"Strengths: {strength_text}. "
            f"Weak areas: {weak_text}. "
            f"Recommended focus: {focus_text}."
            f"{view_text}"
            f"{xai_text}"
            f"{mistake_text}"
        )

    def _default_focus(self, weak_assessment_types: List[str]) -> str:
        if "debug" in weak_assessment_types or "output_prediction" in weak_assessment_types:
            return "Practice code tracing and debugging."

        if "explanation" in weak_assessment_types:
            return "Practice explaining the concept using key points."

        if "transfer" in weak_assessment_types:
            return "Practice applying the concept in new contexts."

        return "Continue light review and mixed practice."

    def _loads(self, value: str | None, default: Any) -> Any:
        if not value:
            return default

        try:
            return json.loads(value)
        except Exception:
            return default

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _unique(self, items: List[str]) -> List[str]:
        seen = set()
        output = []

        for item in items:
            key = str(item).lower()
            if key not in seen:
                output.append(item)
                seen.add(key)

        return output