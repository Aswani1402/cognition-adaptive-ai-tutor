from tutor.assessment.expanded_assessment_generator import attach_expanded_questions_to_bundle
from tutor.evaluation.structured_evaluation_bridge import run_structured_evaluation_bridge


def main():
    concept_resource = {
        "concept_id": "1",
        "concept_name": "Variables",
        "definition": "A variable is a name linked to a value.",
        "syntax": "variable_name = value",
        "examples": ['name = "Alice"\nprint(name)'],
        "key_points": [
            "A variable is a name bound to an object in memory",
            "Python uses dynamic typing",
            "Variables are case-sensitive",
        ],
    }

    base_assessment_bundle = {
        "status": "success",
        "concept_id": "1",
        "concept_name": "Variables",
        "difficulty": "medium",
        "questions": [
            {
                "question_id": "1_debug_base",
                "concept_id": "1",
                "concept_name": "Variables",
                "question_type": "debug",
                "assessment_type": "debug",
                "difficulty": "medium",
                "prompt": 'Find the mistake:\n\nname = Alice"\nprint(name)',
                "expected_answer": {
                    "bug_category": "string_syntax",
                    "fix_text": 'name = "Alice"\nprint(name)',
                },
                "metadata": {
                    "buggy_code": 'name = Alice"\nprint(name)',
                    "bug_category": "string_syntax",
                },
            },
            {
                "question_id": "1_output_prediction_base",
                "concept_id": "1",
                "concept_name": "Variables",
                "question_type": "output_prediction",
                "assessment_type": "output_prediction",
                "difficulty": "medium",
                "prompt": 'What is the output?\n\nname = "Alice"\nprint(name)',
                "expected_answer": "Alice",
                "metadata": {
                    "code": 'name = "Alice"\nprint(name)',
                },
            },
        ],
    }

    requested_types = [
        "debug",
        "output_prediction",
        "syntax_completion",
        "fill_blank",
        "drag_order",
        "match_pairs",
    ]

    assessment_output = attach_expanded_questions_to_bundle(
        assessment_bundle=base_assessment_bundle,
        concept_resource=concept_resource,
        requested_types=requested_types,
        difficulty="medium",
        max_extra_questions=4,
    )

    bridge_output = run_structured_evaluation_bridge(
        assessment_output=assessment_output,
        learner_answers=None,
        use_simulated_answers=True,
    )

    print("\nSTRUCTURED EVALUATION BRIDGE TEST")
    print("Status:", bridge_output.get("status"))
    print("Module:", bridge_output.get("module"))
    print("Structured question count:", bridge_output.get("structured_question_count"))
    print("Structured question types:", bridge_output.get("structured_question_types"))
    print("Used simulated answers:", bridge_output.get("used_simulated_answers"))

    evaluation = bridge_output.get("evaluation") or {}

    print("\nEVALUATION")
    print("status:", evaluation.get("status"))
    print("overall_score:", evaluation.get("overall_score"))
    print("verdict:", evaluation.get("verdict"))
    print("weak:", evaluation.get("weak_assessment_types"))
    print("strong:", evaluation.get("strong_assessment_types"))

    for result in evaluation.get("results", []):
        print(
            {
                "type": result.get("assessment_type"),
                "score": result.get("score"),
                "label": result.get("quality_label"),
                "method": result.get("method"),
            }
        )

    assert bridge_output.get("status") == "success"
    assert bridge_output.get("structured_question_count") == 4
    assert bridge_output.get("used_simulated_answers") is True

    assert evaluation.get("status") == "success"
    assert evaluation.get("overall_score") >= 0.7

    print("\nSTATUS: success")
    print("MODULE: structured_evaluation_bridge")


if __name__ == "__main__":
    main()