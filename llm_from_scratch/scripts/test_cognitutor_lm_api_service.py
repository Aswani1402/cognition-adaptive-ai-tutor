import json

from src.cognitutor_lm_api_service import (
    ask_doubt_and_get_answer,
    get_available_concepts,
    get_available_subjects,
    get_all_task_outputs,
    get_audio_overview_packet,
    get_frontend_contract_sample,
    get_generated_content,
    get_learning_packet,
    get_product_status,
    get_voice_script,
    get_website_ready_packet,
    get_revision_packet,
    get_website_session_packet,
)
from src.cognitutor_lm_config import ROOT


OUT_JSON = ROOT / "outputs" / "service_tests" / "cognitutor_lm_api_service_test.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "cognitutor_lm_api_service_test.md"


def check(name, result, predicate):
    ok = bool(predicate(result))
    return {"name": name, "status": "PASS" if ok else "FAIL", "result": result}


def main() -> None:
    tests = [
        check("subjects", get_available_subjects(), lambda r: len(r) >= 5),
        check("python_concepts", get_available_concepts("Python"), lambda r: len(r) > 0),
        check("data_structures_concepts", get_available_concepts("Data Structures"), lambda r: len(r) > 0),
        check("python_variables_learning_packet", get_learning_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view"), lambda r: r.get("status") == "success" and bool(r.get("teaching_content")) and r.get("source_level") == "easy_content"),
        check("python_variables_medium_code_packet", get_learning_packet("Python", "Variables", difficulty="medium", teaching_view="code_view"), lambda r: r.get("status") == "success" and r.get("source_level") == "medium_content"),
        check("python_variables_hard_challenge_packet", get_learning_packet("Python", "Variables", difficulty="hard", teaching_view="challenge_view"), lambda r: r.get("status") == "success" and r.get("source_level") == "hard_content"),
        check("data_structures_trees_learning_packet", get_learning_packet("Data Structures", "Trees", difficulty="hard", teaching_view="challenge_view"), lambda r: r.get("status") == "success" and bool(r.get("teaching_content"))),
        check("python_variables_mcq", get_generated_content("Python", concept="Variables", task_type="mcq"), lambda r: r.get("status") == "success" and r.get("valid")),
        check("sql_join_debug", get_generated_content("SQL", concept="JOIN", task_type="debug_task"), lambda r: r.get("status") == "success" and r.get("valid")),
        check("python_variables_all_tasks", get_all_task_outputs("Python", "Variables"), lambda r: len(r) == 89),
        check("python_variables_website_packet", get_website_session_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view"), lambda r: r.get("status") == "success" and bool(r.get("teaching_content")) and isinstance(r.get("voice_script"), dict) and r["voice_script"].get("audio_ready") is True and r.get("all_task_count") in {0, 89}),
        check("python_variables_voice_script", get_voice_script("Python", "Variables", difficulty="easy", teaching_view="definition_view", voice_type="teaching_voice_script"), lambda r: r.get("status") == "success" and r.get("voice_script", {}).get("audio_ready") is True and bool(r.get("voice_script", {}).get("voice_sections"))),
        check("python_variables_audio_overview", get_audio_overview_packet("Python", concept_name="Variables", learner_state={"difficulty": "easy", "teaching_view": "definition_view"}), lambda r: r.get("status") == "success" and r.get("audio_ready") is True and bool(r.get("script"))),
        check("product_status", get_product_status(), lambda r: r.get("status") == "success" and r.get("raw_generation_status") == "WARN"),
        check("website_ready_packet", get_website_ready_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view"), lambda r: r.get("status") == "success" and r.get("quality_gate_status") == "PASS" and r.get("website_ready") is True),
        check("frontend_contract_sample", get_frontend_contract_sample(), lambda r: r.get("status") == "success" and r.get("quality_gate_status") == "PASS"),
        check("doubt_answer", ask_doubt_and_get_answer("Python", "Variables", "Why use variables?"), lambda r: r.get("status") == "success"),
        check("revision_packet", get_revision_packet("Python", "Variables"), lambda r: r.get("status") == "success"),
    ]
    status = "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL"
    report = {"status": status, "tests": tests}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# CogniTutorLM API Service Test\n\n" + "\n".join(f"- {t['name']}: {t['status']}" for t in tests) + "\n", encoding="utf-8")
    print(f"status: {status}")
    print(f"output_json: {OUT_JSON}")


if __name__ == "__main__":
    main()
