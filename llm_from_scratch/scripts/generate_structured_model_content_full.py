import json
from datetime import datetime
from typing import Dict, List, Tuple

from scripts.structured_generation_common import ROOT_DIR, build_prompt, load_concepts
from src.live_tutor_generator import generate_with_cognitutor_lm
from src.model_content_validator import validate_model_output


CORE_QUALITY = ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json"
WEBSITE = ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.json"
CORE_REPORT = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_report.json"
REPORT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_report.json"
REPORT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full_report.md"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_full.md"


FULL_CONTENT_TYPES: List[Tuple[str, str]] = [
    ("explanation", "explanation"),
    ("definition_view", "explanation"),
    ("simple_example_view", "explanation"),
    ("step_by_step_view", "explanation"),
    ("analogy_view", "explanation"),
    ("code_view", "explanation"),
    ("misconception_view", "explanation"),
    ("debug_view", "debug_task"),
    ("output_prediction_view", "output_prediction"),
    ("transfer_view", "challenge_question"),
    ("challenge_view", "challenge_question"),
    ("revision_summary_view", "revision_summary"),
    ("mcq", "mcq"),
    ("debug_task", "debug_task"),
    ("output_prediction", "output_prediction"),
    ("transfer_question", "challenge_question"),
    ("challenge_question", "challenge_question"),
    ("explanation_check", "explanation"),
    ("syntax_completion", "debug_task"),
    ("coding_prompt", "challenge_question"),
    ("revision_note", "revision_summary"),
    ("revision_summary", "revision_summary"),
    ("weakness_review", "revision_summary"),
    ("daily_review", "revision_summary"),
    ("personal_revision_plan", "revision_summary"),
    ("recommended_revision_views", "revision_summary"),
    ("concept_recall_flashcard", "flashcard"),
    ("misconception_flashcard", "flashcard"),
    ("example_flashcard", "flashcard"),
    ("debug_flashcard", "flashcard"),
    ("personal_flashcards", "flashcard"),
    ("concept_mindmap", "mindmap"),
    ("center_branches_mindmap", "mindmap"),
    ("correct_answer_feedback", "feedback"),
    ("wrong_answer_feedback", "feedback"),
    ("partial_answer_feedback", "feedback"),
    ("debug_feedback", "feedback"),
    ("output_prediction_feedback", "feedback"),
    ("next_step_feedback", "feedback"),
    ("small_hint", "hint"),
    ("guided_hint", "hint"),
    ("worked_example_hint", "hint"),
    ("debug_hint", "hint"),
    ("syntax_hint", "hint"),
    ("output_prediction_hint", "hint"),
    ("misconception_hint", "hint"),
    ("next_step_hint", "hint"),
    ("concept_doubt_answer", "doubt_answer"),
    ("syntax_doubt_answer", "doubt_answer"),
    ("debug_doubt_answer", "doubt_answer"),
    ("output_doubt_answer", "doubt_answer"),
    ("example_request_answer", "doubt_answer"),
    ("revision_doubt_answer", "doubt_answer"),
    ("next_step_doubt_answer", "doubt_answer"),
    ("notebook_summary", "revision_summary"),
    ("mistake_summary", "revision_summary"),
    ("revision_plan", "revision_summary"),
    ("notebook_weakness_review", "revision_summary"),
    ("notebook_daily_review", "revision_summary"),
    ("notebook_personal_flashcards", "flashcard"),
    ("comeback_summary", "revision_summary"),
    ("returning_learner_summary", "revision_summary"),
    ("practice_question", "challenge_question"),
    ("practice_mcq", "mcq"),
    ("practice_debug_task", "debug_task"),
    ("practice_output_prediction", "output_prediction"),
    ("challenge_practice_question", "challenge_question"),
    ("transfer_task", "challenge_question"),
    ("real_world_application_question", "challenge_question"),
    ("debug_challenge", "debug_task"),
    ("output_prediction_challenge", "output_prediction"),
    ("code_reasoning_task", "challenge_question"),
    ("teaching_voice_script", "voice_script"),
    ("revision_voice_script", "voice_script"),
    ("mistake_feedback_voice_script", "voice_script"),
    ("doubt_explanation_voice_script", "voice_script"),
    ("encouragement_script", "voice_script"),
    ("next_step_guidance_script", "voice_script"),
    ("quick_recall_prompt", "flashcard"),
    ("exam_readiness_check", "mcq"),
    ("common_mistake_check", "mcq"),
    ("one_minute_review", "revision_summary"),
]


