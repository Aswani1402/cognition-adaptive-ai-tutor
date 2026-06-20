import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from src.cognitutor_lm_config import ALL_89_TASK_TYPES, ALL_TASK_OUTPUT, ROOT
from src.concept_resource_loader import load_concept_resources
from src.model_first_runtime import _schema_hint, _style_token, _task_token
from src.model_first_validator import validate_model_output

OUT_BASE = ROOT / "outputs" / "model_first_full_retrain" / "dataset"
TRAIN = ROOT / "training_data" / "model_first_full" / "tutor_train.jsonl"
VAL = ROOT / "training_data" / "model_first_full" / "tutor_val.jsonl"
TEST = ROOT / "training_data" / "model_first_full" / "tutor_test.jsonl"
OUT_JSON = OUT_BASE / "model_first_full_dataset_report.json"
OUT_MD = OUT_BASE / "model_first_full_dataset_report.md"


def _clean(value: Any, max_chars: int = 900) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text[:max_chars].rsplit(" ", 1)[0].strip() if len(text) > max_chars else text


def _context(row: Dict[str, Any], concept_map: Dict[tuple, Dict[str, Any]]) -> str:
    concept = concept_map.get((row.get("domain"), row.get("concept_id"))) or {}
    return "\n".join(
        [
            f"Definition: {_clean(concept.get('definition') or concept.get('base_content'), 420)}",
            f"Key points: {_clean(' '.join(concept.get('key_points') or []), 260)}",
            f"Examples: {_clean(' '.join(concept.get('examples') or []), 240)}",
            f"Misconceptions: {_clean(' '.join(concept.get('misconceptions') or []), 220)}",
        ]
    ).strip()


def _target(row: Dict[str, Any]) -> str:
    output = row.get("output")
    if isinstance(output, (dict, list)):
        return json.dumps(output, ensure_ascii=False)
    return str(output or row.get("answer") or row.get("explanation") or "")


def _frontend_component(task_type: str) -> str:
    if task_type == "mcq":
        return "assessment_mcq"
    if task_type in {"debug_task", "output_prediction"}:
        return "code_assessment"
    if "flashcard" in task_type:
        return "flashcard"
    if "mindmap" in task_type:
        return "mindmap"
    if "voice" in task_type or task_type.endswith("_script"):
        return "voice_script"
    return "teaching_or_support_card"


def _instruction(row: Dict[str, Any], context: str) -> str:
    task_type = row.get("task_type")
    difficulty = row.get("difficulty") or "easy"
    teaching_view = row.get("teaching_view") or ""
    return f"""<bos>
<instruction> Generate project-specific tutor learning output.
{_task_token(task_type)}
<{difficulty}>
{_style_token(task_type, teaching_view)}
<task_type> {task_type}
<concept> {row.get('concept_name')}
<domain> {row.get('domain')}
<teaching_view> {teaching_view}
<context>
{context}
</context>
Required output: {_schema_hint(task_type)}
Output only the requested structured content. Do not invent unrelated content. Use the context above.
Repeat target: {task_type} for {row.get('domain')} / {row.get('concept_name')}.
<answer>"""


def write_jsonl(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    raw_rows = json.loads(ALL_TASK_OUTPUT.read_text(encoding="utf-8")) if ALL_TASK_OUTPUT.exists() else []
    concepts = load_concept_resources()
    concept_map = {(c["domain"], c["concept_id"]): c for c in concepts}
    dataset = []
    seen_targets = set()
    valid_count = 0
    for row in raw_rows:
        task_type = row.get("task_type")
        context = _context(row, concept_map)
        target = _target(row)
        key = (row.get("domain"), row.get("concept_id"), task_type, target)
        validation = validate_model_output(row.get("output") or {}, task_type, row.get("domain"), row.get("concept_name"), row.get("difficulty") or "easy", row.get("teaching_view"))
        valid_count += 1 if validation.get("frontend_renderable") else 0
        if key in seen_targets:
            continue
        seen_targets.add(key)
        instruction = _instruction(row, context)
        dataset.append(
            {
                "instruction": instruction,
                "input": {
                    "domain": row.get("domain"),
                    "concept_id": row.get("concept_id"),
                    "concept_name": row.get("concept_name"),
                    "difficulty": row.get("difficulty"),
                    "teaching_view": row.get("teaching_view"),
                },
                "target": target,
                "output": target,
                "training_text": f"{instruction} {target}\n<eos>",
                "task_type": task_type,
                "task_token": _task_token(task_type),
                "domain": row.get("domain"),
                "concept_id": row.get("concept_id"),
                "concept_name": row.get("concept_name"),
                "difficulty": row.get("difficulty") or "easy",
                "source_level": row.get("source_level"),
                "teaching_view": row.get("teaching_view"),
                "context": context,
                "output_schema": _schema_hint(task_type),
                "frontend_component": _frontend_component(task_type),
            }
        )
    dataset.sort(key=lambda x: (x["domain"] or "", x["concept_id"] or "", x["task_type"] or ""))
    n = len(dataset)
    train = [r for i, r in enumerate(dataset) if i % 10 not in {8, 9}]
    val = [r for i, r in enumerate(dataset) if i % 10 == 8]
    test = [r for i, r in enumerate(dataset) if i % 10 == 9]
    write_jsonl(train, TRAIN)
    write_jsonl(val, VAL)
    write_jsonl(test, TEST)

    domains = Counter(r["domain"] for r in dataset)
    task_counts = Counter(r["task_type"] for r in dataset)
    difficulties = Counter(r["difficulty"] for r in dataset)
    concept_keys = {(r["domain"], r["concept_id"]) for r in dataset}
    expected_concepts = {(c["domain"], c["concept_id"]) for c in concepts}
    duplicate_rate = 1.0 - (n / max(len(raw_rows), 1))
    schema_valid_rate = valid_count / max(len(raw_rows), 1)
    missing_task_types = sorted(set(ALL_89_TASK_TYPES) - set(task_counts))
    missing_concepts = sorted(f"{d}:{cid}" for d, cid in (expected_concepts - concept_keys))
    status = "PASS" if len(domains) == 5 and len(concept_keys) == 38 and len(task_counts) == 89 and not missing_task_types and not missing_concepts and schema_valid_rate >= 0.95 else "WARN"
    report = {
        "status": status,
        "total_rows": n,
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "domain_count": len(domains),
        "concept_count": len(concept_keys),
        "task_type_count": len(task_counts),
        "rows_by_domain": dict(domains),
        "rows_by_task_type": dict(task_counts),
        "rows_by_difficulty": dict(difficulties),
        "missing_task_types": missing_task_types,
        "missing_concepts": missing_concepts,
        "schema_valid_target_rate": schema_valid_rate,
        "duplicate_rate": duplicate_rate,
        "paths": {"train": str(TRAIN), "val": str(VAL), "test": str(TEST)},
    }
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Model-First Full Dataset Report", ""]
    for k, v in report.items():
        if k not in {"rows_by_task_type"}:
            lines.append(f"- {k}: {v}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
