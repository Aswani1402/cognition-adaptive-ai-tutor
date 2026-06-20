import json

from scripts.evaluate_rag_llm_live_guarded_fast import CONCEPTS, DIFFICULTIES, TASK_TYPES
from src.cognitutor_lm_config import ROOT
from src.model_first_runtime import _find_guarded_row
from src.model_first_validator import validate_model_output
from src.rag_llm_live_guarded_generator import generate_live_guarded

OUT_DIR = ROOT / "outputs" / "rag_llm_live_guarded" / "evaluation"
OUT_JSON = OUT_DIR / "live_guarded_vs_guarded_comparison.json"
OUT_MD = OUT_DIR / "live_guarded_vs_guarded_comparison.md"


def main():
    rows = []
    for domain, concept in CONCEPTS:
        for difficulty in DIFFICULTIES[:1]:
            for task_type in TASK_TYPES:
                live = generate_live_guarded(task_type, domain, concept, difficulty=difficulty, teaching_view="definition_view", max_attempts=1)
                guarded = _find_guarded_row(task_type, domain, concept, difficulty, "definition_view")
                guarded_out = (guarded or {}).get("output") or guarded or {}
                guarded_val = validate_model_output(guarded_out, task_type, domain, concept, difficulty, "definition_view", live.get("rag_context"))
                rows.append({"live": live, "guarded_valid": guarded_val.get("frontend_renderable"), "guarded_quality": guarded_val.get("quality_score", 0)})
    attempts = len(rows) or 1
    metrics = {
        "attempts": len(rows),
        "model_valid_rate": sum(1 for r in rows if (r["live"].get("model_attempt") or {}).get("model_valid")) / attempts,
        "fallback_rate": sum(1 for r in rows if r["live"].get("fallback_used")) / attempts,
        "guarded_valid_rate": sum(1 for r in rows if r["guarded_valid"]) / attempts,
        "final_safe_rate": sum(1 for r in rows if r["live"].get("learner_facing_safe")) / attempts,
        "frontend_ready_rate": sum(1 for r in rows if r["live"].get("frontend_ready")) / attempts,
        "average_quality_score": sum((r["live"].get("validation") or {}).get("quality_score", 0) for r in rows) / attempts,
    }
    if metrics["final_safe_rate"] == 1.0:
        metrics["recommended_runtime_mode"] = "rag_llm_live_guarded_primary" if metrics["model_valid_rate"] >= 0.5 else "guarded_primary_with_live_attempt"
    else:
        metrics["recommended_runtime_mode"] = "guarded_only"
    report = {"status": "PASS" if metrics["final_safe_rate"] == 1.0 else "FAIL", "metrics": metrics}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Live Guarded vs Guarded Comparison", ""]
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
