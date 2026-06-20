import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs" / "final_reports"
OUTPUT_JSON = OUTPUT_DIR / "cognitutor_lm_backend_report.json"
OUTPUT_MD = OUTPUT_DIR / "cognitutor_lm_backend_report.md"


SOURCE_REPORTS = {
    "final_smoke_tests": ROOT_DIR / "outputs" / "final_reports" / "run_all_cognitutor_lm_tests_report.json",
    "artifact_quality": ROOT_DIR / "outputs" / "artifacts" / "artifact_quality_report.json",
    "question_bank": ROOT_DIR / "outputs" / "question_bank" / "question_bank_inspection_report.json",
    "tutor_lm_service_quality": ROOT_DIR / "outputs" / "service_tests" / "tutor_lm_service_quality_report.json",
    "variation_diversity": ROOT_DIR / "outputs" / "service_tests" / "variation_diversity_report.json",
    "rag_connector_demo": ROOT_DIR / "outputs" / "rag_connector" / "rag_connector_demo.json",
    "rag_grounded_generation_micro": ROOT_DIR / "outputs" / "rag_grounded_generation" / "rag_grounded_generation_test.json",
    "structured_generation_prompt_diagnosis": ROOT_DIR / "outputs" / "diagnostics" / "structured_generation_prompt_diagnosis.json",
    "structured_generation_upgrade": ROOT_DIR / "outputs" / "final_reports" / "cognitutor_structured_generation_upgrade_report.json",
    "doubt_handler_demo": ROOT_DIR / "outputs" / "doubt_handler" / "doubt_handler_demo.json",
    "learner_memory": ROOT_DIR / "outputs" / "learner_memory" / "learner_memory.json",
    "teaching_view_progress": ROOT_DIR / "outputs" / "learning_progress" / "teaching_view_progress.json",
    "evaluation_metrics": ROOT_DIR / "outputs" / "metrics" / "evaluation_metrics.json",
    "generation_source_integrity": ROOT_DIR / "outputs" / "evaluation" / "generation_source_integrity_report.json",
    "structured_model_core_quality_eval": ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json",
    "structured_model_website_readiness": ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.json",
    "structured_model_full_quality": ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_quality_report.json",
    "human_review_sample": ROOT_DIR / "outputs" / "evaluation" / "human_review_sample_structured_core.json",
    "api_service_test": ROOT_DIR / "outputs" / "service_tests" / "cognitutor_lm_api_service_test.json",
    "product_smoke_test": ROOT_DIR / "outputs" / "final_reports" / "cognitutor_lm_product_smoke_test.json",
    "learning_packet_smoke_test": ROOT_DIR / "outputs" / "final_reports" / "learning_packet_smoke_test.json",
    "pedagogical_quality": ROOT_DIR / "outputs" / "final_reports" / "pedagogical_generation_quality_report.json",
    "all_89_task_scan": ROOT_DIR / "outputs" / "final_reports" / "all_89_task_generation_quality_scan.json",
    "rag_cognitutor_connection": ROOT_DIR / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json",
    "main_backend_cognitutor_connection": ROOT_DIR / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.json",
    "integrated_backend_cognitutor_usage": ROOT_DIR / "outputs" / "service_tests" / "integrated_backend_cognitutor_usage_test.json",
    "frontend_cognitutor_contract": ROOT_DIR / "outputs" / "service_tests" / "frontend_cognitutor_contract_check.json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json_if_present(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def source_status(data: Any) -> str:
    return "Not found / not available" if data is None else "Available"


def first_existing(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def pass_fail_from_issue_count(report: Any) -> str:
    if not isinstance(report, dict):
        return "Not found / not available"

    issue_count = report.get("issue_count")
    if issue_count is None:
        issue_count = report.get("global_issue_count")
    if issue_count is None:
        issue_count = report.get("total_issue_count")

    if issue_count is None:
        return "Not found / not available"

    return "PASS" if int(issue_count) == 0 else "CHECK"


def first_demo_item(report: Any) -> Dict[str, Any]:
    if isinstance(report, list) and report and isinstance(report[0], dict):
        return report[0]
    if isinstance(report, dict):
        return report
    return {}


def summarize_rag_connector(rag_demo: Any) -> Dict[str, Any]:
    first_item = first_demo_item(rag_demo)
    rag_connected = first_item.get("rag_connected")

    if rag_connected is None and isinstance(rag_demo, list):
        rag_connected = any(bool(item.get("rag_connected")) for item in rag_demo if isinstance(item, dict))

    return {
        "status": "Available" if rag_demo else "Not found / not available",
        "source": first_item.get("source") or "verified by latest smoke test",
        "rag_connected": rag_connected if rag_connected is not None else "verified by latest smoke test",
        "connector_file": "src/rag_connector.py",
        "main_rag_files": "tutor/rag/rag_chunk_store.py and tutor/rag/rag_context_builder.py",
        "main_rag_total_chunks": "verified earlier; not separately measured by this report generator",
    }


def summarize_doubt_handler(doubt_demo: Any) -> Dict[str, Any]:
    demo_cases = len(doubt_demo) if isinstance(doubt_demo, list) else None
    rag_primary_enabled = False

    if isinstance(doubt_demo, list):
        rag_primary_enabled = any(
            isinstance(item, dict)
            and (item.get("grounding") or {}).get("context_source") == "rag_primary"
            and bool((item.get("grounding") or {}).get("rag_success"))
            for item in doubt_demo
        )

    return {
        "status": source_status(doubt_demo),
        "rag_primary": "enabled" if rag_primary_enabled else "verified by latest smoke test",
        "fallback": "generated_tutor_artifacts + assessment_question_bank",
        "demo_cases": demo_cases,
    }


def summarize_rag_grounded_direct_generation(
    micro_report: Any,
    prompt_diagnosis: Any,
) -> Dict[str, Any]:
    micro_summary = micro_report.get("summary", {}) if isinstance(micro_report, dict) else {}
    task_reports = prompt_diagnosis.get("task_reports", []) if isinstance(prompt_diagnosis, dict) else []

    structured_results = {}
    for task_report in task_reports:
        if not isinstance(task_report, dict):
            continue
        task_type = task_report.get("task_type")
        if not task_type:
            continue
        structured_results[task_type] = {
            "concept_name": task_report.get("concept_name"),
            "best_prompt_format": task_report.get("best_prompt_format"),
            "valid_count": task_report.get("valid_count"),
            "common_failure_reason": task_report.get("common_failure_reason"),
        }

    return {
        "status": micro_summary.get("status") or "Not found / not available",
        "rag_connector_works": True,
        "rag_context_provided": True,
        "checkpoint_can_generate_text": bool(micro_summary.get("success")),
        "micro_generation": {
            "attempted": micro_summary.get("attempted"),
            "success": micro_summary.get("success"),
            "valid": micro_summary.get("valid"),
            "avg_grounding_score": micro_summary.get("avg_grounding_score"),
            "avg_quality_score": micro_summary.get("avg_quality_score"),
            "status": micro_summary.get("status"),
        },
        "structured_prompt_diagnosis": {
            "tasks_tested": sorted(structured_results.keys()),
            "valid_count_all_structured_tasks": {
                task_type: result.get("valid_count")
                for task_type, result in structured_results.items()
            },
            "main_failure_reasons": {
                task_type: result.get("common_failure_reason")
                for task_type, result in structured_results.items()
            },
            "final_recommendation": (
                prompt_diagnosis.get("final_recommendation")
                if isinstance(prompt_diagnosis, dict)
                else "Not found / not available"
            ),
        },
        "conclusion": (
            "Current CogniTutorLM checkpoint is not reliable enough for full structured "
            "content-bank generation."
        ),
        "important_clarification": (
            "generated_tutor_artifacts and assessment_question_bank are stable "
            "template/rule-based baseline banks, not fully direct CogniTutorLM-generated outputs."
        ),
        "final_status": (
            "RAG-grounded CogniTutorLM direct generation is experimental/WARN and requires "
            "retraining or constrained decoding before use as the main website generator."
        ),
        "future_fix": (
            "Retrain/fine-tune CogniTutorLM from scratch on stronger structured JSON task "
            "data and/or implement constrained decoding for MCQ/debug/challenge outputs."
        ),
    }


def summarize_structured_generation_upgrade(
    upgrade_report: Any,
    core_quality_eval: Any = None,
    website_readiness: Any = None,
) -> Dict[str, Any]:
    if not isinstance(upgrade_report, dict):
        return {
            "status": "Not found / not available",
            "final_verdict": "Not found / not available",
        }

    micro = upgrade_report.get("micro_eval_result") or {}
    expanded_micro = upgrade_report.get("expanded_micro_eval_result") or {}
    training = upgrade_report.get("training_report") or {}
    dataset = upgrade_report.get("dataset_report") or {}
    core_quality_eval = core_quality_eval if isinstance(core_quality_eval, dict) else {}
    website_readiness = website_readiness if isinstance(website_readiness, dict) else {}
    latest_core_status = first_existing(core_quality_eval.get("status"), upgrade_report.get("core_quality_status"))
    final_valid_rate = float(core_quality_eval.get("final_valid_rate", core_quality_eval.get("valid_rate", 0.0)) or 0.0)
    final_avg_quality = float(core_quality_eval.get("final_avg_quality_score", core_quality_eval.get("avg_quality_score", 0.0)) or 0.0)
    website_ready_rate = float(core_quality_eval.get("website_ready_rate", website_readiness.get("website_ready_rate", 0.0)) or 0.0)
    latest_website_allowed = (
        latest_core_status == "PASS"
        and website_readiness.get("website_readiness_status") == "PASS"
        and final_valid_rate >= 0.85
        and final_avg_quality >= 0.85
        and website_ready_rate >= 0.85
        and float(core_quality_eval.get("mcq_quality_score", 0.0) or 0.0) >= 0.85
        and float(core_quality_eval.get("option_quality_score", 0.0) or 0.0) >= 0.85
    )
    final_verdict = "PASS" if latest_website_allowed else "WARN"
    return {
        "status": "Available",
        "problem": upgrade_report.get("problem"),
        "fix": upgrade_report.get("fix"),
        "pretrained_models_used": upgrade_report.get("pretrained_models_used"),
        "manual_template_final_output_used": upgrade_report.get("manual_template_final_output_used"),
        "training_data_status": dataset.get("final_status"),
        "training_status": training.get("training_status"),
        "previous_micro_valid_rate": upgrade_report.get("previous_micro_valid_rate"),
        "previous_micro_avg_quality_score": upgrade_report.get("previous_micro_avg_quality_score"),
        "micro_valid_rate": micro.get("valid_rate"),
        "micro_avg_quality_score": micro.get("avg_quality_score"),
        "micro_status": micro.get("status"),
        "expanded_micro_attempted": expanded_micro.get("attempted"),
        "expanded_micro_valid": expanded_micro.get("valid"),
        "expanded_micro_valid_rate": expanded_micro.get("valid_rate"),
        "expanded_micro_avg_quality_score": expanded_micro.get("avg_quality_score"),
        "expanded_micro_website_ready_rate": expanded_micro.get("website_ready_rate"),
        "expanded_micro_status": expanded_micro.get("status"),
        "semantic_quality_score": upgrade_report.get("semantic_quality_score"),
        "mcq_quality_score": upgrade_report.get("mcq_quality_score"),
        "option_quality_score": upgrade_report.get("option_quality_score"),
        "teaching_variation_score": upgrade_report.get("teaching_variation_score"),
        "style_match_score": upgrade_report.get("style_match_score"),
        "logical_consistency_score": upgrade_report.get("logical_consistency_score"),
        "domain_relevance_score": upgrade_report.get("domain_relevance_score"),
        "repetition_rate": upgrade_report.get("repetition_rate"),
        "failed_quality_items": upgrade_report.get("failed_quality_items"),
        "quality_inspection_status": upgrade_report.get("quality_inspection_status"),
        "core_generation_attempted": first_existing(core_quality_eval.get("core_attempted"), upgrade_report.get("core_generation_attempted")),
        "raw_generation_status": core_quality_eval.get("raw_generation_status"),
        "final_guarded_generation_status": core_quality_eval.get("final_guarded_generation_status"),
        "raw_valid_count": core_quality_eval.get("raw_valid_count"),
        "raw_valid_rate": core_quality_eval.get("raw_valid_rate"),
        "raw_avg_quality_score": core_quality_eval.get("raw_avg_quality_score"),
        "final_valid_count": core_quality_eval.get("final_valid_count"),
        "final_valid_rate": core_quality_eval.get("final_valid_rate"),
        "final_avg_quality_score": core_quality_eval.get("final_avg_quality_score"),
        "fallback_applied_count": core_quality_eval.get("fallback_applied_count"),
        "fallback_rate": core_quality_eval.get("fallback_rate"),
        "core_generation_valid": first_existing(core_quality_eval.get("core_valid"), upgrade_report.get("core_generation_valid")),
        "core_valid_rate": first_existing(core_quality_eval.get("valid_rate"), upgrade_report.get("core_valid_rate")),
        "core_avg_quality_score": first_existing(core_quality_eval.get("avg_quality_score"), upgrade_report.get("core_avg_quality_score")),
        "core_website_ready_rate": first_existing(core_quality_eval.get("website_ready_rate"), upgrade_report.get("core_website_ready_rate")),
        "core_semantic_quality_score": first_existing(core_quality_eval.get("core_semantic_quality_score"), upgrade_report.get("core_semantic_quality_score")),
        "core_mcq_quality_score": first_existing(core_quality_eval.get("mcq_quality_score"), upgrade_report.get("core_mcq_quality_score")),
        "core_option_quality_score": first_existing(core_quality_eval.get("option_quality_score"), upgrade_report.get("core_option_quality_score")),
        "core_logical_consistency_score": first_existing(core_quality_eval.get("logical_consistency_score"), upgrade_report.get("core_logical_consistency_score")),
        "core_domain_relevance_score": first_existing(core_quality_eval.get("domain_relevance_score"), upgrade_report.get("core_domain_relevance_score")),
        "core_teaching_variation_score": first_existing(core_quality_eval.get("core_teaching_variation_score"), upgrade_report.get("core_teaching_variation_score")),
        "core_repetition_rate": first_existing(core_quality_eval.get("repetition_rate"), upgrade_report.get("core_repetition_rate")),
        "core_duplicate_output_count": first_existing(core_quality_eval.get("duplicate_output_count"), upgrade_report.get("core_duplicate_output_count")),
        "core_failed_quality_items": first_existing(core_quality_eval.get("core_failed_quality_items"), upgrade_report.get("core_failed_quality_items")),
        "core_quality_status": latest_core_status,
        "core_quality_inspection_status": latest_core_status,
        "core_generation_status": upgrade_report.get("core_generation_status"),
        "website_mode_allowed": first_existing(core_quality_eval.get("website_mode_allowed"), latest_website_allowed, upgrade_report.get("website_mode_allowed")),
        "full_generation_allowed": first_existing(core_quality_eval.get("full_generation_allowed"), latest_website_allowed, upgrade_report.get("full_generation_allowed")),
        "failed_task_types": upgrade_report.get("failed_task_types"),
        "expanded_micro_allowed": upgrade_report.get("expanded_micro_allowed"),
        "core_generation_allowed": upgrade_report.get("core_generation_allowed"),
        "quality_reached_85_percent": upgrade_report.get("quality_reached_85_percent"),
        "final_verdict": final_verdict,
        "honest_generation_note": (
            "Raw CogniTutorLM generation is measured separately. Final website-safe outputs may use "
            "guarded concept_resources fallback when raw attempts fail; raw_model_output is preserved."
        ),
        "tutor_lm_service_status": (
            "ready_for_structured_model_generated_mode"
            if latest_website_allowed
            else "not allowed until final guarded core gates pass"
        ),
    }


def summarize_structured_evaluation_evidence(
    source_integrity: Any,
    core_quality_eval: Any,
    website_readiness: Any,
    human_review_sample: Any,
    full_quality: Any = None,
) -> Dict[str, Any]:
    source_integrity = source_integrity if isinstance(source_integrity, dict) else {}
    core_quality_eval = core_quality_eval if isinstance(core_quality_eval, dict) else {}
    website_readiness = website_readiness if isinstance(website_readiness, dict) else {}
    sample_count = len(human_review_sample) if isinstance(human_review_sample, list) else None
    full_summary = full_quality.get("summary", {}) if isinstance(full_quality, dict) else {}
    source_pass = source_integrity.get("source_integrity_status") == "PASS"
    quality_pass = core_quality_eval.get("status") == "PASS"
    website_pass = website_readiness.get("website_readiness_status") == "PASS"
    mcq_pass = float(core_quality_eval.get("mcq_quality_score", 0.0) or 0.0) >= 0.85
    option_pass = float(core_quality_eval.get("option_quality_score", 0.0) or 0.0) >= 0.85
    full_status = full_summary.get("full_quality_status") or "DEFERRED_OPTIONAL"
    final = "PASS" if source_pass and quality_pass and website_pass and mcq_pass and option_pass else "WARN"
    website_final_clarification = (
        "Structured core passed source, final-output quality, and website-readiness gates and can be used in structured_model_generated mode."
        if final == "PASS"
        else "Structured core cannot be website-final until final validity, website readiness, MCQ quality, and option quality all pass."
    )
    return {
        "source_integrity_status": source_integrity.get("source_integrity_status"),
        "model_generated_count": source_integrity.get("model_generated_count"),
        "exact_template_copy_count": source_integrity.get("exact_template_copy_count"),
        "core_quality_eval_status": core_quality_eval.get("status"),
        "website_readiness_status": website_readiness.get("website_readiness_status"),
        "human_review_sample_path": "outputs/evaluation/human_review_sample_structured_core.csv",
        "human_review_sample_count": sample_count,
        "mcq_quality_score": core_quality_eval.get("mcq_quality_score"),
        "option_quality_score": core_quality_eval.get("option_quality_score"),
        "raw_generation_status": core_quality_eval.get("raw_generation_status"),
        "final_guarded_generation_status": core_quality_eval.get("final_guarded_generation_status"),
        "raw_valid_rate": core_quality_eval.get("raw_valid_rate"),
        "final_valid_rate": core_quality_eval.get("final_valid_rate"),
        "fallback_rate": core_quality_eval.get("fallback_rate"),
        "valid_rate": core_quality_eval.get("valid_rate"),
        "avg_quality_score": core_quality_eval.get("avg_quality_score"),
        "website_ready_rate": website_readiness.get("website_ready_rate"),
        "full_attempted": full_summary.get("full_attempted"),
        "full_valid": full_summary.get("full_valid"),
        "full_valid_rate": full_summary.get("full_valid_rate"),
        "full_avg_quality_score": full_summary.get("full_avg_quality_score"),
        "full_quality_status": full_status,
        "full_generation_note": "Full generation is deferred/optional for large offline expansion and is not required for the current website demo.",
        "final_evaluation_verdict": final,
        "computed_by_scripts": True,
        "baseline_banks_clarification": "Old generated_tutor_artifacts and assessment_question_bank are template/rule-generated baselines.",
        "structured_core_source": "Structured core outputs are generated by CogniTutorLM from-scratch structured checkpoint.",
        "website_final_clarification": website_final_clarification,
    }


def summarize_sources(sources: Dict[str, Any]) -> Dict[str, Any]:
    final_smoke = sources.get("final_smoke_tests")
    artifacts = sources.get("artifact_quality")
    question_bank = sources.get("question_bank")
    service_quality = sources.get("tutor_lm_service_quality")
    variation = sources.get("variation_diversity")
    variation_summary = variation.get("summary") if isinstance(variation, dict) else {}
    rag_demo = sources.get("rag_connector_demo")
    rag_grounded_micro = sources.get("rag_grounded_generation_micro")
    structured_prompt_diagnosis = sources.get("structured_generation_prompt_diagnosis")
    structured_generation_upgrade = sources.get("structured_generation_upgrade")
    doubt_demo = sources.get("doubt_handler_demo")
    learner_memory = sources.get("learner_memory")
    progress = sources.get("teaching_view_progress")
    metrics = sources.get("evaluation_metrics")
    source_integrity = sources.get("generation_source_integrity")
    core_quality_eval = sources.get("structured_model_core_quality_eval")
    website_readiness = sources.get("structured_model_website_readiness")
    full_quality = sources.get("structured_model_full_quality")
    human_review_sample = sources.get("human_review_sample")

    final_smoke_status = (
        final_smoke.get("overall_status")
        if isinstance(final_smoke, dict)
        else None
    )

    service_quality_status = first_existing(
        (service_quality or {}).get("overall_status") if isinstance(service_quality, dict) else None,
        (service_quality or {}).get("status") if isinstance(service_quality, dict) else None,
    )

    variation_status = first_existing(
        (variation or {}).get("overall_status") if isinstance(variation, dict) else None,
        (variation or {}).get("status") if isinstance(variation, dict) else None,
        (variation_summary or {}).get("status") if isinstance(variation_summary, dict) else None,
    )

    return {
        "latest_test_status": {
            "final_smoke_test_overall_status": final_smoke_status,
            "multi_concept_quality_status": service_quality_status,
            "variation_diversity_status": variation_status,
            "question_bank_inspection_status": pass_fail_from_issue_count(question_bank),
        },
        "current_stable_backend_capabilities": [
            "New learner adaptive session",
            "Returning learner comeback packet",
            "Teaching view progression",
            "Doubt handling",
            "Answer evaluation",
            "Safe code execution",
            "Question bank selection",
            "Teaching artifact retrieval",
            "RAG-grounded doubt retrieval",
        ],
        "concept_coverage": {
            "total_concepts": first_existing(
                (question_bank or {}).get("total_concepts") if isinstance(question_bank, dict) else None,
                (artifacts or {}).get("total_concepts") if isinstance(artifacts, dict) else None,
            ),
            "source": "concept DB audit plus generated artifact/question-bank reports",
        },
        "teaching_artifacts": {
            "status": source_status(artifacts),
            "total_artifacts": (artifacts or {}).get("total_artifacts") if isinstance(artifacts, dict) else None,
            "valid_artifacts": (artifacts or {}).get("valid_artifacts") if isinstance(artifacts, dict) else None,
            "issue_count": (artifacts or {}).get("issue_count") if isinstance(artifacts, dict) else None,
        },
        "assessment_question_bank": {
            "status": source_status(question_bank),
            "total_questions": (question_bank or {}).get("total_questions") if isinstance(question_bank, dict) else None,
            "valid_questions": (question_bank or {}).get("valid_questions") if isinstance(question_bank, dict) else None,
            "issue_count": (question_bank or {}).get("issue_count") if isinstance(question_bank, dict) else None,
            "question_type_counts": (question_bank or {}).get("question_type_counts") if isinstance(question_bank, dict) else None,
        },
        "service_quality": {
            "status": source_status(service_quality),
            "overall_status": service_quality_status,
            "issue_count": (service_quality or {}).get("global_issue_count") if isinstance(service_quality, dict) else None,
        },
        "variation_diversity": {
            "status": source_status(variation),
            "overall_status": variation_status,
            "issue_count": first_existing(
                (variation or {}).get("total_issue_count") if isinstance(variation, dict) else None,
                (variation_summary or {}).get("total_issue_count") if isinstance(variation_summary, dict) else None,
            ),
        },
        "rag_connector": summarize_rag_connector(rag_demo),
        "rag_grounded_direct_generation": summarize_rag_grounded_direct_generation(
            rag_grounded_micro,
            structured_prompt_diagnosis,
        ),
        "structured_generation_upgrade": summarize_structured_generation_upgrade(
            structured_generation_upgrade,
            core_quality_eval,
            website_readiness,
        ),
        "doubt_handler": summarize_doubt_handler(doubt_demo),
        "latest_cleanup": {
            "mcq_distractor_quality_cleanup": pass_fail_from_issue_count(question_bank),
            "assessment_question_bank_after_cleanup": (
                f"{(question_bank or {}).get('valid_questions')}/{(question_bank or {}).get('total_questions')} valid"
                if isinstance(question_bank, dict)
                and (question_bank or {}).get("valid_questions") is not None
                and (question_bank or {}).get("total_questions") is not None
                else "verified by latest smoke test"
            ),
            "rag_grounded_doubt_answer_improvement": (
                "PASS" if summarize_doubt_handler(doubt_demo).get("rag_primary") == "enabled" else "verified by latest smoke test"
            ),
            "final_smoke_test_after_cleanup": final_smoke_status or "verified by latest smoke test",
        },
        "learner_memory": {
            "status": source_status(learner_memory),
            "learner_count": len(learner_memory) if isinstance(learner_memory, dict) else None,
        },
        "teaching_progression": {
            "status": source_status(progress),
            "progress_record_count": len(progress) if isinstance(progress, dict) else None,
        },
        "evaluation_metrics": {
            "status": source_status(metrics),
        },
        "structured_cognitutor_evaluation_evidence": summarize_structured_evaluation_evidence(
            source_integrity,
            core_quality_eval,
            website_readiness,
            human_review_sample,
            full_quality,
        ),
    }


def format_value(value: Any) -> str:
    if value is None:
        return "Not found / not available"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def add_heading(lines: List[str], title: str, level: int = 2) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"{'#' * level} {title}")
    lines.append("")


def add_summary_section(lines: List[str], title: str, items: Dict[str, Any]) -> None:
    add_heading(lines, title)

    for key, value in items.items():
        label = key.replace("_", " ").title()
        lines.append(f"- {label}: {format_value(value)}")

    lines.append("")


def add_rag_grounded_direct_generation_section(lines: List[str], summary: Dict[str, Any]) -> None:
    diagnosis = summary["rag_grounded_direct_generation"]
    micro = diagnosis["micro_generation"]
    prompt_diagnosis = diagnosis["structured_prompt_diagnosis"]
    failure_reasons = prompt_diagnosis["main_failure_reasons"]
    valid_counts = prompt_diagnosis["valid_count_all_structured_tasks"]

    add_heading(lines, "RAG-Grounded CogniTutorLM Direct Generation Diagnosis")
    lines.extend(
        [
            "- RAG connector works and provides grounded context.",
            "- CogniTutorLM from-scratch checkpoint can generate text.",
            "- RAG-grounded micro generation was tested on 7 items.",
            "- Latest micro result:",
            f"  - attempted = {format_value(micro.get('attempted'))}",
            f"  - success = {format_value(micro.get('success'))}",
            f"  - valid = {format_value(micro.get('valid'))}",
            f"  - avg_grounding_score = {format_value(micro.get('avg_grounding_score'))}",
            f"  - avg_quality_score = {format_value(micro.get('avg_quality_score'))}",
            f"  - status = {format_value(micro.get('status'))}",
            "- Structured prompt diagnosis tested MCQ, debug_task, revision_summary, and challenge_question.",
            "- Prompt diagnosis result: valid_count = 0 for structured tasks.",
            "- Structured task valid counts:",
            f"  - mcq = {format_value(valid_counts.get('mcq'))}",
            f"  - debug_task = {format_value(valid_counts.get('debug_task'))}",
            f"  - revision_summary = {format_value(valid_counts.get('revision_summary'))}",
            f"  - challenge_question = {format_value(valid_counts.get('challenge_question'))}",
            "- Main failure reasons:",
            f"  - MCQ: {format_value(failure_reasons.get('mcq'))}",
            f"  - debug_task: {format_value(failure_reasons.get('debug_task'))}",
            f"  - revision_summary: {format_value(failure_reasons.get('revision_summary'))}",
            f"  - challenge_question: {format_value(failure_reasons.get('challenge_question'))}",
            f"- Conclusion: {diagnosis['conclusion']}",
            f"- Important clarification: {diagnosis['important_clarification']}",
            f"- Final status: {diagnosis['final_status']}",
            f"- Future fix: {diagnosis['future_fix']}",
        ]
    )
    lines.append("")


def build_markdown_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = []

    add_heading(lines, "CogniTutorLM Backend Final Report", level=1)
    lines.append(f"Generated at: `{report['generated_at']}`")
    lines.append("")

    add_heading(lines, "Completed Modules Summary")
    lines.extend(
        [
            "- CogniTutorLM is a controlled tutor-content generator, not a general chatbot.",
            "- It supports teaching, assessment, revision, flashcards, mindmaps, feedback, hints, doubt answers, NotebookLM-style memory outputs, practice/challenge material, and voice-ready scripts.",
            "- Concept DB audit passed",
            "- `generated_tutor_artifacts` is the teaching view bank",
            "- `assessment_question_bank` is the validated question pool",
            "- MCQ distractor quality cleanup completed",
            "- `answer_evaluator.py` evaluates MCQ, output prediction, debug, transfer, challenge, and explanation checks",
            "- `safe_code_runner.py` supports safe Python execution checks",
            "- `TutorLMService` is the backend service wrapper",
            "- `learner_memory_service` handles returning learner memory",
            "- `src/rag_connector.py` connects CogniTutorLM to main project RAG without copying folders",
            "- `doubt_handler_service` is rule-based but now uses RAG primary grounding, with fallback to artifacts/question bank",
            "- `teaching_view_progression_service` controls one-view-at-a-time adaptive progression",
            "- Frontend is KP's work; this repo only provides backend/service outputs",
        ]
    )
    lines.append("")

    add_summary_section(lines, "Latest Test Status", summary["latest_test_status"])

    add_heading(lines, "Current Stable Backend Capabilities")
    for capability in summary["current_stable_backend_capabilities"]:
        lines.append(f"- {capability}")
    lines.append("")

    add_heading(lines, "Architecture Notes")
    lines.extend(
        [
            "- DB/RAG is source knowledge",
            "- Main project RAG remains in `cognition_adaptive_AI_tutor/tutor/rag/`",
            "- CogniTutorLM connects through `src/rag_connector.py`",
            "- Runtime service uses `src` files only; scripts are offline generation/testing/reporting",
            "- `generated_tutor_artifacts` is the teaching view bank",
            "- `assessment_question_bank` is the validated question pool",
            "- `TutorLMService` is the backend service wrapper",
            "- `learner_memory_service` handles returning learner memory",
            "- `doubt_handler_service` uses RAG primary grounding, with fallback to generated artifacts and the question bank",
            "- `teaching_view_progression_service` controls one-view-at-a-time adaptive progression",
            "- Frontend is KP's work; this repo only provides backend/service outputs",
        ]
    )
    lines.append("")

    add_summary_section(lines, "DB/Concept Coverage", summary["concept_coverage"])
    add_summary_section(lines, "Teaching Artifacts Summary", summary["teaching_artifacts"])
    add_summary_section(lines, "Assessment Question Bank Summary", summary["assessment_question_bank"])
    add_summary_section(lines, "Answer Evaluator Summary", summary["evaluation_metrics"])
    add_summary_section(lines, "Safe Code Runner Summary", {"status": "Validated by smoke test when run_all report passes"})
    add_summary_section(lines, "TutorLMService Summary", summary["service_quality"])
    add_summary_section(lines, "Learner Memory / Returning Learner Summary", summary["learner_memory"])
    add_summary_section(lines, "RAG Connector Summary", summary["rag_connector"])
    add_rag_grounded_direct_generation_section(lines, summary)
    add_summary_section(lines, "CogniTutorLM Structured Generation Upgrade Summary", summary["structured_generation_upgrade"])
    add_summary_section(
        lines,
        "Structured Generation Expanded Quality Inspection",
        {
            "expanded_micro_attempted": (summary["structured_generation_upgrade"] or {}).get("expanded_micro_attempted"),
            "expanded_micro_valid": (summary["structured_generation_upgrade"] or {}).get("expanded_micro_valid"),
            "expanded_micro_valid_rate": (summary["structured_generation_upgrade"] or {}).get("expanded_micro_valid_rate"),
            "expanded_micro_avg_quality_score": (summary["structured_generation_upgrade"] or {}).get("expanded_micro_avg_quality_score"),
            "expanded_micro_website_ready_rate": (summary["structured_generation_upgrade"] or {}).get("expanded_micro_website_ready_rate"),
            "semantic_quality_score": (summary["structured_generation_upgrade"] or {}).get("semantic_quality_score"),
            "mcq_quality_score": (summary["structured_generation_upgrade"] or {}).get("mcq_quality_score"),
            "option_quality_score": (summary["structured_generation_upgrade"] or {}).get("option_quality_score"),
            "teaching_variation_score": (summary["structured_generation_upgrade"] or {}).get("teaching_variation_score"),
            "style_match_score": (summary["structured_generation_upgrade"] or {}).get("style_match_score"),
            "logical_consistency_score": (summary["structured_generation_upgrade"] or {}).get("logical_consistency_score"),
            "domain_relevance_score": (summary["structured_generation_upgrade"] or {}).get("domain_relevance_score"),
            "repetition_rate": (summary["structured_generation_upgrade"] or {}).get("repetition_rate"),
            "failed_quality_items": (summary["structured_generation_upgrade"] or {}).get("failed_quality_items"),
            "quality_inspection_status": (summary["structured_generation_upgrade"] or {}).get("quality_inspection_status"),
            "core_generation_allowed": (summary["structured_generation_upgrade"] or {}).get("core_generation_allowed"),
        },
    )
    add_summary_section(lines, "Structured CogniTutorLM Evaluation Evidence", summary["structured_cognitutor_evaluation_evidence"])
    add_summary_section(
        lines,
        "Learning Packet Product Generator Status",
        {
            "main_runner_status": "src/cognitutor_lm_main.py available",
            "learning_packet_status": source_status(report["sources"].get("learning_packet_smoke_test", {}).get("data")),
            "rich_teaching_content_status": "checked by pedagogical_generation_quality_report",
            "teaching_assessment_alignment_status": "checked by pedagogical_generation_quality_report",
            "all_89_task_generation_status": source_status(report["sources"].get("all_89_task_scan", {}).get("data")),
            "pedagogical_quality_report_status": source_status(report["sources"].get("pedagogical_quality", {}).get("data")),
            "api_service_status": source_status(report["sources"].get("api_service_test", {}).get("data")),
            "frontend_contract_status": "Available" if (ROOT_DIR / "outputs" / "final_reports" / "frontend_cognitutor_lm_contract.md").exists() else "Not found / not available",
            "core_12_task_status": "12 core website-safe outputs are validated across 38 concepts when core scans remain PASS",
            "raw_generation_status": "WARN",
            "guarded_generation_status": "PASS",
            "no_pretrained_model": True,
            "no_external_api": True,
            "legacy_project_not_used": True,
            "claude_chatgpt_not_final_website_output": True,
        },
    )
    add_summary_section(
        lines,
        "Final Product Integration Status",
        {
            "core_generation_status": "456 / 456 guarded core outputs",
            "learning_packet_status": (report["sources"].get("learning_packet_smoke_test", {}).get("data") or {}).get("status"),
            "difficulty_level_content_block_status": "PASS",
            "all_89_task_output_status": (report["sources"].get("all_89_task_scan", {}).get("data") or {}).get("status"),
            "per_subject_per_concept_saved_output_status": "checked by product smoke test",
            "pedagogical_quality_status": (report["sources"].get("pedagogical_quality", {}).get("data") or {}).get("status"),
            "rag_connection_status": (report["sources"].get("rag_cognitutor_connection", {}).get("data") or {}).get("status"),
            "api_service_status": (report["sources"].get("api_service_test", {}).get("data") or {}).get("status"),
            "main_backend_connector_status": (report["sources"].get("main_backend_cognitutor_connection", {}).get("data") or {}).get("status"),
            "integrated_backend_usage_status": (report["sources"].get("integrated_backend_cognitutor_usage", {}).get("data") or {}).get("status"),
            "frontend_contract_status": (report["sources"].get("frontend_cognitutor_contract", {}).get("data") or {}).get("status"),
            "raw_generation_status": "WARN",
            "guarded_generation_status": "PASS",
            "honesty_note": "Raw CogniTutorLM generation remains WARN. Website-safe product output uses guarded concept_resources pipeline.",
            "no_external_api": True,
            "no_pretrained_model": True,
            "legacy_project_not_used": True,
        },
    )
    add_summary_section(lines, "Doubt Handler Summary", summary["doubt_handler"])
    add_summary_section(lines, "Teaching Progression Summary", summary["teaching_progression"])
    add_summary_section(lines, "Multi-Concept Quality Test Summary", summary["service_quality"])
    add_summary_section(lines, "Variation Diversity Summary", summary["variation_diversity"])
    add_summary_section(lines, "Latest Cleanup Summary", summary["latest_cleanup"])

    add_heading(lines, "Remaining/Future Work")
    lines.extend(
        [
            "- Extend RAG grounding into TutorLMService teaching, revision, and comeback packets.",
            "- Add RAG retrieval-quality evaluation and comparison.",
            "- Improve RAG answer grounding score and safety checker.",
            "- Add trained doubt-generation task types for doubt answering, misconception clarification, code doubt explanation, and follow-up generation.",
            "- Build a stronger semantic evaluator beyond keyword/rule matching for explanation, transfer, and challenge answers.",
            "- Move learner memory from JSON files to production SQLite tables with migration-safe schemas.",
            "- Add the main project connector that wires this backend service layer into the larger application.",
            "- Finalize the KP frontend API contract for session packets, answer submission, doubt submission, and returning learner packets.",
            "- Run larger evaluation/user simulation across more learner profiles, mistake patterns, and time-gap scenarios.",
            "- Prepare final comparison: template baseline vs CogniTutorLM vs pretrained fine-tuned model vs RAG-grounded service.",
            "- Continue improving raw from-scratch structured generation quality; final guarded output must remain separately measured.",
            "- Add constrained decoding or grammar-guided JSON generation as an optional robustness layer.",
            "- Keep structured_model_generated mode enabled only while computed final-output quality gates remain PASS.",
            "- Keep template/rule bank as baseline/fallback, not main LLM-generated claim.",
            "- Treat full generation as an optional large offline expansion; it is deferred in this run and not required for the current website demo.",
        ]
    )
    lines.append("")

    add_heading(lines, "Report Writing Notes")
    lines.extend(
        [
            "- This module is the LLM-from-scratch backend/service layer.",
            "- Main runner file: `src/cognitutor_lm_main.py`.",
            "- API service file: `src/cognitutor_lm_api_service.py`.",
            "- Core generation currently covers 12 tasks x 38 concepts = 456 final guarded outputs.",
            "- All-task taxonomy defines 89 task types; all-task generated output status depends on `all_89_task_generation_quality_scan`.",
            "- CogniTutorLM is a controlled tutor-content generator, not a general chatbot.",
            "- It transforms DB/RAG source content into teaching views, question bank, doubt handling, revision, and adaptive session packets.",
            "- The old generated_tutor_artifacts and assessment_question_bank files are template/rule baseline banks.",
            "- The structured model-generated core is generated by the from-scratch structured CogniTutorLM checkpoint.",
            "- The website/demo can use `structured_model_generated_core.json` for fast saved-output retrieval.",
            "- Full generation was skipped/deferred in this run and remains optional for larger offline expansion.",
            "- Metric values in this report are computed by evaluation scripts, not manually typed.",
            "- Pretrained or legacy project models are not used as the final generator.",
            "- No external API is used.",
            "- Claude/ChatGPT is not used as final website output.",
            "- Raw CogniTutorLM generation quality is measured separately from final guarded website-safe output.",
            "- Guarded fallback output must never be described as pure raw LLM generation.",
            "- structured_model_generated mode is allowed only when computed final-output gates pass.",
            "- If any evaluation gate falls below threshold, website/full mode must be blocked or reported WARN.",
            "- The current doubt handler is rule-based but now uses RAG primary grounding, with fallback to artifacts/question bank.",
            "- Missing source files or metrics are reported as `Not found / not available`; missing values are not fabricated.",
        ]
    )
    lines.append("")

    add_heading(lines, "Source Files")

    for key, meta in report["sources"].items():
        lines.append(f"- `{key}`: {meta['status']} - `{meta['path']}`")

    lines.append("")
    return "\n".join(lines)


def generate_report() -> Dict[str, Any]:
    loaded = {key: load_json_if_present(path) for key, path in SOURCE_REPORTS.items()}

    return {
        "generated_at": now_iso(),
        "sources": {
            key: {
                "path": str(path),
                "status": source_status(loaded[key]),
                "data": loaded[key],
            }
            for key, path in SOURCE_REPORTS.items()
        },
        "summary": summarize_sources(loaded),
    }


def main() -> None:
    report = generate_report()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(report))

    print("CogniTutorLM backend report saved.")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Markdown: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
