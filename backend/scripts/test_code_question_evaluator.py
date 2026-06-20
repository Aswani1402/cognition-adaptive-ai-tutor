from __future__ import annotations

from tutor.evaluation.code_question_evaluator import CodeQuestionEvaluator
from tutor.evaluation.code_runner import SafeCodeRunner


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    evaluator = CodeQuestionEvaluator(
        runner=SafeCodeRunner(timeout_seconds=1.0, max_output_chars=1000)
    )

    coding_correct = evaluator.evaluate(
        {
            "question_id": "Q1",
            "task_type": "coding_question",
            "learner_answer": "print(10)",
            "expected_output": "10",
        }
    )
    _assert(coding_correct["correct"], f"coding correct failed: {coding_correct}")

    coding_wrong = evaluator.evaluate(
        {
            "question_id": "Q2",
            "task_type": "coding_question",
            "learner_answer": "print(9)",
            "expected_output": "10",
        }
    )
    _assert(not coding_wrong["correct"], f"coding wrong unexpectedly passed: {coding_wrong}")
    _assert(coding_wrong["mistake_type"] == "wrong_output", f"wrong mistake type: {coding_wrong}")

    syntax_completion = evaluator.evaluate(
        {
            "question_id": "Q3",
            "task_type": "syntax_completion",
            "starter_code": "x = ",
            "learner_answer": "10\nprint(x)",
            "expected_output": "10",
        }
    )
    _assert(syntax_completion["correct"], f"syntax completion failed: {syntax_completion}")

    debug_passes = evaluator.evaluate(
        {
            "question_id": "Q4",
            "task_type": "debug_task",
            "buggy_code": "x = 5\nprint(y)",
            "expected_fix": "Use x instead of y.",
            "corrected_code": "x = 5\nprint(x)",
            "expected_output": "5",
        }
    )
    _assert(debug_passes["correct"], f"debug task failed: {debug_passes}")

    debug_unsafe = evaluator.evaluate(
        {
            "question_id": "Q5",
            "task_type": "debug_task",
            "corrected_code": "import os\nprint(os.getcwd())",
            "expected_output": "",
        }
    )
    _assert(debug_unsafe["mistake_type"] == "unsafe_code", f"debug unsafe not blocked: {debug_unsafe}")

    output_prediction_correct = evaluator.evaluate(
        {
            "question_id": "Q6",
            "task_type": "output_prediction",
            "code": "print('A')",
            "learner_answer": "A",
        }
    )
    _assert(output_prediction_correct["correct"], f"output prediction correct failed: {output_prediction_correct}")

    output_prediction_wrong = evaluator.evaluate(
        {
            "question_id": "Q7",
            "task_type": "output_prediction",
            "code": "print('A')",
            "learner_answer": "B",
        }
    )
    _assert(not output_prediction_wrong["correct"], f"output prediction wrong passed: {output_prediction_wrong}")
    _assert(output_prediction_wrong["mistake_type"] == "wrong_output", f"wrong output prediction type: {output_prediction_wrong}")

    runtime_error = evaluator.evaluate(
        {
            "question_id": "Q8",
            "task_type": "coding_question",
            "learner_answer": "print(1 / 0)",
            "expected_output": "0",
        }
    )
    _assert(runtime_error["mistake_type"] == "runtime_error", f"runtime error not captured: {runtime_error}")

    syntax_error = evaluator.evaluate(
        {
            "question_id": "Q9",
            "task_type": "coding_question",
            "learner_answer": "print('oops'",
            "expected_output": "oops",
        }
    )
    _assert(syntax_error["mistake_type"] == "syntax_error", f"syntax error not captured: {syntax_error}")

    print("coding_question_correct:", coding_correct["label"])
    print("coding_question_wrong_output:", coding_wrong["mistake_type"])
    print("syntax_completion_correct:", syntax_completion["label"])
    print("debug_task_corrected_code:", debug_passes["label"])
    print("debug_task_unsafe_code:", debug_unsafe["mistake_type"])
    print("output_prediction_correct:", output_prediction_correct["label"])
    print("output_prediction_wrong:", output_prediction_wrong["mistake_type"])
    print("runtime_error:", runtime_error["mistake_type"])
    print("syntax_error:", syntax_error["mistake_type"])
    print("STATUS: success")
    print("MODULE: code_question_evaluator_test")


if __name__ == "__main__":
    main()
