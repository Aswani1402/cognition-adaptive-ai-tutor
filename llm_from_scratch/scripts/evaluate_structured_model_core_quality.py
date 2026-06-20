import json
from collections import defaultdict

from scripts.inspect_structured_core_generation_quality import main as inspect_core_main
from scripts.structured_generation_common import ROOT_DIR


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
QUALITY = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.md"


def rate(count, total):
    return round(count / total, 4) if total else 0.0


def main() -> None:
    inspect_core_main()
    items = json.loads(CORE.read_text(encoding="utf-8")) if CORE.exists() else []
    quality = json.loads(QUALITY.read_text(encoding="utf-8")) if QUALITY.exists() else {}
    summary = quality.get("summary", {})

    task_counts = defaultdict(lambda: {"attempted": 0, "valid": 0})
    raw_task_counts = defaultdict(lambda: {"attempted": 0, "valid": 0})
    domain_counts = defaultdict(lambda: {"attempted": 0, "valid": 0})
    for item in items:
        task_counts[item.get("task_type")]["attempted"] += 1
        task_counts[item.get("task_type")]["valid"] += 1 if item.get("final_valid", item.get("valid")) else 0
        raw_task_counts[item.get("task_type")]["attempted"] += 1
        raw_task_counts[item.get("task_type")]["valid"] += 1 if item.get("raw_valid") else 0
        domain_counts[item.get("domain")]["attempted"] += 1
        domain_counts[item.get("domain")]["valid"] += 1 if item.get("final_valid", item.get("valid")) else 0
    task_rates = {task: {**counts, "valid_rate": rate(counts["valid"], counts["attempted"])} for task, counts in task_counts.items()}
    raw_task_rates = {task: {**counts, "valid_rate": rate(counts["valid"], counts["attempted"])} for task, counts in raw_task_counts.items()}
    domain_rates = {domain: {**counts, "valid_rate": rate(counts["valid"], counts["attempted"])} for domain, counts in domain_counts.items()}

    eval_report = {
        "core_attempted": summary.get("core_attempted"),
        "raw_generation_status": summary.get("raw_generation_status"),
        "final_guarded_generation_status": summary.get("final_guarded_generation_status"),
        "raw_valid_count": summary.get("raw_valid_count"),
        "raw_valid_rate": summary.get("raw_valid_rate"),
        "raw_avg_quality_score": summary.get("raw_avg_quality_score"),
        "core_valid": summary.get("core_valid"),
        "final_valid_count": summary.get("final_valid_count"),
        "final_valid_rate": summary.get("final_valid_rate"),
        "valid_rate": summary.get("core_valid_rate"),
        "avg_quality_score": summary.get("core_avg_quality_score"),
        "final_avg_quality_score": summary.get("final_avg_quality_score"),
        "website_ready_rate": summary.get("core_website_ready_rate"),
        "fallback_applied_count": summary.get("fallback_applied_count"),
        "fallback_rate": summary.get("fallback_rate"),
        "task_type_valid_rates": task_rates,
        "raw_task_type_valid_rates": raw_task_rates,
        "domain_valid_rates": domain_rates,
        "concept_coverage": len({item.get("concept_id") for item in items}),
        "task_type_coverage": sorted(task_counts.keys()),
        "mcq_quality_score": summary.get("core_mcq_quality_score"),
        "option_quality_score": summary.get("core_option_quality_score"),
        "debug_quality_score": None,
        "output_prediction_quality_score": None,
        "explanation_quality_score": None,
        "challenge_quality_score": None,
        "hint_quality_score": None,
        "feedback_quality_score": None,
        "revision_quality_score": None,
        "mindmap_quality_score": None,
        "doubt_answer_quality_score": None,
        "voice_script_quality_score": None,
        "logical_consistency_score": summary.get("core_logical_consistency_score"),
        "domain_relevance_score": summary.get("core_domain_relevance_score"),
        "repetition_rate": summary.get("core_repetition_rate"),
        "duplicate_output_count": summary.get("core_duplicate_output_count"),
        "status": summary.get("core_quality_status"),
        "website_mode_allowed": summary.get("website_mode_allowed"),
        "full_generation_allowed": summary.get("full_generation_allowed"),
    }
    reports = quality.get("item_reports", [])
    for task, key in {
        "debug_task": "debug_quality_score",
        "output_prediction": "output_prediction_quality_score",
        "explanation": "explanation_quality_score",
        "challenge_question": "challenge_quality_score",
        "hint": "hint_quality_score",
        "feedback": "feedback_quality_score",
        "revision_summary": "revision_quality_score",
        "mindmap": "mindmap_quality_score",
        "doubt_answer": "doubt_answer_quality_score",
        "voice_script": "voice_script_quality_score",
    }.items():
        vals = [row.get("semantic_score", 0.0) for row in reports if row.get("task_type") == task]
        eval_report[key] = round(sum(vals) / len(vals), 4) if vals else None

    OUT_JSON.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Structured Model Core Quality Eval\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in eval_report.items())
        + "\n",
        encoding="utf-8",
    )
    for key in [
        "raw_generation_status",
        "final_guarded_generation_status",
        "raw_valid_rate",
        "valid_rate",
        "avg_quality_score",
        "website_ready_rate",
        "mcq_quality_score",
        "option_quality_score",
        "website_mode_allowed",
        "status",
    ]:
        print(f"{key}: {eval_report.get(key)}")


if __name__ == "__main__":
    main()
