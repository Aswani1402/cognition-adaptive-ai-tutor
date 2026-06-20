from __future__ import annotations

from tutor.memory.revision_scheduler import RevisionScheduler


def _base_evidence() -> dict:
    return {
        "learner_id": "14",
        "concept_id": "1",
        "concept_name": "Variables",
        "domain": "Python",
        "mastery_score": 0.6,
        "fused_score": 0.3896,
        "fused_label": "needs_reteaching",
        "weakest_skill": "output_prediction",
        "dominant_mistake_type": "wrong_output",
        "mistake_type_counts": {"wrong_output": 1, "syntax_misunderstanding": 1},
        "behaviour_risk": 0.2488,
        "behaviour_risk_label": "low_risk",
        "review_due": True,
        "recent_scores": [],
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_review_due_output_prediction(scheduler: RevisionScheduler) -> None:
    result = scheduler.build_revision_plan(_base_evidence())
    _assert(result["revision_priority"] == "high", "review_due weak output_prediction should be high priority")
    _assert("output_prediction_view" in result["recommended_revision_views"], "output prediction view missing")
    _assert("output_prediction" in result["recommended_question_types"], "output prediction practice missing")


def test_syntax_mistake(scheduler: RevisionScheduler) -> None:
    evidence = _base_evidence()
    evidence.update({"weakest_skill": "debug", "dominant_mistake_type": "syntax_misunderstanding"})
    result = scheduler.build_revision_plan(evidence)
    _assert("debug_view" in result["recommended_revision_views"], "debug view missing")
    _assert("misconception_view" in result["recommended_revision_views"], "misconception view missing")
    _assert("debug" in result["recommended_question_types"], "debug practice missing")


def test_low_mastery(scheduler: RevisionScheduler) -> None:
    evidence = _base_evidence()
    evidence.update({"mastery_score": 0.25, "review_due": False, "fused_label": "partial", "fused_score": 0.6})
    result = scheduler.build_revision_plan(evidence)
    _assert(result["revision_priority"] in {"medium", "high"}, "low mastery should raise priority")
    _assert("step_by_step_view" in result["recommended_revision_views"], "step-by-step support missing")


def test_high_behaviour_risk(scheduler: RevisionScheduler) -> None:
    evidence = _base_evidence()
    evidence.update({"behaviour_risk": 0.88, "behaviour_risk_label": "high_risk"})
    result = scheduler.build_revision_plan(evidence)
    _assert(result["recommended_revision_views"][0] in {"revision_view", "step_by_step_view"}, "high risk should be supportive")
    _assert("challenge_view" not in result["recommended_revision_views"], "high risk should not recommend challenge first")


def test_strong_learner_light_review(scheduler: RevisionScheduler) -> None:
    evidence = _base_evidence()
    evidence.update(
        {
            "mastery_score": 0.9,
            "fused_score": 0.92,
            "fused_label": "mastered",
            "weakest_skill": "",
            "dominant_mistake_type": "",
            "review_due": False,
            "behaviour_risk": 0.1,
            "behaviour_risk_label": "low_risk",
        }
    )
    result = scheduler.build_revision_plan(evidence)
    _assert(result["revision_priority"] == "low", "strong learner should get low revision priority")
    _assert(result["frontend_revision_packet"]["next_revision_action"] == "light_review_or_continue", "strong learner next action mismatch")


def test_frontend_packet_exists(scheduler: RevisionScheduler) -> None:
    result = scheduler.build_revision_plan(_base_evidence())
    packet = result.get("frontend_revision_packet")
    _assert(isinstance(packet, dict), "frontend_revision_packet missing")
    _assert(packet.get("cards"), "frontend cards missing")
    _assert(packet.get("practice_queue"), "frontend practice queue missing")


def main() -> None:
    scheduler = RevisionScheduler()
    test_review_due_output_prediction(scheduler)
    test_syntax_mistake(scheduler)
    test_low_mastery(scheduler)
    test_high_behaviour_risk(scheduler)
    test_strong_learner_light_review(scheduler)
    test_frontend_packet_exists(scheduler)
    print("STATUS: success")
    print("MODULE: revision_scheduler_test")


if __name__ == "__main__":
    main()
