import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.guarded_generation_service import generate_guarded_tutor_output
from src.model_first_runtime import load_existing_cognitutor_model

try:
    import torch

    torch.manual_seed(7)
except Exception:
    pass


OUT_JSON = ROOT / "evaluation_outputs" / "json" / "final_cognitutorlm_guarded_generation_eval.json"
OUT_REPORT = ROOT / "evaluation_outputs" / "reports" / "final_cognitutorlm_guarded_generation_eval_report.md"
OUT_SUMMARY = ROOT / "evaluation_outputs" / "reports" / "FINAL_COGNITUTORLM_REVIEW_SUMMARY.md"


CONCEPTS = [
    {"concept_id": "P1", "concept_name": "Variables", "subject": "Python", "label": "Python Variables"},
    {"concept_id": "S2", "concept_name": "SQL SELECT Queries", "subject": "SQL", "label": "SQL SELECT"},
    {"concept_id": "H2", "concept_name": "HTML Tags and Elements", "subject": "HTML", "label": "HTML Tags and Elements"},
    {"concept_id": "G3", "concept_name": "Commits and History", "subject": "Git", "label": "Git Commit / Repositories"},
    {"concept_id": "D1", "concept_name": "Arrays", "subject": "Data Structures", "label": "Arrays"},
]

