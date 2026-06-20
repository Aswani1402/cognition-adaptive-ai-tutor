import argparse
import json
import re
import string
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch

from src.format_validator import validate_output
from src.generate import (
    build_prompt,
    extract_json_object,
    fallback_output,
    generate_text,
    load_checkpoint,
)
from src.tokenizer_wrapper import CogniTutorTokenizer


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_CHECKPOINT = ROOT_DIR / "outputs" / "checkpoints" / "cognitutor_s_best.pt"
SAMPLES_DIR = ROOT_DIR / "outputs" / "samples"

STRUCTURED_TASKS = {
    "mcq",
    "debug_task",
    "output_prediction",
    "flashcard",
    "personal_flashcards",
    "mindmap",
}

PLAIN_TEXT_TASKS = {
    "explanation",
    "transfer_question",
    "challenge_question",
    "hint",
    "feedback",
    "revision_note",
    "notebook_summary",
    "revision_plan",
    "daily_review",
}


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def normalize_for_duplicate_check(value: Any) -> str:
    """
    Converts generated output into a simple normalized string for duplicate detection.
    Works for both dict JSON outputs and plain text outputs.
    """
    if isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    else:
        text = str(value)

    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def clean_plain_text_output(
    task_type: str,
    answer: str,
    concept_name: str,
    key_points: str = "",
) -> str:
    """
    Cleans plain-text task outputs so website/demo output is readable.
    This does not touch JSON tasks.
    """
    answer = answer.strip()
    answer = answer.replace("This is This is", "This is")
    answer = re.sub(r"\s+", " ", answer)

    # Stop leaked training tags.
    for marker in [
        "<bos>",
        "<eos>",
        "</s>",
        "<instruction>",
        "<format_rule>",
        "<content>",
        "<key_points>",
        "<misconceptions>",
        "<examples>",
        "<answer>",
    ]:
        if marker in answer:
            answer = answer.split(marker, 1)[0].strip()

    if task_type == "transfer_question":
        answer = answer.replace(" - ", " ")
        answer = answer.replace("- ", "")
        answer = re.sub(r"\s+", " ", answer).strip()

        key = key_points.split("|")[0].strip() if key_points else f"the main idea of {concept_name}"

        bad_endings = (
            " for?",
            " at?",
            " in?",
            " with?",
            " of?",
            " to?",
            " for",
            " at",
            " in",
            " with",
            " of",
            " to",
        )

        if answer.endswith(bad_endings) or len(answer) < 45:
            answer = (
                f"Transfer question: How would you use {concept_name} in a real program "
                f"while applying this rule: {key}?"
            )

        if not answer.endswith("?"):
            answer = answer.rstrip(".") + "?"

    elif task_type == "challenge_question":
        if "<" in answer:
            answer = answer.split("<", 1)[0].strip()

        if not answer.lower().startswith("challenge"):
            key = key_points.split("|")[0].strip() if key_points else f"the main rule of {concept_name}"
            answer = (
                f"Challenge: Create one example using {concept_name}. "
                f"Your example should show this rule: {key}"
            )

        if not answer.endswith("."):
            answer = answer.rstrip(".") + "."

    elif task_type == "explanation":
        if len(answer) < 25:
            key = key_points.split("|")[0].strip() if key_points else f"{concept_name} is an important concept."
            answer = f"{concept_name}: {key}"

    return answer.strip()


