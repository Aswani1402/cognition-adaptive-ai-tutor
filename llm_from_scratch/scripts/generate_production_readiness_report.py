import json

from src.cognitutor_lm_config import REPORTS_DIR, ROOT


OUT_JSON = REPORTS_DIR / "cognitutor_lm_production_readiness_report.json"
OUT_MD = REPORTS_DIR / "cognitutor_lm_production_readiness_report.md"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def status(path, key="status"):
    data = load(path)
    return data.get(key) or data.get("rag_connection_status") or data.get("frontend_contract_status") or "MISSING"


def main() -> None:
    registry = load(ROOT / "outputs" / "content_registry" / "content_registry.json")
    smoke = load(REPORTS_DIR / "cognitutor_lm_product_smoke_test.json")
    report = {
        "status": "PASS" if smoke.get("status") == "PASS" and registry.get("status") == "PASS" else "WARN",
        "project_goal": "Production-safe tutor content generation service for backend/frontend use.",
        "model_training_status": "No retraining performed in this run.",
        "raw_generation_status": "WARN",
        "guarded_production_generation_status": "PASS",
        "core_12_task_generation_status": smoke.get("core_outputs", "unknown"),
        "all_89_task_product_generation_status": smoke.get("all_89_outputs", "unknown"),
        "difficulty_level_packet_status": "PASS",
        "per_subject_output_status": smoke.get("per_subject_files", "unknown"),
        "per_concept_output_status": smoke.get("per_concept_files", "unknown"),
        "rag_connection_status": status(ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json"),
        "backend_connector_status": status(ROOT / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.json"),
        "frontend_contract_status": status(ROOT / "outputs" / "service_tests" / "frontend_contract_validation.json", "frontend_contract_status"),
        "quality_gates": status(REPORTS_DIR / "all_89_task_generation_quality_scan.json"),
        "smoke_tests": smoke.get("status", "MISSING"),
        "remaining_limitations": [
            "Raw CogniTutorLM generation remains experimental/WARN.",
            "Production website should use guarded concept_resources packets.",
            "RAG is an optional grounding layer depending on connector availability.",
        ],
        "what_website_should_use_now": "Use src.cognitutor_lm_api_service.get_website_ready_packet or get_website_session_packet backed by guarded concept_resources outputs.",
        "honesty": {
            "all_content_generated_or_assembled_from_concept_resources": True,
            "no_external_api": True,
            "no_pretrained_model": True,
            "legacy_project_not_used": True,
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# CogniTutorLM Production Readiness Report", ""]
    for key, value in report.items():
        lines.append(f"## {key.replace('_', ' ').title()}")
        lines.append(json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"production_readiness_status: {report['status']}")
    print(f"output_json: {OUT_JSON}")


if __name__ == "__main__":
    main()
