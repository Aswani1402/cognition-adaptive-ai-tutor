from __future__ import annotations

from typing import Any


SUPPORTED_DECISIONS = {
    "teaching_strategy",
    "promotion",
    "learner_weakness",
    "revision_need",
    "policy_decision",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_contributions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positive = [max(0.0, _safe_float(item.get("raw_contribution"))) for item in items]
    total = sum(positive)
    if total <= 0:
        total = 1.0

    normalized = []
    for item, raw in zip(items, positive):
        clean = dict(item)
        clean.pop("raw_contribution", None)
        clean["contribution"] = round(raw / total, 4)
        normalized.append(clean)

    normalized.sort(key=lambda item: item["contribution"], reverse=True)
    return normalized


class DecisionExplainer:
    """
    Transparent model-aware XAI layer.

    This is deterministic feature-contribution reasoning over the same
    evidence used by the tutor pipeline. It is intentionally not SHAP or
    black-box attribution until trained models and dependencies are stable.
    """

    def explain(
        self,
        *,
        decision_type: str,
        decision: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        decision_type = _safe_str(decision_type, "teaching_strategy")
        if decision_type not in SUPPORTED_DECISIONS:
            decision_type = "teaching_strategy"

        evidence = evidence or {}
        contributions = self._build_contributions(decision_type, evidence)
        top_factors = [item["feature"] for item in contributions[:3]]
        confidence = self._confidence(contributions, evidence)
        counterfactuals = self._counterfactuals(decision_type, evidence)

        return {
            "status": "success",
            "module": "DecisionExplainer",
            "decision_type": decision_type,
            "decision": decision,
            "confidence": confidence,
            "feature_contributions": contributions,
            "top_factors": top_factors,
            "counterfactuals": counterfactuals,
            "learner_friendly_explanation": self._learner_explanation(decision_type, decision, contributions, evidence),
            "teacher_dashboard_explanation": self._teacher_explanation(decision_type, decision, contributions, evidence),
            "limitations": [
                "Transparent deterministic contribution scoring, not SHAP/deep-model attribution.",
                "Contribution weights are rule-based until trained decision models are promoted from comparison mode.",
            ],
        }

    def _build_contributions(self, decision_type: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        mastery = _clamp(_safe_float(evidence.get("mastery_score"), 0.5))
        behaviour_risk = _clamp(_safe_float(evidence.get("behaviour_risk", evidence.get("behavior_risk")), 0.0))
        fused_score = _clamp(_safe_float(evidence.get("fused_score"), 0.5))
        fused_label = _safe_str(evidence.get("fused_label"), "unknown")
        weakest_skill = _safe_str(evidence.get("weakest_skill"), "unknown")
        dominant_mistake = _safe_str(evidence.get("dominant_mistake_type"), "unknown")
        high_severity = _safe_float(evidence.get("high_severity_mistake_count"), 0.0)
        review_due = bool(evidence.get("review_due"))
        promotion_confidence = _clamp(_safe_float(evidence.get("promotion_confidence"), 0.5))
        rag_grounding_score = _clamp(_safe_float(evidence.get("rag_grounding_score"), 0.0))
        behaviour_risk_label = _safe_str(evidence.get("behaviour_risk_label", evidence.get("behavior_risk_label")), "")

        if fused_score < 0.55:
            items.append(self._item("fused_score", fused_score, 1.0 - fused_score, "supports_reteaching", "Low fused evaluation score increases need for reteaching."))
        else:
            items.append(self._item("fused_score", fused_score, fused_score * 0.5, "supports_progress", "Strong fused evaluation score supports harder practice or progression."))

        if fused_label in {"needs_reteaching", "focused_remediation", "needs_remediation", "needs_review"}:
            items.append(self._item("fused_label", fused_label, 0.65, "supports_remediation", f"Fusion label {fused_label} indicates support or remediation is needed."))
        elif fused_label in {"mastered", "partial_strong", "strong", "success"}:
            items.append(self._item("fused_label", fused_label, 0.55, "supports_progression", f"Fusion label {fused_label} supports challenge or advancement."))

        if weakest_skill and weakest_skill != "unknown":
            items.append(self._item("weakest_skill", weakest_skill, 0.55, "selects_targeted_assessment", f"Weakest skill {weakest_skill} guides the assessment type selection."))

        if dominant_mistake and dominant_mistake != "unknown":
            raw = 0.45 + min(0.25, high_severity * 0.08)
            items.append(self._item("dominant_mistake_type", dominant_mistake, raw, "selects_teaching_view", f"Dominant mistake {dominant_mistake} informs the chosen teaching view."))

        if behaviour_risk >= 0.7 or behaviour_risk_label == "high_risk":
            items.append(self._item("behaviour_risk", behaviour_risk, behaviour_risk, "supports_lower_difficulty", "High behaviour risk supports supportive teaching and lower difficulty."))
        elif behaviour_risk <= 0.35:
            items.append(self._item("behaviour_risk", behaviour_risk, 0.35, "allows_normal_practice", "Low behaviour risk allows normal practice without extra difficulty reduction."))
        else:
            items.append(self._item("behaviour_risk", behaviour_risk, 0.45, "monitor_confusion", "Medium behaviour risk suggests monitoring and moderate support."))

        if mastery < 0.4:
            items.append(self._item("mastery_score", mastery, 1.0 - mastery, "supports_easy_support", "Low mastery supports easy, step-by-step teaching."))
        elif mastery <= 0.7:
            items.append(self._item("mastery_score", mastery, 0.50, "supports_practice", "Medium mastery supports practice before advancement."))
        else:
            items.append(self._item("mastery_score", mastery, mastery, "supports_challenge", "High mastery supports hard practice, challenge, or progression."))

        if review_due:
            items.append(self._item("review_due", True, 0.85, "supports_revision", "Forgetting/review queue indicates this concept should be revised."))

        if promotion_confidence < 0.55:
            items.append(self._item("promotion_confidence", promotion_confidence, 1.0 - promotion_confidence, "blocks_promotion", "Low promotion confidence explains why the learner is not promoted yet."))
        else:
            items.append(self._item("promotion_confidence", promotion_confidence, promotion_confidence * 0.55, "supports_promotion", "Promotion confidence is high enough to support advancement."))

        if rag_grounding_score >= 0.70:
            items.append(self._item("rag_grounding_score", rag_grounding_score, rag_grounding_score * 0.45, "supports_trusted_content", "High RAG grounding score supports trusting retrieved/generated content."))
        elif rag_grounding_score > 0:
            items.append(self._item("rag_grounding_score", rag_grounding_score, 1.0 - rag_grounding_score, "requires_grounding_check", "Lower RAG grounding score means content should be checked or rewritten."))

        return _normalize_contributions(self._filter_for_decision(decision_type, items))

    def _filter_for_decision(self, decision_type: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        preferred = {
            "teaching_strategy": {"fused_score", "fused_label", "weakest_skill", "dominant_mistake_type", "behaviour_risk", "mastery_score", "review_due"},
            "promotion": {"promotion_confidence", "mastery_score", "fused_score", "fused_label", "behaviour_risk"},
            "learner_weakness": {"weakest_skill", "dominant_mistake_type", "fused_score", "fused_label", "mastery_score"},
            "revision_need": {"review_due", "mastery_score", "fused_score", "promotion_confidence"},
            "policy_decision": {"mastery_score", "behaviour_risk", "fused_score", "review_due", "promotion_confidence", "rag_grounding_score"},
        }
        allowed = preferred.get(decision_type, preferred["teaching_strategy"])
        filtered = [item for item in items if item["feature"] in allowed]
        return filtered or items

    def _item(self, feature: str, value: Any, raw: float, direction: str, explanation: str) -> dict[str, Any]:
        return {
            "feature": feature,
            "value": value,
            "raw_contribution": _clamp(raw),
            "direction": direction,
            "explanation": explanation,
        }

    def _confidence(self, contributions: list[dict[str, Any]], evidence: dict[str, Any]) -> float:
        coverage = min(1.0, len(contributions) / 5.0)
        top = contributions[0]["contribution"] if contributions else 0.0
        has_core = all(key in evidence for key in ["mastery_score", "fused_score", "behaviour_risk"])
        return round(_clamp(0.45 + 0.25 * coverage + 0.20 * top + (0.10 if has_core else 0.0)), 4)

    def _counterfactuals(self, decision_type: str, evidence: dict[str, Any]) -> list[str]:
        counterfactuals = []
        if _safe_float(evidence.get("fused_score"), 0.5) < 0.75:
            counterfactuals.append("If fused_score were above 0.75, the learner could receive challenge_view or advance_concept.")
        if evidence.get("review_due"):
            counterfactuals.append("If review_due were false, the selector may choose code_view instead of revision_view.")
        if _safe_float(evidence.get("behaviour_risk", evidence.get("behavior_risk")), 0.0) >= 0.7:
            counterfactuals.append("If behaviour_risk were low, the tutor could keep normal difficulty instead of supportive routing.")
        if _safe_float(evidence.get("promotion_confidence"), 0.5) < 0.55:
            counterfactuals.append("If promotion_confidence were higher, the learner could be promoted or advanced.")
        if _safe_float(evidence.get("rag_grounding_score"), 0.0) < 0.7:
            counterfactuals.append("If RAG grounding were higher, generated content could be trusted with lower review risk.")
        if not counterfactuals:
            counterfactuals.append(f"If the strongest evidence changed, the {decision_type} decision could change.")
        return counterfactuals

    def _learner_explanation(self, decision_type: str, decision: str, contributions: list[dict[str, Any]], evidence: dict[str, Any]) -> str:
        factors = ", ".join(item["feature"] for item in contributions[:3])
        return (
            f"I chose {decision} because your recent evidence points to {factors}. "
            "We will focus on the next best step before moving ahead."
        )

    def _teacher_explanation(self, decision_type: str, decision: str, contributions: list[dict[str, Any]], evidence: dict[str, Any]) -> str:
        parts = [
            f"{decision_type} decision `{decision}` was explained with transparent feature contributions.",
            "Top factors: "
            + ", ".join(
                f"{item['feature']}={item['value']} ({item['direction']}, {item['contribution']})"
                for item in contributions[:5]
            ),
        ]
        return " ".join(parts)


def explain_decision(*, decision_type: str, decision: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return DecisionExplainer().explain(
        decision_type=decision_type,
        decision=decision,
        evidence=evidence,
    )
