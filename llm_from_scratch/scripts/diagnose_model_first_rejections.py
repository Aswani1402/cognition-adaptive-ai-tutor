import json
from collections import Counter

from src.cognitutor_lm_config import ROOT
from src.model_first_parser import parse_model_output
from src.model_first_runtime import generate_raw_model_output
from src.model_first_validator import validate_model_output
from src.rag_live_context_provider import get_live_rag_context

OUT_DIR = ROOT / "outputs" / "rag_llm_live_guarded" / "diagnostics"
OUT_JSON = OUT_DIR / "model_first_rejection_diagnosis.json"
OUT_MD = OUT_DIR / "model_first_rejection_diagnosis.md"

SAMPLES = [
    ("Python", "Variables", "easy", "explanation"),
    ("Python", "Variables", "easy", "mcq"),
    ("Python", "Variables", "medium", "debug_task"),
    ("Python", "Variables", "medium", "output_prediction"),
    ("Python", "Variables", "hard", "challenge_question"),
    ("SQL", "JOIN Operations", "medium", "explanation"),
    ("SQL", "JOIN Operations", "medium", "mcq"),
    ("HTML", "Forms and Inputs", "easy", "explanation"),
    ("Git", "Branches", "medium", "code_view"),
    ("Data Structures", "Trees", "hard", "mindmap"),
    ("HTML", "Forms and Inputs", "medium", "flashcard"),
    ("Git", "Branches", "easy", "hint"),
    ("SQL", "JOIN Operations", "hard", "true_or_false"),
    ("Data Structures", "Trees", "easy", "voice_script"),
    ("Python", "Variables", "hard", "fill_in_the_blank"),
    ("SQL", "JOIN Operations", "easy", "debug_task"),
    ("HTML", "Forms and Inputs", "hard", "feedback"),
    ("Git", "Branches", "hard", "revision_summary"),
    ("Data Structures", "Trees", "medium", "output_prediction"),
    ("Python", "Variables", "easy", "doubt_answer"),
]


def classify(raw, parsed, parse, validation):
    issues = validation.get("issues") or []
    if not raw:
        return "model_not_producing_output"
    if parse.get("parse_status") == "FAIL":
        return "parser_too_strict"
    if "concept_not_grounded" in issues or "domain_not_grounded" in issues or "wrong_concept_leakage" in issues:
        return "concept/domain mismatch"
    if "task_specific_schema_failed" in issues:
        return "missing required fields"
    if "not_frontend_renderable" in issues:
        return "frontend renderability failure"
    if "repeated_text_loop" in issues:
        return "model output format wrong"
    if validation.get("quality_score", 0) >= 0.70 and issues:
        return "validator too strict"
    if issues:
        return "model output format wrong"
    return "accepted"


def main():
    cases = []
    causes = Counter()
    for domain, concept, difficulty, task_type in SAMPLES:
        teaching_view = task_type if task_type.endswith("_view") else "definition_view"
        context = get_live_rag_context(domain, concept, task_type=task_type, difficulty=difficulty, teaching_view=teaching_view)
        raw = generate_raw_model_output(task_type, context.get("domain") or domain, context.get("concept_name") or concept, difficulty, teaching_view, context)
        parsed = parse_model_output(raw.get("raw_output") or "", task_type)
        validation = validate_model_output(
            parsed.get("parsed_output"),
            task_type,
            context.get("domain") or domain,
            context.get("concept_name") or concept,
            difficulty,
            teaching_view,
            context,
            parser_repair_applied=bool(parsed.get("repair_applied")),
        )
        cause = classify(raw.get("raw_output"), parsed.get("parsed_output"), parsed, validation)
        causes[cause] += 1
        cases.append(
            {
                "domain": domain,
                "concept_name": concept,
                "difficulty": difficulty,
                "task_type": task_type,
                "prompt": raw.get("prompt"),
                "raw_model_output": raw.get("raw_output"),
                "parsed_output": parsed.get("parsed_output"),
                "validation": validation,
                "rejection_reason": None if validation.get("valid") else cause,
                "parser_failed": parsed.get("parse_status") == "FAIL",
                "schema_failed": not validation.get("schema_valid"),
                "concept_match_failed": not validation.get("concept_match"),
                "task_format_failed": not validation.get("task_match"),
                "empty_or_repetitive": (not raw.get("raw_output")) or "repeated_text_loop" in (validation.get("issues") or []),
            }
        )
        print(f"{domain}/{concept}/{difficulty}/{task_type}: {cause}")
    report = {"status": "PASS", "sample_count": len(cases), "top_rejection_causes": dict(causes.most_common(10)), "cases": cases}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Model-First Rejection Diagnosis", "", "## Top Rejection Causes"]
    lines.extend(f"- {k}: {v}" for k, v in causes.most_common(10))
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("Top rejection causes:")
    for cause, count in causes.most_common(10):
        print(f"- {cause}: {count}")


if __name__ == "__main__":
    main()
