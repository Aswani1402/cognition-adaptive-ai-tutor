from tutor.evaluation.evaluation_fusion_engine import fuse_evaluation_outputs


def main() -> None:
    baseline_evaluation_output = {
        "status": "success",
        "overall_score": 0.6,
        "verdict": "needs_light_review",
    }

    rubric_evaluation_output = {
        "status": "success",
        "overall_score": 0.2785,
        "verdict": "weak",
        "weak_assessment_types": [
            "mcq",
            "output_prediction",
            "debug",
            "short_explanation",
        ],
    }

    debug_evaluation_output = {
        "status": "success",
        "overall_score": 0.48,
        "quality_label": "partial",
        "debug_question_count": 1,
    }

    output_prediction_evaluation_output = {
        "status": "success",
        "overall_score": 0.15,
        "quality_label": "weak",
        "dominant_output_error_type": "numeric_instead_of_text",
        "output_prediction_question_count": 1,
    }

    mistake_analysis_output = {
        "status": "success",
        "dominant_mistake_type": "wrong_output",
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

    output = fuse_evaluation_outputs(
        baseline_evaluation_output=baseline_evaluation_output,
        rubric_evaluation_output=rubric_evaluation_output,
        debug_evaluation_output=debug_evaluation_output,
        output_prediction_evaluation_output=output_prediction_evaluation_output,
        mistake_analysis_output=mistake_analysis_output,
    )

    print("\nEVALUATION FUSION ENGINE TEST")
    print("status:", output.get("status"))
    print("module:", output.get("module"))
    print("mode:", output.get("mode"))
    print("fused_score:", output.get("fused_score"))
    print("fused_label:", output.get("fused_label"))
    print("recommended_learning_signal:", output.get("recommended_learning_signal"))
    print("fusion_confidence:", output.get("fusion_confidence"))
    print("fusion_confidence_label:", output.get("fusion_confidence_label"))
    print("evaluator_scores:", output.get("evaluator_scores"))
    print("evaluator_agreement:", output.get("evaluator_agreement"))
    print("weakest_skill_signal:", output.get("weakest_skill_signal"))
    print("dominant_mistake_type:", output.get("dominant_mistake_type"))
    print("high_severity_mistake_count:", output.get("high_severity_mistake_count"))
    print("reason:", output.get("reason"))

    assert output["status"] == "success"
    assert output["mode"] == "comparison_only_not_replacing_final_evaluation"
    assert output.get("fused_score") is not None
    assert output.get("recommended_learning_signal") in {
        "focused_remediation",
        "targeted_reteaching",
        "ready_to_progress",
        "light_review_then_progress",
        "guided_practice",
        "reteach_with_support",
    }
    assert output.get("weakest_skill_signal", {}).get("weakest_skill")

    print("\nSTATUS: success")
    print("MODULE: evaluation_fusion_engine")


if __name__ == "__main__":
    main()