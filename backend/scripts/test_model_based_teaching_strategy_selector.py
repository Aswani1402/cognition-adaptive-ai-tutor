from tutor.strategy.model_based_selector import ModelBasedTeachingStrategySelector


def main():
    selector = ModelBasedTeachingStrategySelector()

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
        "selected_score": 0.4909,
    }

    knowledge_state = {
        "data": {
            "data": {
                "predicted_mastery_last": 0.6
            }
        }
    }

    forgetting_state = {
        "data": {
            "review_priority": {
                "1": 0.2697
            }
        }
    }

    output = selector.predict(
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
        knowledge_state=knowledge_state,
        forgetting_state=forgetting_state,
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])

    if output["status"] != "success":
        print(output)
        return

    print("MODEL TEACHING VIEW:", output["model_teaching_view"])
    print("TEACHING VIEW CONFIDENCE:", output["teaching_view_confidence"])
    print("MODEL PROGRESSION:", output["model_progression_action"])
    print("PROGRESSION CONFIDENCE:", output["progression_confidence"])
    print("ASSESSMENT TYPES:", output["assessment_types"])
    print("FALLBACK VIEWS:", output["fallback_views"])
    print("NEXT ACTIVITY:", output["next_activity"])
    print("REASON:", output["reason"])


if __name__ == "__main__":
    main()