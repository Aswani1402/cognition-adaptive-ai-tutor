from tutor.system.reflection_agent import ReflectionAgent


def main() -> None:
    agent = ReflectionAgent()

    evaluation_output = {
        "overall_score": 0.45,
        "verdict": "needs_review",
        "results": [
            {"assessment_type": "debug", "score": 0.2},
            {"assessment_type": "output_prediction", "score": 0.1},
            {"assessment_type": "explanation", "score": 0.8},
        ],
    }

    multi_evidence_output = {
        "evidence_summary": {
            "mastery_score": 0.52,
            "behavior_label": "stable",
            "evaluation_score": 0.45,
        },
        "final_action": "review",
    }

    policy_output = {
        "data": {
            "strategy": "practice",
            "difficulty": "medium",
        }
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

    output = agent.reflect(
        evaluation=evaluation_output,
        multi_evidence=multi_evidence_output,
        policy_output=policy_output,
        mistake_analysis_output=mistake_analysis_output,
    )

    reflection = output.get("reflection", {})

    print("\nREFLECTION AGENT MISTAKE-AWARE TEST")
    print("status:", output.get("status"))
    print("agent:", output.get("agent"))
    print("diagnosis:", reflection.get("diagnosis"))
    print("dominant_mistake_type:", reflection.get("dominant_mistake_type"))
    print("mistake_type_counts:", reflection.get("mistake_type_counts"))
    print("high_severity_mistake_count:", reflection.get("high_severity_mistake_count"))
    print("mistake_focus:", reflection.get("mistake_focus"))
    print("what_next:", reflection.get("what_next"))

    assert output["status"] == "success"
    assert reflection.get("dominant_mistake_type") == "wrong_output"
    assert reflection.get("high_severity_mistake_count") == 2
    assert reflection.get("mistake_focus")

    print("\nSTATUS: success")
    print("MODULE: reflection_agent_mistake_aware")


if __name__ == "__main__":
    main()