TASK_TYPES = [
    "explanation",
    "mcq",
    "flashcard",
    "hint",
    "revision_summary",
    "debug_task",
    "output_prediction",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def list_existing(patterns: List[str], limit: int = 30) -> List[str]:
    paths: List[Path] = []
    for pattern in patterns:
        paths.extend(ROOT.glob(pattern))
    unique = sorted({p for p in paths if p.is_file()})
    return [rel(p) for p in unique[:limit]]


def build_inventory() -> Dict[str, Any]:
    return {
        "tokenizer_files": list_existing(["data/tokenizer/*", "models/**/cognitutor.model", "models/**/cognitutor.vocab"]),
        "model_architecture_files": list_existing(["src/model.py", "src/cognitutor_lm_config.py"]),
        "checkpoint_paths": list_existing(["models/**/*.pt", "outputs/checkpoints/*.pt"]),
        "generation_service_files": list_existing([
            "src/generate.py",
            "src/model_first_runtime.py",
            "src/rag_llm_live_guarded_generator.py",
            "src/guarded_generation_service.py",
            "src/cognitutor_lm_api_service.py",
            "src/tutor_lm_service.py",
        ]),
        "rag_connector_files": list_existing(["src/rag_connector.py", "src/rag_live_context_provider.py", "src/rag_grounded_live_generator.py"]),
        "artifact_bank_files": list_existing(["outputs/artifacts/*.json", "outputs/artifacts/*.md"]),
        "question_bank_files": list_existing(["outputs/question_bank/*.json", "outputs/question_bank/*.md"]),
        "validators": list_existing([
            "src/*validator*.py",
            "src/production_quality_gate.py",
            "src/guarded_generation_validator.py",
        ]),
        "format_validators": list_existing(["src/format_validator.py", "src/structured_output_normalizer.py", "src/raw_task_schemas.py"]),
        "fallback_generators": list_existing(["src/concept_resources_guarded_fallback.py", "src/model_first_runtime.py", "src/generate.py"]),
        "evaluation_scripts": list_existing(["scripts/evaluate*.py", "scripts/test*.py", "scripts/final_review/*.py"], limit=80),
        "reports_results": list_existing([
            "outputs/final_reports/*.md",
            "outputs/final_reports/*.json",
            "outputs/rag_llm_live_guarded/**/*.md",
            "outputs/rag_llm_live_guarded/**/*.json",
            "evaluation_outputs/**/*.md",
            "evaluation_outputs/**/*.json",
        ], limit=100),
    }


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def summarize_cases(cases: List[Dict[str, Any]], model_state: Dict[str, Any]) -> Dict[str, Any]:
    total = len(cases)
    raw_attempts = sum(1 for c in cases if c.get("model_attempted"))
    raw_valid = sum(1 for c in cases if c.get("raw_valid"))
    fallback_used = sum(1 for c in cases if c.get("fallback_used"))
    final_valid = sum(1 for c in cases if c.get("final_valid"))
    format_pass = sum(1 for c in cases if c.get("format_pass"))
    grounding_pass = sum(1 for c in cases if c.get("grounding_pass"))
    repetition_pass = sum(1 for c in cases if c.get("repetition_pass"))
    safe = sum(1 for c in cases if c.get("learner_facing_safe"))
    by_type: Dict[str, Dict[str, Any]] = {}
    for task_type in TASK_TYPES:
        subset = [c for c in cases if c.get("task_type") == task_type]
        by_type[task_type] = {
            "total": len(subset),
            "raw_valid": sum(1 for c in subset if c.get("raw_valid")),
            "fallback_used": sum(1 for c in subset if c.get("fallback_used")),
            "final_valid": sum(1 for c in subset if c.get("final_valid")),
            "learner_facing_safe": sum(1 for c in subset if c.get("learner_facing_safe")),
        }
    errors = Counter()
    for case in cases:
        for error in case.get("validation_errors") or []:
            errors[error] += 1
    return {
        "total_cases": total,
        "model_available": bool(model_state.get("model_loaded")),
        "raw_model_attempts": raw_attempts,
        "raw_valid_outputs": raw_valid,
        "raw_invalid_outputs": raw_attempts - raw_valid,
        "fallback_used": fallback_used,
        "final_valid_outputs": final_valid,
        "format_validity_rate": rate(format_pass, total),
        "grounding_pass_rate": rate(grounding_pass, total),
        "repetition_pass_rate": rate(repetition_pass, total),
        "final_safe_output_rate": rate(safe, total),
        "task_success_by_type": by_type,
        "fallback_rate": rate(fallback_used, total),
        "errors": dict(errors),
    }


def render_report(payload: Dict[str, Any]) -> str:
    metrics = payload["metrics"]
    model = payload["model_state"]
    lines = [
        "# Final CogniTutorLM Guarded Generation Evaluation",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Total cases: `{metrics['total_cases']}`",
        f"- Model available: `{metrics['model_available']}`",
        f"- Model checkpoint used: `{model.get('model_checkpoint_used')}`",
        f"- Model checkpoint status: `{model.get('model_checkpoint_status')}`",
        f"- Model training report status: `{model.get('model_training_report_status')}`",
        "",
        "## 1. Raw CogniTutorLM Performance",
        "",
        f"- Raw model attempts: `{metrics['raw_model_attempts']}`",
        f"- Raw valid outputs: `{metrics['raw_valid_outputs']}`",
        f"- Raw invalid outputs: `{metrics['raw_invalid_outputs']}`",
        "",
        "Raw output is not treated as learner-facing content until it passes validation.",
        "",
        "## 2. Validator Performance",
        "",
        f"- Format validity rate: `{metrics['format_validity_rate']}`",
        f"- Grounding pass rate: `{metrics['grounding_pass_rate']}`",
        f"- Repetition pass rate: `{metrics['repetition_pass_rate']}`",
        f"- Common raw validation errors: `{metrics['errors']}`",
        "",
        "## 3. Fallback Usage",
        "",
        f"- Fallback used: `{metrics['fallback_used']}`",
        f"- Fallback rate: `{metrics['fallback_rate']}`",
        "",
        "Fallbacks come from RAG/context-grounded concept resources and guarded templates.",
        "",
        "## 4. Final Learner-Facing Output Validity",
        "",
        f"- Final valid outputs: `{metrics['final_valid_outputs']}`",
        f"- Final safe output rate: `{metrics['final_safe_output_rate']}`",
        "",
        "## Task Success By Type",
        "",
    ]
    for task_type, row in metrics["task_success_by_type"].items():
        lines.append(
            f"- `{task_type}`: total={row['total']}, raw_valid={row['raw_valid']}, "
            f"fallback_used={row['fallback_used']}, final_valid={row['final_valid']}, "
            f"safe={row['learner_facing_safe']}"
        )
    lines.extend(["", "## Case Results", ""])
    for case in payload["cases"]:
        lines.append(
            f"- `{case['subject']} / {case['concept_name']} / {case['task_type']}`: "
            f"raw_valid={case['raw_valid']}, fallback_used={case['fallback_used']}, "
            f"final_valid={case['final_valid']}, safe={case['learner_facing_safe']}, "
            f"fallback_source={case.get('fallback_source')}"
        )
    return "\n".join(lines) + "\n"


def render_summary(payload: Dict[str, Any]) -> str:
    metrics = payload["metrics"]
    model = payload["model_state"]
    inventory = payload["inventory"]
    model_exists = bool(inventory["checkpoint_paths"])
    loads = bool(model.get("model_loaded"))
    raw_unstable = loads and metrics["raw_invalid_outputs"] > 0
    lines = [
        "# Final CogniTutorLM Review Summary",
        "",
        "## 1. What CogniTutorLM Is",
        "",
        "CogniTutorLM is a domain-specific tutor generation component for the Cognition-Adaptive AI Tutor. It generates or selects tutor-style content for known learning concepts and routes learner-facing output through validation.",
        "",
        "## 2. What It Is Not",
        "",
        "CogniTutorLM is not a general-purpose ChatGPT-like LLM. It should not be presented as an open-domain conversational model.",
        "",
        "## 3. Actual Model Checkpoint",
        "",
        f"- Checkpoint files found: `{model_exists}`",
        f"- Selected checkpoint: `{model.get('model_checkpoint_used')}`",
        f"- Checkpoint status: `{model.get('model_checkpoint_status')}`",
        "",
        "## 4. Model Load Status",
        "",
        f"- Model loads in this repo: `{loads}`",
        f"- Model source: `{model.get('model_source')}`",
        f"- Training report status: `{model.get('model_training_report_status')}`",
        "",
        "## 5. RAG Connector Usage",
        "",
        "RAG/context is used through `src/rag_live_context_provider.py` and `src/rag_connector.py`. The guarded generation service resolves concept context before attempting raw model generation or fallback.",
        "",
        "## 6. Fallback / Artifact Bank Usage",
        "",
        "Fallback content is available through `src/concept_resources_guarded_fallback.py`, generated artifacts under `outputs/artifacts/`, and question banks under `outputs/question_bank/`. The new guarded service uses RAG/context-grounded concept fallback templates when raw model output fails.",
        "",
        "## 7. Why Validation Is Necessary",
        "",
        "Raw model output can be empty, malformed, repetitive, ungrounded, or wrong for a required task format. Validation prevents those raw attempts from becoming learner-facing content.",
        "",
        "## 8. Guarded Evaluation Results",
        "",
        f"- Total cases: `{metrics['total_cases']}`",
        f"- Raw model attempts: `{metrics['raw_model_attempts']}`",
        f"- Raw valid outputs: `{metrics['raw_valid_outputs']}`",
        f"- Raw invalid outputs: `{metrics['raw_invalid_outputs']}`",
        f"- Fallback used: `{metrics['fallback_used']}`",
        f"- Final valid outputs: `{metrics['final_valid_outputs']}`",
        f"- Final safe output rate: `{metrics['final_safe_output_rate']}`",
        "",
        "## 9. Current Limitation",
        "",
        "The local checkpoint can load, but raw generation is still unstable and often fails strict review validation. The review-safe behavior comes from guarded validation plus fallback, not from claiming the raw model is perfect.",
        "",
        "## 10. Viva-Safe Explanation",
        "",
        "CogniTutorLM is a domain-specific tutor generation component, not a general-purpose ChatGPT-like LLM. The system attempts model output where available, validates the output, and falls back to RAG-grounded safe content when validation fails.",
        "",
        "## Current Status",
        "",
        f"- REAL MODEL AVAILABLE: `{model_exists}`",
        f"- MODEL CHECKPOINT MISSING: `{not model_exists}`",
        f"- MODEL LOADS BUT OUTPUT UNSTABLE: `{raw_unstable}`",
        f"- FALLBACK PIPELINE WORKING: `{metrics['fallback_used'] > 0 and metrics['final_valid_outputs'] == metrics['total_cases']}`",
        f"- VALIDATOR WORKING: `{metrics['raw_invalid_outputs'] > 0 and metrics['final_valid_outputs'] == metrics['total_cases']}`",
        f"- RAG CONNECTOR WORKING: `{any(c.get('rag_used') for c in payload['cases'])}`",
        f"- FRONTEND-RENDERABLE OUTPUT WORKING: `{metrics['final_valid_outputs'] == metrics['total_cases']}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

    model_state_raw = load_existing_cognitutor_model()
    model_state = {k: v for k, v in model_state_raw.items() if k not in {"model", "tokenizer", "device"}}

    cases: List[Dict[str, Any]] = []
    for concept in CONCEPTS:
        for task_type in TASK_TYPES:
            result = generate_guarded_tutor_output(
                task_type=task_type,
                concept_id=concept["concept_id"],
                concept_name=concept["concept_name"],
                subject=concept["subject"],
                difficulty="easy",
                learner_state={"hint_level": "guided"},
                prefer_model=True,
            )
            result["concept_label"] = concept["label"]
            cases.append(result)
            print(
                f"{concept['label']} | {task_type} | raw_valid={result['raw_valid']} "
                f"fallback={result['fallback_used']} final_valid={result['final_valid']}"
            )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_state": model_state,
        "inventory": build_inventory(),
        "concepts": CONCEPTS,
        "task_types": TASK_TYPES,
        "metrics": summarize_cases(cases, model_state),
        "cases": cases,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_REPORT.write_text(render_report(payload), encoding="utf-8")
    OUT_SUMMARY.write_text(render_summary(payload), encoding="utf-8")

    print("")
    print("Guarded generation evaluation complete.")
    print(f"JSON: {rel(OUT_JSON)}")
    print(f"Report: {rel(OUT_REPORT)}")
    print(f"Summary: {rel(OUT_SUMMARY)}")
    print(json.dumps(payload["metrics"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
