from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"
JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_TEACHING_VIEWS = [
    "explanation",
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "comparison_view",
    "real_world_connection_view",
]

TASK_COMPONENT = {
    "mcq": "MCQQuestionCard",
    "true_or_false": "MCQQuestionCard",
    "fill_in_the_blank": "FillBlankCard",
    "syntax_completion": "SyntaxCompletionCard",
    "coding_prompt": "CodeWritingCard",
    "coding_question": "CodeWritingCard",
    "code_reasoning_task": "CodeWritingCard",
    "output_prediction": "OutputPredictionCard",
    "debug_task": "DebugQuestionCard",
    "transfer_question": "TransferQuestionCard",
    "transfer_task": "TransferQuestionCard",
    "real_world_application_question": "TransferQuestionCard",
    "challenge_question": "ChallengeQuestionCard",
    "multi_step_challenge": "ChallengeQuestionCard",
    "puzzle": "PuzzleQuestionCard",
}

VAGUE_PATTERNS = [
    "tiny example",
    "short reasoning challenge using the concept",
    "solve this challenge",
    "write your explanation",
]


def write_result(name: str, result: dict[str, Any]) -> None:
    ok = bool(result.get("ok"))
    lines = [f"# {name}", "", f"Status: {'PASS' if ok else 'FAIL'}", ""]
    for key, value in result.items():
        if key == "details":
            continue
        lines.append(f"- {key}: `{value}`")
    if result.get("details"):
        lines += ["", "## Details", "```json", json.dumps(result["details"], indent=2), "```"]
    (REPORT_DIR / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")
    (JSON_DIR / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def fail(message: str, details: Any = None) -> dict[str, Any]:
    return {"ok": False, "message": message, "details": details}


def passed(message: str, details: Any = None) -> dict[str, Any]:
    return {"ok": True, "message": message, "details": details}


def sentence_count(text: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", str(text).strip()) if part])


def has_vague_prompt(text: str, concept_name: str) -> bool:
    low = str(text or "").lower()
    if "this concept" in low and concept_name.lower() not in low:
        return True
    return any(pattern in low for pattern in VAGUE_PATTERNS)


def question_type(question: dict[str, Any]) -> str:
    return str(question.get("task_type") or question.get("taskType") or question.get("question_type") or question.get("questionType") or "").lower()


def component(question: dict[str, Any]) -> str:
    return str(question.get("frontend_component") or question.get("frontendComponent") or "")


def options(question: dict[str, Any]) -> list[Any]:
    raw = question.get("options") or question.get("choices") or question.get("answer_options") or question.get("mcq_options") or []
    return raw if isinstance(raw, list) else []


def correct_answer(question: dict[str, Any]) -> Any:
    for key in ("correct_answer", "correctAnswer", "expected_answer", "answer", "correct_option", "correct_option_id", "correct_option_index"):
        if question.get(key) not in (None, ""):
            return question[key]
    return None


def validate_question(question: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    qtype = question_type(question)
    concept = str(question.get("concept_name") or question.get("conceptName") or "")
    prompt = str(question.get("prompt") or "")
    if not question.get("subject"):
        errors.append("missing subject")
    if not question.get("concept_id"):
        errors.append("missing concept_id")
    if not concept:
        errors.append("missing concept_name")
    if not question.get("difficulty"):
        errors.append("missing difficulty")
    if not qtype:
        errors.append("missing task_type")
    if not prompt:
        errors.append("missing prompt")
    if has_vague_prompt(prompt, concept):
        errors.append("vague prompt")
    expected_component = TASK_COMPONENT.get(qtype)
    if expected_component and component(question) != expected_component:
        errors.append(f"component mismatch expected {expected_component}, got {component(question)}")
    if qtype == "mcq":
        if len(options(question)) != 4:
            errors.append(f"mcq options count {len(options(question))}, expected 4")
        if correct_answer(question) is None:
            errors.append("mcq missing correct answer")
    if qtype == "true_or_false" and len(options(question)) != 2:
        errors.append("true_or_false missing two options")
    if "output_prediction" in qtype:
        if not (question.get("code") or question.get("starter_code") or question.get("starterCode") or question.get("code_snippet")):
            errors.append("output prediction missing snippet")
        if not (question.get("expected_output") or question.get("expectedOutput") or correct_answer(question)):
            errors.append("output prediction missing expected output")
    if "debug" in qtype and not (question.get("buggy_code") or question.get("buggyCode") or question.get("starter_code") or question.get("starterCode")):
        errors.append("debug missing buggy snippet")
    if qtype in {"coding_prompt", "coding_question", "code_reasoning_task"} and len(prompt.split()) < 8:
        errors.append("coding prompt missing clear goal")
    if qtype in {"transfer_question", "transfer_task", "real_world_application_question"} and not any(word in prompt.lower() for word in ["scenario", "situation", "dashboard", "teammate", "page", "app", "real", "queue", "school"]):
        errors.append("transfer task missing realistic scenario")
    if qtype in {"challenge_question", "multi_step_challenge"} and len(prompt.split()) < 12:
        errors.append("challenge too vague")
    if sentence_count(str(question.get("hint") or question.get("hint_short") or "")) > 2:
        errors.append("hint too long")
    return errors
