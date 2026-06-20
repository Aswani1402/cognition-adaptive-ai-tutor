import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.concept_resource_loader import find_concept
from src.concept_resources_guarded_fallback import build_guarded_fallback
from src.guarded_generation_validator import validate_guarded_tutor_output
from src.model_first_parser import parse_model_output
from src.rag_live_context_provider import get_live_rag_context


ROOT_DIR = Path(__file__).resolve().parents[1]


def _normalize_task_type(task_type: str) -> str:
    aliases = {
        "summary": "revision_summary",
        "revision_note": "revision_summary",
        "personal_flashcards": "flashcard",
    }
    return aliases.get(str(task_type or "").strip(), str(task_type or "").strip() or "explanation")


def _as_dict(value: Any, task_type: str) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    parsed = parse_model_output(str(value or ""), task_type).get("parsed_output")
    if isinstance(parsed, dict):
        return parsed
    return {"title": task_type.replace("_", " ").title(), "content": str(value or "").strip()}


def _safe_minimal_output(task_type: str, concept_name: str, subject: str) -> Dict[str, Any]:
    if task_type == "mcq":
        correct = f"{concept_name} is a core concept in {subject}."
        return {
            "question": f"Which statement best matches {concept_name}?",
            "options": [
                correct,
                "It is unrelated to the current subject.",
                "It removes the need to practice examples.",
                "It is only a file name.",
            ],
            "answer": correct,
            "explanation": f"The correct answer keeps the focus on {concept_name} in {subject}.",
        }
    if task_type == "flashcard":
        return {
            "front": f"What is the key idea of {concept_name}?",
            "back": f"{concept_name} is a core {subject} concept. Review its definition, example, and common mistake.",
        }
    if task_type == "debug_task":
        return {
            "buggy_code": f"# Buggy {subject} example for {concept_name}",
            "expected_fix": f"# Apply the correct {concept_name} rule here.",
            "hint": f"Start by checking the main rule for {concept_name}.",
            "explanation": f"The fix should follow the validated {concept_name} concept notes.",
        }
    if task_type == "output_prediction":
        return {
            "question": f"What does this {subject} example show about {concept_name}?",
            "code": f"# {concept_name} example",
            "answer": f"It demonstrates the main rule of {concept_name}.",
            "explanation": f"The output should be reasoned from the {concept_name} rule.",
        }
    if task_type == "hint":
        return {"hint": f"Focus on the main rule for {concept_name} before choosing the final answer."}
    if task_type == "revision_summary":
        return {
            "title": f"{concept_name} revision summary",
            "content": f"Review {concept_name} in {subject}: definition, key rule, example, and common mistake.",
            "key_points": [f"{concept_name} belongs to {subject}.", "Use a small example to check understanding."],
            "example": f"Write one simple {subject} example using {concept_name}.",
            "quick_check": f"Can you explain why {concept_name} matters?",
        }
    return {
        "title": concept_name,
        "content": f"{concept_name} is a key topic in {subject}. Study its definition, example, and common mistake.",
        "key_points": [f"{concept_name} belongs to {subject}.", "Use a small example to verify the idea."],
        "example": f"Try a short {subject} example for {concept_name}.",
        "quick_check": f"Explain {concept_name} in one sentence.",
    }


def _resolve_rag_context(
    task_type: str,
    concept_id: str,
    concept_name: str,
    subject: str,
    difficulty: str,
    rag_context: Dict[str, Any] | str | None,
) -> Dict[str, Any]:
    if isinstance(rag_context, dict):
        return rag_context
    if isinstance(rag_context, str) and rag_context.strip():
        return {
            "status": "PASS",
            "rag_used": True,
            "domain": subject,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "context_text": rag_context.strip(),
            "sections": {"context": rag_context.strip()},
            "source": "provided_rag_context",
            "issues": [],
        }
    return get_live_rag_context(
        subject,
        concept_name,
        concept_id=concept_id,
        task_type=task_type,
        difficulty=difficulty,
    )


def _fallback_output(
    task_type: str,
    concept_id: str,
    concept_name: str,
    subject: str,
    difficulty: str,
    learner_state: Optional[Dict[str, Any]],
    rag_context: Dict[str, Any],
) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    concept = find_concept(subject, concept=concept_name, concept_id=concept_id)
    source = "rag_grounded_template" if rag_context.get("rag_used") or rag_context.get("context_text") else "concept_resource_fallback"
    if concept:
        text = build_guarded_fallback(concept, task_type)
        output = _as_dict(text, task_type)
    else:
        source = "minimal_safe_template"
        output = _safe_minimal_output(task_type, concept_name, subject)

    validation = validate_guarded_tutor_output(
        output,
        task_type,
        concept_name,
        subject,
        difficulty,
        learner_state=learner_state,
        rag_context=rag_context,
    )
    if validation["valid"]:
        return output, source, validation

    output = _safe_minimal_output(task_type, concept_name, subject)
    validation = validate_guarded_tutor_output(
        output,
        task_type,
        concept_name,
        subject,
        difficulty,
        learner_state=learner_state,
        rag_context=rag_context,
    )
    return output, "minimal_safe_template", validation


