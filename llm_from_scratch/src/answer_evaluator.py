import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.safe_code_runner import run_python_code, run_python_test_cases, normalize_output

ROOT_DIR = Path(__file__).resolve().parents[1]

QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"


def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).strip().lower()
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize whitespace but preserve newlines for output comparison first.
    text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
    text = text.strip()

    return text


def normalize_for_loose_match(text: Any) -> str:
    text = normalize_text(text)

    # Remove punctuation for flexible comparison.
    cleaned = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)

    return " ".join("".join(cleaned).split())


def extract_keywords(text: Any, min_len: int = 4) -> List[str]:
    text = normalize_for_loose_match(text)
    words = text.split()

    stopwords = {
        "this",
        "that",
        "with",
        "from",
        "into",
        "about",
        "should",
        "would",
        "could",
        "where",
        "when",
        "what",
        "which",
        "using",
        "used",
        "rule",
        "main",
        "idea",
        "concept",
        "correct",
        "answer",
        "example",
        "works",
        "work",
        "learner",
        "explain",
        "because",
        "there",
        "their",
        "your",
        "also",
        "only",
    }

    keywords = []
    for word in words:
        if len(word) >= min_len and word not in stopwords and word not in keywords:
            keywords.append(word)

    return keywords


def keyword_overlap_score(learner_answer: str, expected_text: str) -> Tuple[float, List[str], List[str]]:
    learner_keywords = set(extract_keywords(learner_answer))
    expected_keywords = set(extract_keywords(expected_text))

    if not expected_keywords:
        return 0.0, [], []

    matched = sorted(learner_keywords & expected_keywords)
    missing = sorted(expected_keywords - learner_keywords)

    score = len(matched) / max(len(expected_keywords), 1)
    return score, matched, missing


