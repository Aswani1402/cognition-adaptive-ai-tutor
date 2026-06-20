import argparse
import csv
import json
from collections import Counter, defaultdict

from src.cognitutor_lm_config import ALL_TASK_OUTPUT, ROOT
from src.model_first_runtime import generate_model_first_safe, load_existing_cognitutor_model
from src.model_first_validator import validate_model_output
from src.rag_live_context_provider import get_live_rag_context

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "evaluation"
OUT_JSON = OUT_DIR / "retrained_full_coverage.json"
OUT_MD = OUT_DIR / "retrained_full_coverage.md"
OUT_CSV = OUT_DIR / "retrained_full_coverage_cases.csv"


def _paths(raw_limit: int, no_raw_decode: bool):
    if no_raw_decode:
        suffix = "noraw"
    else:
        suffix = f"raw{raw_limit}"
    return (
        OUT_DIR / f"retrained_full_coverage_{suffix}.json",
        OUT_DIR / f"retrained_full_coverage_{suffix}.md",
        OUT_DIR / f"retrained_full_coverage_{suffix}_cases.csv",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-limit", type=int, default=100)
    parser.add_argument("--no-raw-decode", action="store_true")
    args = parser.parse_args()
    raw_limit = 0 if args.no_raw_decode else max(0, int(args.raw_limit))
    all_rows = json.loads(ALL_TASK_OUTPUT.read_text(encoding="utf-8")) if ALL_TASK_OUTPUT.exists() else []
    loaded = load_existing_cognitutor_model()
    cases = []
    for idx, row in enumerate(all_rows):
        task_type = row.get("task_type")
        domain = row.get("domain")
        concept = row.get("concept_name")
        difficulty = row.get("difficulty") or "easy"
        teaching_view = row.get("teaching_view") or ("definition_view" if task_type == "explanation" else None)
        if idx < raw_limit:
            context = get_live_rag_context(domain, concept, concept_id=row.get("concept_id"), task_type=task_type, difficulty=difficulty, teaching_view=teaching_view)
            result = generate_model_first_safe(task_type, domain, concept, difficulty, teaching_view, context, max_attempts=1)
            validation = result.get("raw_validation") or result.get("validation") or {}
            raw_output = result.get("raw_output")
            parsed_output = result.get("parsed_output")
            model_valid = bool(result.get("model_valid"))
            fallback_used = bool(result.get("fallback_used"))
            final_source = result.get("final_source")
            final_output = result.get("final_output")
            safe = bool(result.get("learner_facing_safe"))
            frontend_ready = bool((result.get("validation") or {}).get("frontend_renderable"))
        else:
            final_output = row.get("output") or row
            validation = validate_model_output(final_output, task_type, domain, concept, difficulty, teaching_view)
            raw_output = ""
            parsed_output = None
            model_valid = False
            fallback_used = True
            final_source = "guarded_product_generator"
            safe = bool(validation.get("frontend_renderable"))
            frontend_ready = bool(validation.get("frontend_renderable"))
        cases.append({
            "domain": domain,
            "concept_id": row.get("concept_id"),
            "concept_name": concept,
            "task_type": task_type,
            "difficulty": difficulty,
            "teaching_view": teaching_view,
            "model_checkpoint_used": loaded.get("model_checkpoint_used"),
            "raw_output": raw_output,
            "parsed_output": parsed_output,
            "validation": validation,
            "model_valid": model_valid,
            "accepted_after_repair": bool(validation.get("accepted_after_repair")),
            "fallback_used": fallback_used,
            "final_source": final_source,
            "frontend_ready": frontend_ready,
            "learner_facing_safe": safe,
            "quality_score": validation.get("quality_score"),
            "raw_decode_evaluated": idx < raw_limit,
        })
    n = len(cases) or 1
    by_task = defaultdict(list)
    by_domain = defaultdict(list)
    by_diff = defaultdict(list)
    failures = []
    for c in cases:
        by_task[c["task_type"]].append(c)
        by_domain[c["domain"]].append(c)
        by_diff[c["difficulty"]].append(c)
        if not c["learner_facing_safe"] or not c["frontend_ready"]:
            failures.append(c)
    raw_cases = [c for c in cases if c["raw_decode_evaluated"]]
    raw_n = len(raw_cases) or 1
    metrics = {
        "subject_count": len({c["domain"] for c in cases}),
        "concept_count": len({(c["domain"], c["concept_id"]) for c in cases}),
        "task_type_count": len({c["task_type"] for c in cases}),
        "expected_case_count": 3382,
        "evaluated_case_count": len(cases),
        "full_evaluated_case_count": len(cases),
        "raw_limit_requested": raw_limit,
        "model_checkpoint_used": loaded.get("model_checkpoint_used"),
        "model_checkpoint_status": loaded.get("model_checkpoint_status"),
        "model_training_report_status": loaded.get("model_training_report_status"),
        "raw_decode_evaluated_count": sum(1 for c in cases if c["raw_decode_evaluated"]),
        "raw_model_valid_count_on_raw_decode": sum(1 for c in raw_cases if c["model_valid"]),
        "raw_model_valid_rate_on_raw_decode": (sum(1 for c in raw_cases if c["model_valid"]) / raw_n) if raw_cases else None,
        "raw_fallback_rate_on_raw_decode": (sum(1 for c in raw_cases if c["fallback_used"]) / raw_n) if raw_cases else None,
        "model_loaded": bool(loaded.get("model_loaded")),
        "model_valid_count": sum(1 for c in cases if c["model_valid"]),
        "model_valid_rate": sum(1 for c in cases if c["model_valid"]) / n,
        "accepted_after_repair_count": sum(1 for c in cases if c["accepted_after_repair"]),
        "fallback_count": sum(1 for c in cases if c["fallback_used"]),
        "fallback_rate": sum(1 for c in cases if c["fallback_used"]) / n,
        "full_fallback_rate": sum(1 for c in cases if c["fallback_used"]) / n,
        "frontend_ready_rate": sum(1 for c in cases if c["frontend_ready"]) / n,
        "learner_facing_safe_rate": sum(1 for c in cases if c["learner_facing_safe"]) / n,
        "full_final_safe_rate": sum(1 for c in cases if c["learner_facing_safe"]) / n,
        "average_quality_score": sum(float(c["quality_score"] or 0) for c in cases) / n,
        "final_source_distribution": dict(Counter(c["final_source"] for c in cases)),
        "model_valid_rate_by_task_type": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_task.items()},
        "model_valid_rate_by_domain": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_domain.items()},
        "model_valid_rate_by_difficulty": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_diff.items()},
        "fallback_rate_by_task_type": {k: sum(1 for x in v if x["fallback_used"]) / len(v) for k, v in by_task.items()},
        "failures_by_concept": dict(Counter(f"{c['domain']} / {c['concept_name']}" for c in failures)),
        "failures_by_task_type": dict(Counter(c["task_type"] for c in failures)),
        "raw_decode_limit_note": "Raw-decoded metrics are computed only over raw_decode_evaluated_count. Remaining cases use guarded final-output coverage.",
    }
    raw_rate = metrics["raw_model_valid_rate_on_raw_decode"]
    metrics["status"] = "PASS" if raw_rate is not None and raw_rate >= 0.85 and metrics["learner_facing_safe_rate"] == 1.0 and metrics["frontend_ready_rate"] >= 0.95 else ("WARN" if metrics["learner_facing_safe_rate"] == 1.0 else "FAIL")
    report = {"status": metrics["status"], "metrics": metrics, "cases": cases}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json, out_md, out_csv = _paths(raw_limit, args.no_raw_decode)
    for path in {OUT_JSON, out_json}:
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["domain", "concept_id", "concept_name", "task_type", "difficulty", "teaching_view", "model_checkpoint_used", "model_valid", "accepted_after_repair", "fallback_used", "final_source", "frontend_ready", "learner_facing_safe", "quality_score", "raw_decode_evaluated"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in cases:
            writer.writerow({k: c.get(k) for k in fieldnames})
    md_text = "# Retrained Full Coverage Evaluation\n\n" + "\n".join(f"- {k}: {v}" for k, v in metrics.items() if not isinstance(v, dict))
    for path in {OUT_MD, out_md}:
        path.write_text(md_text, encoding="utf-8")
    print(json.dumps({"status": metrics["status"], "metrics": metrics}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
