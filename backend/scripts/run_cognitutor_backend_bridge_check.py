import json
from pathlib import Path
from typing import Any, Dict, List

from tutor.generation.cognitutor_lm_connector import (
    get_cognitutor_api_service,
    get_cognitutor_all_task_outputs,
    get_cognitutor_audio_overview,
    get_cognitutor_notebook_packet,
    get_cognitutor_session_packet,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "evaluation_outputs" / "reports"
OUT_JSON = OUT_DIR / "cognitutor_lm_backend_bridge_full_coverage_report.json"
OUT_MD = OUT_DIR / "cognitutor_lm_backend_bridge_full_coverage_report.md"

ASSESSMENT_TYPES = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
}
MINDMAP_VARIANTS = ["mindmap", "concept_mindmap", "comparison_mindmap"]
VOICE_VARIANTS = [
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
]
LEVEL_VIEWS = {
    "easy": "definition_view",
    "medium": "code_view",
    "hard": "challenge_view",
}
FLASHCARD_VARIANTS = {
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
}


def load_concepts() -> List[Dict[str, Any]]:
    api = get_cognitutor_api_service()
    return api.load_concept_resources()


def flashcard_count_for_level(tasks: List[Dict[str, Any]], level: str) -> int:
    count = 0
    for row in tasks:
        if row.get("task_type") not in FLASHCARD_VARIANTS:
            continue
        output = row.get("output") or {}
        cards_by_difficulty = output.get("cards_by_difficulty") or output.get("all_level_flashcards") or {}
        if isinstance(cards_by_difficulty, dict):
            card = cards_by_difficulty.get(level)
            if isinstance(card, dict) and card.get("front") and card.get("back"):
                count += 1
        elif row.get("difficulty") == level:
            count += 1
    return count


def concept_check(concept: Dict[str, Any]) -> Dict[str, Any]:
    domain = concept["domain"]
    concept_name = concept["concept_name"]
    api = get_cognitutor_api_service()
    packets = {
        level: api.get_learning_packet(
            domain,
            concept_name=concept_name,
            difficulty=level,
            teaching_view=view,
        )
        for level, view in LEVEL_VIEWS.items()
    }
    all_tasks_response = get_cognitutor_all_task_outputs(domain, concept_name=concept_name)
    tasks = all_tasks_response.get("tasks", []) if isinstance(all_tasks_response, dict) else []
    assessment_types = sorted({row.get("task_type") for row in tasks if row.get("task_type") in ASSESSMENT_TYPES})
    flashcard_counts = {level: flashcard_count_for_level(tasks, level) for level in LEVEL_VIEWS}
    mindmap_count = len({row.get("task_type") for row in tasks if row.get("task_type") in set(MINDMAP_VARIANTS)})
    voice_success = len(
        {
            row.get("task_type")
            for row in tasks
            if row.get("task_type") in set(VOICE_VARIANTS)
            and (row.get("audio_ready") is True or (row.get("output") or {}).get("audio_ready") is True)
            and (row.get("script") or (row.get("output") or {}).get("script"))
        }
    )
    notebook = api.get_notebook_packet(domain, concept_name=concept_name, learner_state={"learner_id": "demo_learner_001"})
    audio = api.get_audio_overview_packet(domain, concept_name=concept_name, learner_state={"difficulty": "easy", "teaching_view": "definition_view"})
    checks = {
        "easy_packet": packets["easy"].get("status") == "success",
        "medium_packet": packets["medium"].get("status") == "success",
        "hard_packet": packets["hard"].get("status") == "success",
        "assessment_count": len(assessment_types),
        "assessment_count_pass": len(assessment_types) >= 17,
        "flashcards_easy": flashcard_counts["easy"],
        "flashcards_medium": flashcard_counts["medium"],
        "flashcards_hard": flashcard_counts["hard"],
        "flashcards_easy_pass": flashcard_counts["easy"] >= 7,
        "flashcards_medium_pass": flashcard_counts["medium"] >= 7,
        "flashcards_hard_pass": flashcard_counts["hard"] >= 7,
        "mindmap_variants": mindmap_count,
        "mindmap_variants_pass": mindmap_count >= 3,
        "voice_variants": voice_success,
        "voice_variants_pass": voice_success >= 8,
        "notebook_status": notebook.get("status") == "success",
        "audio_overview_success": audio.get("status") == "success" and audio.get("audio_ready") is True,
        "all_task_count": len(tasks),
        "all_task_count_pass": len(tasks) == 89,
    }
    passed = all(
        [
            checks["easy_packet"],
            checks["medium_packet"],
            checks["hard_packet"],
            checks["assessment_count_pass"],
            checks["flashcards_easy_pass"],
            checks["flashcards_medium_pass"],
            checks["flashcards_hard_pass"],
            checks["mindmap_variants_pass"],
            checks["voice_variants_pass"],
            checks["notebook_status"],
            checks["audio_overview_success"],
            checks["all_task_count_pass"],
        ]
    )
    return {
        "domain": domain,
        "concept_id": concept["concept_id"],
        "concept_name": concept_name,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
    }


def markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# CogniTutorLM Backend Bridge Full Coverage Report",
        "",
        f"- status: {report['status']}",
        f"- total_concepts_checked: {report['total_concepts_checked']}",
        f"- concepts_passed: {report['concepts_passed']}",
        f"- concepts_failed: {report['concepts_failed']}",
        f"- failed_concepts: {report['failed_concepts']}",
        "- raw_generation_status: WARN",
        "- guarded_generation_status: PASS",
        "",
        "## Failed Concepts",
    ]
    for item in report["concept_reports"]:
        if item["status"] != "PASS":
            lines.append(f"- {item['domain']} / {item['concept_id']} / {item['concept_name']}: {item['checks']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    concepts = load_concepts()
    concept_reports = [concept_check(concept) for concept in concepts]
    failed = [r for r in concept_reports if r["status"] != "PASS"]
    status = "PASS" if len(concepts) == 38 and not failed else ("WARN" if len(concepts) == 38 else "FAIL")
    report = {
        "status": status,
        "total_concepts_checked": len(concepts),
        "concepts_passed": len(concept_reports) - len(failed),
        "concepts_failed": len(failed),
        "failed_concepts": [f"{r['domain']} / {r['concept_id']} / {r['concept_name']}" for r in failed],
        "raw_generation_status": "WARN",
        "guarded_generation_status": "PASS",
        "concept_reports": concept_reports,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    print("total_concepts_checked:", report["total_concepts_checked"])
    print("concepts_passed:", report["concepts_passed"])
    print("concepts_failed:", report["concepts_failed"])
    print("failed_concepts:", report["failed_concepts"])
    print("status:", status)


if __name__ == "__main__":
    main()
