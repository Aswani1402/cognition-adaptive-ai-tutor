import json
from pathlib import Path

from src.cognitutor_lm_api_service import get_website_session_packet
from src.cognitutor_lm_config import REPORTS_DIR, ROOT


OUT_JSON = ROOT / "outputs" / "service_tests" / "frontend_cognitutor_contract_check.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "frontend_cognitutor_contract_check.md"
CONTRACT_MD = REPORTS_DIR / "frontend_cognitutor_lm_contract.md"
FRONTEND = ROOT.parent / "frontend_ui" / "KP-UI"
REQUIRED = [
    "teaching_content",
    "aligned_assessments",
    "hint",
    "feedback_template",
    "revision_summary",
    "flashcard",
    "mindmap",
    "voice_script",
    "next_step",
    "metadata",
    "difficulty",
    "teaching_view",
    "source_level",
]


def frontend_mentions() -> set[str]:
    mentions = set()
    if not FRONTEND.exists():
        return mentions
    for path in (FRONTEND / "src").rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".jsx", ".md"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for field in REQUIRED:
                if field in text:
                    mentions.add(field)
    return mentions


def main() -> None:
    packet = get_website_session_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view")
    backend_missing = [field for field in REQUIRED if field not in packet]
    frontend_seen = frontend_mentions()
    frontend_missing = [field for field in REQUIRED if field not in frontend_seen]
    status = "PASS" if not backend_missing and len(frontend_missing) <= 4 else ("FAIL" if backend_missing else "WARN")
    report = {
        "frontend_path": str(FRONTEND),
        "frontend_contract_status": status,
        "missing_frontend_fields": frontend_missing,
        "missing_backend_fields": backend_missing,
        "recommended_patch": "Map source_level and metadata as hidden/debug reviewer fields if not already rendered.",
        "request_format": {"domain": "Python", "concept": "Variables", "difficulty": "easy", "teaching_view": "definition_view", "learner_id": "demo_learner_001"},
        "response_required_fields": REQUIRED,
        "current_backend_route": "Backend connector should call src.cognitutor_lm_api_service.get_website_session_packet or expose equivalent route.",
        "status": status,
    }
    mapping = {
        "teaching_content.title": "lesson title",
        "beginner_explanation": "teaching body",
        "example": "example card",
        "aligned_assessments": "assessment renderer",
        "hint": "hint panel",
        "feedback_template": "feedback panel",
        "revision_summary": "revision card",
        "flashcard": "flashcard deck",
        "mindmap": "mindmap view",
        "voice_script": "Cogni mascot script",
        "metadata.source_level": "hidden/debug/reviewer info",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Frontend CogniTutorLM Contract",
        "",
        "## Request Format",
        "```json",
        json.dumps(report["request_format"], indent=2),
        "```",
        "",
        "## Response Format",
        "```json",
        json.dumps({field: "<required>" for field in REQUIRED}, indent=2),
        "```",
        "",
        f"Current backend route: {report['current_backend_route']}",
        "",
        "## Missing Fields",
        f"- Frontend: {frontend_missing}",
        f"- Backend: {backend_missing}",
        "",
        "## UI Mapping",
    ]
    lines.extend(f"- {k} -> {v}" for k, v in mapping.items())
    lines.extend(["", f"frontend_contract_status: {status}", ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    CONTRACT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"frontend_contract_status: {status}")
    print(f"missing_frontend_fields: {frontend_missing}")
    print(f"missing_backend_fields: {backend_missing}")


if __name__ == "__main__":
    main()
