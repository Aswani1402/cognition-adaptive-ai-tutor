from tutor.assessment.structured_question_types import (
    make_debug_question,
    make_output_prediction_question,
    make_syntax_completion_question,
    make_code_writing_question,
    make_drag_order_question,
    make_match_pairs_question,
    make_fill_blank_question,
    make_challenge_question,
    normalize_assessment_bundle_for_frontend,
)


def main():
    concept_id = "1"
    concept_name = "Variables"
    difficulty = "medium"

    questions = [
        make_debug_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            buggy_code='name = Alice"\nprint(name)',
            expected_fix='name = "Alice"\nprint(name)',
            bug_type="string_syntax",
        ),
        make_output_prediction_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            code='name = "Alice"\nprint(name)',
            expected_output="Alice",
        ),
        make_syntax_completion_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            incomplete_code="_____ = 10\nprint(x)",
            missing_part="x",
        ),
        make_code_writing_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            task="Write Python code that stores a name in a variable and prints it.",
            expected_features=["assignment", "print"],
        ),
        make_drag_order_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            prompt="Arrange the steps for using a variable.",
            items=["Assign a value", "Use the variable", "Choose a valid name"],
            correct_order=[2, 0, 1],
        ),
        make_match_pairs_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            prompt="Match each term with its meaning.",
            pairs=[
                {"left": "variable", "right": "name linked to value"},
                {"left": "assignment", "right": "giving a value to a name"},
            ],
        ),
        make_fill_blank_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            sentence="A variable is a ____ linked to a value.",
            blanks=["name"],
        ),
        make_challenge_question(
            concept_id=concept_id,
            concept_name=concept_name,
            difficulty=difficulty,
            challenge_prompt="Create a small billing example using variables.",
            success_criteria=["uses variables", "performs calculation", "prints result"],
        ),
    ]

    bundle = {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": concept_name,
        "difficulty": difficulty,
        "questions": questions,
    }

    normalized = normalize_assessment_bundle_for_frontend(bundle)

    print("\nSTRUCTURED QUESTION TYPES TEST")
    print("Status:", normalized["status"])
    print("Question count:", normalized["question_count"])
    print("Frontend ready:", normalized["frontend_ready"])
    print("Components used:", normalized["frontend_components_used"])

    for q in normalized["questions"]:
        print(
            {
                "type": q["question_type"],
                "component": q["frontend_component"],
                "render_mode": q["metadata"].get("render_mode"),
            }
        )

    assert normalized["frontend_ready"] is True
    assert normalized["question_count"] == 8
    assert all(q.get("frontend_component") for q in normalized["questions"])
    assert all(q.get("metadata", {}).get("render_mode") for q in normalized["questions"])

    print("\nSTATUS: success")
    print("MODULE: structured_question_types")


if __name__ == "__main__":
    main()