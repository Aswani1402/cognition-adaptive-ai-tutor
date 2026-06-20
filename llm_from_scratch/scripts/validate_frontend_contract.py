import json
from typing import Any, Dict, List

from src.cognitutor_lm_api_service import get_frontend_contract_sample
from src.cognitutor_lm_config import REPORTS_DIR, ROOT


OUT_JSON = ROOT / "outputs" / "service_tests" / "frontend_contract_validation.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "frontend_contract_validation.md"
CONTRACT_MD = REPORTS_DIR / "frontend_cognitutor_lm_contract.md"

REQUIRED_PATHS = [
    "status",
    "domain",
    "concept_id",
    "concept_name",
    "difficulty",
    "source_level",
    "teaching_view",
    "teaching_content.title",
    "teaching_content.beginner_explanation",
    "teaching_content.definition",
    "teaching_content.example",
    "aligned_assessments",
    "hint",
    "feedback_template.correct",
    "feedback_template.partial",
    "feedback_template.wrong",
    "revision_summary",
    "flashcard",
    "mindmap",
    "voice_script",
    "next_step",
    "metadata",
    "quality_gate_status",
    "website_ready",
]


def get_path(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def main() -> None:
    packet = get_frontend_contract_sample()
    missing = [path for path in REQUIRED_PATHS if get_path(packet, path) in (None, "", [])]
    status = "PASS" if not missing and packet.get("website_ready") else "FAIL"
    report = {
        "frontend_contract_status": status,
        "status": status,
        "missing_backend_fields": missing,
        "missing_frontend_fields": [],
        "sample_domain": packet.get("domain"),
        "sample_concept": packet.get("concept_name"),
        "quality_gate_status": packet.get("quality_gate_status"),
        "website_ready": packet.get("website_ready"),
        "recommended_patch": "No backend patch required." if status == "PASS" else "Add missing fields to website packet response.",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Frontend CogniTutorLM Contract",
        "",
        "## Request Format",
        "```json",
        json.dumps({"domain": "Python", "concept": "Variables", "difficulty": "easy", "teaching_view": "definition_view", "learner_id": "demo_learner_001"}, indent=2),
        "```",
        "",
        "## Response Required Fields",
    ]
    lines.extend(f"- {path}" for path in REQUIRED_PATHS)
    lines.extend(
        [
            "",
            "## UI Mapping",
            "- teaching_content.title -> lesson title",
            "- beginner_explanation -> teaching body",
            "- example -> example card",
            "- aligned_assessments -> assessment renderer",
            "- hint -> hint panel",
            "- feedback_template -> feedback panel",
            "- revision_summary -> revision card",
            "- flashcard -> flashcard deck",
            "- mindmap -> mindmap view",
            "- voice_script -> Cogni mascot script",
            "- metadata.source_level -> hidden/debug/reviewer info",
            "",
            f"frontend_contract_status: {status}",
            f"missing_backend_fields: {missing}",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CONTRACT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"frontend_contract_status: {status}")
    print(f"missing_backend_fields: {missing}")


if __name__ == "__main__":
    main()
