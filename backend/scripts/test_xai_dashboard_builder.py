from __future__ import annotations

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once
from tutor.xai.xai_dashboard_builder import XAIDashboardBuilder


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    integrated_output = run_integrated_tutor_once(
        learner_id="14",
        reward_dry_run=True,
    )
    dashboard = XAIDashboardBuilder().build(
        integrated_output=integrated_output,
        learner_id="14",
    )

    _assert(dashboard["status"] == "success", f"dashboard failed: {dashboard}")
    _assert(dashboard["module"] == "XAIDashboardBuilder", f"wrong module: {dashboard}")
    _assert(dashboard["cards"], f"cards missing: {dashboard}")
    _assert(dashboard["top_factors"], f"top factors missing: {dashboard}")
    _assert(dashboard["counterfactuals"], f"counterfactuals missing: {dashboard}")

    for name, value in dashboard["factor_contributions"].items():
        _assert(isinstance(value, (int, float)), f"{name} contribution not numeric: {value}")
        _assert(0.0 <= float(value) <= 1.0, f"{name} contribution out of range: {value}")

    cards = dashboard["cards"]
    learner_state = cards.get("learner_state_card", {})
    _assert("mastery_score" in learner_state, f"KT evidence missing: {learner_state}")
    _assert("behaviour_risk" in learner_state, f"Behaviour evidence missing: {learner_state}")
    _assert("fused_score" in learner_state, f"Evaluation evidence missing: {learner_state}")

    decision = cards.get("decision_reason_card", {})
    _assert(decision.get("selected_teaching_view"), f"teaching view missing: {decision}")
    _assert(decision.get("selected_difficulty"), f"difficulty missing: {decision}")
    _assert(decision.get("selected_strategy"), f"strategy missing: {decision}")

    promotion = cards.get("promotion_explanation_card", {})
    _assert("promotion_confidence" in promotion, f"promotion confidence missing: {promotion}")
    _assert("teacher_evidence_card" in cards, f"teacher evidence card missing: {cards}")

    print("card_count:", len(cards))
    print("top_factors:", dashboard["top_factors"][:3])
    print("completeness:", dashboard["explanation_quality"].get("explanation_completeness_score"))
    print("STATUS: success")
    print("MODULE: xai_dashboard_builder_test")


if __name__ == "__main__":
    main()
