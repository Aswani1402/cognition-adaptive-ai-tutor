from tutor.policy.adaptive_policy_bridge import AdaptivePolicyBridge


def main():
    policy_output = {
        "status": "success",
        "data": {
            "next_concept_id": "1",
            "difficulty": "medium",
            "strategy": "practice",
            "decision_type": "dqn_rl_policy_override",
        },
    }

    adaptive_path_output = {
        "status": "success",
        "selected_next_concept": "31",
        "recommended_difficulty": "easy",
        "recommended_strategy": "remedial",
        "selected_score": 0.72,
        "selected_reason": "Selected 31 because mastery is low and review need is high.",
    }

    view_performance_output = {
        "status": "success",
        "logged": {
            "teaching_view": "definition_view",
            "reward": 0.4512,
            "outcome_label": "weak_success",
        },
    }

    evaluation_output = {
        "overall_score": 0.60,
        "verdict": "needs_light_review",
    }

    multi_evidence_output = {
        "final_action": "light_review",
    }

    bridge = AdaptivePolicyBridge()

    output = bridge.reconcile(
        policy_output=policy_output,
        adaptive_path_output=adaptive_path_output,
        view_performance_output=view_performance_output,
        evaluation_output=evaluation_output,
        multi_evidence_output=multi_evidence_output,
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("AGREEMENT:", output["agreement"])
    print("OVERRIDE ALLOWED:", output["override_allowed"])
    print("FINAL RECOMMENDATION:", output["final_recommendation"])
    print("REASON:", output["reason"])
    print("EVIDENCE FLAGS:", output["evidence_flags"])


if __name__ == "__main__":
    main()