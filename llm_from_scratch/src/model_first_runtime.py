import json
from functools import lru_cache
from typing import Any, Dict, List

from pathlib import Path
import torch

from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT, TASK_TOKENS
from src.concept_resource_loader import find_concept
from src.concept_resources_guarded_fallback import build_guarded_fallback
from src.model_first_parser import parse_model_output
from src.model_first_validator import validate_model_output


def _source_level(difficulty: str) -> str:
    return {"easy": "basic", "medium": "intermediate", "hard": "advanced"}.get(str(difficulty), "basic")


@lru_cache(maxsize=1)
def load_existing_cognitutor_model():
    try:
        from src.generate import get_device, load_checkpoint
        from src.tokenizer_wrapper import CogniTutorTokenizer

        device = get_device()
        checkpoint_path, model_source, model_version = _select_model_checkpoint()
        model, config, checkpoint = load_checkpoint(checkpoint_path, device)
        tokenizer = CogniTutorTokenizer()
        checkpoint_status = _checkpoint_status(checkpoint_path, model_source)
        return {
            "model_loaded": True,
            "model": model,
            "tokenizer": tokenizer,
            "device": device,
            "checkpoint_path": str(checkpoint_path),
            "model_checkpoint_used": str(checkpoint_path),
            "model_checkpoint_status": checkpoint_status.get("checkpoint_status"),
            "model_training_report_status": checkpoint_status.get("training_report_status"),
            "model_source": model_source,
            "model_version": model_version,
            "error": None,
        }
    except Exception as exc:
        return {
            "model_loaded": False,
            "model": None,
            "tokenizer": None,
            "device": None,
            "checkpoint_path": str(MODEL_CHECKPOINT),
            "model_checkpoint_used": None,
            "model_checkpoint_status": "unloaded",
            "model_training_report_status": "unloaded",
            "model_source": "none",
            "model_version": "unloaded",
            "error": str(exc),
        }


def _select_model_checkpoint():
    candidates = [
        (ROOT / "models" / "cognitutor_lm_model_first_full_fixed" / "best_model.pt", "model_first_full_fixed", "model_first_full_fixed"),
        (ROOT / "models" / "cognitutor_lm_model_first_full" / "best_model.pt", "model_first_full_retrained", "model_first_full"),
        (ROOT / "models" / "cognitutor_lm_raw_format_fix" / "best_model.pt", "raw_format_fix", "raw_format_fix"),
        (MODEL_CHECKPOINT, "structured_generation", "structured_generation"),
    ]
    for path, source, version in candidates:
        if Path(path).exists() and _checkpoint_looks_valid(Path(path), source):
            return Path(path), source, version
    return MODEL_CHECKPOINT, "structured_generation_missing", "missing"


def _checkpoint_looks_valid(path: Path, source: str) -> bool:
    if source not in {"model_first_full_retrained", "model_first_full_fixed"}:
        return True
    try:
        status = _checkpoint_status(path, source)
        if status.get("training_report_status") != "PASS":
            return False
        checkpoint = torch.load(path, map_location="cpu")
        metrics = checkpoint.get("val_metrics") or {}
        val_loss = float(metrics.get("val_loss"))
        return torch.isfinite(torch.tensor(val_loss)) and val_loss < 998.0
    except Exception:
        return False


def _checkpoint_status(path: Path, source: str) -> Dict[str, Any]:
    if source == "model_first_full_fixed":
        report_path = ROOT / "outputs" / "model_first_full_retrain" / "training" / "full_fixed_training_report.json"
    elif source == "model_first_full_retrained":
        report_path = ROOT / "outputs" / "model_first_full_retrain" / "training" / "full_retrain_training_report.json"
    else:
        return {"checkpoint_status": "accepted_stable", "training_report_status": "not_required"}
    if not path.exists():
        return {"checkpoint_status": "missing", "training_report_status": "missing"}
    if not report_path.exists():
        return {"checkpoint_status": "rejected_missing_training_report", "training_report_status": "missing"}
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report_status = report.get("training_status")
        finite_updates = int(report.get("finite_update_count") or 0)
        val_loss = report.get("best_val_loss")
        finite_val = val_loss is not None and torch.isfinite(torch.tensor(float(val_loss))).item()
        accepted = report_status == "PASS" and finite_updates > 0 and finite_val
        return {
            "checkpoint_status": "accepted" if accepted else "rejected_bad_training_report",
            "training_report_status": report_status,
            "finite_update_count": finite_updates,
            "best_val_loss": val_loss,
        }
    except Exception as exc:
        return {"checkpoint_status": "rejected_report_read_error", "training_report_status": "read_error", "error": str(exc)}


