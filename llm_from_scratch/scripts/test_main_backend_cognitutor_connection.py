import json
import sys
from pathlib import Path

from src.cognitutor_lm_config import ROOT


OUT_JSON = ROOT / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.md"
MAIN_BACKEND = ROOT.parent / "cognition_adaptive_AI_tutor"
REQUIRED = [
    "get_cognitutor_teaching_packet",
    "get_cognitutor_assessment_packet",
    "get_cognitutor_doubt_answer",
    "get_cognitutor_revision_packet",
    "get_cognitutor_session_packet",
    "get_cognitutor_all_task_outputs",
    "get_cognitutor_flashcards",
    "get_cognitutor_mindmap",
    "get_cognitutor_notebook_packet",
    "get_cognitutor_audio_overview",
    "get_cognitutor_similar_question",
]


def main() -> None:
    result = {
        "backend_path": str(MAIN_BACKEND),
        "backend_connector_import_status": "FAIL",
        "backend_packet_fetch_status": "WARN",
        "backend_all_tasks_status": "WARN",
        "missing_required_functions": REQUIRED,
        "status": "WARN",
        "reason": "",
    }
    try:
        if str(MAIN_BACKEND) not in sys.path:
            sys.path.insert(0, str(MAIN_BACKEND))
        from tutor.generation import cognitutor_lm_connector as connector

        result["backend_connector_import_status"] = "PASS"
        missing = [name for name in REQUIRED if not hasattr(connector, name)]
        result["missing_required_functions"] = missing
        if not missing:
            packet_cases = [
                connector.get_cognitutor_teaching_packet("Python", concept_name="Variables", difficulty="easy", teaching_view="definition_view"),
                connector.get_cognitutor_teaching_packet("Python", concept_name="Variables", difficulty="medium", teaching_view="code_view"),
                connector.get_cognitutor_teaching_packet("Python", concept_name="Variables", difficulty="hard", teaching_view="challenge_view"),
                connector.get_cognitutor_teaching_packet("SQL", concept_name="JOIN", difficulty="medium", teaching_view="code_view"),
                connector.get_cognitutor_teaching_packet("Data Structures", concept_name="Trees", difficulty="hard", teaching_view="challenge_view"),
            ]
            all_tasks = connector.get_cognitutor_all_task_outputs("Python", concept_name="Variables")
            flashcards = connector.get_cognitutor_flashcards("Python", concept_name="Variables", variant="all")
            mindmap = connector.get_cognitutor_mindmap("Python", concept_name="Variables")
            notebook = connector.get_cognitutor_notebook_packet("Python", concept_name="Variables", learner_state={"learner_id": "demo_learner_001"})
            audio = connector.get_cognitutor_audio_overview("Python", concept_name="Variables", learner_state={"difficulty": "easy", "teaching_view": "definition_view"})
            similar = connector.get_cognitutor_similar_question("Python", "Variables", question_type="practice_question", difficulty="medium")
            packet_ok = all(
                p.get("status") == "success"
                and p.get("teaching_content")
                and p.get("aligned_assessments")
                and p.get("source_level")
                and p.get("quality_gate_status")
                and all(a.get("alignment_reason") for a in p.get("aligned_assessments", []))
                for p in packet_cases
            )
            all_tasks_ok = all_tasks.get("status") == "success" and all_tasks.get("task_count") == 89
            extras_ok = (
                len(flashcards.get("flashcards", [])) >= 7
                and mindmap.get("status") == "success"
                and notebook.get("status") == "success"
                and audio.get("status") == "success"
                and similar.get("status") == "success"
            )
            result["backend_packet_fetch_status"] = "PASS" if packet_ok else "FAIL"
            result["backend_all_tasks_status"] = "PASS" if all_tasks_ok else "FAIL"
            result["backend_frontend_bridge_fields_status"] = "PASS" if extras_ok else "FAIL"
            result["packet_case_statuses"] = [
                {
                    "status": p.get("status"),
                    "domain": p.get("domain"),
                    "concept_name": p.get("concept_name"),
                    "difficulty": p.get("difficulty"),
                    "teaching_view": p.get("teaching_view"),
                    "source_level": p.get("source_level"),
                    "quality_gate_status": p.get("quality_gate_status"),
                    "assessment_count": len(p.get("aligned_assessments", [])),
                }
                for p in packet_cases
            ]
            result["all_tasks_count"] = all_tasks.get("task_count")
            result["flashcard_count"] = len(flashcards.get("flashcards", []))
            result["mindmap_status"] = mindmap.get("status")
            result["notebook_status"] = notebook.get("status")
            result["audio_overview_status"] = audio.get("status")
            result["similar_question_status"] = similar.get("status")
            result["status"] = "PASS" if packet_ok and all_tasks_ok and extras_ok else "FAIL"
        else:
            result["reason"] = "Main backend connector imports, but exact requested get_cognitutor_* contract functions are not present."
    except Exception as exc:
        result["status"] = "WARN"
        result["reason"] = f"Main backend connector unavailable or optional: {type(exc).__name__}: {exc}"

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Main Backend CogniTutor Connection Test\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()) + "\n", encoding="utf-8")
    for key in ["backend_connector_import_status", "backend_packet_fetch_status", "backend_all_tasks_status", "status"]:
        print(f"{key}: {result[key]}")


if __name__ == "__main__":
    main()
