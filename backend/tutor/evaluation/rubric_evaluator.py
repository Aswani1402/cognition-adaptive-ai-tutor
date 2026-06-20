from __future__ import annotations

from typing import Any, Dict, List


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize(value: Any) -> str:
    return _safe_str(value).lower().strip()


def _tokenize(text: str) -> set[str]:
    cleaned = (
        text.lower()
        .replace("\n", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace('"', " ")
        .replace("'", " ")
    )

    stopwords = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "with",
        "that",
        "this",
        "it",
        "as",
    }

    return {
        token
        for token in cleaned.split()
        if token and token not in stopwords
    }


def _expected_text(expected_answer: Any) -> str:
    if isinstance(expected_answer, dict):
        return _safe_str(
            expected_answer.get("expected_fix")
            or expected_answer.get("fix_text")
            or expected_answer.get("answer")
            or expected_answer.get("output")
            or expected_answer.get("value")
            or ""
        )

    return _safe_str(expected_answer)


def _question_type(question: Dict[str, Any]) -> str:
    return _safe_str(
        question.get("assessment_type") or question.get("question_type"),
        "unknown",
    )


def _keyword_overlap_score(answer: str, expected: str) -> float:
    answer_tokens = _tokenize(answer)
    expected_tokens = _tokenize(expected)

    if not expected_tokens:
        return 0.0

    overlap = answer_tokens.intersection(expected_tokens)
    return len(overlap) / max(1, len(expected_tokens))


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clip_score(score: float) -> float:
    return max(0.0, min(1.0, float(score)))


