from tutor.assessment.adaptive_question_generator import generate_assessment_bundle
from tutor.assessment.learner_answer_simulator import simulate_answers_for_assessment
from tutor.evaluation.mistake_type_classifier import classify_mistakes_for_evaluation


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

    print("\nMISTAKE TYPE CLASSIFIER TEST")
    print("assessment_status:", assessment_output.get("status"))
    print("question_count:", assessment_output.get("question_count"))

    for profile in ["strong", "average", "weak", "debug_weak", "low_confidence"]:
        learner_answers = simulate_answers_for_assessment(
            assessment_output=assessment_output,
            learner_profile=profile,
        )

        fake_evaluation_output = {
            "status": "success",
            "results": []
        }

        for question in assessment_output.get("questions", []):
            q_type = question.get("assessment_type") or question.get("question_type")

            if profile == "strong":
                score = 1.0
            elif profile == "average":
                score = 0.55
            elif profile == "weak":
                score = 0.0
            elif profile == "debug_weak" and q_type == "debug":
                score = 0.2
            elif profile == "low_confidence":
                score = 0.5
            else:
                score = 0.4

            fake_evaluation_output["results"].append(
                {
                    "assessment_type": q_type,
                    "score": score,
                }
            )

        output = classify_mistakes_for_evaluation(
            assessment_output=assessment_output,
            learner_answers=learner_answers,
            evaluation_output=fake_evaluation_output,
        )

        print("\nPROFILE:", profile)
        print("status:", output.get("status"))
        print("module:", output.get("module"))
        print("dominant_mistake_type:", output.get("dominant_mistake_type"))
        print("mistake_type_counts:", output.get("mistake_type_counts"))
        print("high_severity_count:", output.get("high_severity_count"))

        for item in output.get("classified_mistakes", []):
            print(
                item.get("assessment_type"),
                "=>",
                item.get("mistake_type"),
                "| severity:",
                item.get("severity"),
            )

        assert output["status"] == "success"
        assert output["classified_mistakes"]

    print("\nSTATUS: success")
    print("MODULE: mistake_type_classifier")


if __name__ == "__main__":
    main()