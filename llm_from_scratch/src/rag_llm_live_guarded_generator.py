from typing import Any, Dict

from src.model_first_runtime import generate_model_first_safe
from src.rag_live_context_provider import get_live_rag_context


def generate_live_guarded(
    task_type,
    domain,
    concept_name,
    concept_id=None,
    difficulty="easy",
    teaching_view=None,
    learner_state=None,
    max_attempts=3,
) -> Dict[str, Any]:
    rag_context = get_live_rag_context(
        domain,
        concept_name,
        concept_id=concept_id,
        task_type=task_type,
        difficulty=difficulty,
        teaching_view=teaching_view,
    )
    model_attempt = generate_model_first_safe(
        task_type,
        rag_context.get("domain") or domain,
        rag_context.get("concept_name") or concept_name,
        difficulty=difficulty,
        teaching_view=teaching_view,
        context=rag_context,
        max_attempts=max_attempts,
    )
    validation = model_attempt.get("validation") or {}
    attempts = model_attempt.get("repair_attempts") or []
    last_parse = (attempts[-1].get("parse") if attempts else {}) or {}
    raw_validation = model_attempt.get("raw_validation") or validation
    return {
        "status": "success" if model_attempt.get("learner_facing_safe") else "fail",
        "architecture": "rag_llm_live_guarded_generator",
        "task_type": task_type,
        "domain": rag_context.get("domain") or domain,
        "concept_id": rag_context.get("concept_id") or concept_id,
        "concept_name": rag_context.get("concept_name") or concept_name,
        "difficulty": difficulty,
        "teaching_view": teaching_view,
        "learner_state": learner_state or {},
        "rag_context": rag_context,
        "model_attempt": model_attempt,
        "fallback_used": bool(model_attempt.get("fallback_used")),
        "fallback_source": model_attempt.get("final_source") if model_attempt.get("fallback_used") else None,
        "final_source": model_attempt.get("final_source"),
        "final_output": model_attempt.get("final_output"),
        "validation": validation,
        "raw_output_present": bool(model_attempt.get("raw_output")),
        "parse_status": last_parse.get("parse_status"),
        "validator_status": "PASS" if raw_validation.get("valid") else "FAIL",
        "accepted_after_repair": bool(raw_validation.get("accepted_after_repair")),
        "model_valid": bool(model_attempt.get("model_valid")),
        "model_quality_score": raw_validation.get("quality_score"),
        "model_checkpoint_used": model_attempt.get("model_checkpoint_used"),
        "model_checkpoint_status": model_attempt.get("model_checkpoint_status"),
        "model_training_report_status": model_attempt.get("model_training_report_status"),
        "model_source": model_attempt.get("model_source"),
        "model_version": model_attempt.get("model_version"),
        "rejection_reason": raw_validation.get("rejection_category") if not model_attempt.get("model_valid") else None,
        "learner_facing_safe": bool(model_attempt.get("learner_facing_safe")),
        "frontend_ready": bool(validation.get("frontend_renderable")),
        "metadata": {
            "generation_mode_requested": "rag_llm_live_guarded",
            "rag_used": bool(rag_context.get("rag_used")),
            "model_attempted": bool(model_attempt.get("model_attempted")),
            "model_loaded": bool(model_attempt.get("model_loaded")),
            "model_valid": bool(model_attempt.get("model_valid")),
            "model_quality_score": validation.get("quality_score"),
            "model_checkpoint_used": model_attempt.get("model_checkpoint_used"),
            "model_checkpoint_status": model_attempt.get("model_checkpoint_status"),
            "model_training_report_status": model_attempt.get("model_training_report_status"),
            "model_source": model_attempt.get("model_source"),
            "model_version": model_attempt.get("model_version"),
            "fallback_used": bool(model_attempt.get("fallback_used")),
            "fallback_source": model_attempt.get("final_source") if model_attempt.get("fallback_used") else None,
            "final_source": model_attempt.get("final_source"),
            "learner_facing_safe": bool(model_attempt.get("learner_facing_safe")),
        },
    }
