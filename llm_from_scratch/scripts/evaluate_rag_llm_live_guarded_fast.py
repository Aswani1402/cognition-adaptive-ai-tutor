import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import product

from src.cognitutor_lm_config import ROOT
from src.rag_llm_live_guarded_generator import generate_live_guarded

OUT_DIR = ROOT / "outputs" / "rag_llm_live_guarded" / "evaluation"
OUT_JSON = OUT_DIR / "rag_llm_live_guarded_fast.json"
OUT_MD = OUT_DIR / "rag_llm_live_guarded_fast.md"
OUT_CSV = OUT_DIR / "rag_llm_live_guarded_fast_cases.csv"

CONCEPTS = [
    ("Python", "Variables"),
    ("SQL", "JOIN Operations"),
    ("HTML", "Forms and Inputs"),
    ("Git", "Branches"),
    ("Data Structures", "Trees"),
]
DIFFICULTIES = ["easy", "medium", "hard"]
TASK_TYPES = [
    "explanation", "definition_view", "code_view", "mcq", "debug_task",
    "output_prediction", "fill_in_the_blank", "true_or_false", "flashcard",
    "mindmap", "hint", "feedback", "doubt_answer", "revision_summary", "voice_script",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    cases = list(product(CONCEPTS, DIFFICULTIES, TASK_TYPES))
    if args.limit:
        cases = cases[: args.limit]
    rows = []
    for (domain, concept), difficulty, task_type in cases:
        teaching_view = task_type if task_type.endswith("_view") else "definition_view"
        result = generate_live_guarded(task_type, domain, concept, difficulty=difficulty, teaching_view=teaching_view)
        model_attempt = result.get("model_attempt") or {}
        row = {
            "domain": domain,
            "concept": concept,
            "difficulty": difficulty,
            "task_type": task_type,
            "rag_status": (result.get("rag_context") or {}).get("status"),
            "raw_model_output": model_attempt.get("raw_output"),
            "parsed_output": model_attempt.get("parsed_output"),
            "validation": result.get("validation"),
            "model_loaded": model_attempt.get("model_loaded"),
            "model_valid": model_attempt.get("model_valid"),
            "fallback_used": result.get("fallback_used"),
            "final_source": result.get("final_source"),
            "final_output": result.get("final_output"),
            "frontend_ready": result.get("frontend_ready"),
            "learner_facing_safe": result.get("learner_facing_safe"),
            "quality_score": (result.get("validation") or {}).get("quality_score", 0),
        }
        rows.append(row)
        print(f"{len(rows)}/{len(cases)} {domain}/{concept}/{difficulty}/{task_type}: safe={row['learner_facing_safe']} source={row['final_source']}")

    attempts = len(rows) or 1
    final_sources = Counter(str(r["final_source"]) for r in rows)
    failures_by_task_type = Counter(r["task_type"] for r in rows if not r["learner_facing_safe"] or not r["frontend_ready"])
    failures_by_concept = Counter(f"{r['domain']} / {r['concept']}" for r in rows if not r["learner_facing_safe"] or not r["frontend_ready"])
    metrics = {
        "attempts": len(rows),
        "model_loaded": any(r["model_loaded"] for r in rows),
        "rag_success_rate": sum(1 for r in rows if r["rag_status"] == "PASS") / attempts,
        "model_valid_count": sum(1 for r in rows if r["model_valid"]),
        "model_valid_rate": sum(1 for r in rows if r["model_valid"]) / attempts,
        "fallback_count": sum(1 for r in rows if r["fallback_used"]),
        "fallback_rate": sum(1 for r in rows if r["fallback_used"]) / attempts,
        "frontend_ready_rate": sum(1 for r in rows if r["frontend_ready"]) / attempts,
        "learner_facing_safe_rate": sum(1 for r in rows if r["learner_facing_safe"]) / attempts,
        "average_quality_score": sum(float(r["quality_score"] or 0) for r in rows) / attempts,
        "final_source_distribution": dict(final_sources),
        "failures_by_task_type": dict(failures_by_task_type),
        "failures_by_concept": dict(failures_by_concept),
    }
    metrics["status"] = "PASS" if metrics["learner_facing_safe_rate"] == 1.0 and metrics["frontend_ready_rate"] >= 0.95 else ("WARN" if metrics["learner_facing_safe_rate"] == 1.0 else "FAIL")
    report = {"status": metrics["status"], "metrics": metrics, "cases": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "concept", "difficulty", "task_type", "rag_status", "model_loaded", "model_valid", "fallback_used", "final_source", "frontend_ready", "learner_facing_safe", "quality_score"])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in writer.fieldnames})
    lines = ["# RAG LLM Live Guarded Fast Evaluation", ""]
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
