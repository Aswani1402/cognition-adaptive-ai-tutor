from tutor.assessment.expanded_assessment_generator import generate_expanded_assessment_questions
from tutor.evaluation.structured_answer_evaluator import (
    evaluate_structured_answer,
    evaluate_structured_answer_batch,
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
        "fill_blank",
        "drag_order",
        "match_pairs",
        "code_writing",
        "challenge",
    ]

    questions = generate_expanded_assessment_questions(
        concept_resource=concept_resource,
        requested_types=requested_types,
        difficulty="medium",
    )

    sample_answers = {
        "syntax_completion": "x",
        "fill_blank": "name",
        "drag_order": [1, 2, 0],
        "match_pairs": {
            "variable": "name linked to a value",
            "assignment": "giving a value to a name",
            "dynamic typing": "type is decided by assigned value",
        },
        "code_writing": 'name = "Alice"\nprint(name)',
        "challenge": 'I can use a variable like price = 50 and print it. This works because the name stores the value for later use.',
    }

    print("\nSTRUCTURED ANSWER EVALUATOR TEST")

    for question in questions:
        q_type = question.get("question_type")
        result = evaluate_structured_answer(
            question=question,
            learner_answer=sample_answers.get(q_type),
        )

        print(
            {
                "type": q_type,
                "score": result.get("score"),
                "label": result.get("quality_label"),
                "feedback": result.get("feedback"),
            }
        )

        assert result.get("method") == "structured_rule_evaluator"
        assert result.get("score") is not None

    batch_result = evaluate_structured_answer_batch(
        questions=questions,
        learner_answers=sample_answers,
    )

    print("\nBATCH RESULT")
    print("status:", batch_result.get("status"))
    print("overall_score:", batch_result.get("overall_score"))
    print("verdict:", batch_result.get("verdict"))
    print("weak:", batch_result.get("weak_assessment_types"))
    print("strong:", batch_result.get("strong_assessment_types"))

    assert batch_result.get("status") == "success"
    assert batch_result.get("max_score") == len(questions)
    assert batch_result.get("overall_score") >= 0.6

    print("\nSTATUS: success")
    print("MODULE: structured_answer_evaluator")


if __name__ == "__main__":
    main()