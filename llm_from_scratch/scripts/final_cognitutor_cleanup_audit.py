import json
from pathlib import Path

from scripts.structured_generation_common import ROOT_DIR


OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "final_cognitutor_cleanup_audit.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "final_cognitutor_cleanup_audit.md"

REQUIRED_SOURCE = [
    "src/live_tutor_generator.py",
    "src/model_content_validator.py",
    "src/tutor_lm_service.py",
    "src/rag_connector.py",
    "src/learner_memory_service.py",
    "src/doubt_handler_service.py",
    "src/safe_code_runner.py",
    "src/answer_evaluator.py",
]

REQUIRED_SCRIPTS = [
    "scripts/audit_cognitutor_training_state.py",
    "scripts/build_structured_generation_training_dataset.py",
    "scripts/train_structured_cognitutor_generation.py",
    "scripts/evaluate_structured_generation_micro.py",
    "scripts/evaluate_structured_generation_expanded_micro.py",
    "scripts/inspect_structured_generation_quality.py",
    "scripts/generate_structured_model_content_core.py",
    "scripts/inspect_structured_core_generation_quality.py",
    "scripts/evaluate_generation_source_integrity.py",
    "scripts/evaluate_structured_model_core_quality.py",
    "scripts/evaluate_structured_model_website_readiness.py",
    "scripts/create_human_review_sample.py",
    "scripts/generate_cognitutor_lm_backend_report.py",
]

REQUIRED_OUTPUTS = [
    "outputs/final_reports/cognitutor_lm_backend_report.md",
    "outputs/final_reports/cognitutor_lm_backend_report.json",
    "outputs/final_reports/cognitutor_structured_generation_upgrade_report.md",
    "outputs/final_reports/cognitutor_structured_generation_upgrade_report.json",
    "outputs/final_reports/structured_generation_dataset_report.md",
    "outputs/final_reports/structured_generation_dataset_report.json",
    "outputs/final_reports/structured_cognitutor_training_report.md",
    "outputs/final_reports/structured_cognitutor_training_report.json",
    "outputs/evaluation/structured_generation_micro_eval.md",
    "outputs/evaluation/structured_generation_micro_eval.json",
    "outputs/evaluation/structured_generation_expanded_micro_eval.md",
    "outputs/evaluation/structured_generation_expanded_micro_eval.json",
    "outputs/model_generated/structured_model_generated_core.md",
    "outputs/model_generated/structured_model_generated_core.json",
    "outputs/model_generated/structured_model_generated_core_report.md",
    "outputs/model_generated/structured_model_generated_core_report.json",
    "outputs/model_generated/structured_model_generated_core_quality_report.md",
    "outputs/model_generated/structured_model_generated_core_quality_report.json",
    "outputs/evaluation/generation_source_integrity_report.md",
    "outputs/evaluation/generation_source_integrity_report.json",
    "outputs/evaluation/structured_model_core_quality_eval.md",
    "outputs/evaluation/structured_model_core_quality_eval.json",
    "outputs/evaluation/structured_model_website_readiness_eval.md",
    "outputs/evaluation/structured_model_website_readiness_eval.json",
    "outputs/evaluation/human_review_sample_structured_core.csv",
    "outputs/evaluation/human_review_sample_structured_core.md",
    "outputs/evaluation/human_review_sample_structured_core.json",
]

REQUIRED_MODEL = [
    "models/cognitutor_lm_structured_generation/best_model.pt",
    "models/cognitutor_lm_structured_generation/cognitutor.model",
    "models/cognitutor_lm_structured_generation/cognitutor.vocab",
    "models/cognitutor_lm_structured_generation/structured_generation_config.json",
]


def check(paths):
    return {
        path: {
            "exists": (ROOT_DIR / path).exists(),
            "path": str(ROOT_DIR / path),
        }
        for path in paths
    }


def main() -> None:
    sections = {
        "required_source_files": check(REQUIRED_SOURCE),
        "required_structured_generation_scripts": check(REQUIRED_SCRIPTS),
        "required_output_evidence": check(REQUIRED_OUTPUTS),
        "model_checkpoint_and_tokenizer": check(REQUIRED_MODEL),
    }
    missing = [
        path
        for section in sections.values()
        for path, meta in section.items()
        if not meta["exists"]
    ]
    status = "PASS" if not missing else "WARN"
    report = {"status": status, "missing_count": len(missing), "missing": missing, **sections}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Final CogniTutor Cleanup Audit", "", f"- status: {status}", f"- missing_count: {len(missing)}"]
    if missing:
        lines.extend(["", "## Missing"])
        lines.extend(f"- {path}" for path in missing)
    for title, section in sections.items():
        lines.extend(["", f"## {title.replace('_', ' ').title()}"])
        lines.extend(f"- {'OK' if meta['exists'] else 'MISSING'}: {path}" for path, meta in section.items())
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cleanup_audit_status: {status}")
    print(f"missing_count: {len(missing)}")


if __name__ == "__main__":
    main()
