import json
from pathlib import Path
from typing import Any, Iterable, Set

from scripts.structured_generation_common import ROOT_DIR


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
ARTIFACTS = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
QUESTION_BANK = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"
OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "generation_source_integrity_report.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "generation_source_integrity_report.md"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def collect_outputs(value: Any) -> Set[str]:
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"output", "content", "answer", "question", "explanation", "front", "back"} and isinstance(item, str):
                text = item.strip()
                if text:
                    found.add(text)
            else:
                found |= collect_outputs(item)
    elif isinstance(value, list):
        for item in value:
            found |= collect_outputs(item)
    return found


def main() -> None:
    core = load(CORE) or []
    template_outputs = collect_outputs(load(ARTIFACTS)) | collect_outputs(load(QUESTION_BANK))
    total = len(core)
    model_generated = [
        item for item in core
        if item.get("generation_source") == "cognitutor_lm_from_scratch_structured_model"
        and item.get("model_used") == "CogniTutorLM-from-scratch-structured"
        and item.get("prompt")
        and item.get("output")
    ]
    template_labeled = [
        item for item in core
        if item.get("generation_source") in {"template_baseline", "template_fallback"}
    ]
    exact_copies = [
        item for item in core
        if str(item.get("output", "")).strip() in template_outputs
    ]
    status = "PASS" if total and len(model_generated) == total and not template_labeled and not exact_copies else "WARN"
    report = {
        "total_items": total,
        "model_generated_count": len(model_generated),
        "template_labeled_count": len(template_labeled),
        "exact_template_copy_count": len(exact_copies),
        "suspicious_duplicate_examples": [
            {
                "item_id": item.get("item_id"),
                "concept_name": item.get("concept_name"),
                "task_type": item.get("task_type"),
                "output": item.get("output"),
            }
            for item in exact_copies[:20]
        ],
        "source_integrity_status": status,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Generation Source Integrity Report\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in report.items() if key != "suspicious_duplicate_examples")
        + "\n",
        encoding="utf-8",
    )
    print(f"total_items: {total}")
    print(f"model_generated_count: {len(model_generated)}")
    print(f"template_labeled_count: {len(template_labeled)}")
    print(f"exact_template_copy_count: {len(exact_copies)}")
    print(f"source_integrity_status: {status}")


if __name__ == "__main__":
    main()