def get_task_plan(num_questions: int) -> List[str]:
    """
    Builds the mix of task types for 10, 15, or 20 questions.
    For other numbers, it starts from 15-question distribution and trims/extends.
    """
    if num_questions <= 10:
        plan = [
            "mcq",
            "mcq",
            "mcq",
            "mcq",
            "output_prediction",
            "output_prediction",
            "debug_task",
            "debug_task",
            "transfer_question",
            "challenge_question",
        ]
        return plan[:num_questions]

    if num_questions <= 15:
        plan = [
            "mcq",
            "mcq",
            "mcq",
            "mcq",
            "mcq",
            "output_prediction",
            "output_prediction",
            "output_prediction",
            "debug_task",
            "debug_task",
            "debug_task",
            "transfer_question",
            "transfer_question",
            "challenge_question",
            "explanation",
        ]
        return plan[:num_questions]

    plan = [
        "mcq",
        "mcq",
        "mcq",
        "mcq",
        "mcq",
        "mcq",
        "mcq",
        "output_prediction",
        "output_prediction",
        "output_prediction",
        "output_prediction",
        "debug_task",
        "debug_task",
        "debug_task",
        "debug_task",
        "transfer_question",
        "transfer_question",
        "challenge_question",
        "challenge_question",
        "explanation",
    ]

    if num_questions <= 20:
        return plan[:num_questions]

    # If user asks more than 20, cycle through useful assessment tasks.
    cycle = [
        "mcq",
        "output_prediction",
        "debug_task",
        "transfer_question",
        "challenge_question",
    ]

    while len(plan) < num_questions:
        plan.append(cycle[len(plan) % len(cycle)])

    return plan


def get_temperature(task_type: str, attempt: int = 0) -> float:
    base = {
        "mcq": 0.8,
        "debug_task": 0.7,
        "output_prediction": 0.7,
        "transfer_question": 0.7,
        "challenge_question": 0.7,
        "explanation": 0.6,
        "flashcard": 0.7,
    }.get(task_type, 0.7)

    # Increase slightly on retries to reduce duplicates.
    return min(base + (attempt * 0.1), 1.0)


def get_max_new_tokens(task_type: str) -> int:
    return {
        "mcq": 140,
        "debug_task": 120,
        "output_prediction": 120,
        "transfer_question": 100,
        "challenge_question": 100,
        "explanation": 120,
        "flashcard": 90,
    }.get(task_type, 120)


def parse_output_by_task(task_type: str, answer: str) -> Any:
    if task_type in STRUCTURED_TASKS:
        json_text = extract_json_object(answer)
        try:
            return json.loads(json_text)
        except Exception:
            return json_text

    return answer


def generate_single_question(
    *,
    model,
    tokenizer,
    device,
    task_type: str,
    concept_name: str,
    domain: str,
    difficulty: str,
    learner_state: str,
    teaching_style: str,
    base_content: str,
    key_points: str,
    misconceptions: str,
    examples: str,
    seen_outputs: set,
    question_index: int,
    max_retries: int = 3,
) -> Tuple[Dict[str, Any], bool]:
    """
    Generates one question and retries if duplicate/invalid.
    Returns:
    - question item dict
    - whether a duplicate was removed/retried
    """
    duplicate_removed = False
    best_item = None

    for attempt in range(max_retries + 1):
        prompt = build_prompt(
            concept_name=concept_name,
            domain=domain,
            difficulty=difficulty,
            learner_state=learner_state,
            teaching_style=teaching_style,
            task_type=task_type,
            base_content=base_content,
            key_points=key_points,
            misconceptions=misconceptions,
            examples=examples,
        )

        answer, _ = generate_text(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            device=device,
            max_new_tokens=get_max_new_tokens(task_type),
            temperature=get_temperature(task_type, attempt),
            top_k=50,
        )

        used_fallback = False

        if task_type in STRUCTURED_TASKS:
            answer = extract_json_object(answer)
        else:
            answer = clean_plain_text_output(
                task_type=task_type,
                answer=answer,
                concept_name=concept_name,
                key_points=key_points,
            )

        validation = validate_output(
            task_type=task_type,
            generated_text=answer,
            concept_name=concept_name,
            key_points=key_points.split("|") if key_points else None,
        )

        if task_type in STRUCTURED_TASKS and not validation["valid"]:
            fallback = fallback_output(
                task_type=task_type,
                concept_name=concept_name,
                domain=domain,
                base_content=base_content,
                key_points=key_points,
            )

            if fallback is not None:
                answer = json.dumps(fallback, ensure_ascii=False)
                used_fallback = True

                validation = validate_output(
                    task_type=task_type,
                    generated_text=answer,
                    concept_name=concept_name,
                    key_points=key_points.split("|") if key_points else None,
                )

        parsed_output = parse_output_by_task(task_type, answer)
        normalized = normalize_for_duplicate_check(parsed_output)

        item = {
            "question_id": f"Q{question_index}",
            "task_type": task_type,
            "difficulty": difficulty,
            "output": parsed_output,
            "raw_output": answer,
            "valid": bool(validation["valid"]),
            "used_fallback": used_fallback,
            "duplicate": normalized in seen_outputs,
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        }

        best_item = item

        if normalized not in seen_outputs and item["valid"]:
            seen_outputs.add(normalized)
            return item, duplicate_removed

        duplicate_removed = True

    # If all retries failed or duplicated, keep best valid/fallback output.
    if best_item is None:
        best_item = {
            "question_id": f"Q{question_index}",
            "task_type": task_type,
            "difficulty": difficulty,
            "output": "",
            "raw_output": "",
            "valid": False,
            "used_fallback": False,
            "duplicate": True,
            "errors": ["Generation failed"],
            "warnings": [],
        }

    seen_outputs.add(normalize_for_duplicate_check(best_item["output"]))
    return best_item, duplicate_removed


