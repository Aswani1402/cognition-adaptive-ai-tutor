from tutor.path.adaptive_path_selector import AdaptivePathSelector


def main():
    dependency_output = {
        "status": "success",
        "recommended_next_concept": "1",
        "unlocked_concepts": ["1", "2", "3"],
        "blocked_concepts": [
            {
                "concept_id": "4",
                "blocked_by": ["2"],
                "threshold": 0.7,
            }
        ],
    }

    mastery = {
        "1": 0.60,
        "2": 0.30,
        "3": 0.75,
    }

    forgetting_priority = {
        "1": 0.26,
        "2": 0.55,
        "3": 0.10,
    }

    evaluation_evidence = {
        "overall_score": 0.60,
        "weak_item_count": 2,
        "item_count": 5,
        "verdict": "needs_light_review",
    }

    behaviour_evidence = {
        "behavior_label": "stable",
        "behavior_score": 0.6062,
        "wrong_rate": 0.4,
        "slow_rate": 0.2,
        "low_confidence_rate": 1.0,
        "hint_rate": 0.0,
    }

    view_performance = {
        "status": "success",
        "logged": {
            "teaching_view": "definition_view",
            "reward": 0.4512,
            "outcome_label": "weak_success",
        },
    }

    selector = AdaptivePathSelector()

    output = selector.select_next_path(
        dependency_output=dependency_output,
        mastery=mastery,
        forgetting_priority=forgetting_priority,
        evaluation_evidence=evaluation_evidence,
        behaviour_evidence=behaviour_evidence,
        view_performance=view_performance,
        current_concept_id="1",
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("SELECTED:", output["selected_next_concept"])
    print("DIFFICULTY:", output["recommended_difficulty"])
    print("STRATEGY:", output["recommended_strategy"])
    print("SCORE:", output["selected_score"])
    print("REASON:", output["selected_reason"])

    print("\nRANKED CANDIDATES")
    for item in output["ranked_candidates"]:
        print(item)


if __name__ == "__main__":
    main()