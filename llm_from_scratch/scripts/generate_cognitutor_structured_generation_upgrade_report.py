import json
from pathlib import Path

from scripts.structured_generation_common import ROOT_DIR


OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_structured_generation_upgrade_report.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_structured_generation_upgrade_report.md"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> None:
    dataset = load(ROOT_DIR / "outputs" / "final_reports" / "structured_generation_dataset_report.json")
    training = load(ROOT_DIR / "outputs" / "final_reports" / "structured_cognitutor_training_report.json")
    micro = load(ROOT_DIR / "outputs" / "evaluation" / "structured_generation_micro_eval.json").get("summary", {})
    expanded_micro = load(ROOT_DIR / "outputs" / "evaluation" / "structured_generation_expanded_micro_eval.json").get("summary", {})
    quality_inspection = load(ROOT_DIR / "outputs" / "evaluation" / "structured_generation_quality_inspection.json").get("summary", {})
    failure_analysis = load(ROOT_DIR / "outputs" / "final_reports" / "structured_micro_failure_analysis.json")
    core = load(ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_report.json")
    core_quality = load(ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json").get("summary", {})
    source_integrity = load(ROOT_DIR / "outputs" / "evaluation" / "generation_source_integrity_report.json")
    core_quality_eval = load(ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json")
    website_readiness = load(ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.json")
    full = load(ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_report.json")
    micro_pass = micro.get("valid_rate", 0) >= 0.85 and micro.get("avg_quality_score", 0) >= 0.85
    expanded_micro_pass = (
        expanded_micro.get("valid_rate", 0) >= 0.85
        and expanded_micro.get("avg_quality_score", 0) >= 0.85
        and expanded_micro.get("website_ready_rate", 0) >= 0.85
        and expanded_micro.get("all_5_subjects_represented") is True
        and expanded_micro.get("at_least_8_task_types_represented") is True
    )
    quality_pass = quality_inspection.get("status") == "PASS" and quality_inspection.get("core_generation_allowed") is True
    core_pass = (
        core.get("status") == "PASS"
        and core_quality.get("core_quality_status") == "PASS"
        and core_quality.get("website_mode_allowed") is True
    )
    full_pass = full.get("valid_rate", 0) >= 0.85 and full.get("avg_quality_score", 0) >= 0.85
    core_allowed = bool(micro_pass and expanded_micro_pass and quality_pass)
    website_mode_allowed = bool(core_pass)
    full_generation_allowed = bool(core_pass)
    source_integrity_pass = source_integrity.get("source_integrity_status") == "PASS"
    core_quality_eval_pass = core_quality_eval.get("status") == "PASS"
    website_readiness_pass = website_readiness.get("website_readiness_status") == "PASS"
    website_mode_status = "PASS" if source_integrity_pass and core_quality_eval_pass and website_readiness_pass and website_mode_allowed else "SKIPPED_NOT_ALLOWED"
    final_structured_model_verdict = "PASS" if website_mode_status == "PASS" else "WARN"
    verdict = "PASS" if core_pass else ("WARN" if micro else "FAIL")
    report = {
        "problem": "Current checkpoint could not reliably generate structured MCQ/debug/challenge outputs.",
        "fix": "Structured from-scratch training/fine-tuning stage added.",
        "pretrained_models_used": False,
        "manual_template_final_output_used": False,
        "previous_micro_valid_rate": 0.1667,
        "previous_micro_avg_quality_score": 0.4867,
        "new_micro_valid_rate": micro.get("valid_rate"),
        "new_micro_avg_quality_score": micro.get("avg_quality_score"),
        "expanded_micro_eval_result": expanded_micro,
        "expanded_micro_valid_rate": expanded_micro.get("valid_rate"),
        "expanded_micro_avg_quality_score": expanded_micro.get("avg_quality_score"),
        "expanded_micro_website_ready_rate": expanded_micro.get("website_ready_rate"),
        "expanded_micro_status": expanded_micro.get("status"),
        "quality_inspection_result": quality_inspection,
        "quality_inspection_status": quality_inspection.get("status"),
        "semantic_quality_score": quality_inspection.get("semantic_quality_score"),
        "mcq_quality_score": quality_inspection.get("mcq_quality_score"),
        "option_quality_score": quality_inspection.get("option_quality_score"),
        "teaching_variation_score": quality_inspection.get("teaching_variation_score"),
        "style_match_score": quality_inspection.get("style_match_score"),
        "logical_consistency_score": quality_inspection.get("logical_consistency_score"),
        "domain_relevance_score": quality_inspection.get("domain_relevance_score"),
        "repetition_rate": quality_inspection.get("repetition_rate"),
        "failed_quality_items": quality_inspection.get("failed_quality_items"),
        "failed_task_types": failure_analysis.get("failed_task_types", []),
        "expanded_micro_allowed": bool(micro_pass),
        "core_generation_allowed": core_allowed,
        "core_quality_inspection_result": core_quality,
        "core_generation_attempted": core.get("attempted"),
        "core_generation_valid": core.get("valid"),
        "core_valid_rate": core.get("valid_rate"),
        "core_avg_quality_score": core.get("avg_quality_score"),
        "core_website_ready_rate": core_quality.get("core_website_ready_rate"),
        "core_semantic_quality_score": core_quality.get("core_semantic_quality_score"),
        "core_mcq_quality_score": core_quality.get("core_mcq_quality_score"),
        "core_option_quality_score": core_quality.get("core_option_quality_score"),
        "core_logical_consistency_score": core_quality.get("core_logical_consistency_score"),
        "core_domain_relevance_score": core_quality.get("core_domain_relevance_score"),
        "core_teaching_variation_score": core_quality.get("core_teaching_variation_score"),
        "core_repetition_rate": core_quality.get("core_repetition_rate"),
        "core_duplicate_output_count": core_quality.get("core_duplicate_output_count"),
        "core_failed_quality_items": core_quality.get("core_failed_quality_items"),
        "core_quality_status": core_quality.get("core_quality_status"),
        "core_quality_inspection_status": core_quality.get("core_quality_status"),
        "core_generation_status": core.get("status"),
        "website_mode_allowed": website_mode_allowed,
        "full_generation_allowed": full_generation_allowed,
        "source_integrity_status": source_integrity.get("source_integrity_status"),
        "core_quality_eval_status": core_quality_eval.get("status"),
        "website_readiness_status": website_readiness.get("website_readiness_status"),
        "website_mode_status": website_mode_status,
        "final_structured_model_verdict": final_structured_model_verdict,
        "dataset_report": dataset,
        "training_report": training,
        "failure_analysis": failure_analysis,
        "micro_eval_result": micro,
        "core_generation_result": core,
        "full_generation_result": full,
        "quality_reached_85_percent": bool(micro_pass),
        "expanded_micro_reached_85_percent": bool(expanded_micro_pass),
        "quality_inspection_passed": bool(quality_pass),
        "final_verdict": verdict,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# CogniTutor Structured Generation Upgrade Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"dataset_report", "training_report"}) + "\n", encoding="utf-8")
    print(f"Training_data_status: {dataset.get('final_status')}")
    print(f"Training_status: {training.get('training_status')}")
    print("Previous_micro_valid_rate: 0.1667")
    print(f"Micro_valid_rate: {micro.get('valid_rate')}")
    print(f"Micro_avg_quality: {micro.get('avg_quality_score')}")
    print(f"Expanded_micro_valid_rate: {expanded_micro.get('valid_rate')}")
    print(f"Expanded_micro_avg_quality: {expanded_micro.get('avg_quality_score')}")
    print(f"Expanded_micro_website_ready_rate: {expanded_micro.get('website_ready_rate')}")
    print(f"Expanded_micro_status: {expanded_micro.get('status')}")
    print(f"Quality_inspection_status: {quality_inspection.get('status')}")
    print(f"Semantic_quality_score: {quality_inspection.get('semantic_quality_score')}")
    print(f"MCQ_quality_score: {quality_inspection.get('mcq_quality_score')}")
    print(f"Option_quality_score: {quality_inspection.get('option_quality_score')}")
    print(f"Teaching_variation_score: {quality_inspection.get('teaching_variation_score')}")
    print(f"Style_match_score: {quality_inspection.get('style_match_score')}")
    print(f"Logical_consistency_score: {quality_inspection.get('logical_consistency_score')}")
    print(f"Domain_relevance_score: {quality_inspection.get('domain_relevance_score')}")
    print(f"Repetition_rate: {quality_inspection.get('repetition_rate')}")
    print(f"Failed_quality_items: {quality_inspection.get('failed_quality_items')}")
    print(f"Failed_task_types: {failure_analysis.get('failed_task_types', [])}")
    print(f"Reached_85_percent: {micro_pass}")
    print(f"Expanded_micro_reached_85_percent: {expanded_micro_pass}")
    print(f"Quality_inspection_passed: {quality_pass}")
    print(f"Expanded_micro_allowed: {micro_pass}")
    print(f"Core_generation_allowed: {core_allowed}")
    print(f"Core_valid_rate: {core.get('valid_rate')}")
    print(f"Core_avg_quality: {core.get('avg_quality_score')}")
    print(f"Core_website_ready_rate: {core_quality.get('core_website_ready_rate')}")
    print(f"Core_semantic_quality_score: {core_quality.get('core_semantic_quality_score')}")
    print(f"Core_mcq_quality_score: {core_quality.get('core_mcq_quality_score')}")
    print(f"Core_option_quality_score: {core_quality.get('core_option_quality_score')}")
    print(f"Core_logical_consistency_score: {core_quality.get('core_logical_consistency_score')}")
    print(f"Core_domain_relevance_score: {core_quality.get('core_domain_relevance_score')}")
    print(f"Core_teaching_variation_score: {core_quality.get('core_teaching_variation_score')}")
    print(f"Core_repetition_rate: {core_quality.get('core_repetition_rate')}")
    print(f"Core_failed_quality_items: {core_quality.get('core_failed_quality_items')}")
    print(f"Core_quality_inspection_status: {core_quality.get('core_quality_status')}")
    print(f"Core_generation_status: {core.get('status')}")
    print(f"Website_mode_allowed: {website_mode_allowed}")
    print(f"Full_generation_allowed: {full_generation_allowed}")
    print(f"Source_integrity_status: {source_integrity.get('source_integrity_status')}")
    print(f"Core_quality_eval_status: {core_quality_eval.get('status')}")
    print(f"Website_readiness_status: {website_readiness.get('website_readiness_status')}")
    print(f"Website_mode_status: {website_mode_status}")
    print(f"Final_structured_model_verdict: {final_structured_model_verdict}")
    print(f"Full_valid_rate: {full.get('valid_rate')}")
    print(f"Full_avg_quality: {full.get('avg_quality_score')}")
    print("TutorLMService_status: not_patched_until_core_full_pass")
    print(f"Final_verdict: {verdict}")
    print(f"Report_path: {OUT_MD}")


if __name__ == "__main__":
    main()