def _build_prompt(task_type: str, domain: str, concept_name: str, difficulty: str, teaching_view: str | None, context: Dict[str, Any] | None, validation_errors: List[str] | None = None) -> str:
    sections = (context or {}).get("sections") or {}
    schema = _schema_hint(task_type)
    task_token = _task_token(task_type)
    difficulty_token = f"<{difficulty}>"
    style_token = _style_token(task_type, teaching_view)
    context_text = _short_context(sections)
    errors = "; ".join(validation_errors or [])
    repair_line = f"\nPrevious validation errors to fix: {errors}" if errors else ""
    return f"""<bos>
<instruction> Generate project-specific tutor learning output.
{task_token}
{difficulty_token}
{style_token}
<task_type> {task_type}
<concept> {concept_name}
<domain> {domain}
<teaching_view> {teaching_view or ""}
<context>
{context_text}
</context>
Required output: {schema}
Output only the requested structured content. Do not invent unrelated content. Use the context above.{repair_line}
Repeat target: {task_type} for {domain} / {concept_name}.
<answer>"""


def _clip(value: str, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].strip()


def _short_context(sections: Dict[str, Any]) -> str:
    return (
        f"Definition: {_clip(sections.get('definition', ''), 360)}\n"
        f"Key points: {_clip(sections.get('key_points', ''), 280)}\n"
        f"Examples: {_clip(sections.get('examples', ''), 260)}\n"
        f"Misconceptions: {_clip(sections.get('misconceptions', ''), 220)}"
    ).strip()


def _task_token(task_type: str) -> str:
    aliases = {
        "debug_task": "<task_debug>",
        "challenge_question": "<task_challenge>",
        "revision_summary": "<task_revision>",
        "definition_view": "<task_explanation>",
        "simple_example_view": "<task_explanation>",
        "step_by_step_view": "<task_explanation>",
        "analogy_view": "<task_explanation>",
        "code_view": "<task_explanation>",
        "misconception_view": "<task_explanation>",
        "voice_script": "<task_voice_script>",
    }
    return aliases.get(task_type) or TASK_TOKENS.get(task_type) or f"<task_{task_type}>"


def _style_token(task_type: str, teaching_view: str | None) -> str:
    source = teaching_view or task_type
    if "code" in source or "debug" in source or "output_prediction" in source:
        return "<style_code>"
    if "analogy" in source:
        return "<style_analogy>"
    if "step" in source:
        return "<style_step_by_step>"
    if "revision" in source:
        return "<style_revision>"
    if "misconception" in source:
        return "<style_misconception>"
    return "<style_simple>"


def _schema_hint(task_type: str) -> str:
    if task_type == "mcq":
        return 'JSON object with "question", "options" exactly 4 strings, "answer", and "explanation".'
    if task_type == "debug_task":
        return 'JSON object with buggy_code, expected_fix, hint, explanation.'
    if task_type == "output_prediction":
        return 'JSON object with question, code, answer, explanation.'
    if task_type == "fill_in_the_blank":
        return 'JSON object with question, blank, answer, explanation.'
    if task_type == "true_or_false":
        return 'JSON object with statement, answer boolean, explanation.'
    if "flashcard" in task_type:
        return 'JSON object with front and back.'
    if "mindmap" in task_type:
        return 'JSON object with center and branches list.'
    if "voice" in task_type or task_type.endswith("_script"):
        return 'JSON object with script.'
    if "hint" in task_type:
        return 'JSON object with hint.'
    if "feedback" in task_type:
        return 'JSON object with feedback.'
    return 'JSON object with "title", "content", "example", "key_points" list, and "quick_check".'


