import argparse
import json
import math
from pathlib import Path
from typing import Dict, List

import torch
from tqdm import tqdm

from src.dataset import create_dataloaders
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

METRICS_DIR = ROOT_DIR / "outputs" / "metrics"
SAMPLES_DIR = ROOT_DIR / "outputs" / "samples"


STRUCTURED_TASKS = {
    "mcq",
    "debug_task",
    "flashcard",
    "mindmap",
    "output_prediction",
    "personal_flashcards",
}


TASK_TYPES = [
    "mcq",
    "flashcard",
    "debug_task",
    "output_prediction",
    "personal_flashcards",
    "explanation",
    "notebook_summary",
    "revision_plan",
    "daily_review",
]


DEFAULT_CASES = [
    {
        "concept_name": "Variables",
        "domain": "Python",
        "base_content": "A variable is a name used to store and reuse a value in a program.",
        "key_points": "A variable is a name bound to an object in memory | Python uses dynamic typing",
        "misconceptions": "Variables can be used before assignment",
        "examples": 'name = "Alice"\\nprint(name)',
    },
    {
        "concept_name": "SELECT",
        "domain": "SQL",
        "base_content": "SELECT is used to retrieve columns from a database table.",
        "key_points": "SELECT chooses columns to display | FROM chooses the table",
        "misconceptions": "SELECT changes the data in the table",
        "examples": "SELECT name FROM students;",
    },
    {
        "concept_name": "Tags & Elements",
        "domain": "HTML",
        "base_content": "HTML tags mark the beginning and end of elements on a web page.",
        "key_points": "Tags define page structure | Elements usually have opening and closing tags",
        "misconceptions": "All tags must always have closing tags",
        "examples": "<p>Hello</p>",
    },
    {
        "concept_name": "Commits & History",
        "domain": "Git",
        "base_content": "A commit records a snapshot of changes in a repository.",
        "key_points": "Commits save project history | Commit messages explain changes",
        "misconceptions": "A commit automatically uploads changes to GitHub",
        "examples": 'git commit -m "save changes"',
    },
]


def has_repetition(text: str) -> bool:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if len(lines) >= 3 and len(lines) != len(set(lines)):
        return True

    words = text.lower().split()
    if len(words) < 12:
        return False

    repeated_pairs = 0
    for i in range(len(words) - 3):
        phrase = " ".join(words[i : i + 3])
        rest = " ".join(words[i + 3 :])
        if phrase in rest:
            repeated_pairs += 1

    return repeated_pairs >= 3


@torch.no_grad()
def compute_loss_metrics(checkpoint_path: Path, max_batches: int = 100):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, _, _ = load_checkpoint(checkpoint_path, device)
    _, val_loader, test_loader = create_dataloaders(batch_size=4, context_length=256)

    def average_loss(loader):
        model.eval()
        losses = []

        for batch_idx, batch in enumerate(loader):
            if batch_idx >= max_batches:
                break

            input_ids = batch["input_ids"].to(device)
            target_ids = batch["target_ids"].to(device)

            _, loss = model(input_ids, target_ids)
            losses.append(loss.item())

        avg = sum(losses) / len(losses)
        ppl = math.exp(avg) if avg < 20 else float("inf")

        return avg, ppl

    val_loss, val_ppl = average_loss(val_loader)
    test_loss, test_ppl = average_loss(test_loader)

    return {
        "val_loss": val_loss,
        "val_perplexity": val_ppl,
        "test_loss": test_loss,
        "test_perplexity": test_ppl,
    }


