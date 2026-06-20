import json
from collections import Counter

from scripts.inspect_structured_generation_quality import inspect_json_task, inspect_mcq, inspect_text_task, norm
from scripts.structured_generation_common import ROOT_DIR


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "final_structured_generation_quality_sanity_check.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "final_structured_generation_quality_sanity_check.md"
TASKS = {
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "revision_summary",
    "hint",
    "feedback",
    "mindmap",
    "doubt_answer",
    "voice_script",
}


def main() -> None:
    items = json.loads(CORE.read_text(encoding="utf-8")) if CORE.exists() else []
    outputs = Counter(norm(item.get("output")) for item in items)
    repeated = sum(count for text, count in outputs.items() if text and count > 1)
    valid_items = sum(1 for item in items if item.get("valid"))
    website_ready = sum(1 for item in items if item.get("valid") and item.get("output") and item.get("quality_score", 0) >= 0.85)
    mcq_scores = []
    option_scores = []
    failed = []
    for item in items:
        task = item.get("task_type")
        if task == "mcq":
            score, option_score, issues = inspect_mcq(item)
            mcq_scores.append(score)
            option_scores.append(option_score)
        elif task in {"flashcard", "debug_task", "output_prediction", "challenge_question", "mindmap"}:
            score, issues = inspect_json_task(item)
        else:
            score, issues = inspect_text_task(item)
        if issues or not item.get("valid"):
            failed.append(
                {
                    "item_id": item.get("item_id"),
                    "task_type": task,
                    "domain": item.get("domain"),
                    "concept_name": item.get("concept_name"),
                    "issues": issues + item.get("issues", []),
                    "output": item.get("output"),
                }
            )
    total = len(items)
    valid_rate = round(valid_items / total, 4) if total else 0.0
    website_ready_rate = round(website_ready / total, 4) if total else 0.0
    mcq_quality_score = round(sum(mcq_scores) / len(mcq_scores), 4) if mcq_scores else 0.0
    option_quality_score = round(sum(option_scores) / len(option_scores), 4) if option_scores else 0.0
    task_coverage = sorted({item.get("task_type") for item in items})
    domain_coverage = sorted({item.get("domain") for item in items})
    concept_coverage = len({item.get("concept_id") for item in items})
    final_status = "PASS" if valid_rate >= 0.85 and mcq_quality_score >= 0.85 and option_quality_score >= 0.85 else "WARN"
    report = {
        "total_items": total,
        "valid_items": valid_items,
        "valid_rate": valid_rate,
        "mcq_quality_score": mcq_quality_score,
        "option_quality_score": option_quality_score,
        "task_type_coverage": task_coverage,
        "domain_coverage": domain_coverage,
        "concept_coverage": concept_coverage,
        "website_ready_rate": website_ready_rate,
        "repetition_rate": round(repeated / total, 4) if total else 0.0,
        "failed_count": len(failed),
        "failed_examples": failed[:50],
        "final_status": final_status,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Final Structured Generation Quality Sanity Check\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in report.items() if key != "failed_examples")
        + "\n",
        encoding="utf-8",
    )
    print(f"total_items: {total}")
    print(f"valid_items: {valid_items}")
    print(f"valid_rate: {valid_rate}")
    print(f"mcq_quality_score: {mcq_quality_score}")
    print(f"option_quality_score: {option_quality_score}")
    print(f"task_type_coverage: {task_coverage}")
    print(f"domain_coverage: {domain_coverage}")
    print(f"concept_coverage: {concept_coverage}")
    print(f"website_ready_rate: {website_ready_rate}")
    print(f"final_status: {final_status}")


if __name__ == "__main__":
    main()
