from tutor.agents.evaluator_agent import EvaluatorAgent
from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment


def main() -> None:
    concept_resource = {
        "concept_id": "1",
        "concept_name": "Variables",
        "definition": "A variable is a named storage location that holds a value.",
        "examples": ['name = "Alice"\nprint(name)'],
        "key_points": [
            "A variable is a name bound to an object in memory",
            "Python uses dynamic typing",
            "Variables are case-sensitive",
        ],
        "misconceptions": [
            "Variables can be used before assignment",
        ],
    }

    assessment_output = generate_assessment_bundle(
        concept_resource=concept_resource,
        difficulty="medium",
        requested_types=[
            "mcq",
            "debug",
            "output_prediction",
            "short_explanation",
            "transfer",
        ],
    )

    evaluator = EvaluatorAgent()

    print("\nEVALUATOR AGENT EVALUATION FUSION TEST")

    for profile in ["strong", "average", "weak", "debug_weak", "low_confidence"]:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        output = evaluator.run(
            assessment_bundle=assessment_output,
            learner_answers=learner_answers,
        )

        baseline = output.get("evaluation", {})
        fusion = output.get("evaluation_fusion_output", {})

        print("\nPROFILE:", profile)
        print("agent_status:", output.get("status"))
        print("evaluation_fusion_mode:", output.get("evaluation_fusion_mode"))

        print("baseline_score:", baseline.get("overall_score"))
        print("baseline_verdict:", baseline.get("verdict"))

        print("fusion_status:", fusion.get("status"))
        print("fused_score:", fusion.get("fused_score"))
        print("fused_label:", fusion.get("fused_label"))
        print("recommended_learning_signal:", fusion.get("recommended_learning_signal"))
        print("fusion_confidence:", fusion.get("fusion_confidence"))
        print("fusion_confidence_label:", fusion.get("fusion_confidence_label"))
        print("evaluator_agreement:", fusion.get("evaluator_agreement"))
        print("weakest_skill_signal:", fusion.get("weakest_skill_signal"))
        print("dominant_mistake_type:", fusion.get("dominant_mistake_type"))

        assert output["status"] == "success"
        assert (
            output.get("evaluation_fusion_mode")
            == "comparison_only_not_replacing_final_evaluation"
        )
        assert fusion["status"] == "success"
        assert fusion.get("fused_score") is not None
        assert fusion.get("recommended_learning_signal") is not None

    print("\nSTATUS: success")
    print("MODULE: evaluator_agent_evaluation_fusion")


if __name__ == "__main__":
    main()