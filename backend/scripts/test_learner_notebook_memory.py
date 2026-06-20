from tutor.memory.learner_notebook_memory import LearnerNotebookMemory


def main():
    memory = LearnerNotebookMemory()

    evaluation_output = {
        "overall_score": 0.6,
        "verdict": "needs_light_review",
        "feedback_summary": "Needs improvement in: output_prediction, debug",
        "results": [
            {
                "assessment_type": "mcq",
                "prompt": "Choose the correct statement.",
                "learner_answer": "A variable stores a value.",
                "expected_answer": "A variable is a named storage location.",
                "score": 1.0,
                "feedback": "Correct answer.",
            },
            {
                "assessment_type": "output_prediction",
                "prompt": "What is the output?",
                "learner_answer": "15",
                "expected_answer": "Alice",
                "score": 0.0,
                "feedback": "Expected output: Alice",
            },
            {
                "assessment_type": "debug",
                "prompt": "Find the mistake.",
                "learner_answer": "Use x instead of x1.",
                "expected_answer": "Fix the string quotes.",
                "score": 0.0,
                "feedback": "Expected fix: Fix the string quotes.",
            },
            {
                "assessment_type": "explanation",
                "prompt": "Explain variables.",
                "learner_answer": "A variable stores a value.",
                "expected_answer": "A variable is a named storage location.",
                "score": 1.0,
                "feedback": "Good explanation.",
            },
            {
                "assessment_type": "transfer",
                "prompt": "Apply variables.",
                "learner_answer": "Variables store prices.",
                "expected_answer": "Variables store reusable values.",
                "score": 1.0,
                "feedback": "Good application.",
            },
        ],
    }

    reflection_output = {
        "status": "success",
        "reflection": {
            "diagnosis": "Learner understands the concept verbally but struggles with code execution and debugging.",
            "what_next": "Give short code tracing and debugging practice.",
        },
    }

    learner_insight_output = {
        "status": "success",
        "learner_profile_live": {
            "strengths": ["mcq", "explanation", "transfer"],
            "weaknesses": ["output_prediction", "debug"],
            "learning_pattern": "Learner understands verbal meaning but struggles with code execution.",
            "recommended_focus": "Give short code tracing and debugging practice.",
        },
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

    xai_output = {
        "status": "success",
        "data": {
            "reason": "Policy selected concept 1. Top factors were mastery_need, evaluation_need, view_reward_need.",
            "evidence": {
                "feature_contributions": {
                    "decision_pressure_label": "low_support_needed",
                    "total_decision_pressure": 0.3958,
                    "top_factors": [
                        {"feature": "mastery_need"},
                        {"feature": "evaluation_need"},
                        {"feature": "view_reward_need"},
                    ],
                }
            },
        },
    }

    output = memory.update_memory(
        learner_id=14,
        concept_id="1",
        concept_name="Variables",
        evaluation_output=evaluation_output,
        reflection_output=reflection_output,
        learner_insight_output=learner_insight_output,
        view_performance_output=view_performance_output,
        xai_output=xai_output,
    )

    print("\nSTATUS:", output["status"])
    print("MODULE:", output["module"])
    print("MEMORY ID:", output["memory_id"])
    print("\nSUMMARY:")
    print(output["notebook_summary"])

    print("\nWEAK TYPES:", output["weak_assessment_types"])
    print("STRENGTHS:", output["strengths"])

    print("\nREVISION PLAN:")
    for item in output["revision_plan"]:
        print(item)

    print("\nNEXT PRACTICE QUEUE:")
    for item in output["next_practice_queue"]:
        print(item)

    latest = memory.get_latest_memory(learner_id=14, limit=2)

    print("\nLATEST MEMORY:")
    print(latest)


if __name__ == "__main__":
    main()