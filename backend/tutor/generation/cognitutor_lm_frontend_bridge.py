from __future__ import annotations

from typing import Any, Dict

from tutor.generation.cognitutor_lm_connector import (
    get_cognitutor_all_task_outputs,
    get_cognitutor_audio_overview,
    get_cognitutor_flashcards,
    get_cognitutor_mindmap,
    get_cognitutor_notebook_packet,
    get_cognitutor_session_packet,
    get_cognitutor_similar_question,
)


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


def build_frontend_cognitutor_packet(
    learner_id: str,
    domain: str,
    concept: str,
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
) -> Dict[str, Any]:
    session = get_cognitutor_session_packet(domain, concept, learner_id=learner_id, difficulty=difficulty, teaching_view=teaching_view, use_rag=True)
    if session.get("status") != "success":
        return {"status": "WARN", "reason": "CogniTutorLM session packet unavailable", "session": session}

    all_tasks = get_cognitutor_all_task_outputs(domain, concept_name=concept)
    tasks = all_tasks.get("tasks", []) if isinstance(all_tasks, dict) else []
    assessment_bank = session.get("assessment_bank") or [
        row for row in tasks if row.get("task_type") in ASSESSMENT_TYPES
    ]
    flashcards = get_cognitutor_flashcards(domain, concept_name=concept, variant="all")
    mindmap = get_cognitutor_mindmap(domain, concept_name=concept, variant="concept_mindmap")
    notebook = get_cognitutor_notebook_packet(domain, concept_name=concept, learner_state={"learner_id": learner_id})
    audio = get_cognitutor_audio_overview(domain, concept_name=concept, learner_state={"difficulty": difficulty, "teaching_view": teaching_view})
    similar = get_cognitutor_similar_question(domain, concept, question_type="practice_question", difficulty=difficulty)

    assessment_types_available = sorted({q.get("questionType") or q.get("task_type") or q.get("taskType") for q in assessment_bank if isinstance(q, dict)})
    flashcard_variants_available = sorted({card.get("card_type") for card in flashcards.get("flashcards", []) if isinstance(card, dict) and card.get("card_type")})
    mindmaps = session.get("mindmaps") or {
        "concept_mindmap": mindmap.get("mindmap", {}),
    }
    mindmap_variants_available = session.get("mindmap_variants_available") or sorted([key for key, value in mindmaps.items() if value])
    voice_variants_available = session.get("voice_variants_available") or sorted((session.get("voice_scripts") or {}).keys())
    return {
        "status": "success",
        "source": "main_backend_cognitutor_lm_frontend_bridge",
        "learner_id": learner_id,
        "domain": session.get("domain", domain),
        "concept_id": session.get("concept_id"),
        "concept_name": session.get("concept_name", concept),
        "difficulty": session.get("difficulty", difficulty),
        "source_level": session.get("source_level"),
        "teaching_view": session.get("teaching_view", teaching_view),
        "teaching_content": session.get("teaching_content"),
        "aligned_assessments": session.get("aligned_assessments", []),
        "assessment_bank": assessment_bank,
        "assessment_types_available": assessment_types_available,
        "all_assessment_types": assessment_types_available,
        "puzzle_tasks": session.get("puzzle_tasks", []),
        "all_task_outputs": tasks,
        "flashcards": flashcards.get("flashcards", []),
        "flashcard_variants_available": flashcard_variants_available,
        "mindmap": mindmaps.get("concept_mindmap") or mindmap.get("mindmap", {}),
        "mindmaps": mindmaps,
        "mindmap_variants_available": mindmap_variants_available,
        "notebook": notebook,
        "mistake_summary": notebook.get("mistake_summary", []),
        "mistakes": notebook.get("mistake_summary", []),
        "revision_plan": notebook.get("revision_plan", []),
        "revision": notebook.get("revision_plan", []),
        "voice_script": session.get("voice_script"),
        "voice_scripts": session.get("voice_scripts", {}),
        "voice_variants_available": voice_variants_available,
        "audio_overview": audio,
        "doubt_answer": None,
        "similar_question": similar.get("question") or similar.get("similar_question"),
        "next_step": session.get("next_step"),
        "all_task_outputs_available": len(tasks) == 89,
        "all_task_count": session.get("all_task_count") or len(tasks),
        "rag_metadata": session.get("rag_metadata") or {
            "rag_used": session.get("rag_used"),
            "rag_context_count": session.get("rag_context_count"),
            "rag_grounding_status": session.get("rag_grounding_status", "WARN"),
        },
        "frontend_ready": True,
        "metadata": {
            "raw_generation_status": session.get("raw_generation_status", "WARN"),
            "guarded_generation_status": session.get("final_guarded_generation_status", "PASS"),
            "rag_used": session.get("rag_used"),
            "rag_context_count": session.get("rag_context_count"),
            "rag_grounding_status": session.get("rag_grounding_status", "WARN"),
            "all_task_count": session.get("all_task_count"),
        },
    }


if __name__ == "__main__":
    packet = build_frontend_cognitutor_packet("demo_learner_001", "Python", "Variables", "easy", "definition_view")
    print("status:", packet.get("status"))
    print("teaching_title:", (packet.get("teaching_content") or {}).get("title"))
    print("assessment_count:", len(packet.get("assessment_bank") or []))
    print("flashcard_count:", len(packet.get("flashcards") or []))
    print("mindmap_status:", bool(packet.get("mindmap")))
    print("audio_overview_status:", (packet.get("audio_overview") or {}).get("status"))