def evaluate_answer_with_rubric(
    question: Dict[str, Any],
    learner_answer: Any,
) -> Dict[str, Any]:
    """
    Baseline rubric evaluator.

    Current role:
    - More detailed than simple exact match.
    - Gives dimension-wise scores.
    - Later can be replaced with a trained evaluator/regressor.

    Dimensions:
    - correctness
    - concept_coverage
    - specificity
    - code_reasoning
    - clarity
    """

    q_type = _question_type(question)
    answer_raw = _safe_str(learner_answer)
    answer = _normalize(answer_raw)
    expected_raw = _expected_text(question.get("expected_answer"))
    expected = _normalize(expected_raw)

    metadata = (
        question.get("metadata", {})
        if isinstance(question.get("metadata"), dict)
        else {}
    )

    if not answer:
        return {
            "status": "success",
            "module": "RubricEvaluator",
            "assessment_type": q_type,
            "overall_score": 0.0,
            "quality_label": "no_answer",
            "rubric_scores": {
                "correctness": 0.0,
                "concept_coverage": 0.0,
                "specificity": 0.0,
                "code_reasoning": 0.0,
                "clarity": 0.0,
            },
            "feedback": "No answer was provided.",
            "evidence": {
                "expected_answer": expected_raw,
                "learner_answer": answer_raw,
            },
        }

    correctness = 0.0
    concept_coverage = 0.0
    specificity = 0.0
    code_reasoning = 0.0
    clarity = 0.0

    overlap = _keyword_overlap_score(answer, expected)

    # General clarity score
    word_count = len(answer.split())
    if word_count >= 8:
        clarity = 1.0
    elif word_count >= 4:
        clarity = 0.65
    else:
        clarity = 0.35

    vague_markers = {"maybe", "not sure", "i think", "something", "thing"}
    if _contains_any(answer, list(vague_markers)):
        clarity = min(clarity, 0.45)

    # Type-specific scoring
    if q_type == "output_prediction":
        if expected and answer == expected:
            correctness = 1.0
            concept_coverage = 1.0
            specificity = 1.0
            code_reasoning = 0.8
            clarity = max(clarity, 0.8)
        else:
            correctness = 0.0
            concept_coverage = 0.2
            specificity = 0.2
            code_reasoning = 0.1

    elif q_type in {"debug", "debug_task"}:
        bug_category = _normalize(metadata.get("bug_category") or metadata.get("bug_type"))

        quote_related = _contains_any(
            answer,
            ["quote", "quotes", "string", "quotation", "missing quote"],
        )

        fix_related = _contains_any(
            answer,
            ["fix", "correct", "change", "add", "use"],
        )

        if bug_category == "string_syntax" and quote_related:
            correctness = 0.85
            concept_coverage = 0.8
            specificity = 0.85
            code_reasoning = 0.8
        elif expected and overlap >= 0.5:
            correctness = 0.7
            concept_coverage = 0.65
            specificity = 0.6
            code_reasoning = 0.6
        elif "no mistake" in answer or "nothing wrong" in answer:
            correctness = 0.0
            concept_coverage = 0.1
            specificity = 0.1
            code_reasoning = 0.0
        elif fix_related:
            correctness = 0.35
            concept_coverage = 0.35
            specificity = 0.35
            code_reasoning = 0.35
        else:
            correctness = 0.2
            concept_coverage = 0.25
            specificity = 0.2
            code_reasoning = 0.2

    elif q_type in {"short_explanation", "explanation"}:
        concept_words = ["variable", "name", "value", "store", "reuse", "refer"]
        matched = sum(1 for word in concept_words if word in answer)

        concept_coverage = min(1.0, matched / 4)
        correctness = max(overlap, concept_coverage)

        if matched >= 3:
            specificity = 0.8
        elif matched >= 2:
            specificity = 0.55
        else:
            specificity = 0.25

        code_reasoning = 0.5

    elif q_type == "transfer":
        transfer_words = [
            "price",
            "counter",
            "configuration",
            "api",
            "name",
            "data",
            "store",
            "real",
            "use",
        ]

        matched = sum(1 for word in transfer_words if word in answer)
        concept_coverage = min(1.0, matched / 4)
        correctness = concept_coverage
        specificity = min(1.0, matched / 3)
        code_reasoning = 0.45

    elif q_type == "mcq":
        options = question.get("options") or []
        correct_index = question.get("correct_option_index")
        correct_option = ""

        if isinstance(correct_index, int) and 0 <= correct_index < len(options):
            correct_option = _normalize(options[correct_index])

        if correct_option and answer == correct_option:
            correctness = 1.0
            concept_coverage = 1.0
            specificity = 1.0
            code_reasoning = 0.5
            clarity = 1.0
        elif expected and answer == expected:
            correctness = 1.0
            concept_coverage = 1.0
            specificity = 1.0
            code_reasoning = 0.5
            clarity = 1.0
        else:
            correctness = 0.0
            concept_coverage = 0.2
            specificity = 0.2
            code_reasoning = 0.2

    elif q_type in {"code_writing", "syntax_completion"}:
        has_assignment = "=" in answer
        has_print = "print" in answer
        has_quotes = '"' in answer_raw or "'" in answer_raw

        correctness = 0.0
        if has_assignment:
            correctness += 0.35
        if has_print:
            correctness += 0.25
        if has_quotes:
            correctness += 0.25

        concept_coverage = correctness
        specificity = 0.8 if has_assignment and has_print else 0.45
        code_reasoning = correctness
        clarity = max(clarity, 0.7)

    else:
        correctness = overlap
        concept_coverage = overlap
        specificity = min(1.0, word_count / 10)
        code_reasoning = 0.4

    rubric_scores = {
        "correctness": _clip_score(correctness),
        "concept_coverage": _clip_score(concept_coverage),
        "specificity": _clip_score(specificity),
        "code_reasoning": _clip_score(code_reasoning),
        "clarity": _clip_score(clarity),
    }

    weights = {
        "correctness": 0.4,
        "concept_coverage": 0.25,
        "specificity": 0.15,
        "code_reasoning": 0.15,
        "clarity": 0.05,
    }

    overall_score = sum(
        rubric_scores[key] * weight
        for key, weight in weights.items()
    )
    overall_score = round(_clip_score(overall_score), 4)

    if overall_score >= 0.85:
        quality_label = "strong"
    elif overall_score >= 0.65:
        quality_label = "partial_strong"
    elif overall_score >= 0.45:
        quality_label = "partial"
    elif overall_score > 0:
        quality_label = "weak"
    else:
        quality_label = "incorrect"

    feedback_parts = []

    if rubric_scores["correctness"] < 0.5:
        feedback_parts.append("The answer does not fully match the expected solution.")
    if rubric_scores["concept_coverage"] < 0.5:
        feedback_parts.append("Important concept points are missing.")
    if rubric_scores["specificity"] < 0.5:
        feedback_parts.append("The answer needs more specific detail.")
    if rubric_scores["code_reasoning"] < 0.5 and q_type in {
        "debug",
        "debug_task",
        "output_prediction",
        "code_writing",
        "syntax_completion",
    }:
        feedback_parts.append("Code reasoning or tracing needs more practice.")
    if rubric_scores["clarity"] < 0.5:
        feedback_parts.append("The answer is unclear or too vague.")

    if not feedback_parts:
        feedback_parts.append("Good answer with sufficient detail.")

    return {
        "status": "success",
        "module": "RubricEvaluator",
        "assessment_type": q_type,
        "overall_score": overall_score,
        "quality_label": quality_label,
        "rubric_scores": rubric_scores,
        "feedback": " ".join(feedback_parts),
        "evidence": {
            "expected_answer": expected_raw,
            "learner_answer": answer_raw,
            "keyword_overlap": round(overlap, 4),
        },
    }


def evaluate_answers_with_rubric(
    assessment_output: Dict[str, Any],
    learner_answers: Dict[str, Any],
) -> Dict[str, Any]:
    questions = assessment_output.get("questions", [])

    results = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        q_type = _question_type(question)
        learner_answer = learner_answers.get(q_type, "")

        rubric_output = evaluate_answer_with_rubric(
            question=question,
            learner_answer=learner_answer,
        )

        results.append(
            {
                "assessment_type": q_type,
                "question_id": question.get("question_id"),
                "learner_answer": learner_answer,
                **rubric_output,
            }
        )

    scores = [
        float(item.get("overall_score", 0.0) or 0.0)
        for item in results
    ]

    overall_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    weak_assessment_types = [
        item.get("assessment_type")
        for item in results
        if float(item.get("overall_score", 0.0) or 0.0) < 0.65
    ]

    strong_assessment_types = [
        item.get("assessment_type")
        for item in results
        if float(item.get("overall_score", 0.0) or 0.0) >= 0.75
    ]

    if overall_score >= 0.85:
        verdict = "mastered"
    elif overall_score >= 0.65:
        verdict = "partial"
    elif overall_score >= 0.45:
        verdict = "needs_light_review"
    else:
        verdict = "weak"

    return {
        "status": "success",
        "module": "RubricEvaluator",
        "overall_score": overall_score,
        "verdict": verdict,
        "question_count": len(results),
        "weak_assessment_types": weak_assessment_types,
        "strong_assessment_types": strong_assessment_types,
        "results": results,
    }