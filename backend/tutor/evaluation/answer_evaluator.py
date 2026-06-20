from __future__ import annotations

from typing import Any
import re

from tutor.evaluation.code_question_evaluator import CodeQuestionEvaluator
from tutor.evaluation.semantic_answer_evaluator import SemanticAnswerEvaluator


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_type(question: dict[str, Any]) -> str:
    return _safe_str(
        question.get("task_type")
        or question.get("question_type")
        or question.get("assessment_type"),
        "unknown",
    )


def _learner_answer(question: dict[str, Any]) -> Any:
    for key in ["learner_answer", "selected_option", "corrected_code", "predicted_output", "answer"]:
        if question.get(key) is not None:
            return question.get(key)
    return ""


def _expected_answer(question: dict[str, Any]) -> Any:
    for key in ["expected_answer", "answer", "correct_answer", "correctAnswer", "expected_output", "expectedOutput"]:
        if question.get(key) is not None:
            return question.get(key)
    return ""


def _label_for_score(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.45:
        return "partial"
    return "weak"


def _looks_like_code(value: Any) -> bool:
    text = _safe_str(value)
    if not text:
        return False
    stripped = text.lstrip()
    return (
        stripped.startswith(("print", "for ", "while ", "def ", "if ", "class "))
        or "\nprint(" in text
        or "print(" in text
        or "=" in text
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _unified_result(
    question: dict[str, Any],
    task_type: str,
    correct: bool,
    score: float,
    feedback: str,
    mistake_type: str,
    routed_to: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    score = _clamp(score)
    return {
        "status": "success",
        "module": "AnswerEvaluator",
        "question_id": _safe_str(question.get("question_id") or question.get("id")),
        "task_type": task_type,
        "correct": bool(correct),
        "score": round(score, 4),
        "label": _label_for_score(score),
        "feedback": feedback,
        "mistake_type": mistake_type,
        "routed_to": routed_to,
        "details": details,
    }


def _norm_text(value: Any) -> str:
    if isinstance(value, dict):
        value = " ".join(str(v) for v in value.values())
    text = str(value or "").strip().lower()
    text = text.replace('"', "'")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\"']|[\"']$", "", text)
    return text.strip(" .;:!?")


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", _norm_text(value)))


def _semantic_equivalence_score(answer: Any, expected: Any, question: dict[str, Any]) -> float:
    answer_text = _norm_text(answer)
    expected_text = _norm_text(expected)
    if not answer_text or not expected_text:
        return 0.0
    if answer_text == expected_text:
        return 1.0
    if answer_text in expected_text or expected_text in answer_text:
        return 0.92
    ans_tokens = _tokens(answer_text)
    exp_tokens = _tokens(expected_text)
    if not ans_tokens or not exp_tokens:
        return 0.0
    overlap = len(ans_tokens & exp_tokens) / max(len(exp_tokens), 1)

    prompt = _norm_text(question.get("prompt"))
    concept = _norm_text(question.get("concept_name") or question.get("sourceConcept") or question.get("concept"))
    variable_context = "variable" in prompt or "variable" in concept
    if variable_context:
        if "refer" in answer_text and ({"value", "object"} & ans_tokens):
            return 1.0
        if "store" in answer_text and ({"value", "object", "data"} & ans_tokens):
            return 0.9
        if answer_text in {"value", "object", "value/object", "data"}:
            return 0.92
    if overlap >= 0.8:
        return 0.9
    if overlap >= 0.5:
        return 0.6
    return 0.0


def _score_from_details(details: dict[str, Any]) -> float:
    for key in ["score", "overall_score"]:
        if details.get(key) is not None:
            try:
                return _clamp(float(details.get(key)))
            except Exception:
                pass
    return 0.0


class AnswerEvaluator:
    def __init__(
        self,
        code_evaluator: CodeQuestionEvaluator | None = None,
        semantic_evaluator: SemanticAnswerEvaluator | None = None,
    ) -> None:
        self.code_evaluator = code_evaluator or CodeQuestionEvaluator()
        self.semantic_evaluator = semantic_evaluator or SemanticAnswerEvaluator()

    def evaluate(self, question: dict[str, Any]) -> dict[str, Any]:
        task_type = _normalize_type(question)

        if task_type == "mcq":
            return self._evaluate_mcq(question, task_type)

        if task_type == "output_prediction":
            if question.get("code") or question.get("buggy_code"):
                return self._route_to_code(question, task_type, routed_to="CodeQuestionEvaluator")
            return self._route_to_output_prediction(question, task_type)

        if task_type in {"debug", "debug_task"}:
            if question.get("corrected_code"):
                return self._route_to_code(question, "debug_task", routed_to="DebugAnswerEvaluator+CodeQuestionEvaluator")
            return self._route_to_debug(question, task_type)

        if task_type in {"fill_blank", "fill_in_the_blank", "true_or_false"}:
            return self._evaluate_direct_answer(question, task_type)

        if task_type in {"coding_question", "coding_prompt", "syntax_completion", "code_tracing"}:
            if task_type == "code_tracing" and not (question.get("learner_answer") or question.get("code")):
                return self._route_to_output_prediction(question, task_type)
            return self._route_to_code(question, task_type, routed_to="CodeQuestionEvaluator")

        if task_type in {"challenge", "challenge_question", "transfer", "transfer_question", "practice_question", "transfer_task", "real_world_application_question", "debug_challenge", "output_prediction_challenge", "multi_step_challenge", "code_reasoning_task"}:
            has_executable_code = bool(
                question.get("code")
                or question.get("test_cases")
                or (question.get("expected_output") is not None and _looks_like_code(question.get("learner_answer")))
            )
            if has_executable_code:
                return self._route_to_code(question, task_type, routed_to="CodeQuestionEvaluator")
            return self._route_to_semantic(question, task_type)

        if task_type in {"explanation", "explanation_check", "transfer_question", "doubt_followup"}:
            return self._route_to_semantic(question, task_type)

        if task_type in {"short_answer", "definition_check"}:
            return self._route_to_rubric(question, task_type)

        return self._route_to_rubric(question, task_type)

    def _evaluate_mcq(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        learner = _learner_answer(question)
        expected_raw = _expected_answer(question)
        expected = expected_raw
        if not expected and question.get("correctAnswer") is not None:
            expected = question.get("correctAnswer")
        score = _semantic_equivalence_score(learner, expected, question)
        correct = score >= 0.85
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=correct,
            score=score,
            feedback="Correct. That option captures the concept." if correct else "Selected option is not the best match.",
            mistake_type="none" if correct else "wrong_option",
            routed_to="mcq_semantic_match",
            details={"learner_answer": learner, "expected_answer": expected},
        )

    def _evaluate_direct_answer(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        learner = _learner_answer(question)
        expected = _expected_answer(question) or question.get("correctAnswer")
        if not expected and isinstance(question.get("blanks"), list):
            expected = " ".join(str(item.get("answer")) for item in question["blanks"] if isinstance(item, dict))
        score = _semantic_equivalence_score(learner, expected, question)
        correct = score >= 0.85
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=correct,
            score=score,
            feedback="Correct. Your answer matches the expected response." if correct else "Compare your answer with the expected response.",
            mistake_type="none" if correct else "wrong_answer",
            routed_to="direct_semantic_match",
            details={"learner_answer": learner, "expected_answer": expected},
        )

    def _route_to_code(self, question: dict[str, Any], task_type: str, routed_to: str) -> dict[str, Any]:
        code_question = dict(question)
        code_question["task_type"] = "debug_task" if task_type == "debug_task" else task_type
        details = self.code_evaluator.evaluate(code_question)
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=bool(details.get("correct")),
            score=_score_from_details(details),
            feedback=_safe_str(details.get("feedback")),
            mistake_type=_safe_str(details.get("mistake_type"), "none"),
            routed_to=routed_to,
            details=details,
        )

    def _route_to_output_prediction(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        try:
            from tutor.evaluation.output_prediction_evaluator import evaluate_output_prediction_answer

            q = dict(question)
            if "expected_answer" not in q and question.get("expected_output") is not None:
                q["expected_answer"] = {"expected_output": question.get("expected_output")}
            details = evaluate_output_prediction_answer(q, _learner_answer(question))
        except Exception as exc:
            details = {"overall_score": 0.0, "feedback": str(exc), "output_error_type": "evaluator_error"}

        score = _score_from_details(details)
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=score >= 0.85,
            score=score,
            feedback=_safe_str(details.get("feedback"), "Output prediction evaluated."),
            mistake_type=_safe_str(details.get("output_error_type"), "none" if score >= 0.85 else "wrong_output"),
            routed_to="OutputPredictionEvaluator",
            details=details,
        )

    def _route_to_debug(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        try:
            from tutor.evaluation.debug_answer_evaluator import evaluate_debug_answer

            q = dict(question)
            if "expected_answer" not in q and question.get("expected_fix") is not None:
                q["expected_answer"] = {"expected_fix": question.get("expected_fix")}
            details = evaluate_debug_answer(q, _learner_answer(question))
        except Exception as exc:
            details = {"overall_score": 0.0, "feedback": str(exc), "detected_bug_category": "evaluator_error"}

        score = _score_from_details(details)
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=score >= 0.85,
            score=score,
            feedback=_safe_str(details.get("feedback"), "Debug answer evaluated."),
            mistake_type="none" if score >= 0.85 else "incomplete_fix",
            routed_to="DebugAnswerEvaluator",
            details=details,
        )

    def _route_to_rubric(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        try:
            from tutor.evaluation.rubric_evaluator import evaluate_answer_with_rubric

            q = dict(question)
            if "expected_answer" not in q:
                q["expected_answer"] = question.get("expected_output") or question.get("correct_answer") or question.get("answer")
            details = evaluate_answer_with_rubric(q, _learner_answer(question))
        except Exception as exc:
            details = {"overall_score": 0.0, "feedback": str(exc)}

        score = _score_from_details(details)
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=score >= 0.85,
            score=score,
            feedback=_safe_str(details.get("feedback"), "Answer evaluated with rubric."),
            mistake_type="none" if score >= 0.85 else "partial" if score >= 0.45 else "weak_answer",
            routed_to="RubricEvaluator",
            details=details,
        )

    def _route_to_semantic(self, question: dict[str, Any], task_type: str) -> dict[str, Any]:
        rubric_output: dict[str, Any] | None = None
        try:
            from tutor.evaluation.rubric_evaluator import evaluate_answer_with_rubric

            q = dict(question)
            if "expected_answer" not in q:
                q["expected_answer"] = (
                    question.get("reference_answer")
                    or question.get("expected_output")
                    or question.get("correct_answer")
                    or question.get("answer")
                )
            rubric_output = evaluate_answer_with_rubric(q, _learner_answer(question))
        except Exception as exc:
            rubric_output = {"overall_score": 0.0, "feedback": str(exc)}

        expected = (
            question.get("expected_answer")
            or question.get("reference_answer")
            or question.get("correct_answer")
            or question.get("answer")
            or question.get("expected_output")
        )
        details = self.semantic_evaluator.evaluate(
            learner_answer=_learner_answer(question),
            expected_answer=expected,
            key_points=question.get("key_points") if isinstance(question.get("key_points"), list) else None,
            concept_name=_safe_str(question.get("concept_name") or question.get("concept")),
            task_type=task_type,
            rubric_output=rubric_output,
        )
        score = _score_from_details(details)
        return _unified_result(
            question=question,
            task_type=task_type,
            correct=score >= 0.80,
            score=score,
            feedback=_safe_str(details.get("feedback"), "Answer evaluated semantically."),
            mistake_type="none" if score >= 0.80 else "partial" if score >= 0.45 else "weak_answer",
            routed_to="SemanticAnswerEvaluator+RubricEvaluator",
            details={
                **details,
                "rubric_output": rubric_output,
            },
        )


def evaluate_answer(question: dict[str, Any]) -> dict[str, Any]:
    return AnswerEvaluator().evaluate(question)
