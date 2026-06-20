from tutor.memory.learner_notebook_memory import LearnerNotebookMemory


def main() -> None:
    memory = LearnerNotebookMemory()

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

    learner_insight_output = {
        "status": "success",
        "module": "LearnerInsightLayer",
        "learner_profile_live": {
            "strengths": ["explanation", "transfer"],
            "weaknesses": ["debug", "output_prediction"],
            "learning_pattern": (
                "Learner understands verbally but struggles with code execution."
            ),
            "recommended_focus": (
                "Focus on output prediction and code tracing practice."
            ),
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

    view_performance_output = {
        "logged": {
            "teaching_view": "debug_view",
            "reward": 0.45,
            "outcome_label": "needs_review",
            "difficulty": "medium",
        }
    }

    xai_output = {
        "status": "success",
        "data": {
            "reason": "Evaluation and mistake analysis indicate code tracing support is needed.",
            "evidence": {
                "feature_contributions": {
                    "decision_pressure_label": "support_needed",
                    "total_decision_pressure": 0.72,
                    "top_factors": [
                        {"feature": "evaluation_need"},
                        {"feature": "view_reward_need"},
                    ],
                }
            },
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

    output = memory.update_memory(
        learner_id="14",
        concept_id="1",
        concept_name="Variables",
        evaluation_output=evaluation_output,
        reflection_output=reflection_output,
        learner_insight_output=learner_insight_output,
        view_performance_output=view_performance_output,
        xai_output=xai_output,
        mistake_analysis_output=mistake_analysis_output,
    )

    print("\nLEARNER NOTEBOOK MEMORY MISTAKE-AWARE TEST")
    print("status:", output.get("status"))
    print("module:", output.get("module"))
    print("memory_id:", output.get("memory_id"))
    print("notebook_summary:", output.get("notebook_summary"))
    print("dominant_mistake_type:", output.get("dominant_mistake_type"))
    print("mistake_type_counts:", output.get("mistake_type_counts"))
    print("high_severity_mistake_count:", output.get("high_severity_mistake_count"))
    print("mistake_focus:", output.get("mistake_focus"))
    print("revision_plan:", output.get("revision_plan"))
    print("next_practice_queue:", output.get("next_practice_queue"))

    assert output["status"] == "success"
    assert output.get("dominant_mistake_type") == "wrong_output"
    assert output.get("mistake_focus")
    assert "Dominant mistake type: wrong_output" in output.get("notebook_summary", "")
    assert "Mistake focus:" in output.get("notebook_summary", "")

    latest = memory.get_latest_memory(learner_id="14", limit=1)
    latest_memory = latest.get("memories", [{}])[0]

    print("\nLATEST MEMORY CHECK")
    print("memory_count:", latest.get("memory_count"))
    print("latest_dominant_mistake_type:", latest_memory.get("dominant_mistake_type"))
    print("latest_mistake_focus:", latest_memory.get("mistake_focus"))

    assert latest["status"] == "success"
    assert latest.get("memory_count", 0) >= 1
    assert latest_memory.get("dominant_mistake_type") == "wrong_output"
    assert latest_memory.get("mistake_focus")

    print("\nSTATUS: success")
    print("MODULE: learner_notebook_memory_mistake_aware")


if __name__ == "__main__":
    main()