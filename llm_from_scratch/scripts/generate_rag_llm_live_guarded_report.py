import json

from src.cognitutor_lm_config import ROOT

BASE = ROOT / "outputs" / "rag_llm_live_guarded"
OUT_DIR = BASE / "reports"
OUT_JSON = OUT_DIR / "rag_llm_live_guarded_report.json"
OUT_MD = OUT_DIR / "rag_llm_live_guarded_report.md"

REQUIRED_WORDING = (
    "The trained CogniTutorLM model is used as the first live generation attempt. "
    "Its output is accepted only when parser, schema validation, grounding validation, "
    "and frontend-renderability checks pass. If the raw model output fails, the system "
    "falls back to the existing guarded CogniTutorLM product generator, and then to "
    "RAG/artifact/concept-resource/template fallback if needed. This makes the trained "
    "LLM useful while preserving learner-facing safety."
)


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def main():
    inspection = load(BASE / "inspection" / "existing_model_inspection.json", {})
    fast = load(BASE / "evaluation" / "rag_llm_live_guarded_fast.json", {})
    full = load(BASE / "evaluation" / "rag_llm_live_guarded_full_coverage.json", {})
    comparison = load(BASE / "evaluation" / "live_guarded_vs_guarded_comparison.json", {})
    selected_eval = full if full.get("metrics") else fast
    model_valid_rate = float((selected_eval.get("metrics") or {}).get("model_valid_rate") or 0)
    architecture_wording = (
        "The final system implements a RAG + LLM live guarded generation architecture. CogniTutorLM contributes validated live outputs where the model output passes schema, grounding, and frontend-renderability checks. Guarded fallback remains active for reliability."
        if model_valid_rate > 0
        else "The final system implements a RAG + LLM live guarded generation architecture. CogniTutorLM is attempted as the first live generation source, but only outputs that pass validation are accepted. In the current evaluation, learner-facing safety is maintained through the guarded product generator fallback when raw model outputs are not valid."
    )
    report = {
        "status": selected_eval.get("status") or "WARN",
        "what_was_already_completed": ["guarded product generator", "all-89 outputs", "learning packets", "RAG/API/backend bridge status from existing reports"],
        "why_live_raw_llm_alone_was_risky": "Raw generation can be malformed, ungrounded, repetitive, or not renderable.",
        "architecture": architecture_wording,
        "parser_validator_repair_loop": "parse_model_output plus validate_model_output with up to 3 model attempts.",
        "fallback_hierarchy": ["raw_cognitutor_lm_validated", "guarded_product_generator", "rag_artifact_fallback", "concept_resource_fallback", "template_baseline"],
        "evaluation_metrics": selected_eval.get("metrics", {}),
        "runtime_recommendation": (comparison.get("metrics") or {}).get("recommended_runtime_mode", "WARN/MANUAL_REQUIRED"),
        "what_can_be_claimed": "Learner-facing output is gated by parser, validator, and fallback hierarchy.",
        "what_cannot_be_claimed": "Raw model success is not claimed unless model_valid is true in saved evaluation.",
        "saved_files": {
            "inspection": str(BASE / "inspection"),
            "evaluation": str(BASE / "evaluation"),
            "reports": str(OUT_DIR),
        },
        "inspection": inspection,
        "comparison": comparison,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# RAG + LLM Live Guarded Generator Report", "", REQUIRED_WORDING, ""]
    for key in ["status", "runtime_recommendation", "what_cannot_be_claimed"]:
        lines.append(f"- {key}: {report.get(key)}")
    lines.append("")
    lines.append("## Evaluation Metrics")
    for key, value in report["evaluation_metrics"].items():
        lines.append(f"- {key}: {value}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "runtime_recommendation": report["runtime_recommendation"], "report": str(OUT_JSON)}, indent=2))


if __name__ == "__main__":
    main()
