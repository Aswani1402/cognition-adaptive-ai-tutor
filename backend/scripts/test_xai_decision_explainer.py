from __future__ import annotations

from tutor.xai.decision_explainer import DecisionExplainer


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _top(output: dict) -> set[str]:
    return set(output.get("top_factors", []))


def main() -> None:
    explainer = DecisionExplainer()

    reteaching = explainer.explain(
        decision_type="teaching_strategy",
        decision="revision_view",
        evidence={
            "mastery_score": 0.6,
            "behaviour_risk": 0.2488,
            "fused_score": 0.3896,
            "fused_label": "needs_reteaching",
            "weakest_skill": "output_prediction",
            "dominant_mistake_type": "wrong_output",
            "high_severity_mistake_count": 2,
            "review_due": True,
            "promotion_confidence": 0.3893,
            "rag_grounding_score": 0.95,
        },
    )
    _assert(reteaching["status"] == "success", f"reteaching failed: {reteaching}")
    _assert(
        {"fused_score", "review_due", "weakest_skill"} & _top(reteaching),
        f"reteaching top factors missing expected evidence: {reteaching}",
    )

    high_risk = explainer.explain(
        decision_type="teaching_strategy",
        decision="step_by_step_view",
        evidence={
            "mastery_score": 0.68,
            "behaviour_risk": 0.82,
            "behaviour_risk_label": "high_risk",
            "fused_score": 0.72,
            "fused_label": "partial",
            "weakest_skill": "debug",
            "dominant_mistake_type": "syntax_misunderstanding",
        },
    )
    text = (high_risk["teacher_dashboard_explanation"] + " " + high_risk["learner_friendly_explanation"]).lower()
    _assert("supportive" in text or "lower" in text, f"high risk not explained as supportive/lower: {high_risk}")
    _assert("behaviour_risk" in _top(high_risk), f"high risk top factor missing behaviour_risk: {high_risk}")

    high_mastery = explainer.explain(
        decision_type="teaching_strategy",
        decision="challenge_view",
        evidence={
            "mastery_score": 0.86,
            "behaviour_risk": 0.12,
            "fused_score": 0.88,
            "fused_label": "mastered",
            "weakest_skill": "none",
            "promotion_confidence": 0.82,
        },
    )
    _assert(
        any(item["direction"] in {"supports_challenge", "supports_progression"} for item in high_mastery["feature_contributions"]),
        f"high mastery did not support challenge/advance: {high_mastery}",
    )

    no_promotion = explainer.explain(
        decision_type="promotion",
        decision="not_promoted",
        evidence={
            "mastery_score": 0.60,
            "behaviour_risk": 0.24,
            "fused_score": 0.39,
            "fused_label": "needs_reteaching",
            "promotion_confidence": 0.31,
        },
    )
    _assert(
        any(item["feature"] == "promotion_confidence" and item["direction"] == "blocks_promotion" for item in no_promotion["feature_contributions"]),
        f"no promotion missing promotion confidence block: {no_promotion}",
    )
    _assert("promoted" in " ".join(no_promotion["counterfactuals"]).lower(), f"no promotion counterfactual missing: {no_promotion}")

    rag_grounding = explainer.explain(
        decision_type="policy_decision",
        decision="trust_grounded_content",
        evidence={
            "mastery_score": 0.60,
            "behaviour_risk": 0.24,
            "fused_score": 0.62,
            "rag_grounding_score": 0.95,
        },
    )
    _assert(
        any(item["feature"] == "rag_grounding_score" and item["direction"] == "supports_trusted_content" for item in rag_grounding["feature_contributions"]),
        f"RAG grounding trust not explained: {rag_grounding}",
    )

    print("reteaching_top_factors:", reteaching["top_factors"])
    print("high_behaviour_risk_top_factors:", high_risk["top_factors"])
    print("high_mastery_top_factors:", high_mastery["top_factors"])
    print("no_promotion_top_factors:", no_promotion["top_factors"])
    print("rag_grounding_top_factors:", rag_grounding["top_factors"])
    print("STATUS: success")
    print("MODULE: xai_decision_explainer_test")


if __name__ == "__main__":
    main()
