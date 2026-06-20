from __future__ import annotations

from typing import Any

from tutor.evaluation.code_runner import SafeCodeRunner


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _label_for_score(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.45:
        return "partial"
    return "weak"


def _base_result(
    question_id: str,
    task_type: str,
    correct: bool,
    score: float,
    feedback: str,
    execution: dict[str, Any] | None = None,
    test_results: list[dict[str, Any]] | None = None,
    mistake_type: str = "none",
) -> dict[str, Any]:
    score = _clamp(score)
    return {
        "status": "success",
        "module": "CodeQuestionEvaluator",
        "question_id": question_id,
        "task_type": task_type,
        "correct": bool(correct),
        "score": round(score, 4),
        "label": _label_for_score(score),
        "feedback": feedback,
        "execution": execution or {},
        "test_results": test_results or [],
        "mistake_type": mistake_type,
    }


def _mistake_from_execution(execution: dict[str, Any]) -> str:
    status = execution.get("execution_status")
    if status == "syntax_error":
        return "syntax_error"
    if status == "runtime_error":
        return "runtime_error"
    if status == "blocked":
        return "unsafe_code"
    if status == "timeout":
        return "runtime_error"
    if status == "failed":
        return "wrong_output"
    return "none"


class CodeQuestionEvaluator:
    def __init__(self, runner: SafeCodeRunner | None = None) -> None:
        self.runner = runner or SafeCodeRunner()

    def evaluate(self, question: dict[str, Any]) -> dict[str, Any]:
        task_type = _text(question.get("task_type") or question.get("assessment_type") or "coding_question")

        if task_type == "debug_task":
            return self._evaluate_debug_task(question)
        if task_type == "output_prediction":
            return self._evaluate_output_prediction(question)
        if task_type in {
            "coding_question",
            "syntax_completion",
            "code_tracing",
            "challenge",
            "transfer",
            "transfer_with_code",
        }:
            return self._evaluate_executable_code(question, task_type)

        return self._evaluate_executable_code(question, task_type)

    def _evaluate_executable_code(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        question_id = _text(question.get("question_id") or question.get("id") or "")
        learner_code = _text(
            question.get("learner_answer")
            or question.get("submitted_code")
            or question.get("code")
            or question.get("answer")
        )
        starter_code = _text(question.get("starter_code"))

        code = learner_code
        if starter_code and "{answer}" in starter_code:
            code = starter_code.replace("{answer}", learner_code)
        elif starter_code and learner_code and task_type == "syntax_completion":
            code = starter_code + learner_code

        expected_output = question.get("expected_output")
        test_cases = question.get("test_cases") or []
        execution = self.runner.run(
            code=code,
            expected_output=str(expected_output) if expected_output is not None else None,
            test_cases=test_cases,
        )

        mistake_type = _mistake_from_execution(execution)
        correct = bool(execution.get("passed"))
        score = float(execution.get("score", 0.0) or 0.0)
        feedback = "Code passed." if correct else "Code did not pass the required output or tests."
        if mistake_type == "syntax_error":
            feedback = "Code has a syntax error."
        elif mistake_type == "runtime_error":
            feedback = "Code raised a runtime error."
        elif mistake_type == "unsafe_code":
            feedback = "Code used a blocked operation."

        return _base_result(
            question_id=question_id,
            task_type=task_type,
            correct=correct,
            score=score,
            feedback=feedback,
            execution=execution,
            test_results=execution.get("test_results", []),
            mistake_type=mistake_type,
        )

    def _evaluate_debug_task(self, question: dict[str, Any]) -> dict[str, Any]:
        question_id = _text(question.get("question_id") or question.get("id") or "")
        corrected_code = _text(
            question.get("corrected_code")
            or question.get("learner_answer")
            or question.get("submitted_code")
        )
        expected_output = question.get("expected_output")
        test_cases = question.get("test_cases") or []
        expected_fix = _text(question.get("expected_fix"))
        learner_text = _text(question.get("learner_answer"))

        execution = self.runner.run(
            code=corrected_code,
            expected_output=str(expected_output) if expected_output is not None else None,
            test_cases=test_cases,
        )

        mistake_type = _mistake_from_execution(execution)
        correct = bool(execution.get("passed"))
        score = float(execution.get("score", 0.0) or 0.0)

        if not correct and expected_fix and learner_text:
            expected_tokens = {item.lower() for item in expected_fix.replace("_", " ").split() if len(item) > 3}
            learner_tokens = {item.lower() for item in learner_text.replace("_", " ").split() if len(item) > 3}
            overlap = len(expected_tokens.intersection(learner_tokens)) / max(1, len(expected_tokens))
            if overlap >= 0.25:
                score = max(score, 0.4)
                mistake_type = "incomplete_fix"

        feedback = "Corrected code passes." if correct else "Debug fix is incomplete."
        if mistake_type == "syntax_error":
            feedback = "Corrected code has a syntax error."
        elif mistake_type == "runtime_error":
            feedback = "Corrected code raises a runtime error."
        elif mistake_type == "unsafe_code":
            feedback = "Corrected code used a blocked operation."

        return _base_result(
            question_id=question_id,
            task_type="debug_task",
            correct=correct,
            score=score,
            feedback=feedback,
            execution=execution,
            test_results=execution.get("test_results", []),
            mistake_type=mistake_type,
        )

    def _evaluate_output_prediction(self, question: dict[str, Any]) -> dict[str, Any]:
        question_id = _text(question.get("question_id") or question.get("id") or "")
        learner_answer = _text(question.get("learner_answer") or question.get("predicted_output") or question.get("answer"))
        expected_output = _text(question.get("expected_output"))
        code = _text(question.get("code") or question.get("buggy_code"))

        execution: dict[str, Any] = {}
        actual_output = expected_output

        if code:
            execution = self.runner.run(code=code)
            if execution.get("execution_status") in {"syntax_error", "runtime_error", "blocked", "timeout"}:
                mistake_type = _mistake_from_execution(execution)
                return _base_result(
                    question_id=question_id,
                    task_type="output_prediction",
                    correct=False,
                    score=0.0,
                    feedback="Could not verify output because the reference code did not run safely.",
                    execution=execution,
                    mistake_type=mistake_type,
                )
            actual_output = _text(execution.get("stdout"))

        correct = learner_answer.strip() == actual_output.strip()
        return _base_result(
            question_id=question_id,
            task_type="output_prediction",
            correct=correct,
            score=1.0 if correct else 0.0,
            feedback="Predicted output is correct." if correct else "Predicted output does not match.",
            execution=execution,
            mistake_type="none" if correct else "wrong_output",
        )


def evaluate_code_question(question: dict[str, Any]) -> dict[str, Any]:
    return CodeQuestionEvaluator().evaluate(question)
