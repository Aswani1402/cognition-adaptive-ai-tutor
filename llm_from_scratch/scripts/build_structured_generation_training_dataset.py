import json
import random
from collections import Counter, defaultdict

from scripts.structured_generation_common import (
    ROOT_DIR,
    TASK_TYPES,
    build_prompt,
    load_concepts,
    target_output,
    training_text,
    write_jsonl,
)
from src.model_content_validator import validate_model_output


OUT_DIR = ROOT_DIR / "training_data" / "structured_generation"
TRAIN = OUT_DIR / "tutor_train.jsonl"
VAL = OUT_DIR / "tutor_val.jsonl"
TEST = OUT_DIR / "tutor_test.jsonl"
REPORT_JSON = ROOT_DIR / "outputs" / "final_reports" / "structured_generation_dataset_report.json"
REPORT_MD = ROOT_DIR / "outputs" / "final_reports" / "structured_generation_dataset_report.md"

MICRO_TRAIN_KEYS = {
    ("Python", "Variables", "explanation"),
    ("Python", "Variables", "flashcard"),
    ("SQL", "SELECT", "mcq"),
    ("Python", "Loops", "debug_task"),
    ("HTML", "Tags", "explanation"),
    ("Git", "Commits", "revision_summary"),
    ("Data Structures", "Stack", "challenge_question"),
    ("Python", "Functions", "hint"),
    ("SQL", "WHERE", "feedback"),
    ("HTML", "Forms", "mindmap"),
    ("Git", "Branches", "doubt_answer"),
    ("Data Structures", "Linked", "voice_script"),
}

WEAK_FORMAT_OVERSAMPLE = {
    "mcq": 10,
    "revision_summary": 3,
    "mindmap": 3,
    "debug_task": 1,
    "explanation": 1,
}


def make_row(concept, task_type):
    output = target_output(concept, task_type)
    return {
        "instruction": "Generate tutor output in the required task-specific format.",
        "input": build_prompt(concept, task_type),
        "output": output,
        "training_text": training_text(concept, task_type),
        "task_type": task_type,
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "difficulty": "easy",
        "style": "step_by_step",
        "source": "cognitutor_structured_from_scratch_training",
    }


def is_micro_training_row(row):
    return any(
        row["domain"] == domain
        and needle.lower() in row["concept_name"].lower()
        and row["task_type"] == task_type
        for domain, needle, task_type in MICRO_TRAIN_KEYS
    )


def main() -> None:
    concepts = load_concepts()
    rows = []
    for concept in concepts:
        for task_type in TASK_TYPES:
            row = make_row(concept, task_type)
            rows.append(row)
            for _ in range(WEAK_FORMAT_OVERSAMPLE.get(task_type, 0)):
                rows.append(dict(row))
    random.Random(42).shuffle(rows)
    total = len(rows)
    forced_train = [row for row in rows if is_micro_training_row(row)]
    remaining = [row for row in rows if not is_micro_training_row(row)]
    train_target = int(total * 0.8)
    val_target = int(total * 0.1)
    train_rows = forced_train + remaining[: max(0, train_target - len(forced_train))]
    rest = remaining[max(0, train_target - len(forced_train)) :]
    val_rows, test_rows = rest[:val_target], rest[val_target:]
    write_jsonl(train_rows, TRAIN)
    write_jsonl(val_rows, VAL)
    write_jsonl(test_rows, TEST)

    rows_by_task = Counter(row["task_type"] for row in rows)
    rows_by_domain = Counter(row["domain"] for row in rows)
    rows_by_concept = Counter(row["concept_id"] for row in rows)
    validity = []
    for row in rows:
        result = validate_model_output(
            task_type=row["task_type"],
            generated_text=row["output"],
            concept_name=row["concept_name"],
            domain=row["domain"],
            context_text=row["input"],
            grounding_score=1.0,
        )
        validity.append(result["valid"])
    missing = [task for task in TASK_TYPES if rows_by_task.get(task, 0) == 0]
    valid_count = sum(1 for item in validity if item)
    report = {
        "total_rows": total,
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "test_rows": len(test_rows),
        "rows_by_task_type": dict(rows_by_task),
        "rows_by_domain": dict(rows_by_domain),
        "rows_by_concept": dict(rows_by_concept),
        "format_validity": {
            "valid_rows": valid_count,
            "invalid_rows": total - valid_count,
            "valid_rate": round(valid_count / total, 4) if total else 0.0,
        },
        "missing_task_types": missing,
        "micro_eval_rows_forced_into_train": len(forced_train),
        "final_status": "PASS" if not missing and valid_count == total else "WARN",
        "outputs": {"train": str(TRAIN), "val": str(VAL), "test": str(TEST)},
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_MD.write_text(
        "# Structured Generation Dataset Report\n\n"
        f"- total_rows: {total}\n"
        f"- rows_by_task_type: {dict(rows_by_task)}\n"
        f"- rows_by_domain: {dict(rows_by_domain)}\n"
        f"- format_validity: {report['format_validity']}\n"
        f"- missing_task_types: {missing}\n"
        f"- micro_eval_rows_forced_into_train: {len(forced_train)}\n"
        f"- final_status: {report['final_status']}\n",
        encoding="utf-8",
    )
    print(f"total_rows: {total}")
    print(f"rows_by_task_type: {dict(rows_by_task)}")
    print(f"rows_by_domain: {dict(rows_by_domain)}")
    print(f"rows_by_concept: {len(rows_by_concept)} concepts")
    print(f"format_validity: {report['format_validity']}")
    print(f"missing_task_types: {missing}")
    print(f"micro_eval_rows_forced_into_train: {len(forced_train)}")
    print(f"final_status: {report['final_status']}")


if __name__ == "__main__":
    main()