def evaluate_generation(checkpoint_path: Path, max_new_tokens: int = 120):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, _, _ = load_checkpoint(checkpoint_path, device)
    tokenizer = CogniTutorTokenizer()

    results = []
    valid_count = 0
    total_count = 0
    repetition_count = 0
    fallback_count = 0

    for case in tqdm(DEFAULT_CASES, desc="Evaluating generation"):
        for task_type in TASK_TYPES:
            prompt = build_prompt(
                concept_name=case["concept_name"],
                domain=case["domain"],
                difficulty="easy",
                learner_state="low_mastery",
                teaching_style="code_first",
                task_type=task_type,
                base_content=case["base_content"],
                key_points=case["key_points"],
                misconceptions=case["misconceptions"],
                examples=case["examples"],
            )

            answer, _ = generate_text(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                device=device,
                max_new_tokens=max_new_tokens,
                temperature=0,
                top_k=50,
            )

            used_fallback = False

            if task_type in STRUCTURED_TASKS:
                answer = extract_json_object(answer)

            validation = validate_output(
                task_type=task_type,
                generated_text=answer,
                concept_name=case["concept_name"],
                key_points=case["key_points"].split("|"),
            )

            if task_type in STRUCTURED_TASKS and not validation["valid"]:
                fallback = fallback_output(
                    task_type=task_type,
                    concept_name=case["concept_name"],
                    domain=case["domain"],
                    base_content=case["base_content"],
                    key_points=case["key_points"],
                )

                if fallback is not None:
                    answer = json.dumps(fallback, ensure_ascii=False)
                    used_fallback = True
                    fallback_count += 1

                    validation = validate_output(
                        task_type=task_type,
                        generated_text=answer,
                        concept_name=case["concept_name"],
                        key_points=case["key_points"].split("|"),
                    )

            is_valid = validation["valid"]
            repeated = has_repetition(answer)

            total_count += 1
            valid_count += int(is_valid)
            repetition_count += int(repeated)

            results.append(
                {
                    "task_type": task_type,
                    "concept_name": case["concept_name"],
                    "domain": case["domain"],
                    "generated_output": answer,
                    "valid": is_valid,
                    "used_fallback": used_fallback,
                    "repetition_detected": repeated,
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                    "parsed": validation["parsed"],
                }
            )

    format_validity = valid_count / total_count if total_count else 0.0
    repetition_rate = repetition_count / total_count if total_count else 0.0
    fallback_rate = fallback_count / total_count if total_count else 0.0

    return {
        "total_cases": total_count,
        "valid_cases": valid_count,
        "format_validity_percent": round(format_validity * 100, 2),
        "repetition_rate_percent": round(repetition_rate * 100, 2),
        "fallback_rate_percent": round(fallback_rate * 100, 2),
        "samples": results,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="outputs/checkpoints/cognitutor_s_best.pt",
    )
    parser.add_argument("--max_new_tokens", type=int, default=120)
    parser.add_argument("--loss_batches", type=int, default=100)

    args = parser.parse_args()

    checkpoint_path = ROOT_DIR / args.checkpoint

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    print("Computing loss metrics...")
    loss_metrics = compute_loss_metrics(
        checkpoint_path=checkpoint_path,
        max_batches=args.loss_batches,
    )

    print("Evaluating generation quality...")
    generation_metrics = evaluate_generation(
        checkpoint_path=checkpoint_path,
        max_new_tokens=args.max_new_tokens,
    )

    final_metrics = {
        "checkpoint": str(checkpoint_path),
        "loss_metrics": loss_metrics,
        "generation_metrics": {
            "total_cases": generation_metrics["total_cases"],
            "valid_cases": generation_metrics["valid_cases"],
            "format_validity_percent": generation_metrics["format_validity_percent"],
            "repetition_rate_percent": generation_metrics["repetition_rate_percent"],
            "fallback_rate_percent": generation_metrics["fallback_rate_percent"],
        },
    }

    metrics_path = METRICS_DIR / "evaluation_metrics.json"
    samples_path = SAMPLES_DIR / "evaluation_samples.json"

    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2, ensure_ascii=False)

    with samples_path.open("w", encoding="utf-8") as f:
        json.dump(generation_metrics["samples"], f, indent=2, ensure_ascii=False)

    print("\nEvaluation complete.")
    print(f"Metrics saved to: {metrics_path}")
    print(f"Samples saved to: {samples_path}")

    print("\nSummary:")
    print(json.dumps(final_metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()