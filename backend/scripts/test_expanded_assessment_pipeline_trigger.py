from tutor.assessment.expanded_assessment_generator import attach_expanded_questions_to_bundle


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
                "options": None,
                "correct_option_index": None,
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
                "options": None,
                "correct_option_index": None,
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
    ]

    expanded_bundle = attach_expanded_questions_to_bundle(
        assessment_bundle=base_assessment_bundle,
        concept_resource=concept_resource,
        requested_types=requested_types,
        difficulty="medium",
        max_extra_questions=2,
    )

    print("\nEXPANDED ASSESSMENT PIPELINE TRIGGER TEST")
    print("Status:", expanded_bundle.get("status"))
    print("Question count:", expanded_bundle.get("question_count"))
    print("Frontend ready:", expanded_bundle.get("frontend_ready"))
    print("Expanded added:", expanded_bundle.get("expanded_question_types_added"))
    print("Components used:", expanded_bundle.get("frontend_components_used"))

    print("\nQUESTIONS")
    for q in expanded_bundle.get("questions", []):
        print(
            {
                "type": q.get("question_type"),
                "component": q.get("frontend_component"),
                "render_mode": q.get("metadata", {}).get("render_mode"),
            }
        )

    assert expanded_bundle.get("frontend_ready") is True
    assert expanded_bundle.get("question_count") == 4

    added = expanded_bundle.get("expanded_question_types_added", [])
    assert "syntax_completion" in added
    assert "fill_blank" in added

    types = [
        q.get("question_type")
        for q in expanded_bundle.get("questions", [])
    ]

    assert "debug" in types
    assert "output_prediction" in types
    assert "syntax_completion" in types
    assert "fill_blank" in types

    print("\nSTATUS: success")
    print("MODULE: expanded_assessment_pipeline_trigger")
    print("Expanded assessment trigger works safely.")


if __name__ == "__main__":
    main()