def generate_guarded_tutor_output(
    task_type: str,
    concept_id: str,
    concept_name: str,
    subject: str,
    difficulty: str,
    learner_state: dict | None = None,
    rag_context: dict | str | None = None,
    prefer_model: bool = True,
) -> dict:
    task_type = _normalize_task_type(task_type)
    learner_state = learner_state or {}
    notes = []
    resolved_context = _resolve_rag_context(task_type, concept_id, concept_name, subject, difficulty, rag_context)

    model_attempted = False
    model_loaded = False
    raw_output = ""
    raw_valid = False
    raw_validation: Dict[str, Any] = {
        "valid": False,
        "errors": ["model_not_attempted"],
        "grounding_pass": False,
        "repetition_pass": False,
        "format_pass": False,
        "learner_facing_safe": False,
    }
    final_output: Dict[str, Any]
    fallback_used = True
    fallback_source = None
    model_metadata: Dict[str, Any] = {}

    if prefer_model:
        try:
            from src.model_first_runtime import generate_raw_model_output, load_existing_cognitutor_model

            model_state = load_existing_cognitutor_model()
            model_loaded = bool(model_state.get("model_loaded"))
            model_metadata = {
                "model_checkpoint_used": model_state.get("model_checkpoint_used"),
                "model_checkpoint_status": model_state.get("model_checkpoint_status"),
                "model_training_report_status": model_state.get("model_training_report_status"),
                "model_source": model_state.get("model_source"),
                "model_version": model_state.get("model_version"),
                "model_error": model_state.get("error"),
            }
            if model_loaded:
                raw = generate_raw_model_output(
                    task_type,
                    subject,
                    concept_name,
                    difficulty=difficulty,
                    context=resolved_context,
                )
                model_attempted = True
                raw_output = raw.get("raw_output") or ""
                model_metadata.update(
                    {
                        "model_checkpoint_used": raw.get("model_checkpoint_used"),
                        "model_checkpoint_status": raw.get("model_checkpoint_status"),
                        "model_training_report_status": raw.get("model_training_report_status"),
                        "model_source": raw.get("model_source"),
                        "model_version": raw.get("model_version"),
                        "model_error": raw.get("error"),
                    }
                )
                parsed = parse_model_output(raw_output, task_type)
                parsed_output = parsed.get("parsed_output")
                raw_validation = validate_guarded_tutor_output(
                    parsed_output,
                    task_type,
                    concept_name,
                    subject,
                    difficulty,
                    learner_state=learner_state,
                    rag_context=resolved_context,
                    raw_text=raw_output,
                )
                raw_valid = bool(raw_validation.get("valid"))
                if raw_valid and isinstance(parsed_output, dict):
                    final_output = parsed_output
                    fallback_used = False
                    fallback_source = None
                    final_validation = raw_validation
                    notes.append("Raw CogniTutorLM output accepted after validation.")
                else:
                    final_output, fallback_source, final_validation = _fallback_output(
                        task_type,
                        concept_id,
                        concept_name,
                        subject,
                        difficulty,
                        learner_state,
                        resolved_context,
                    )
                    notes.append("Raw CogniTutorLM output rejected; fallback used.")
            else:
                model_attempted = False
                final_output, fallback_source, final_validation = _fallback_output(
                    task_type,
                    concept_id,
                    concept_name,
                    subject,
                    difficulty,
                    learner_state,
                    resolved_context,
                )
                notes.append("Model checkpoint/service unavailable; fallback used without raw attempt.")
        except Exception as exc:
            notes.append(f"Model attempt path failed: {exc}")
            final_output, fallback_source, final_validation = _fallback_output(
                task_type,
                concept_id,
                concept_name,
                subject,
                difficulty,
                learner_state,
                resolved_context,
            )
    else:
        notes.append("prefer_model=False; fallback used intentionally.")
        final_output, fallback_source, final_validation = _fallback_output(
            task_type,
            concept_id,
            concept_name,
            subject,
            difficulty,
            learner_state,
            resolved_context,
        )

    final_valid = bool(final_validation.get("valid"))
    learner_facing_safe = bool(final_validation.get("learner_facing_safe"))
    if not final_valid or not learner_facing_safe:
        emergency = _safe_minimal_output(task_type, concept_name, subject)
        emergency_validation = validate_guarded_tutor_output(
            emergency,
            task_type,
            concept_name,
            subject,
            difficulty,
            learner_state=learner_state,
            rag_context=resolved_context,
        )
        final_output = emergency
        fallback_used = True
        fallback_source = "minimal_safe_template"
        final_validation = emergency_validation
        final_valid = bool(emergency_validation.get("valid"))
        learner_facing_safe = bool(emergency_validation.get("learner_facing_safe"))
        notes.append("Fallback output required minimal safe template repair.")

    status = "success" if final_valid and learner_facing_safe else "fail"
    result = {
        "status": status,
        "task_type": task_type,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "subject": subject,
        "difficulty": difficulty,
        "model_attempted": model_attempted,
        "model_loaded": model_loaded,
        "raw_output": raw_output,
        "raw_valid": raw_valid,
        "validation_errors": raw_validation.get("errors") or [],
        "fallback_used": fallback_used,
        "fallback_source": fallback_source,
        "final_output": final_output,
        "final_valid": final_valid,
        "grounding_pass": bool(final_validation.get("grounding_pass")),
        "repetition_pass": bool(final_validation.get("repetition_pass")),
        "format_pass": bool(final_validation.get("format_pass")),
        "learner_facing_safe": learner_facing_safe,
        "notes": notes,
        "raw_validation": raw_validation,
        "final_validation": final_validation,
        "rag_context_status": resolved_context.get("status"),
        "rag_used": bool(resolved_context.get("rag_used") or resolved_context.get("context_text")),
        "rag_source": resolved_context.get("source"),
    }
    result.update(model_metadata)
    return result


if __name__ == "__main__":
    sample = generate_guarded_tutor_output(
        task_type="mcq",
        concept_id="P1",
        concept_name="Variables",
        subject="Python",
        difficulty="easy",
    )
    print(json.dumps(sample, indent=2, ensure_ascii=False))
