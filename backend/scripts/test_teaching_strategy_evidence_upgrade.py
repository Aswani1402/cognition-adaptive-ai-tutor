from __future__ import annotations

from tutor.strategy.selector import recommend_evidence_aware_teaching_strategy


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _base_kwargs(**overrides):
    data = {
        "learner_id": "14",
        "concept_id": "1",
        "concept_name": "Variables",
        "policy_output": {
            "status": "success",
            "data": {
                "next_concept_id": "1",
                "difficulty": "medium",
                "strategy": "practice",
            },
        },
        "evaluation_output": {
            "overall_score": 0.62,
            "results": [],
        },
        "evaluation_fusion_output": {
            "status": "success",
            "fused_score": 0.62,
            "fused_label": "partial",
        },
        "mistake_analysis_output": {},
        "behaviour_state": {
            "data": {
                "behavior_risk": 0.22,
                "behavior_risk_label": "low_risk",
                "behavior_confidence": 0.70,
            }
        },
        "knowledge_state": {
            "data": {
                "predicted_mastery_last": 0.58,
                "written_state": {"1": 0.58},
            }
        },
        "forgetting_state": {
            "data": {
                "review_queue": [],
                "review_priority": {},
            }
        },
        "view_performance_output": {
            "logged": {
                "teaching_view": "definition_view",
                "reward": 0.62,
            }
        },
        "learner_notebook_memory_output": {},
        "xai_output": {},
        "adaptive_path_output": {},
        "conn": None,
        "log": False,
    }
    data.update(overrides)
    return data


def main() -> None:
    output_prediction = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            evaluation_fusion_output={
                "fused_score": 0.48,
                "fused_label": "focused_remediation",
                "weakest_skill_signal": {"weakest_skill": "output_prediction"},
            }
        )
    )
    _assert(
        output_prediction["teaching_view"] in {"code_view", "debug_view"},
        f"output prediction did not route to code/debug view: {output_prediction}",
    )
    _assert(
        "output_prediction" in output_prediction["assessment_types"],
        f"output prediction assessment missing: {output_prediction}",
    )

    debug_weakness = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            evaluation_fusion_output={
                "fused_score": 0.46,
                "fused_label": "focused_remediation",
                "weakest_skill_signal": {"weakest_skill": "debug"},
            },
            mistake_analysis_output={"dominant_mistake_type": "syntax_misunderstanding"},
        )
    )
    _assert(debug_weakness["teaching_view"] == "debug_view", f"debug view not selected: {debug_weakness}")
    _assert("debug" in debug_weakness["assessment_types"], f"debug assessment missing: {debug_weakness}")

    low_mastery = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.30,
                    "written_state": {"1": 0.30},
                }
            },
            evaluation_fusion_output={"fused_score": 0.35, "fused_label": "needs_reteaching"},
        )
    )
    _assert(low_mastery["difficulty"] == "easy", f"low mastery not easy: {low_mastery}")
    _assert(
        low_mastery["teaching_view"] in {"definition_view", "step_by_step_view"},
        f"low mastery view not supportive: {low_mastery}",
    )

    high_mastery = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            policy_output={
                "status": "success",
                "data": {
                    "next_concept_id": "1",
                    "difficulty": "medium",
                    "strategy": "advanced",
                },
            },
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.86,
                    "written_state": {"1": 0.86},
                }
            },
            evaluation_output={"overall_score": 0.88, "results": [{"assessment_type": "transfer", "score": 0.9}]},
            evaluation_fusion_output={"fused_score": 0.88, "fused_label": "mastered"},
        )
    )
    _assert(high_mastery["difficulty"] == "hard", f"high mastery not hard: {high_mastery}")
    _assert(
        high_mastery["teaching_view"] in {"challenge_view", "transfer_view"},
        f"high mastery did not route to challenge/transfer: {high_mastery}",
    )
    _assert(
        high_mastery["progression_action"] in {"level_up", "advance_concept"},
        f"high mastery progression wrong: {high_mastery}",
    )

    high_risk = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            policy_output={
                "status": "success",
                "data": {
                    "next_concept_id": "1",
                    "difficulty": "hard",
                    "strategy": "advanced",
                },
            },
            behaviour_state={
                "data": {
                    "behavior_risk": 0.82,
                    "behavior_risk_label": "high_risk",
                }
            },
            knowledge_state={
                "data": {
                    "predicted_mastery_last": 0.78,
                    "written_state": {"1": 0.78},
                }
            },
            evaluation_fusion_output={"fused_score": 0.78, "fused_label": "partial_strong"},
        )
    )
    _assert(high_risk["difficulty"] != "hard", f"high risk did not reduce difficulty: {high_risk}")
    _assert(
        high_risk["teaching_view"] in {"step_by_step_view", "revision_view", "misconception_view", "code_view"},
        f"high risk did not use a supportive view: {high_risk}",
    )
    _assert(
        high_risk["next_activity"] in {"supportive_practice", "reteach_with_support"},
        f"high risk next activity not supportive: {high_risk}",
    )
    _assert(
        high_risk["progression_action"] in {"same_level_change_view_or_practice", "reteach"},
        f"high risk progression not supportive: {high_risk}",
    )

    forgetting_due = recommend_evidence_aware_teaching_strategy(
        **_base_kwargs(
            forgetting_state={
                "data": {
                    "review_queue": ["1"],
                    "review_priority": {"1": 0.92},
                }
            }
        )
    )
    _assert(
        forgetting_due["teaching_view"] in {"revision_view", "flashcard_view"},
        f"forgetting due did not route to revision: {forgetting_due}",
    )
    _assert(
        forgetting_due["next_activity"] == "revision_before_new_content",
        f"forgetting due next activity wrong: {forgetting_due}",
    )

    missing_evidence = recommend_evidence_aware_teaching_strategy(
        learner_id="14",
        concept_id="1",
        conn=None,
        log=False,
    )
    _assert(missing_evidence["status"] == "success", f"missing evidence fallback failed: {missing_evidence}")
    _assert(missing_evidence.get("evidence_used"), f"evidence_used missing: {missing_evidence}")

    print("weak_output_prediction:", output_prediction["teaching_view"], output_prediction["assessment_types"])
    print("syntax_debug_weakness:", debug_weakness["teaching_view"], debug_weakness["assessment_types"])
    print("low_mastery:", low_mastery["difficulty"], low_mastery["teaching_view"])
    print("high_mastery:", high_mastery["difficulty"], high_mastery["teaching_view"], high_mastery["progression_action"])
    print("high_behaviour_risk:", high_risk["difficulty"], high_risk["teaching_view"])
    print("forgetting_due:", forgetting_due["teaching_view"], forgetting_due["next_activity"])
    print("missing_evidence:", missing_evidence["status"], missing_evidence["teaching_view"])
    print("STATUS: success")
    print("MODULE: teaching_strategy_evidence_upgrade_test")


if __name__ == "__main__":
    main()