def build_markdown_report(bundle: Dict[str, Any]) -> str:
    lines = []

    lines.append("# CogniTutorLM Assessment Bundle")
    lines.append("")
    lines.append(f"Concept: **{bundle['concept_name']}**")
    lines.append(f"Domain: **{bundle['domain']}**")
    lines.append(f"Difficulty: **{bundle['difficulty']}**")
    lines.append(f"Questions generated: **{bundle['num_generated']} / {bundle['num_requested']}**")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    for key, value in bundle["summary"].items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    lines.append("## Questions")
    lines.append("")

    for q in bundle["questions"]:
        lines.append(f"### {q['question_id']} — {q['task_type']}")
        lines.append("")
        lines.append(f"- Valid: `{q['valid']}`")
        lines.append(f"- Used fallback: `{q['used_fallback']}`")
        lines.append(f"- Duplicate: `{q['duplicate']}`")
        lines.append("")

        output = q["output"]

        if isinstance(output, dict):
            lines.append("```json")
            lines.append(json.dumps(output, indent=2, ensure_ascii=False))
            lines.append("```")
        else:
            lines.append(str(output))

        if q["errors"]:
            lines.append("")
            lines.append(f"Errors: `{q['errors']}`")

        if q["warnings"]:
            lines.append("")
            lines.append(f"Warnings: `{q['warnings']}`")

        lines.append("")

    return "\n".join(lines)


