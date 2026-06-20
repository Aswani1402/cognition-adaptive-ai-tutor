from __future__ import annotations


def main() -> None:
    from tutor.system.agentic_orchestrator import SafeTutorOrchestrator

    output = SafeTutorOrchestrator().run(
        {
            "learner_id": "agentic_safety_learner",
            "subject": "Python",
            "concept_id": "P1",
            "concept_name": "Variables",
            "difficulty": "hard",
            "activity_type": "answer_submit",
            "learner_answer": "wrong",
            "behaviour_payload": {
                "confidence": 0.3,
                "time_taken_sec": 95,
                "hint_used": True,
                "hint_count": 3,
                "attempt_count": 2,
                "wrong_attempt_count": 1,
            },
        },
        {
            "evaluation": {"status": "success", "score": 0.2, "label": "wrong", "mistake_type": "misconception"},
            "kt_update": {"status": "success", "model_used": "fallback_cumulative", "fallback_used": True, "mastery_after": 0.2},
            "behaviour_update": {"status": "success", "model_used": "scoring_formula", "behaviour_risk": 0.9},
            "path_update": {"difficulty_passed": False, "concept_completed": False, "next_concept_id": "P2"},
            "policy_update": {"safe_action_applied": True, "recommended_action": "next_concept", "final_action": "next_concept"},
        },
    )
    checks = output["safety_checks"]
    assert checks["promotion_allowed"] is False
    assert checks["behaviour_risk_ok"] is False
    assert checks["wrong_or_partial_blocks_promotion"] is True
    assert output["final_decision"]["next_activity"] in {"hint", "similar_question", "flashcard", "revision"}
    print("agentic safety checks test success")
    print("final_decision:", output["final_decision"]["next_activity"])


if __name__ == "__main__":
    main()