def generate_raw_model_output(task_type, domain, concept_name, difficulty="easy", teaching_view=None, context=None, validation_errors=None):
    loaded = load_existing_cognitutor_model()
    if not loaded["model_loaded"]:
        return {
            "model_attempted": True,
            "model_loaded": False,
            "raw_output": "",
            "error": loaded["error"],
            "checkpoint_path": loaded["checkpoint_path"],
            "model_checkpoint_used": loaded.get("model_checkpoint_used"),
            "model_checkpoint_status": loaded.get("model_checkpoint_status"),
            "model_training_report_status": loaded.get("model_training_report_status"),
            "model_source": loaded.get("model_source"),
            "model_version": loaded.get("model_version"),
        }
    try:
        from src.generate import generate_text

        prompt = _build_prompt(task_type, domain, concept_name, difficulty, teaching_view, context, validation_errors)
        raw, _full = generate_text(
            loaded["model"],
            loaded["tokenizer"],
            prompt,
            loaded["device"],
            max_new_tokens=140,
            temperature=0.2,
            top_k=40,
        )
        return {
            "model_attempted": True,
            "model_loaded": True,
            "raw_output": raw,
            "prompt": prompt,
            "error": None,
            "checkpoint_path": loaded["checkpoint_path"],
            "model_checkpoint_used": loaded.get("model_checkpoint_used"),
            "model_checkpoint_status": loaded.get("model_checkpoint_status"),
            "model_training_report_status": loaded.get("model_training_report_status"),
            "model_source": loaded.get("model_source"),
            "model_version": loaded.get("model_version"),
        }
    except Exception as exc:
        return {
            "model_attempted": True,
            "model_loaded": True,
            "raw_output": "",
            "error": str(exc),
            "checkpoint_path": loaded["checkpoint_path"],
            "model_checkpoint_used": loaded.get("model_checkpoint_used"),
            "model_checkpoint_status": loaded.get("model_checkpoint_status"),
            "model_training_report_status": loaded.get("model_training_report_status"),
            "model_source": loaded.get("model_source"),
            "model_version": loaded.get("model_version"),
        }


def _find_guarded_row(task_type: str, domain: str, concept_name: str, difficulty: str, teaching_view: str | None) -> Dict[str, Any] | None:
    from src.cognitutor_lm_api_service import get_all_task_outputs

    rows = get_all_task_outputs(domain, concept_name=concept_name)
    preferred = [
        row for row in rows
        if row.get("task_type") == task_type
        and (not difficulty or row.get("difficulty") in {difficulty, "revision", None})
        and (not teaching_view or row.get("teaching_view") in {teaching_view, None})
    ]
    return (preferred or [row for row in rows if row.get("task_type") == task_type] or rows or [None])[0]


def _guarded_output(task_type: str, domain: str, concept_name: str, difficulty: str, teaching_view: str | None) -> Dict[str, Any]:
    row = _find_guarded_row(task_type, domain, concept_name, difficulty, teaching_view)
    if row:
        return {"source": "guarded_product_generator", "output": row.get("output") or row}
    concept = find_concept(domain, concept=concept_name)
    if concept:
        text = build_guarded_fallback(concept, task_type)
        parsed = parse_model_output(text, task_type).get("parsed_output")
        return {"source": "concept_resource_fallback", "output": parsed}
    return {"source": "template_baseline", "output": {"title": concept_name, "content": f"Review {concept_name} in {domain}.", "key_points": [], "example": "", "quick_check": ""}}


