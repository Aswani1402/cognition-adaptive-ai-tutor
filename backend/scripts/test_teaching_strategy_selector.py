from tutor.strategy.selector import recommend_evidence_aware_teaching_strategy


def main():
    policy_output = {
        "status": "success",
        "data": {
            "next_concept_id": "1",
            "difficulty": "medium",
            "strategy": "practice",
            "content_type": "worked_example",
            "decision_type": "dqn_rl_policy_override",
            "explanation_mode": "code",
        },
    }

    evaluation_output = {
        "overall_score": 0.6,
        "verdict": "needs_light_review",
        "feedback_summary": "Needs improvement in: output_prediction, debug",
        "results": [
            {"assessment_type": "mcq", "score": 1.0},
            {"assessment_type": "output_prediction", "score": 0.0},
            {"assessment_type": "debug", "score": 0.0},
            {"assessment_type": "explanation", "score": 1.0},
            {"assessment_type": "transfer", "score": 1.0},
        ],
    }

    behaviour_state = {
        "data": {
            "behavior_label": "stable",
            "behavior_score": 0.6062,
            "wrong_rate": 0.4,
            "slow_rate": 0.2,
            "low_confidence_rate": 1.0,
            "hint_rate": 0.0,
        }
    }

    view_performance_output = {
        "status": "success",
        "logged": {
            "teaching_view": "definition_view",
            "reward": 0.4512,
            "outcome_label": "weak_success",
            "difficulty": "medium",
        },
    }

    learner_notebook_memory_output = {
        "weak_assessment_types": ["output_prediction", "debug"],
        "next_practice_queue": [
            {"concept_id": "1", "practice_type": "output_prediction", "priority": "high"},
            {"concept_id": "1", "practice_type": "debug", "priority": "high"},
        ],
    }

    xai_output = {
        "data": {
            "evidence": {
                "feature_contributions": {
                    "top_factors": [
                        {"feature": "mastery_need"},
                        {"feature": "evaluation_need"},
                        {"feature": "view_reward_need"},
                    ]
                }
            }
        }
    }

    adaptive_path_output = {
        "status": "success",
        "selected_next_concept": "31",
        "recommended_strategy": "remedial",
        "recommended_difficulty": "easy",
    }

    output = recommend_evidence_aware_teaching_strategy(
        learner_id="14",
        concept_id="1",
        concept_name="Variables",
        policy_output=policy_output,
        evaluation_output=evaluation_output,
        behaviour_state=behaviour_state,
        view_performance_output=view_performance_output,
        learner_notebook_memory_output=learner_notebook_memory_output,
        xai_output=xai_output,
        adaptive_path_output=adaptive_path_output,
        conn=None,
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("DIFFICULTY:", output["difficulty"])
    print("TEACHING VIEW:", output["teaching_view"])
    print("EXPLANATION MODE:", output["explanation_mode"])
    print("ASSESSMENT DIFFICULTY:", output["assessment_difficulty"])
    print("ASSESSMENT TYPES:", output["assessment_types"])
    print("FALLBACK VIEWS:", output["fallback_views"])
    print("NEXT ACTIVITY:", output["next_activity"])
    print("PROGRESSION:", output["progression_action"])
    print("\nREASON:", output["reason"])


if __name__ == "__main__":
    main()