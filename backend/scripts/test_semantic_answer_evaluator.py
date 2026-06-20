from __future__ import annotations

from tutor.evaluation.semantic_answer_evaluator import SemanticAnswerEvaluator


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    evaluator = SemanticAnswerEvaluator()

    cases = [
        (
            "correct_explanation_strong",
            {
                "learner_answer": "A variable stores a value with a name so the program can reuse that value later.",
                "expected_answer": "A variable stores a value with a name so it can be reused later in a program.",
                "key_points": ["stores a value", "has a name", "can be reused later"],
                "concept_name": "variable",
                "task_type": "explanation",
            },
            0.80,
            "strong",
        ),
        (
            "partial_explanation",
            {
                "learner_answer": "A variable stores data.",
                "expected_answer": "A variable stores a value with a name so it can be reused later.",
                "key_points": ["stores a value", "has a name", "can be reused later"],
                "concept_name": "variable",
                "task_type": "explanation_check",
            },
            0.35,
            "partial",
        ),
        (
            "irrelevant_explanation",
            {
                "learner_answer": "The weather is cold and the sky is blue.",
                "expected_answer": "A loop repeats a block of code while a condition is true.",
                "key_points": ["repeats code", "condition controls the loop"],
                "concept_name": "loop",
                "task_type": "explanation",
            },
            0.0,
            "weak",
        ),
        (
            "transfer_question_strong",
            {
                "learner_answer": "In a billing program, variables can store price and quantity, then reuse them to calculate the total.",
                "expected_answer": "Variables can store real-world values such as prices and quantities for later calculations.",
                "key_points": ["store prices", "store quantities", "calculate total"],
                "concept_name": "variables",
                "task_type": "transfer_question",
            },
            0.65,
            "partial",
        ),
        (
            "transfer_question_partial",
            {
                "learner_answer": "Use a variable for the price.",
                "expected_answer": "Variables can store prices and quantities and reuse them in a calculation.",
                "key_points": ["store prices", "store quantities", "reuse in calculation"],
                "concept_name": "variables",
                "task_type": "transfer_question",
            },
            0.25,
            "weak",
        ),
        (
            "short_vague_answer",
            {
                "learner_answer": "It stores things.",
                "expected_answer": "A variable stores a named value so it can be reused.",
                "key_points": ["named value", "reused"],
                "concept_name": "variable",
                "task_type": "explanation",
            },
            0.10,
            "weak",
        ),
        (
            "empty_answer",
            {
                "learner_answer": "",
                "expected_answer": "A function groups reusable code.",
                "key_points": ["groups code", "reusable"],
                "concept_name": "function",
                "task_type": "explanation",
            },
            0.0,
            "weak",
        ),
        (
            "challenge_text_answer",
            {
                "learner_answer": "First initialize the total, then loop through each number and add it to the total.",
                "expected_answer": "Initialize an accumulator, iterate through the numbers, and update the accumulator each step.",
                "key_points": ["initialize accumulator", "iterate numbers", "update total"],
                "concept_name": "accumulator loop",
                "task_type": "challenge_question",
            },
            0.45,
            "partial",
        ),
        (
            "rubric_fusion_case",
            {
                "learner_answer": "A list stores multiple values in order and can be indexed.",
                "expected_answer": "A list stores multiple ordered values and supports indexing.",
                "key_points": ["multiple values", "ordered", "indexing"],
                "concept_name": "list",
                "task_type": "explanation",
                "rubric_output": {"overall_score": 0.9},
            },
            0.75,
            "partial",
        ),
    ]

    outputs = []
    for name, kwargs, min_score, expected_min_label in cases:
        rubric_output = kwargs.pop("rubric_output", None)
        output = evaluator.evaluate(**kwargs, rubric_output=rubric_output)
        outputs.append((name, output))
        _assert(output["status"] == "success", f"{name} failed: {output}")
        _assert(0.0 <= output["score"] <= 1.0, f"{name} score out of range: {output}")
        _assert(output["score"] >= min_score, f"{name} score too low: {output}")
        if name in {"irrelevant_explanation", "short_vague_answer", "empty_answer"}:
            _assert(output["label"] == "weak", f"{name} should be weak: {output}")
        if name == "correct_explanation_strong":
            _assert(output["label"] == "strong", f"{name} should be strong: {output}")
        _assert(output["method"] in {"embedding_cosine", "tfidf_cosine", "token_overlap", "empty_answer", "empty_reference"}, f"{name} method invalid: {output}")

    for name, output in outputs:
        print(f"{name}: score={output['score']} label={output['label']} method={output['method']}")
    print("STATUS: success")
    print("MODULE: semantic_answer_evaluator_test")


if __name__ == "__main__":
    main()
