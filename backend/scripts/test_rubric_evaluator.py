from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment
from tutor.evaluation.rubric_evaluator import evaluate_answers_with_rubric


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

    print("\nRUBRIC EVALUATOR TEST")
    print("assessment_status:", assessment_output.get("status"))
    print("question_count:", assessment_output.get("question_count"))

    for profile in ["strong", "average", "weak", "debug_weak", "low_confidence"]:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        output = evaluate_answers_with_rubric(
            assessment_output=assessment_output,
            learner_answers=learner_answers,
        )

        print("\nPROFILE:", profile)
        print("status:", output.get("status"))
        print("module:", output.get("module"))
        print("overall_score:", output.get("overall_score"))
        print("verdict:", output.get("verdict"))
        print("weak_assessment_types:", output.get("weak_assessment_types"))
        print("strong_assessment_types:", output.get("strong_assessment_types"))

        for item in output.get("results", []):
            print(
                item.get("assessment_type"),
                "score:",
                item.get("overall_score"),
                "label:",
                item.get("quality_label"),
                "rubric:",
                item.get("rubric_scores"),
            )

        assert output["status"] == "success"
        assert output["results"]

    print("\nSTATUS: success")
    print("MODULE: rubric_evaluator")


if __name__ == "__main__":
    main()