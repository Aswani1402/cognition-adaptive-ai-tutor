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

    print("\nEVALUATOR AGENT DEBUG COMPARISON TEST")

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
        debug_output = output.get("debug_evaluation_output", {})

        print("\nPROFILE:", profile)
        print("agent_status:", output.get("status"))
        print("debug_evaluation_mode:", output.get("debug_evaluation_mode"))

        print("baseline_status:", evaluation_output.get("status"))
        print("baseline_score:", evaluation_output.get("overall_score"))
        print("baseline_verdict:", evaluation_output.get("verdict"))

        print("debug_status:", debug_output.get("status"))
        print("debug_question_count:", debug_output.get("debug_question_count"))
        print("debug_score:", debug_output.get("overall_score"))
        print("debug_label:", debug_output.get("quality_label"))

        assert output["status"] == "success"
        assert output.get("debug_evaluation_mode") == "comparison_only_not_replacing_final_evaluation"
        assert debug_output["status"] == "success"
        assert debug_output.get("debug_question_count", 0) >= 1

    print("\nSTATUS: success")
    print("MODULE: evaluator_agent_debug_comparison")


if __name__ == "__main__":
    main()