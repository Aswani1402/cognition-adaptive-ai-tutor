from tutor.xai.feature_contribution_explainer import FeatureContributionExplainer


def main():
    knowledge_state = {
        "data": {
            "data": {
                "predicted_mastery_last": 0.60
            }
        }
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

    forgetting_state = {
        "data": {
            "review_priority": {
                "1": 0.2693
            }
        }
    }

    evaluation_output = {
        "overall_score": 0.60,
        "verdict": "needs_light_review",
    }

    view_performance_output = {
        "logged": {
            "teaching_view": "definition_view",
            "reward": 0.4512,
        }
    }

    adaptive_path_output = {
        "status": "success",
        "selected_next_concept": "31",
        "selected_score": 0.5384,
    }

    adaptive_policy_bridge_output = {
        "status": "success",
        "agreement": False,
        "override_allowed": False,
    }

    explainer = FeatureContributionExplainer()

    output = explainer.explain(
        knowledge_state=knowledge_state,
        behaviour_state=behaviour_state,
        forgetting_state=forgetting_state,
        evaluation_output=evaluation_output,
        view_performance_output=view_performance_output,
        adaptive_path_output=adaptive_path_output,
        adaptive_policy_bridge_output=adaptive_policy_bridge_output,
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("PRESSURE:", output["decision_pressure_label"])
    print("TOTAL:", output["total_decision_pressure"])
    print("SUMMARY:", output["summary"])

    print("\nTOP FACTORS")
    for factor in output["top_factors"]:
        print(factor)


if __name__ == "__main__":
    main()