def load_question_bank(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    bank_path = path or QUESTION_BANK_PATH

    if not bank_path.exists():
        raise FileNotFoundError(
            f"Question bank not found: {bank_path}\n"
            "Run: python -m scripts.generate_assessment_question_bank"
        )

    with bank_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_question_by_id(
    question_bank: List[Dict[str, Any]],
    concept_id: str,
    question_type: str,
    variant_id: int,
) -> Optional[Dict[str, Any]]:
    for item in question_bank:
        if (
            str(item.get("concept_id")) == str(concept_id)
            and str(item.get("question_type")) == str(question_type)
            and int(item.get("variant_id", -1)) == int(variant_id)
        ):
            return item

    return None


def evaluate_mcq(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    qjson = question.get("question_json") or {}
    expected_answer = qjson.get("answer")

    learner = normalize_text(learner_answer)
    expected = normalize_text(expected_answer)

    correct = learner == expected

    # Also allow option letter if frontend sends A/B/C/D.
    options = qjson.get("options", [])
    if not correct and isinstance(learner_answer, str):
        answer_raw = learner_answer.strip().upper()
        letter_map = {"A": 0, "B": 1, "C": 2, "D": 3}

        if answer_raw in letter_map and len(options) == 4:
            selected = options[letter_map[answer_raw]]
            correct = normalize_text(selected) == expected

    score = 1.0 if correct else 0.0

    if correct:
        feedback = "Correct. You selected the option that matches the main concept rule."
        mistake_type = None
    else:
        feedback = f"Not correct. The correct answer is: {expected_answer}"
        mistake_type = "wrong_option"

    return {
        "correct": correct,
        "score": score,
        "feedback": feedback,
        "mistake_type": mistake_type,
        "expected_answer": expected_answer,
        "learner_answer": learner_answer,
    }


def evaluate_output_prediction(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    qjson = question.get("question_json") or {}

    expected_answer = qjson.get("answer", "")
    explanation = qjson.get("explanation", "")

    learner_norm = normalize_text(learner_answer)
    expected_norm = normalize_text(expected_answer)

    correct = learner_norm == expected_norm

    # Loose comparison for common newline/space issues.
    if not correct:
        learner_loose = normalize_for_loose_match(learner_answer)
        expected_loose = normalize_for_loose_match(expected_answer)
        correct = learner_loose == expected_loose

    score = 1.0 if correct else 0.0

    if correct:
        feedback = f"Correct. {explanation}".strip()
        mistake_type = None
    else:
        feedback = (
            f"Not correct. Expected output: {expected_answer}. "
            f"Review the code carefully and trace each step."
        )
        mistake_type = "wrong_output_prediction"

    return {
        "correct": correct,
        "score": score,
        "feedback": feedback,
        "mistake_type": mistake_type,
        "expected_answer": expected_answer,
        "learner_answer": learner_answer,
    }


def infer_debug_expected_output(question: Dict[str, Any]) -> Optional[str]:
    """
    Try to infer expected stdout from expected_fix for simple debug tasks.
    This is useful for website-style debug questions where learner submits fixed code.
    """
    qjson = question.get("question_json") or {}
    expected_fix = qjson.get("expected_fix", "")

    if not expected_fix:
        return None

    result = run_python_code(expected_fix, timeout_seconds=2)

    if result.get("success"):
        return result.get("stdout", "")

    return None


def evaluate_code_execution_if_possible(
    question: Dict[str, Any],
    learner_code: Any,
) -> Dict[str, Any]:
    """
    Optional execution-based evaluation.
    Used mainly for Python debug/coding-style tasks.
    """
    learner_code = str(learner_code or "").strip()

    if not learner_code:
        return {
            "execution_checked": False,
            "execution_correct": False,
            "execution_score": 0.0,
            "execution_feedback": "No code was provided for execution.",
            "execution_result": None,
            "test_results": [],
        }

    domain = str(question.get("domain") or "").lower()

    # Current safe runner supports Python only.
    if domain != "python":
        return {
            "execution_checked": False,
            "execution_correct": False,
            "execution_score": 0.0,
            "execution_feedback": "Execution check is currently available only for Python questions.",
            "execution_result": None,
            "test_results": [],
        }

    expected_output = infer_debug_expected_output(question)

    # If expected_fix itself does not run or has no output, still run learner code
    # and return execution info, but do not judge correctness by output.
    if expected_output is None:
        execution_result = run_python_code(learner_code, timeout_seconds=2)

        return {
            "execution_checked": True,
            "execution_correct": bool(execution_result.get("success")),
            "execution_score": 0.5 if execution_result.get("success") else 0.0,
            "execution_feedback": (
                "Your code runs without an execution error."
                if execution_result.get("success")
                else f"Your code has an execution error: {execution_result.get('error_message')}"
            ),
            "execution_result": execution_result,
            "test_results": [],
        }

    test_result = run_python_test_cases(
        code=learner_code,
        test_cases=[
            {
                "test_id": "debug_expected_output",
                "expected_output": expected_output,
            }
        ],
        timeout_seconds=2,
    )

    passed = bool(test_result.get("success"))
    score = float(test_result.get("score", 0.0))

    return {
        "execution_checked": True,
        "execution_correct": passed,
        "execution_score": score,
        "execution_feedback": (
            "Your code runs and produces the expected output."
            if passed
            else "Your code did not produce the expected output."
        ),
        "execution_result": None,
        "test_results": test_result.get("test_results", []),
    }


def evaluate_debug_task(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    qjson = question.get("question_json") or {}

    expected_fix = qjson.get("expected_fix", "")
    hint = qjson.get("hint", "")

    learner_norm = normalize_text(learner_answer)
    expected_norm = normalize_text(expected_fix)

    exact = learner_norm == expected_norm

    learner_loose = normalize_for_loose_match(learner_answer)
    expected_loose = normalize_for_loose_match(expected_fix)

    loose = learner_loose == expected_loose

    # Optional execution check for Python debug tasks.
    execution_eval = evaluate_code_execution_if_possible(question, learner_answer)

    # Partial score from keyword/code token overlap.
    overlap_score, matched, missing = keyword_overlap_score(learner_answer, expected_fix)

    if exact or loose:
        correct = True
        score = 1.0
        feedback = "Correct. Your fix matches the expected correction."
        mistake_type = None

    elif execution_eval.get("execution_checked") and execution_eval.get("execution_correct"):
        correct = True
        score = max(0.9, float(execution_eval.get("execution_score", 0.0)))
        feedback = "Correct. Your code runs safely and produces the expected output."
        mistake_type = None

    elif execution_eval.get("execution_checked") and not execution_eval.get("execution_correct"):
        correct = False

        # If code runs but output is wrong, give partial credit.
        test_results = execution_eval.get("test_results") or []
        has_runtime_error = False

        if execution_eval.get("execution_result"):
            has_runtime_error = execution_eval["execution_result"].get("success") is False

        if test_results:
            has_runtime_error = any(item.get("error_message") for item in test_results)

        if overlap_score >= 0.65:
            score = 0.6
            mistake_type = "partial_debug_fix"
            feedback = (
                "Partially correct. Your answer has some important parts, "
                "but the execution result does not fully match the expected output. "
                f"Hint: {hint}"
            )
        elif has_runtime_error:
            score = 0.0
            mistake_type = "debug_runtime_error"
            feedback = (
                "Your code still has an execution error. "
                f"Hint: {hint}"
            )
        else:
            score = 0.3
            mistake_type = "wrong_debug_output"
            feedback = (
                "Your code runs, but it does not produce the expected output. "
                f"Hint: {hint}"
            )

    elif overlap_score >= 0.65:
        correct = False
        score = 0.6
        feedback = (
            "Partially correct. Your answer contains some important parts of the fix, "
            f"but it does not fully match the expected correction. Hint: {hint}"
        )
        mistake_type = "partial_debug_fix"

    else:
        correct = False
        score = 0.0
        feedback = f"Not correct. Review the bug again. Hint: {hint}"
        mistake_type = "incorrect_debug_fix"

    return {
        "correct": correct,
        "score": score,
        "feedback": feedback,
        "mistake_type": mistake_type,
        "expected_answer": expected_fix,
        "learner_answer": learner_answer,
        "matched_keywords": matched,
        "missing_keywords": missing[:8],
        "execution_checked": execution_eval.get("execution_checked"),
        "execution_correct": execution_eval.get("execution_correct"),
        "execution_feedback": execution_eval.get("execution_feedback"),
        "test_results": execution_eval.get("test_results", []),
        "execution_result": execution_eval.get("execution_result"),
    }



def evaluate_rubric_text_question(
    question: Dict[str, Any],
    learner_answer: Any,
    task_type: str,
) -> Dict[str, Any]:
    learner_text = str(learner_answer or "").strip()

    if not learner_text:
        return {
            "correct": False,
            "score": 0.0,
            "feedback": "No answer was provided. Try explaining the idea in your own words.",
            "mistake_type": "empty_answer",
            "expected_answer": None,
            "learner_answer": learner_answer,
            "matched_keywords": [],
            "missing_keywords": [],
        }

    qjson = question.get("question_json")
    answer_key = question.get("answer_key_json") or {}
    concept_name = str(question.get("concept_name") or "").strip()

    if isinstance(qjson, dict):
        expected_text = (
            qjson.get("expected_key_points")
            or answer_key.get("expected_key_points")
            or json.dumps(qjson, ensure_ascii=False)
        )
    else:
        expected_text = (
            answer_key.get("expected_key_points")
            or question.get("question_text")
            or concept_name
            or ""
        )

    keyword_score, matched, missing = keyword_overlap_score(learner_text, expected_text)

    learner_norm = normalize_for_loose_match(learner_text)
    concept_norm = normalize_for_loose_match(concept_name)

    word_count = len(learner_text.split())

    concept_score = 0.0
    if concept_norm and concept_norm in learner_norm:
        concept_score = 0.25

    length_score = 0.0
    if word_count >= 5:
        length_score = 0.15
    if word_count >= 10:
        length_score = 0.25

    application_words = {
        "use",
        "apply",
        "example",
        "project",
        "program",
        "real",
        "problem",
        "organize",
        "create",
        "show",
        "explain",
        "fix",
        "practice",
        "value",
        "code",
        "output",
    }

    learner_words = set(learner_norm.split())
    application_overlap = learner_words & application_words
    application_score = 0.0
    if application_overlap:
        application_score = 0.2

    # Keyword score is still useful, but it should not be the only score.
    combined_score = min(
        1.0,
        (keyword_score * 0.45) + concept_score + length_score + application_score,
    )

    # Task-specific minimum partial credit.
    if task_type in {"transfer_question", "challenge_question"}:
        if concept_score > 0 and application_score > 0 and word_count >= 8:
            combined_score = max(combined_score, 0.45)

    if task_type == "explanation_check":
        if concept_score > 0 and word_count >= 8:
            combined_score = max(combined_score, 0.35)

    score = round(combined_score, 3)

    if score >= 0.7:
        correct = True
        feedback = "Good answer. You covered the main idea clearly and applied it meaningfully."
        mistake_type = None
    elif score >= 0.35:
        correct = False
        feedback = (
            "Partially correct. Your answer is relevant, but it needs more concept detail. "
            "Add the key rule and one clear example."
        )
        mistake_type = "partial_concept_coverage"
    else:
        correct = False
        feedback = (
            "Not enough concept coverage. Try using the key rule and a small example in your answer."
        )
        mistake_type = "low_concept_coverage"

    return {
        "correct": correct,
        "score": score,
        "feedback": feedback,
        "mistake_type": mistake_type,
        "expected_answer": expected_text,
        "learner_answer": learner_answer,
        "matched_keywords": matched,
        "missing_keywords": missing[:8],
    }

def evaluate_answer(question: Dict[str, Any], learner_answer: Any) -> Dict[str, Any]:
    question_type = question.get("question_type")

    if question_type == "mcq":
        result = evaluate_mcq(question, learner_answer)

    elif question_type == "output_prediction":
        result = evaluate_output_prediction(question, learner_answer)

    elif question_type == "debug_task":
        result = evaluate_debug_task(question, learner_answer)

    elif question_type in {"transfer_question", "challenge_question", "explanation_check"}:
        result = evaluate_rubric_text_question(question, learner_answer, question_type)

    else:
        result = {
            "correct": False,
            "score": 0.0,
            "feedback": f"Unsupported question type: {question_type}",
            "mistake_type": "unsupported_question_type",
            "expected_answer": None,
            "learner_answer": learner_answer,
        }

    result.update(
        {
            "concept_id": question.get("concept_id"),
            "concept_name": question.get("concept_name"),
            "domain": question.get("domain"),
            "question_type": question_type,
            "variant_id": question.get("variant_id"),
            "next_signal": make_next_signal(result),
        }
    )

    return result


def make_next_signal(result: Dict[str, Any]) -> Dict[str, Any]:
    score = float(result.get("score", 0.0))

    if score >= 0.8:
        return {
            "mastery_signal": "positive",
            "recommended_next_action": "continue_or_increase_difficulty",
        }

    if score >= 0.4:
        return {
            "mastery_signal": "partial",
            "recommended_next_action": "give_feedback_and_retry_similar",
        }

    return {
        "mastery_signal": "weak",
        "recommended_next_action": "remediate_with_different_view",
    }


def run_self_test() -> None:
    question_bank = load_question_bank()

    print("\nAnswer evaluator self-test")
    print("=" * 80)

    # Find one sample of each type.
    samples = {}
    for item in question_bank:
        qtype = item.get("question_type")
        if qtype not in samples:
            samples[qtype] = item

    test_cases = []

    if "mcq" in samples:
        q = samples["mcq"]
        correct_answer = q["question_json"]["answer"]
        test_cases.append(("mcq_correct", q, correct_answer))
        test_cases.append(("mcq_wrong", q, "wrong answer"))

    if "output_prediction" in samples:
        q = samples["output_prediction"]
        correct_answer = q["question_json"]["answer"]
        test_cases.append(("output_prediction_correct", q, correct_answer))
        test_cases.append(("output_prediction_wrong", q, "wrong output"))

    if "debug_task" in samples:
        q = samples["debug_task"]
        correct_answer = q["question_json"]["expected_fix"]
        test_cases.append(("debug_task_correct", q, correct_answer))
        test_cases.append(("debug_task_wrong", q, "print(name)"))

    # Execution-based tests for Python debug task.
    if q.get("domain") == "Python":
        test_cases.append(
            (
                "debug_task_execution_correct",
                q,
                q["question_json"]["expected_fix"],
            )
        )
        test_cases.append(
            (
                "debug_task_execution_runtime_error",
                q,
                "print(name)",
            )
        )

    if "explanation_check" in samples:
        q = samples["explanation_check"]
        test_cases.append(
            (
                "explanation_check_partial",
                q,
                f"{q['concept_name']} means the main idea can be applied with an example.",
            )
        )

    if "transfer_question" in samples:
        q = samples["transfer_question"]
        test_cases.append(
            (
                "transfer_question_sample",
                q,
                f"I would use {q['concept_name']} in a real project to organize and apply the main rule.",
            )
        )

    if "challenge_question" in samples:
        q = samples["challenge_question"]
        test_cases.append(
            (
                "challenge_question_sample",
                q,
                f"Example using {q['concept_name']}: I apply the concept correctly and explain the result.",
            )
        )

    for name, question, answer in test_cases:
        result = evaluate_answer(question, answer)

        print(f"\n{name}")
        print("-" * 80)
        print(f"Question type: {question['question_type']}")
        print(f"Concept: {question['concept_id']} - {question['concept_name']}")
        print(f"Learner answer: {answer}")
        print(
            json.dumps(
                {
                    "correct": result["correct"],
                    "score": result["score"],
                    "feedback": result["feedback"],
                    "mistake_type": result["mistake_type"],
                    "next_signal": result["next_signal"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()