def generate_assessment_bundle(
    concept_name: str,
    domain: str,
    difficulty: str,
    learner_state: str,
    teaching_style: str,
    base_content: str,
    key_points: str,
    misconceptions: str,
    examples: str,
    checkpoint_path: str = "outputs/checkpoints/cognitutor_s_best.pt",
    num_questions: int = 15,
) -> Dict[str, Any]:
    """
    Main public function.

    This function can be called later from:
    - backend API
    - main tutor pipeline
    - website connector
    """
    device = get_device()

    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.is_absolute():
        ckpt_path = ROOT_DIR / ckpt_path

    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    model, _, _ = load_checkpoint(ckpt_path, device)
    tokenizer = CogniTutorTokenizer()

    task_plan = get_task_plan(num_questions)

    questions = []
    seen_outputs = set()
    duplicate_retry_count = 0

    for idx, task_type in enumerate(task_plan, start=1):
        item, duplicate_removed = generate_single_question(
            model=model,
            tokenizer=tokenizer,
            device=device,
            task_type=task_type,
            concept_name=concept_name,
            domain=domain,
            difficulty=difficulty,
            learner_state=learner_state,
            teaching_style=teaching_style,
            base_content=base_content,
            key_points=key_points,
            misconceptions=misconceptions,
            examples=examples,
            seen_outputs=seen_outputs,
            question_index=idx,
        )

        duplicate_retry_count += int(duplicate_removed)
        questions.append(item)

    valid_count = sum(1 for q in questions if q["valid"])
    fallback_count = sum(1 for q in questions if q["used_fallback"])
    duplicate_count = sum(1 for q in questions if q["duplicate"])
    task_distribution = dict(Counter(q["task_type"] for q in questions))

    bundle = {
        "status": "success",
        "model": "CogniTutorLM-S",
        "checkpoint": str(ckpt_path),
        "concept_name": concept_name,
        "domain": domain,
        "difficulty": difficulty,
        "learner_state": learner_state,
        "teaching_style": teaching_style,
        "num_requested": num_questions,
        "num_generated": len(questions),
        "questions": questions,
        "summary": {
            "valid_count": valid_count,
            "fallback_count": fallback_count,
            "duplicate_count": duplicate_count,
            "duplicate_retry_count": duplicate_retry_count,
            "task_distribution": task_distribution,
        },
    }

    return bundle


def save_bundle(bundle: Dict[str, Any], slug: str = "variables") -> Dict[str, str]:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    json_path = SAMPLES_DIR / f"assessment_bundle_{slug}.json"
    md_path = SAMPLES_DIR / f"assessment_bundle_{slug}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(bundle))

    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--concept_name", type=str, default="Variables")
    parser.add_argument("--domain", type=str, default="Python")
    parser.add_argument("--difficulty", type=str, default="easy")
    parser.add_argument("--learner_state", type=str, default="low_mastery")
    parser.add_argument("--teaching_style", type=str, default="code_first")
    parser.add_argument("--num_questions", type=int, default=15)
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="outputs/checkpoints/cognitutor_s_best.pt",
    )

    parser.add_argument(
        "--base_content",
        type=str,
        default="A variable is a name used to store and reuse a value in a program.",
    )
    parser.add_argument(
        "--key_points",
        type=str,
        default=(
            "A variable is a name bound to an object in memory | "
            "Python uses dynamic typing | "
            "Variables are case-sensitive"
        ),
    )
    parser.add_argument(
        "--misconceptions",
        type=str,
        default=(
            "Variables can be used before assignment | "
            "Python variables store values directly"
        ),
    )
    parser.add_argument(
        "--examples",
        type=str,
        default='name = "Alice"\\nprint(name)',
    )

    args = parser.parse_args()

    bundle = generate_assessment_bundle(
        concept_name=args.concept_name,
        domain=args.domain,
        difficulty=args.difficulty,
        learner_state=args.learner_state,
        teaching_style=args.teaching_style,
        base_content=args.base_content,
        key_points=args.key_points,
        misconceptions=args.misconceptions,
        examples=args.examples,
        checkpoint_path=args.checkpoint,
        num_questions=args.num_questions,
    )

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", args.concept_name.lower()).strip("_")
    saved = save_bundle(bundle, slug=slug)

    print("\nAssessment bundle generated.")
    print(f"Concept: {bundle['concept_name']}")
    print(f"Domain: {bundle['domain']}")
    print(f"Total questions: {bundle['num_generated']}")
    print(f"Valid: {bundle['summary']['valid_count']}/{bundle['num_generated']}")
    print(f"Fallback used: {bundle['summary']['fallback_count']}")
    print(f"Duplicates kept: {bundle['summary']['duplicate_count']}")
    print(f"Duplicate retries: {bundle['summary']['duplicate_retry_count']}")
    print(f"Task distribution: {bundle['summary']['task_distribution']}")
    print(f"Output JSON: {saved['json_path']}")
    print(f"Output Markdown: {saved['markdown_path']}")


if __name__ == "__main__":
    main()