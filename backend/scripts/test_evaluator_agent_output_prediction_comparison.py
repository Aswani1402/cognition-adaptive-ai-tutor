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

    print("\nEVALUATOR AGENT OUTPUT PREDICTION COMPARISON TEST")

    for profile in ["strong", "average", "weak", "debug_weak", "low_confidence"]:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        output = evaluator.run(
            assessment_bundle=assessment_output,
            learner_answers=learner_answers,
        )

        evaluation_output = output.get("evaluation", {})
        output_prediction_output = output.get("output_prediction_evaluation_output", {})

        print("\nPROFILE:", profile)
        print("agent_status:", output.get("status"))
        print(
            "output_prediction_evaluation_mode:",
            output.get("output_prediction_evaluation_mode"),
        )

        print("baseline_status:", evaluation_output.get("status"))
        print("baseline_score:", evaluation_output.get("overall_score"))
        print("baseline_verdict:", evaluation_output.get("verdict"))

        print("output_prediction_status:", output_prediction_output.get("status"))
        print(
            "output_prediction_question_count:",
            output_prediction_output.get("output_prediction_question_count"),
        )
        print("output_prediction_score:", output_prediction_output.get("overall_score"))
        print("output_prediction_label:", output_prediction_output.get("quality_label"))
        print(
            "dominant_output_error_type:",
            output_prediction_output.get("dominant_output_error_type"),
        )

        assert output["status"] == "success"
        assert (
            output.get("output_prediction_evaluation_mode")
            == "comparison_only_not_replacing_final_evaluation"
        )
        assert output_prediction_output["status"] == "success"
        assert output_prediction_output.get("output_prediction_question_count", 0) >= 1

    print("\nSTATUS: success")
    print("MODULE: evaluator_agent_output_prediction_comparison")


if __name__ == "__main__":
    main()