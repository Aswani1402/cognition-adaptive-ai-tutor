import csv
import json
from collections import Counter, defaultdict
from itertools import product

from src.cognitutor_lm_config import ROOT
from src.rag_llm_live_guarded_generator import generate_live_guarded

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "evaluation"
OUT_JSON = OUT_DIR / "retrained_fast_evaluation.json"
OUT_MD = OUT_DIR / "retrained_fast_evaluation.md"
OUT_CSV = OUT_DIR / "retrained_fast_cases.csv"

CONCEPTS = [("Python", "Variables"), ("SQL", "JOIN Operations"), ("HTML", "Forms and Inputs"), ("Git", "Branches"), ("Data Structures", "Trees")]
DIFFICULTIES = ["easy", "medium", "hard"]
TASK_TYPES = ["explanation", "definition_view", "code_view", "mcq", "debug_task", "output_prediction", "fill_in_the_blank", "true_or_false", "flashcard", "mindmap", "hint", "feedback", "doubt_answer", "revision_summary", "voice_script", "challenge_question", "transfer_question"]


def summarize(rows):
    n = len(rows) or 1
    valid = [r for r in rows if r["model_valid"]]
    failures = [r for r in rows if not r["model_valid"]]
    by_task = defaultdict(list)
    by_domain = defaultdict(list)
    by_diff = defaultdict(list)
    for r in rows:
        by_task[r["task_type"]].append(r)
        by_domain[r["domain"]].append(r)
        by_diff[r["difficulty"]].append(r)
    return {
        "attempts": len(rows),
        "model_loaded": any(r["model_loaded"] for r in rows),
        "model_checkpoint_used": next((r["model_checkpoint_used"] for r in rows if r.get("model_checkpoint_used")), None),
        "model_valid_count": len(valid),
        "model_valid_rate": len(valid) / n,
        "schema_valid_rate": sum(1 for r in rows if r["schema_valid"]) / n,
        "concept_match_rate": sum(1 for r in rows if r["concept_match"]) / n,
        "domain_match_rate": sum(1 for r in rows if r["domain_match"]) / n,
        "task_match_rate": sum(1 for r in rows if r["task_match"]) / n,
        "frontend_renderable_rate": sum(1 for r in rows if r["frontend_ready"]) / n,
        "fallback_rate": sum(1 for r in rows if r["fallback_used"]) / n,
        "learner_facing_safe_rate": sum(1 for r in rows if r["learner_facing_safe"]) / n,
        "average_quality_score": sum(float(r["quality_score"] or 0) for r in rows) / n,
        "validity_by_task_type": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_task.items()},
        "validity_by_domain": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_domain.items()},
        "validity_by_difficulty": {k: sum(1 for x in v if x["model_valid"]) / len(v) for k, v in by_diff.items()},
        "top_failure_reasons": dict(Counter(r["rejection_reason"] or "unknown" for r in failures).most_common(10)),
    }


def main():
    rows = []
    for (domain, concept), difficulty, task_type in product(CONCEPTS, DIFFICULTIES, TASK_TYPES):
        teaching_view = task_type if task_type.endswith("_view") else "definition_view"
        result = generate_live_guarded(task_type, domain, concept, difficulty=difficulty, teaching_view=teaching_view, max_attempts=1)
        attempt = result.get("model_attempt") or {}
        validation = attempt.get("raw_validation") or result.get("validation") or {}
        row = {
            "domain": domain,
            "concept_name": concept,
            "difficulty": difficulty,
            "task_type": task_type,
            "model_loaded": attempt.get("model_loaded"),
            "model_checkpoint_used": attempt.get("model_checkpoint_used") or result.get("model_checkpoint_used"),
            "model_valid": attempt.get("model_valid"),
            "schema_valid": validation.get("schema_valid"),
            "concept_match": validation.get("concept_match"),
            "domain_match": validation.get("domain_match"),
            "task_match": validation.get("task_match"),
            "frontend_ready": result.get("frontend_ready"),
            "fallback_used": result.get("fallback_used"),
            "learner_facing_safe": result.get("learner_facing_safe"),
            "quality_score": validation.get("quality_score"),
            "rejection_reason": validation.get("rejection_category"),
            "final_source": result.get("final_source"),
        }
        rows.append(row)
        print(f"{len(rows)}/255 {domain}/{concept}/{difficulty}/{task_type}: valid={row['model_valid']} source={row['final_source']}")
    metrics = summarize(rows)
    metrics["status"] = "PASS" if metrics["model_valid_rate"] >= 0.85 and metrics["learner_facing_safe_rate"] == 1.0 else ("WARN" if metrics["learner_facing_safe_rate"] == 1.0 else "FAIL")
    report = {"status": metrics["status"], "metrics": metrics, "cases": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    OUT_MD.write_text("# Retrained Model-First Fast Evaluation\n\n" + "\n".join(f"- {k}: {v}" for k, v in metrics.items() if not isinstance(v, dict)), encoding="utf-8")
    print(json.dumps({"status": metrics["status"], "metrics": metrics}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
