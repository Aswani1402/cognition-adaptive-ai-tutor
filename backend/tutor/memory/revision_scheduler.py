from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict


SUPPORTIVE_VIEWS = ["revision_view", "flashcard_view", "step_by_step_view"]
TARGETED_VIEWS = {
    "output_prediction": "output_prediction_view",
    "debug": "debug_view",
    "syntax_misunderstanding": "misconception_view",
    "wrong_output": "output_prediction_view",
    "debug_misdiagnosis": "debug_view",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "due"}
    return bool(value)


def _unique(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        clean = str(item).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        output.append(clean)
        seen.add(key)
    return output


def _priority_from_score(score: int) -> str:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _iso_after(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


class RevisionScheduler:
    """Transparent NotebookLM-style revision scheduler.

    The scheduler is intentionally deterministic and audit-friendly. It does
    not write to the database; it converts current learner evidence into a
    revision priority, spaced repetition plan, cards, and a frontend packet.
    """

    def build_revision_plan(self, evidence: dict[str, Any]) -> dict[str, Any]:
        learner_id = str(evidence.get("learner_id") or "")
        concept_id = str(evidence.get("concept_id") or "")
        concept_name = str(evidence.get("concept_name") or "current concept")
        domain = str(evidence.get("domain") or "")
        mastery_score = _safe_float(evidence.get("mastery_score"), 0.0)
        fused_score = _safe_float(evidence.get("fused_score"), 1.0)
        fused_label = str(evidence.get("fused_label") or "").lower()
        weakest_skill = str(evidence.get("weakest_skill") or "").lower()
        dominant_mistake_type = str(evidence.get("dominant_mistake_type") or "").lower()
        mistake_type_counts = evidence.get("mistake_type_counts") or {}
        behaviour_risk = _safe_float(evidence.get("behaviour_risk"), 0.0)
        behaviour_risk_label = str(evidence.get("behaviour_risk_label") or "").lower()
        review_due = _safe_bool(evidence.get("review_due"))
        recent_scores = evidence.get("recent_scores") or []

        priority_score = 0
        reasons: list[str] = []
        views: list[str] = []
        question_types: list[str] = []

        if review_due:
            priority_score += 2
            reasons.append("review is due from forgetting evidence")
            views.extend(["revision_view", "flashcard_view"])

        if fused_label == "needs_reteaching" or fused_score < 0.5:
            priority_score += 2
            reasons.append("evaluation fusion indicates reteaching or low performance")
            views.extend(["revision_view", "misconception_view"])
            question_types.extend(["mcq", "explanation_check"])

        if mastery_score < 0.4:
            priority_score += 2
            reasons.append("KT mastery is low")
            views.extend(["step_by_step_view", "definition_view", "revision_view"])
            question_types.extend(["mcq", "explanation_check"])
        elif mastery_score < 0.7:
            priority_score += 1
            reasons.append("KT mastery is partial and benefits from targeted practice")
            views.extend(["revision_view", "flashcard_view"])
            question_types.extend(["mcq"])
        else:
            reasons.append("KT mastery is strong enough for light review")
            views.extend(["flashcard_view"])

        if weakest_skill == "output_prediction":
            priority_score += 1
            reasons.append("weakest skill is output prediction")
            views.append("output_prediction_view")
            question_types.extend(["output_prediction", "debug"])
        elif weakest_skill in {"debug", "debugging"}:
            priority_score += 1
            reasons.append("weakest skill is debugging")
            views.append("debug_view")
            question_types.extend(["debug", "output_prediction"])
        elif weakest_skill:
            question_types.append(weakest_skill)

        if dominant_mistake_type in {"syntax_misunderstanding", "debug_misdiagnosis"}:
            priority_score += 1
            reasons.append(f"dominant mistake type is {dominant_mistake_type}")
            views.extend(["debug_view", "misconception_view"])
            question_types.append("debug")
        elif dominant_mistake_type == "wrong_output":
            priority_score += 1
            reasons.append("dominant mistake type is wrong output")
            views.append("output_prediction_view")
            question_types.append("output_prediction")

        if behaviour_risk >= 0.7 or behaviour_risk_label == "high_risk":
            priority_score += 1
            reasons.append("behaviour risk is high, so revision should be supportive")
            views = ["revision_view", "step_by_step_view", "flashcard_view"] + views
            question_types.extend(["mcq", "explanation_check"])

        if recent_scores and _safe_float(sum(recent_scores) / max(1, len(recent_scores)), 1.0) < 0.5:
            priority_score += 1
            reasons.append("recent scores are weak")

        revision_priority = _priority_from_score(priority_score)
        if revision_priority == "low" and review_due:
            revision_priority = "medium"

        views = _unique(views or SUPPORTIVE_VIEWS)
        question_types = _unique(question_types or ["mcq", "mixed_review"])

        weak_concept = {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
            "priority": revision_priority,
            "reason": "; ".join(reasons[:3]) or "light maintenance review",
        }

        cards = self._build_spaced_repetition_cards(
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            weakest_skill=weakest_skill,
            dominant_mistake_type=dominant_mistake_type,
            question_types=question_types,
        )
        daily_plan = self._build_daily_plan(weak_concept, views, question_types)
        weekly_plan = self._build_weekly_plan(weak_concept, cards)
        practice_queue = self._build_practice_queue(weak_concept, question_types)
        today_focus = self._today_focus(concept_name, weakest_skill, dominant_mistake_type, review_due)
        next_action = self._next_action(revision_priority, views, question_types)
        notebook_summary = self._summary(concept_name, revision_priority, reasons, mastery_score, fused_score)

        retention_prediction: Dict[str, Any] = {}
        try:
            from tutor.forgetting.retention_predictor import RetentionPredictor

            rp = RetentionPredictor()
            rp.load()
            ev_retention = {
                "learner_id": learner_id,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "mastery_score": mastery_score,
                "fused_score": fused_score,
                "behaviour_risk": behaviour_risk,
                "behaviour_confidence": _safe_float(evidence.get("behaviour_confidence"), 0.5),
                "review_due": review_due,
                "recent_scores": recent_scores if isinstance(recent_scores, list) else [],
                "recent_score": _safe_float(recent_scores[-1], 0.0) if recent_scores else fused_score,
                "average_recent_score": _safe_float(
                    sum(recent_scores) / max(1, len(recent_scores)), fused_score
                )
                if recent_scores
                else fused_score,
                "attempt_count": float(len(recent_scores)) if recent_scores else 1.0,
                "days_since_last_practice": _safe_float(evidence.get("days_since_last_practice"), 0.0),
                "time_gap_days": _safe_float(evidence.get("time_gap_days"), evidence.get("days_since_last_practice")),
                "mistake_count": _safe_float(
                    (mistake_type_counts or {}).get("total")
                    if isinstance(mistake_type_counts, dict)
                    else evidence.get("mistake_count"),
                    0.0,
                ),
                "difficulty": evidence.get("difficulty"),
                "confidence": _safe_float(evidence.get("confidence"), 0.5),
            }
            retention_prediction = rp.predict_with_fallback(
                ev_retention,
                fallback_revision={"revision_priority": revision_priority, "review_due": review_due},
            )
        except Exception as exc:
            retention_prediction = {
                "status": "warning",
                "module": "RetentionPredictor",
                "model_used": False,
                "fallback_used": True,
                "retention_risk_label": "medium",
                "review_due": bool(review_due),
                "revision_priority": "medium_priority",
                "recommended_review_interval": "next_day",
                "confidence": 0.0,
                "top_features": [],
                "frontend_component": "RetentionRiskCard",
                "limitations": [f"{type(exc).__name__}: {exc}"],
            }

        return {
            "status": "success",
            "module": "RevisionScheduler",
            "learner_id": learner_id,
            "revision_priority": revision_priority,
            "revision_reason": "; ".join(reasons) or "Learner is ready for light review.",
            "recommended_revision_views": views,
            "recommended_question_types": question_types,
            "weak_concepts": [weak_concept],
            "daily_review_plan": daily_plan,
            "weekly_review_plan": weekly_plan,
            "spaced_repetition_cards": cards,
            "frontend_revision_packet": {
                "notebook_summary": notebook_summary,
                "today_focus": today_focus,
                "next_revision_action": next_action,
                "cards": cards,
                "practice_queue": practice_queue,
                "revision_priority": revision_priority,
                "recommended_revision_views": views,
                "recommended_question_types": question_types,
            },
            "evidence_used": {
                "mastery_score": mastery_score,
                "fused_score": fused_score,
                "fused_label": fused_label,
                "weakest_skill": weakest_skill,
                "dominant_mistake_type": dominant_mistake_type,
                "mistake_type_counts": mistake_type_counts,
                "behaviour_risk": behaviour_risk,
                "behaviour_risk_label": behaviour_risk_label,
                "review_due": review_due,
            },
            "retention_prediction": retention_prediction,
        }

    def _build_spaced_repetition_cards(
        self,
        *,
        concept_id: str,
        concept_name: str,
        domain: str,
        weakest_skill: str,
        dominant_mistake_type: str,
        question_types: list[str],
    ) -> list[dict[str, Any]]:
        prompts = [
            {
                "interval": "immediate_review",
                "due_at": _iso_after(0),
                "prompt": f"What is the key idea of {concept_name}?",
                "card_type": "definition_recall",
            },
            {
                "interval": "next_day",
                "due_at": _iso_after(1),
                "prompt": f"Solve one short {question_types[0]} item for {concept_name}.",
                "card_type": "targeted_practice",
            },
            {
                "interval": "three_days",
                "due_at": _iso_after(3),
                "prompt": f"Explain a common mistake in {concept_name}.",
                "card_type": "misconception_check",
            },
            {
                "interval": "one_week",
                "due_at": _iso_after(7),
                "prompt": f"Apply {concept_name} in a new {domain or 'course'} example.",
                "card_type": "transfer_check",
            },
        ]

        if weakest_skill == "output_prediction" or dominant_mistake_type == "wrong_output":
            prompts[1]["prompt"] = f"Trace a short {concept_name} example and predict the exact output."
            prompts[1]["card_type"] = "output_prediction"
        if dominant_mistake_type == "syntax_misunderstanding":
            prompts[2]["prompt"] = f"Find and fix a syntax mistake related to {concept_name}."
            prompts[2]["card_type"] = "debug"

        for item in prompts:
            item["concept_id"] = concept_id
            item["concept_name"] = concept_name
            item["domain"] = domain
        return prompts

    def _build_daily_plan(
        self,
        weak_concept: dict[str, Any],
        views: list[str],
        question_types: list[str],
    ) -> list[dict[str, Any]]:
        return [
            {
                "day": "today",
                "concept_id": weak_concept["concept_id"],
                "concept_name": weak_concept["concept_name"],
                "view": views[0],
                "question_type": question_types[0],
                "goal": "Warm up with focused revision before new content.",
            },
            {
                "day": "tomorrow",
                "concept_id": weak_concept["concept_id"],
                "concept_name": weak_concept["concept_name"],
                "view": views[min(1, len(views) - 1)],
                "question_type": question_types[min(1, len(question_types) - 1)],
                "goal": "Repeat the weak skill with one fresh example.",
            },
        ]

    def _build_weekly_plan(self, weak_concept: dict[str, Any], cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "week": "current_week",
                "concept_id": weak_concept["concept_id"],
                "concept_name": weak_concept["concept_name"],
                "scheduled_intervals": [card["interval"] for card in cards],
                "goal": "Complete spaced repetition cards and one mixed practice set.",
            }
        ]

    def _build_practice_queue(self, weak_concept: dict[str, Any], question_types: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "concept_id": weak_concept["concept_id"],
                "concept_name": weak_concept["concept_name"],
                "practice_type": question_type,
                "priority": weak_concept["priority"],
            }
            for question_type in question_types[:4]
        ]

    def _today_focus(self, concept_name: str, weakest_skill: str, dominant_mistake_type: str, review_due: bool) -> str:
        if review_due:
            return f"Review {concept_name} before starting new material."
        if weakest_skill == "output_prediction" or dominant_mistake_type == "wrong_output":
            return f"Practice tracing {concept_name} examples and predicting output."
        if dominant_mistake_type == "syntax_misunderstanding":
            return f"Review syntax mistakes around {concept_name}."
        return f"Do a light review of {concept_name}."

    def _next_action(self, priority: str, views: list[str], question_types: list[str]) -> str:
        if priority == "high":
            return f"start_with_{views[0]}_and_{question_types[0]}_practice"
        if priority == "medium":
            return f"warm_up_with_{views[0]}"
        return "light_review_or_continue"

    def _summary(
        self,
        concept_name: str,
        priority: str,
        reasons: list[str],
        mastery_score: float,
        fused_score: float,
    ) -> str:
        reason_text = "; ".join(reasons[:3]) if reasons else "performance is stable"
        return (
            f"{concept_name} has {priority} revision priority because {reason_text}. "
            f"KT mastery is {round(mastery_score, 4)} and evaluation fusion score is {round(fused_score, 4)}."
        )


def build_revision_schedule(evidence: dict[str, Any]) -> dict[str, Any]:
    return RevisionScheduler().build_revision_plan(evidence)
