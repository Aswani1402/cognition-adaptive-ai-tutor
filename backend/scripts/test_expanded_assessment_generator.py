from tutor.assessment.expanded_assessment_generator import (
    generate_expanded_assessment_questions,
    attach_expanded_questions_to_bundle,
)


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

    requested_types = [
        "syntax_completion",
        "code_writing",
        "drag_order",
        "match_pairs",
        "fill_blank",
        "challenge",
    ]

    questions = generate_expanded_assessment_questions(
        concept_resource=concept_resource,
        requested_types=requested_types,
        difficulty="medium",
    )

    print("\nEXPANDED ASSESSMENT GENERATOR TEST")
    print("Generated count:", len(questions))

    for q in questions:
        print(
            {
                "type": q.get("question_type"),
                "component": q.get("frontend_component"),
                "render_mode": q.get("metadata", {}).get("render_mode"),
                "prompt": q.get("prompt"),
            }
        )

    assert len(questions) == 6
    assert all(q.get("frontend_component") for q in questions)
    assert all(q.get("metadata", {}).get("render_mode") for q in questions)

    base_bundle = {
        "status": "success",
        "concept_id": "1",
        "concept_name": "Variables",
        "difficulty": "medium",
        "questions": [],
    }

    expanded_bundle = attach_expanded_questions_to_bundle(
        assessment_bundle=base_bundle,
        concept_resource=concept_resource,
        requested_types=requested_types,
        difficulty="medium",
        max_extra_questions=6,
    )

    print("\nBUNDLE")
    print("question_count:", expanded_bundle.get("question_count"))
    print("frontend_ready:", expanded_bundle.get("frontend_ready"))
    print("expanded_added:", expanded_bundle.get("expanded_question_types_added"))
    print("components:", expanded_bundle.get("frontend_components_used"))

    assert expanded_bundle.get("frontend_ready") is True
    assert expanded_bundle.get("question_count") == 6
    assert len(expanded_bundle.get("expanded_question_types_added", [])) == 6

    print("\nSTATUS: success")
    print("MODULE: expanded_assessment_generator")


if __name__ == "__main__":
    main()