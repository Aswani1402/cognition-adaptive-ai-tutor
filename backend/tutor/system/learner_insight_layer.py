from __future__ import annotations

from typing import Any


class LearnerInsightLayer:
    def build(
        self,
        evaluation: dict,
        reflection_output: dict,
        mistake_analysis_output: dict | None = None,
    ) -> dict:
        mistake_analysis_output = mistake_analysis_output or {}

        reflection = (
            reflection_output.get("reflection", {})
            if isinstance(reflection_output, dict)
            else {}
        )

        results = evaluation.get("results", []) if isinstance(evaluation, dict) else []

        strengths = []
        weaknesses = []

        for item in results:
            if not isinstance(item, dict):
                continue

            assessment_type = item.get("assessment_type")
            score = float(item.get("score", 0.0) or 0.0)

            if not assessment_type:
                continue

            if score >= 0.75:
                strengths.append(assessment_type)
            else:
                weaknesses.append(assessment_type)

        dominant_mistake_type = (
            mistake_analysis_output.get("dominant_mistake_type")
            or reflection.get("dominant_mistake_type")
        )

        mistake_type_counts = (
            mistake_analysis_output.get("mistake_type_counts")
            or reflection.get("mistake_type_counts")
            or {}
        )

        high_severity_count = (
            mistake_analysis_output.get("high_severity_count")
            or reflection.get("high_severity_mistake_count")
            or 0
        )

        classified_mistakes = mistake_analysis_output.get("classified_mistakes", [])
        mistake_focus = reflection.get("mistake_focus", [])

        if not mistake_focus:
            for item in classified_mistakes:
                if not isinstance(item, dict):
                    continue

                severity = item.get("severity")
                assessment_type = item.get("assessment_type")
                mistake_type = item.get("mistake_type")

                if severity in {"medium", "high"} and assessment_type and mistake_type:
                    mistake_focus.append(f"{assessment_type}:{mistake_type}")

        recommended_focus = reflection.get("what_next")

        if dominant_mistake_type == "wrong_output":
            recommended_focus = (
                "Focus on output prediction and code tracing practice."
            )
        elif dominant_mistake_type == "syntax_misunderstanding":
            recommended_focus = (
                "Focus on syntax correction, especially quotes, assignment, and valid code structure."
            )
        elif dominant_mistake_type == "debug_misdiagnosis":
            recommended_focus = (
                "Focus on debugging practice where the learner must identify the actual bug before fixing it."
            )
        elif dominant_mistake_type == "low_confidence":
            recommended_focus = (
                "Use confidence-building practice with hints, short checks, and positive feedback."
            )
        elif dominant_mistake_type == "concept_misconception":
            recommended_focus = (
                "Re-teach the misconception directly using misconception_view and short examples."
            )

        learner_profile_live = {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "learning_pattern": reflection.get("diagnosis"),
            "recommended_focus": recommended_focus,
            "dominant_mistake_type": dominant_mistake_type,
            "mistake_type_counts": mistake_type_counts,
            "high_severity_mistake_count": high_severity_count,
            "mistake_focus": mistake_focus,
        }

        return {
            "status": "success",
            "module": "LearnerInsightLayer",
            "learner_profile_live": learner_profile_live,
        }