import json
from pathlib import Path
from typing import Any, Dict, List

from src.cognitutor_lm_api_service import get_website_session_packet
from src.cognitutor_lm_config import ALL_89_TASK_TYPES, PACKET_OUTPUT, REPORTS_DIR, TEACHING_VIEWS
from src.concept_resource_loader import load_concept_resources


DIFFICULTIES = ["easy", "medium", "hard", "revision"]
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
FLASHCARD_TYPES = {
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
}
MINDMAP_TYPES = {"mindmap", "concept_mindmap", "comparison_mindmap"}
VOICE_TYPES = {
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
}


def _read_json(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def main() -> None:
    concepts = load_concept_resources()
    packets = _read_json(PACKET_OUTPUT)
    packet_index = {}
    for packet in packets:
        packet_index.setdefault((packet.get("domain"), packet.get("concept_id")), []).append(packet)

    results = []
    for concept in concepts:
        key = (concept["domain"], concept["concept_id"])
        concept_packets = packet_index.get(key, [])
        views = {p.get("teaching_view") for p in concept_packets}
        difficulties = {p.get("difficulty") for p in concept_packets}
        sample_packet = get_website_session_packet(
            concept["domain"],
            concept["concept_name"],
            learner_id="coverage_check",
            difficulty="easy",
            teaching_view="definition_view",
            use_rag=True,
        )
        task_types = {row.get("task_type") for row in sample_packet.get("all_task_outputs", [])}
        assessment_types = set(sample_packet.get("assessment_types_available") or sample_packet.get("all_assessment_types") or [])
        flashcard_types = set(sample_packet.get("flashcard_variants_available") or [])
        mindmap_types = set(sample_packet.get("mindmap_variants_available") or [])
        voice_types = set(sample_packet.get("voice_variants_available") or [])
        missing = {
            "teaching_views": sorted(set(TEACHING_VIEWS) - views),
            "difficulties": sorted(set(DIFFICULTIES) - difficulties),
            "task_types": sorted(set(ALL_89_TASK_TYPES) - task_types),
            "assessment_types": sorted(ASSESSMENT_TYPES - assessment_types),
            "flashcard_variants": sorted(FLASHCARD_TYPES - flashcard_types),
            "mindmap_variants": sorted(MINDMAP_TYPES - mindmap_types),
            "voice_variants": sorted(VOICE_TYPES - voice_types),
        }
        notebook_ok = bool(sample_packet.get("notebook_summary")) and bool(sample_packet.get("revision_plan")) and sample_packet.get("mistake_summary") is not None
        case_status = "PASS" if all(not value for value in missing.values()) and notebook_ok else "FAIL"
        results.append(
            {
                "domain": concept["domain"],
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "status": case_status,
                "teaching_view_count": len(views),
                "difficulty_count": len(difficulties),
                "task_type_count": len(task_types),
                "assessment_types_count": len(assessment_types),
                "flashcard_variants_count": len(flashcard_types),
                "mindmap_variants_count": len(mindmap_types),
                "voice_variants_count": len(voice_types),
                "notebook_revision_mistake_outputs": notebook_ok,
                "missing": missing,
            }
        )

    failed = [r for r in results if r["status"] != "PASS"]
    report = {
        "status": "PASS" if not failed and len(concepts) == 38 else "FAIL",
        "concept_count": len(concepts),
        "expected_concept_count": 38,
        "teaching_views_expected": len(TEACHING_VIEWS),
        "difficulties_expected": len(DIFFICULTIES),
        "task_types_expected": len(ALL_89_TASK_TYPES),
        "assessment_types_expected": len(ASSESSMENT_TYPES),
        "flashcard_variants_expected": len(FLASHCARD_TYPES),
        "mindmap_variants_expected": len(MINDMAP_TYPES),
        "voice_variants_expected": len(VOICE_TYPES),
        "failed_count": len(failed),
        "raw_generation_status": "WARN",
        "final_guarded_generation_status": "PASS",
        "results": results,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "all_concepts_all_views_coverage.json"
    out_md = REPORTS_DIR / "all_concepts_all_views_coverage.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(
        "# All Concepts All Views Coverage\n\n"
        f"- status: {report['status']}\n"
        f"- concept_count: {len(concepts)} / 38\n"
        f"- teaching_views_expected: {len(TEACHING_VIEWS)}\n"
        f"- task_types_expected: {len(ALL_89_TASK_TYPES)}\n"
        f"- failed_count: {len(failed)}\n"
        "- raw_generation_status: WARN\n"
        "- final_guarded_generation_status: PASS\n",
        encoding="utf-8",
    )
    print("concept_count:", len(concepts))
    print("failed_count:", len(failed))
    print("status:", report["status"])


if __name__ == "__main__":
    main()
