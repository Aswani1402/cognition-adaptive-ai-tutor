from tutor.system.learner_insight_layer import LearnerInsightLayer


def main() -> None:
    layer = LearnerInsightLayer()

    evaluation_output = {
        "overall_score": 0.45,
        "verdict": "needs_review",
        "results": [
            {"assessment_type": "debug", "score": 0.2},
            {"assessment_type": "output_prediction", "score": 0.1},
            {"assessment_type": "explanation", "score": 0.8},
            {"assessment_type": "transfer", "score": 0.85},
        ],
    }

    reflection_output = {
        "status": "success",
        "agent": "ReflectionAgent",
        "reflection": {
            "diagnosis": (
                "Learner understands verbally but struggles with code execution. "
                "Specific mistake patterns detected: output_prediction:wrong_output, "
                "debug:syntax_misunderstanding."
            ),
            "what_next": "Give focused remediation using the exact mistake pattern.",
            "dominant_mistake_type": "wrong_output",
            "mistake_type_counts": {
                "wrong_output": 1,
                "syntax_misunderstanding": 1,
            },
            "high_severity_mistake_count": 2,
            "mistake_focus": [
                "output_prediction:wrong_output",
                "debug:syntax_misunderstanding",
            ],
        },
    }

    mistake_analysis_output = {
        "status": "success",
        "module": "MistakeTypeClassifier",
        "dominant_mistake_type": "wrong_output",
        "mistake_type_counts": {
            "wrong_output": 1,
            "syntax_misunderstanding": 1,
        },
        "high_severity_count": 2,
        "classified_mistakes": [
            {
                "assessment_type": "output_prediction",
                "mistake_type": "wrong_output",
                "severity": "high",
            },
            {
                "assessment_type": "debug",
                "mistake_type": "syntax_misunderstanding",
                "severity": "high",
            },
        ],
    }

    output = layer.build(
        evaluation=evaluation_output,
        reflection_output=reflection_output,
        mistake_analysis_output=mistake_analysis_output,
    )

    profile = output.get("learner_profile_live", {})

    print("\nLEARNER INSIGHT MISTAKE-AWARE TEST")
    print("status:", output.get("status"))
    print("module:", output.get("module"))
    print("strengths:", profile.get("strengths"))
    print("weaknesses:", profile.get("weaknesses"))
    print("learning_pattern:", profile.get("learning_pattern"))
    print("recommended_focus:", profile.get("recommended_focus"))
    print("dominant_mistake_type:", profile.get("dominant_mistake_type"))
    print("mistake_type_counts:", profile.get("mistake_type_counts"))
    print("high_severity_mistake_count:", profile.get("high_severity_mistake_count"))
    print("mistake_focus:", profile.get("mistake_focus"))

    assert output["status"] == "success"
    assert profile.get("dominant_mistake_type") == "wrong_output"
    assert "debug" in profile.get("weaknesses", [])
    assert "output_prediction" in profile.get("weaknesses", [])
    assert profile.get("mistake_focus")

    print("\nSTATUS: success")
    print("MODULE: learner_insight_mistake_aware")


if __name__ == "__main__":
    main()