def gates_pass() -> bool:
    core_quality = json.loads(CORE_QUALITY.read_text(encoding="utf-8")) if CORE_QUALITY.exists() else {}
    website = json.loads(WEBSITE.read_text(encoding="utf-8")) if WEBSITE.exists() else {}
    return (
        core_quality.get("status") == "PASS"
        and float(core_quality.get("valid_rate", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("avg_quality_score", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("website_ready_rate", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("mcq_quality_score", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("option_quality_score", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("logical_consistency_score", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("domain_relevance_score", 0.0) or 0.0) >= 0.85
        and float(core_quality.get("repetition_rate", 1.0) or 1.0) <= 0.15
        and website.get("website_readiness_status") == "PASS"
    )


def alias_prompt(prompt: str, content_type: str) -> str:
    return prompt.replace("<answer>", f"<content_type> {content_type}\n<answer>")


def main() -> None:
    if not gates_pass():
        report = {"status": "SKIPPED", "reason": "core_or_website_gate_not_pass"}
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
        REPORT_MD.write_text("# Structured Full Generation Report\n\nSkipped: core_or_website_gate_not_pass\n", encoding="utf-8")
        OUT_JSON.write_text("[]", encoding="utf-8")
        OUT_MD.write_text("# Structured Model Generated Full\n\nSkipped: core_or_website_gate_not_pass\n", encoding="utf-8")
        print("status: SKIPPED")
        print("reason: core_or_website_gate_not_pass")
        return

    items = []
    concepts = load_concepts()
    for concept in concepts:
        for content_type, base_task_type in FULL_CONTENT_TYPES:
            prompt = alias_prompt(build_prompt(concept, base_task_type), content_type)
            gen = generate_with_cognitutor_lm(prompt, base_task_type, max_new_tokens=140, temperature=0.0, top_p=1.0)
            validation = validate_model_output(
                base_task_type,
                gen.get("output", ""),
                concept["concept_name"],
                concept["domain"],
                prompt,
                grounding_score=1.0 if gen.get("output") else 0.0,
            )
            items.append(
                {
                    "item_id": f"{concept['domain']}:{concept['concept_id']}:{content_type}",
                    "concept_id": concept["concept_id"],
                    "concept_name": concept["concept_name"],
                    "domain": concept["domain"],
                    "task_type": content_type,
                    "base_task_type": base_task_type,
                    "generation_source": "cognitutor_lm_from_scratch_structured_model",
                    "model_used": "CogniTutorLM-from-scratch-structured",
                    "prompt": prompt,
                    "output": gen.get("output", ""),
                    "valid": validation["valid"],
                    "quality_score": validation["quality_score"],
                    "issues": validation["issues"],
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )

    attempted = len(items)
    valid = sum(1 for item in items if item.get("valid") is True)
    valid_rate = round(valid / attempted, 4) if attempted else 0.0
    avg_quality = round(sum(float(item.get("quality_score", 0.0)) for item in items) / attempted, 4) if attempted else 0.0
    status = "PASS" if valid_rate >= 0.85 and avg_quality >= 0.85 else "WARN"
    report = {
        "status": status,
        "attempted": attempted,
        "valid": valid,
        "valid_rate": valid_rate,
        "avg_quality_score": avg_quality,
        "concepts_attempted": len({item["concept_id"] for item in items}),
        "domains_covered": sorted({item["domain"] for item in items}),
        "content_types_covered": sorted({item["task_type"] for item in items}),
        "base_task_types_covered": sorted({item["base_task_type"] for item in items}),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Structured Model Generated Full\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in report.items())
        + "\n",
        encoding="utf-8",
    )
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_MD.write_text(
        "# Structured Full Generation Report\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in report.items())
        + "\n",
        encoding="utf-8",
    )
    if CORE_REPORT.exists():
        core_report = json.loads(CORE_REPORT.read_text(encoding="utf-8"))
        core_report["full_generation_status"] = status
        core_report["full_generation_report_path"] = str(REPORT_JSON)
        CORE_REPORT.write_text(json.dumps(core_report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"status: {status}")
    print(f"attempted: {attempted}")
    print(f"valid: {valid}")
    print(f"valid_rate: {valid_rate}")
    print(f"avg_quality_score: {avg_quality}")


if __name__ == "__main__":
    main()
