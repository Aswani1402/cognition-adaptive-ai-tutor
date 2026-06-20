from __future__ import annotations

from tutor.evaluation.answer_evaluator import AnswerEvaluator


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    evaluator = AnswerEvaluator()

    mcq_correct = evaluator.evaluate(
        {
            "question_id": "A1",
            "question_type": "mcq",
            "selected_option": "B",
            "correct_answer": "B",
        }
    )
    _assert(mcq_correct["correct"], f"mcq correct failed: {mcq_correct}")

    mcq_wrong = evaluator.evaluate(
        {
            "question_id": "A2",
            "assessment_type": "mcq",
            "selected_option": "A",
            "correct_answer": "B",
        }
    )
    _assert(not mcq_wrong["correct"], f"mcq wrong passed: {mcq_wrong}")

    output_correct = evaluator.evaluate(
        {
            "question_id": "A3",
            "task_type": "output_prediction",
            "expected_output": "10",
            "learner_answer": "10",
        }
    )
    _assert(output_correct["correct"], f"output prediction correct failed: {output_correct}")

    output_wrong = evaluator.evaluate(
        {
            "question_id": "A4",
            "task_type": "output_prediction",
            "expected_output": "10",
            "learner_answer": "9",
        }
    )
    _assert(not output_wrong["correct"], f"output prediction wrong passed: {output_wrong}")

    debug_code = evaluator.evaluate(
        {
            "question_id": "A5",
            "task_type": "debug_task",
            "corrected_code": "x = 5\nprint(x)",
            "expected_output": "5",
            "expected_fix": "Use x instead of y.",
        }
    )
    _assert(debug_code["correct"], f"debug corrected code failed: {debug_code}")

    coding = evaluator.evaluate(
        {
            "question_id": "A6",
            "task_type": "coding_question",
            "learner_answer": "print(10)",
            "expected_output": "10",
        }
    )
    _assert(coding["correct"], f"coding question failed: {coding}")

    syntax_completion = evaluator.evaluate(
        {
            "question_id": "A7",
            "task_type": "syntax_completion",
            "starter_code": "x = ",
            "learner_answer": "10\nprint(x)",
            "expected_output": "10",
        }
    )
    _assert(syntax_completion["correct"], f"syntax completion failed: {syntax_completion}")

    explanation = evaluator.evaluate(
        {
            "question_id": "A8",
            "task_type": "explanation",
            "learner_answer": "A variable is a named value stored so a program can reuse it later.",
            "expected_answer": "A variable stores a value and can be reused later in a program.",
        }
    )
    _assert(explanation["score"] >= 0.45, f"explanation too weak: {explanation}")

    transfer = evaluator.evaluate(
        {
            "question_id": "A9",
            "task_type": "transfer_question",
            "learner_answer": "Use variables to store prices and quantities, then calculate a bill total.",
            "expected_answer": "Variables can store real-world values such as prices and quantities for later calculations.",
        }
    )
    _assert(transfer["routed_to"] == "SemanticAnswerEvaluator+RubricEvaluator", f"transfer not semantic routed: {transfer}")
    _assert(transfer["score"] >= 0.45, f"transfer too weak: {transfer}")

    challenge_code = evaluator.evaluate(
        {
            "question_id": "A10",
            "task_type": "challenge",
            "learner_answer": "total = 7 + 3\nprint(total)",
            "expected_output": "10",
        }
    )
    _assert(challenge_code["correct"], f"challenge code failed: {challenge_code}")
    _assert(challenge_code["routed_to"] == "CodeQuestionEvaluator", f"challenge not code routed: {challenge_code}")

    unsafe = evaluator.evaluate(
        {
            "question_id": "A11",
            "task_type": "coding_question",
            "learner_answer": "import os\nprint(os.getcwd())",
            "expected_output": "",
        }
    )
    _assert(unsafe["mistake_type"] == "unsafe_code", f"unsafe code not blocked: {unsafe}")

    print("mcq_correct:", mcq_correct["label"])
    print("mcq_wrong:", mcq_wrong["mistake_type"])
    print("output_prediction_correct:", output_correct["label"])
    print("output_prediction_wrong:", output_wrong["mistake_type"])
    print("debug_task_corrected_code:", debug_code["label"])
    print("coding_question_correct:", coding["label"])
    print("syntax_completion_correct:", syntax_completion["label"])
    print("explanation:", explanation["label"])
    print("transfer_question:", transfer["label"])
    print("challenge_with_code:", challenge_code["label"])
    print("unsafe_code:", unsafe["mistake_type"])
    print("STATUS: success")
    print("MODULE: answer_evaluator_test")


if __name__ == "__main__":
    main()