def generate_model_first_safe(task_type, domain, concept_name, difficulty="easy", teaching_view=None, context=None, max_attempts=3):
    repair_attempts: List[Dict[str, Any]] = []
    raw_output = ""
    parsed_output = None
    validation: Dict[str, Any] = {"valid": False, "quality_score": 0.0, "issues": ["not_attempted"]}
    model_loaded = False

    for attempt in range(1, max_attempts + 1):
        raw = generate_raw_model_output(
            task_type,
            domain,
            concept_name,
            difficulty=difficulty,
            teaching_view=teaching_view,
            context=context,
            validation_errors=validation.get("issues") if attempt > 1 else None,
        )
        raw_output = raw.get("raw_output") or ""
        model_loaded = bool(raw.get("model_loaded"))
        parsed = parse_model_output(raw_output, task_type)
        parsed_output = parsed.get("parsed_output")
        validation = validate_model_output(parsed_output, task_type, domain, concept_name, difficulty, teaching_view, context, parser_repair_applied=bool(parsed.get("repair_applied")))
        repair_attempts.append({
            "attempt": attempt,
            "raw_output": raw_output,
            "parse": parsed,
            "validation": validation,
            "model_checkpoint_used": raw.get("model_checkpoint_used"),
            "model_checkpoint_status": raw.get("model_checkpoint_status"),
            "model_training_report_status": raw.get("model_training_report_status"),
            "model_source": raw.get("model_source"),
            "model_version": raw.get("model_version"),
        })
        if validation.get("valid"):
            return {
                "status": "success",
                "model_attempted": True,
                "model_loaded": model_loaded,
                "task_type": task_type,
                "domain": domain,
                "concept_name": concept_name,
                "difficulty": difficulty,
                "source_level": _source_level(difficulty),
                "teaching_view": teaching_view,
                "raw_output": raw_output,
                "parsed_output": parsed_output,
                "model_valid": True,
                "validation": validation,
                "repair_attempts": repair_attempts,
                "fallback_used": False,
                "final_output": parsed_output,
                "final_source": "retrained_raw_cognitutor_lm_validated" if (raw.get("model_source") in {"model_first_full_retrained", "model_first_full_fixed"}) else "raw_cognitutor_lm_validated",
                "model_checkpoint_used": raw.get("model_checkpoint_used"),
                "model_checkpoint_status": raw.get("model_checkpoint_status"),
                "model_training_report_status": raw.get("model_training_report_status"),
                "model_source": raw.get("model_source"),
                "model_version": raw.get("model_version"),
                "learner_facing_safe": True,
            }
        if not model_loaded:
            break

    fallback = _guarded_output(task_type, domain, concept_name, difficulty, teaching_view)
    fallback_validation = validate_model_output(fallback["output"], task_type, domain, concept_name, difficulty, teaching_view, context)
    final_source = fallback["source"]
    if not fallback_validation.get("frontend_renderable"):
        final_source = "rag_artifact_fallback" if context and context.get("context_text") else "concept_resource_fallback"
        fallback = _guarded_output("explanation", domain, concept_name, difficulty, teaching_view)
        fallback_validation = validate_model_output(fallback["output"], "explanation", domain, concept_name, difficulty, teaching_view, context)

    return {
        "status": "warn" if fallback_validation.get("frontend_renderable") else "fail",
        "model_attempted": True,
        "model_loaded": model_loaded,
        "task_type": task_type,
        "domain": domain,
        "concept_name": concept_name,
        "difficulty": difficulty,
        "source_level": _source_level(difficulty),
        "teaching_view": teaching_view,
        "raw_output": raw_output,
        "parsed_output": parsed_output,
        "model_valid": False,
        "validation": fallback_validation,
        "raw_validation": validation,
        "repair_attempts": repair_attempts,
        "fallback_used": True,
        "final_output": fallback["output"],
        "final_source": final_source,
        "model_checkpoint_used": (repair_attempts[-1].get("model_checkpoint_used") if repair_attempts else None),
        "model_checkpoint_status": (repair_attempts[-1].get("model_checkpoint_status") if repair_attempts else None),
        "model_training_report_status": (repair_attempts[-1].get("model_training_report_status") if repair_attempts else None),
        "model_source": (repair_attempts[-1].get("model_source") if repair_attempts else None),
        "model_version": (repair_attempts[-1].get("model_version") if repair_attempts else None),
        "learner_facing_safe": bool(fallback_validation.get("frontend_renderable")),
    }
