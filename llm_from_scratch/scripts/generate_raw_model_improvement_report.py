import json

from src.cognitutor_lm_config import ROOT

BASE = ROOT / "outputs" / "rag_llm_live_guarded"
OUT_DIR = BASE / "reports"
OUT_JSON = OUT_DIR / "raw_model_improvement_report.json"
OUT_MD = OUT_DIR / "raw_model_improvement_report.md"


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def main():
    fast = load(BASE / "evaluation" / "rag_llm_live_guarded_fast.json", {})
    diagnosis = load(BASE / "diagnostics" / "model_first_rejection_diagnosis.json", {})
    comparison = load(BASE / "evaluation" / "live_guarded_vs_guarded_comparison.json", {})
    metrics = fast.get("metrics") or {}
    improved = float(metrics.get("model_valid_rate") or 0)
    wording = (
        "Raw CogniTutorLM acceptance improved after aligning prompts, parser repair, and validation logic. The system uses raw model outputs when valid and fallback when invalid."
        if improved > 0
        else "Raw CogniTutorLM was attempted and diagnosed, but outputs did not pass strict learner-facing validation. The final runtime remains guarded-primary with live model attempts recorded for research."
    )
    report = {
        "initial_model_valid_rate": 0.0,
        "improved_model_valid_rate": improved,
        "top_rejection_causes": diagnosis.get("top_rejection_causes", {}),
        "parser_fixes_applied": ["plain teaching text wrapping", "MCQ A/B/C/D parsing", "flashcard Q/A parsing", "mindmap bullet parsing", "voice/hint/feedback wrappers"],
        "validator_fixes_applied": ["accepted_after_repair field", "rejection_category field", "quality threshold with hard safety issues"],
        "prompt_fixes_applied": ["training-style task token", "difficulty token", "style token", "context block", "answer marker"],
        "quick_training_done_or_skipped": "skipped",
        "fallback_rate": metrics.get("fallback_rate"),
        "learner_facing_safe_rate": metrics.get("learner_facing_safe_rate"),
        "frontend_ready_rate": metrics.get("frontend_ready_rate"),
        "runtime_recommendation": (comparison.get("metrics") or {}).get("recommended_runtime_mode", "guarded_primary_raw_model_experimental"),
        "wording": wording,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Raw Model Improvement Report", "", wording, ""]
    for key, value in report.items():
        if key != "wording":
            lines.append(f"- {key}: {value}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
