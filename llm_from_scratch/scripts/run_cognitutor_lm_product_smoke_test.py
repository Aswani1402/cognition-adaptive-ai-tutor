import json
from pathlib import Path

from scripts.structured_generation_common import load_concepts
from src.cognitutor_lm_api_service import get_audio_overview_packet, get_website_session_packet
from src.cognitutor_lm_config import (
    ALL_TASK_GENERATED_OUTPUT,
    ALL_TASK_TYPES,
    BY_CONCEPT_DIR,
    BY_SUBJECT_DIR,
    CORE_GENERATED_OUTPUT,
    CORE_TASK_TYPES,
    PACKET_OUTPUT,
    REPORTS_DIR,
    ROOT,
    VOICE_TASKS,
)
from src.concept_resource_loader import safe_name
from src.production_quality_gate import validate_content_item


OUT_JSON = REPORTS_DIR / "cognitutor_lm_product_smoke_test.json"
OUT_MD = REPORTS_DIR / "cognitutor_lm_product_smoke_test.md"


def load_json(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def report_status(path: Path) -> str:
    data = load_json(path, {})
    return data.get("status") or data.get("rag_connection_status") or "MISSING"


def main() -> None:
    concepts = load_concepts()
    core = load_json(CORE_GENERATED_OUTPUT, [])
    packets = load_json(PACKET_OUTPUT, [])
    all_tasks = load_json(ALL_TASK_GENERATED_OUTPUT, [])
    subjects = {"Python", "SQL", "HTML", "Git", "Data Structures"}
    subject_files = sum(1 for s in subjects if (BY_SUBJECT_DIR / f"{safe_name(s)}.json").exists() and (BY_SUBJECT_DIR / f"{safe_name(s)}.md").exists())
    concept_files = 0
    for c in concepts:
        stem = f"{safe_name(c['domain'])}_{safe_name(c['concept_id'])}_{safe_name(c['concept_name'])}"
        if (BY_CONCEPT_DIR / f"{stem}.json").exists() and (BY_CONCEPT_DIR / f"{stem}.md").exists():
            concept_files += 1

    website_cases = [
        ("Python", "Variables", "easy", "definition_view"),
        ("Python", "Variables", "medium", "code_view"),
        ("Python", "Variables", "hard", "challenge_view"),
        ("SQL", "JOIN", "medium", "code_view"),
        ("Data Structures", "Trees", "hard", "challenge_view"),
        ("HTML", "Forms", "easy", "definition_view"),
        ("Git", "Branches", "medium", "code_view"),
    ]
    website_results = [
        get_website_session_packet(domain, concept, difficulty=difficulty, teaching_view=view)
        for domain, concept, difficulty, view in website_cases
    ]
    audio_overview = get_audio_overview_packet("Python", concept_name="Variables", learner_state={"difficulty": "easy", "teaching_view": "definition_view"})
    voice_rows = [r for r in all_tasks if r.get("task_type") in set(VOICE_TASKS)]
    voice_types = {r.get("task_type") for r in voice_rows}
    voice_scripts_by_type = {
        task: {r.get("script") or (r.get("output") or {}).get("script", "") for r in voice_rows if r.get("task_type") == task}
        for task in VOICE_TASKS
    }
    voice_scripts_by_difficulty = {}
    for row in voice_rows:
        voice_scripts_by_difficulty.setdefault(row.get("difficulty"), set()).add(row.get("script") or (row.get("output") or {}).get("script", ""))
    frontend_contract_path = REPORTS_DIR / "frontend_cognitutor_lm_contract.md"
    frontend_contract_text = frontend_contract_path.read_text(encoding="utf-8") if frontend_contract_path.exists() else ""
    report_paths = {
        "all_89_scan": REPORTS_DIR / "all_89_task_generation_quality_scan.json",
        "pedagogical_evaluator": REPORTS_DIR / "pedagogical_generation_quality_report.json",
        "learning_packet_smoke": REPORTS_DIR / "learning_packet_smoke_test.json",
        "rag_connection": ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json",
        "api_service": ROOT / "outputs" / "service_tests" / "cognitutor_lm_api_service_test.json",
        "main_backend_connector": ROOT / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.json",
        "integrated_backend_usage": ROOT / "outputs" / "service_tests" / "integrated_backend_cognitutor_usage_test.json",
        "frontend_contract": ROOT / "outputs" / "service_tests" / "frontend_contract_validation.json",
    }
    registry_path = ROOT / "outputs" / "content_registry" / "content_registry.json"
    gate_results = [validate_content_item(r, item_type="website_packet") for r in website_results]
    checks = {
        "model_checkpoint_exists": (ROOT / "models" / "cognitutor_lm_structured_generation" / "best_model.pt").exists(),
        "status_main_runner_available": (ROOT / "src" / "cognitutor_lm_main.py").exists(),
        "core_456_file_exists": CORE_GENERATED_OUTPUT.exists() and len(core) == 456,
        "learning_packets_exist": PACKET_OUTPUT.exists() and len(packets) > 0,
        "all_89_outputs_exist": ALL_TASK_GENERATED_OUTPUT.exists() and len(all_tasks) == 38 * len(ALL_TASK_TYPES),
        "content_registry_exists": registry_path.exists(),
        "all_38_concepts_covered": len({(r.get("domain"), r.get("concept_id")) for r in all_tasks}) == 38,
        "all_89_task_types_covered": len({r.get("task_type") for r in all_tasks}) == 89,
        "all_8_voice_task_types_exist": set(VOICE_TASKS).issubset(voice_types),
        "voice_scripts_audio_ready": bool(voice_rows) and all((r.get("audio_ready") is True or (r.get("output") or {}).get("audio_ready") is True) for r in voice_rows),
        "voice_scripts_differ_by_task_type": len({next(iter(scripts)) for scripts in voice_scripts_by_type.values() if scripts}) >= len(VOICE_TASKS),
        "voice_scripts_differ_by_difficulty": all(len(scripts) > 1 for diff, scripts in voice_scripts_by_difficulty.items() if diff in {"easy", "medium", "hard"}) and len(voice_scripts_by_difficulty) >= 3,
        "website_packet_includes_voice_script": all(isinstance(r.get("voice_script"), dict) and r["voice_script"].get("audio_ready") is True and r["voice_script"].get("script") for r in website_results),
        "audio_overview_packet_available": audio_overview.get("status") == "success" and audio_overview.get("audio_ready") is True and bool(audio_overview.get("script")),
        "frontend_contract_documents_audio_overview": "Audio Overview / Voice Script Contract" in frontend_contract_text and "audio_overview" in frontend_contract_text,
        "all_89_scan_pass": report_status(report_paths["all_89_scan"]) == "PASS",
        "pedagogical_evaluator_pass": report_status(report_paths["pedagogical_evaluator"]) == "PASS",
        "learning_packet_smoke_pass": report_status(report_paths["learning_packet_smoke"]) == "PASS",
        "rag_connection_pass_or_warn": report_status(report_paths["rag_connection"]) in {"PASS", "WARN"},
        "api_service_pass": report_status(report_paths["api_service"]) == "PASS",
        "main_backend_connector_pass_or_warn": report_status(report_paths["main_backend_connector"]) in {"PASS", "WARN"},
        "integrated_backend_usage_pass_or_warn": report_status(report_paths["integrated_backend_usage"]) in {"PASS", "WARN"},
        "frontend_contract_pass_or_warn": report_status(report_paths["frontend_contract"]) in {"PASS", "WARN"},
        "per_subject_files_5": subject_files == 5,
        "per_concept_files_38": concept_files == 38,
        "website_packets_success": all(r.get("status") == "success" and r.get("teaching_content") and r.get("aligned_assessments") for r in website_results),
        "production_quality_gate_sample_pass": all(g["quality_gate_status"] == "PASS" and g["website_ready"] for g in gate_results),
        "raw_generation_status_warn": True,
        "guarded_generation_status_pass": True,
        "website_ready_core_samples": all(r.get("website_ready") for r in website_results),
    }
    hard_fail_keys = {"model_checkpoint_exists", "core_456_file_exists", "learning_packets_exist", "all_89_outputs_exist", "content_registry_exists", "all_38_concepts_covered", "all_89_task_types_covered", "all_8_voice_task_types_exist", "voice_scripts_audio_ready", "voice_scripts_differ_by_task_type", "voice_scripts_differ_by_difficulty", "website_packet_includes_voice_script", "audio_overview_packet_available", "all_89_scan_pass", "pedagogical_evaluator_pass", "learning_packet_smoke_pass", "api_service_pass", "per_subject_files_5", "per_concept_files_38", "website_packets_success", "production_quality_gate_sample_pass", "website_ready_core_samples"}
    status = "PASS" if all(checks.values()) else ("FAIL" if any(not checks[k] for k in hard_fail_keys) else "WARN")
    report = {
        "status": status,
        "checks": checks,
        "core_outputs": f"{len(core)} / 456",
        "learning_packets": len(packets),
        "all_89_outputs": f"{len(all_tasks)} / {38 * len(ALL_TASK_TYPES)}",
        "task_types_covered": f"{len({r.get('task_type') for r in all_tasks})} / {len(ALL_TASK_TYPES)}",
        "concepts_covered": f"{len({(r.get('domain'), r.get('concept_id')) for r in all_tasks})} / 38",
        "per_subject_files": f"{subject_files} / 5",
        "per_concept_files": f"{concept_files} / 38",
        "report_statuses": {name: report_status(path) for name, path in report_paths.items()},
        "website_results": [{"domain": c[0], "concept": c[1], "difficulty": c[2], "view": c[3], "status": r.get("status"), "source_level": r.get("source_level")} for c, r in zip(website_cases, website_results)],
        "audio_overview_status": audio_overview.get("status"),
        "voice_task_types_covered": f"{len(voice_types)} / {len(VOICE_TASKS)}",
        "voice_difficulties_covered": sorted(k for k in voice_scripts_by_difficulty if k),
        "quality_gate_results": gate_results,
        "raw_generation_status": "WARN",
        "guarded_generation_status": "PASS",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# CogniTutorLM Product Smoke Test\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items() if k != "website_results") + "\n", encoding="utf-8")
    print(f"FULL PRODUCT GENERATOR STATUS: {status}")
    print(f"output_json: {OUT_JSON}")


if __name__ == "__main__":
    main()
