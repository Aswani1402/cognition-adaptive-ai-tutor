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

    learner_answers = simulate_answers_for_assessment(
        assessment_output=assessment_output,
        learner_profile="weak",
    )

    evaluator = EvaluatorAgent()

    output = evaluator.run(
        assessment_bundle=assessment_output,
        learner_answers=learner_answers,
    )

    mistake_output = output.get("mistake_analysis_output", {})

    print("\nEVALUATOR AGENT MISTAKE ANALYSIS TEST")
    print("status:", output.get("status"))
    print("agent:", output.get("agent"))
    print("evaluation_status:", output.get("evaluation", {}).get("status"))
    print("learning_signal:", output.get("learning_signal"))

    print("\nMISTAKE ANALYSIS")
    print("status:", mistake_output.get("status"))
    print("module:", mistake_output.get("module"))
    print("dominant_mistake_type:", mistake_output.get("dominant_mistake_type"))
    print("mistake_type_counts:", mistake_output.get("mistake_type_counts"))
    print("high_severity_count:", mistake_output.get("high_severity_count"))

    for item in mistake_output.get("classified_mistakes", []):
        print(
            item.get("assessment_type"),
            "=>",
            item.get("mistake_type"),
            "| severity:",
            item.get("severity"),
        )

    assert output["status"] == "success"
    assert mistake_output["status"] == "success"
    assert mistake_output["classified_mistakes"]
    assert mistake_output["high_severity_count"] >= 1

    print("\nSTATUS: success")
    print("MODULE: evaluator_agent_mistake_analysis")


if __name__ == "__main__":
    main()