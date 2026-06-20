from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment
from tutor.evaluation.debug_answer_evaluator import evaluate_debug_answers_from_assessment


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

    print("\nDEBUG ANSWER EVALUATOR TEST")
    print("assessment_status:", assessment_output.get("status"))
    print("question_count:", assessment_output.get("question_count"))

    for profile in ["strong", "average", "weak", "debug_weak", "low_confidence"]:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        output = evaluate_debug_answers_from_assessment(
            assessment_output=assessment_output,
            learner_answers=learner_answers,
        )

        print("\nPROFILE:", profile)
        print("status:", output.get("status"))
        print("module:", output.get("module"))
        print("debug_question_count:", output.get("debug_question_count"))
        print("overall_score:", output.get("overall_score"))
        print("quality_label:", output.get("quality_label"))

        for item in output.get("results", []):
            print("question_id:", item.get("question_id"))
            print("debug_scores:", item.get("debug_scores"))
            print("feedback:", item.get("feedback"))

        assert output["status"] == "success"
        assert output.get("debug_question_count", 0) >= 1

    print("\nSTATUS: success")
    print("MODULE: debug_answer_evaluator")


if __name__ == "__main__":
    main()