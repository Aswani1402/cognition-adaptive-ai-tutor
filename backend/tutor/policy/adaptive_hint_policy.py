from __future__ import annotations

"""
Deterministic evidence-scored adaptive hint selection.

For model-supported hint selection (comparison / fallback mode), see
:class:`tutor.policy.learned_hint_policy.LearnedHintPolicy`, which keeps this policy as the safe baseline.
"""

from typing import Any

from tutor.evaluation.hint_generator import HintGenerator


HINT_TYPES = {
    "small_hint",
    "guided_hint",
    "worked_example",
    "misconception_hint",
    "debug_hint",
    "output_prediction_hint",
    "syntax_hint",
    "next_step_hint",
}

EVIDENCE_FIELDS = [
    "learner_id",
    "concept_id",
    "concept_name",
    "question_type",
    "learner_answer",
    "expected_answer",
    "score",
    "evaluation_label",
    "mistake_type",
    "weakest_skill",
    "behaviour_risk",
    "mastery_score",
    "hint_count_used",
    "difficulty",
    "teaching_view",
    "key_points",
    "example",
]


class AdaptiveHintPolicy:
    """Transparent evidence-scored adaptive hint selector."""

    MODULE = "AdaptiveHintPolicy"
    FRONTEND_COMPONENT = "AdaptiveHintCard"

    def __init__(self, hint_generator: HintGenerator | None = None) -> None:
        self.hint_generator = hint_generator or HintGenerator()

    def select_hint(self, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        evidence = evidence or {}
        normalized, fallback_used = self._normalize_evidence(evidence)

        support_need = self._compute_support_need(normalized)
        hint_level = self._level_from_support_need(support_need)
        hint_type = self._base_hint_type(hint_level)
        hint_type, hint_level = self._apply_overrides(hint_type, hint_level, normalized, support_need)
        hint_text = self.hint_generator.generate(hint_type=hint_type, evidence=normalized)

        return {
            "status": "success",
            "module": self.MODULE,
            "hint_type": hint_type,
            "hint_level": hint_level,
            "hint_text": hint_text,
            "support_need": round(support_need, 6),
            "evidence": {
                "weakness_pressure": round(1.0 - normalized["score"], 6),
                "mastery_need": round(1.0 - normalized["mastery_score"], 6),
                "behaviour_pressure": round(normalized["behaviour_risk"], 6),
                "repeat_hint_pressure": round(min(normalized["hint_count_used"] / 3.0, 1.0), 6),
                "score": normalized["score"],
                "mastery_score": normalized["mastery_score"],
                "behaviour_risk": normalized["behaviour_risk"],
                "hint_count_used": normalized["hint_count_used"],
                "question_type": normalized.get("question_type"),
                "mistake_type": normalized.get("mistake_type"),
                "weakest_skill": normalized.get("weakest_skill"),
                "evaluation_label": normalized.get("evaluation_label"),
                "evidence_fields_used": EVIDENCE_FIELDS,
            },
            "frontend_component": self.FRONTEND_COMPONENT,
            "fallback_used": fallback_used,
        }

    def _normalize_evidence(self, evidence: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        normalized = {field: evidence.get(field) for field in EVIDENCE_FIELDS}
        missing_core = any(evidence.get(field) in (None, "") for field in ["score", "mastery_score", "behaviour_risk"])

        normalized["score"] = self._bounded_float(evidence.get("score"), 0.5)
        normalized["mastery_score"] = self._bounded_float(evidence.get("mastery_score"), 0.5)
        normalized["behaviour_risk"] = self._bounded_float(evidence.get("behaviour_risk"), 0.3)
        normalized["hint_count_used"] = max(0.0, self._float(evidence.get("hint_count_used"), 0.0))
        normalized["question_type"] = self._clean(evidence.get("question_type"), "general")
        normalized["mistake_type"] = self._clean(evidence.get("mistake_type"), "unknown")
        normalized["evaluation_label"] = self._clean(evidence.get("evaluation_label"), "unknown")
        normalized["concept_name"] = self._clean(evidence.get("concept_name"), "current concept")
        normalized["weakest_skill"] = self._clean(evidence.get("weakest_skill"), "current skill")
        normalized["difficulty"] = self._clean(evidence.get("difficulty"), "medium")
        normalized["teaching_view"] = self._clean(evidence.get("teaching_view"), "current view")
        return normalized, missing_core

    def _compute_support_need(self, evidence: dict[str, Any]) -> float:
        weakness_pressure = 1.0 - evidence["score"]
        mastery_need = 1.0 - evidence["mastery_score"]
        behaviour_pressure = evidence["behaviour_risk"]
        repeat_hint_pressure = min(evidence["hint_count_used"] / 3.0, 1.0)
        support_need = (
            0.40 * weakness_pressure
            + 0.25 * mastery_need
            + 0.20 * behaviour_pressure
            + 0.15 * repeat_hint_pressure
        )
        return max(0.0, min(1.0, support_need))

    def _level_from_support_need(self, support_need: float) -> str:
        if support_need < 0.35:
            return "small_hint"
        if support_need < 0.65:
            return "guided_hint"
        return "worked_example"

    def _base_hint_type(self, hint_level: str) -> str:
        return hint_level if hint_level in HINT_TYPES else "next_step_hint"

    def _apply_overrides(
        self,
        hint_type: str,
        hint_level: str,
        evidence: dict[str, Any],
        support_need: float,
    ) -> tuple[str, str]:
        question_type = str(evidence.get("question_type", "")).lower()
        mistake_type = str(evidence.get("mistake_type", "")).lower()
        hint_count = evidence["hint_count_used"]

        if hint_count >= 3 or support_need >= 0.78:
            return "worked_example", "worked_example"
        if "syntax_misunderstanding" in mistake_type or question_type == "syntax_completion":
            return "syntax_hint", hint_level
        if question_type in {"debug_task", "debug"} or "debug" in mistake_type:
            return "debug_hint", hint_level
        if question_type == "output_prediction" or "wrong_output" in mistake_type:
            return "output_prediction_hint", hint_level
        if "misconception" in mistake_type:
            return "misconception_hint", hint_level
        return hint_type, hint_level

    def _bounded_float(self, value: Any, default: float) -> float:
        return max(0.0, min(1.0, self._float(value, default)))

    def _float(self, value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    def _clean(self, value: Any, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default


def select_adaptive_hint(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return AdaptiveHintPolicy().select_hint(evidence)
