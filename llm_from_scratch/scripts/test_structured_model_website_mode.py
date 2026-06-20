import json
import os

from scripts.structured_generation_common import ROOT_DIR
from src.tutor_lm_service import TutorLMService


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
CORE_QUALITY = ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json"
OUT_JSON = ROOT_DIR / "outputs" / "service_tests" / "structured_model_website_mode_report.json"
OUT_MD = ROOT_DIR / "outputs" / "service_tests" / "structured_model_website_mode_report.md"

REQUIRED = {
    "status",
    "concept_id",
    "concept_name",
    "domain",
    "task_type",
    "generation_source",
    "model_used",
    "output",
    "valid",
    "quality_score",
    "issues",
}


def main() -> None:
    mode = os.environ.get("TUTOR_CONTENT_MODE")
    quality = json.loads(CORE_QUALITY.read_text(encoding="utf-8")) if CORE_QUALITY.exists() else {}
    if mode != "structured_model_generated" or quality.get("status") != "PASS":
        report = {
            "status": "WARN",
            "reason": "structured_model_generated_content_not_ready",
            "mode": mode,
            "core_quality_status": quality.get("status"),
            "website_ready_rate": quality.get("website_ready_rate"),
            "template_fallback_used": False,
        }
    else:
        service = TutorLMService()
        returned = service.list_structured_model_outputs()
        tasks = {item.get("task_type") for item in returned}
        required_task_checks = {
            "explanation": service.get_structured_model_output(task_type="explanation"),
            "mcq": service.get_structured_model_output(task_type="mcq"),
            "debug_task": service.get_structured_model_output(task_type="debug_task"),
            "flashcard": service.get_structured_model_output(task_type="flashcard"),
            "mindmap": service.get_structured_model_output(task_type="mindmap"),
            "hint": service.get_structured_model_output(task_type="hint"),
            "revision_summary": service.get_structured_model_output(task_type="revision_summary"),
        }
        missing_field_count = sum(1 for item in returned if not REQUIRED.issubset(item))
        source_ok = all(
            item.get("generation_source") == "cognitutor_lm_from_scratch_structured_model"
            for item in returned
        )
        required_task_status = all(item.get("status") == "success" for item in required_task_checks.values())
        report = {
            "status": "PASS"
            if quality.get("website_ready_rate", 0) >= 0.85
            and missing_field_count == 0
            and source_ok
            and required_task_status
            else "WARN",
            "website_ready_rate": quality.get("website_ready_rate"),
            "template_fallback_used": False,
            "has_explanation": "explanation" in tasks,
            "has_mcq": "mcq" in tasks,
            "has_debug_task": "debug_task" in tasks,
            "has_flashcard": "flashcard" in tasks,
            "has_mindmap": "mindmap" in tasks,
            "has_hint_or_revision": bool({"hint", "revision_summary"} & tasks),
            "missing_field_count": missing_field_count,
            "source_ok": source_ok,
            "required_task_status": required_task_status,
            "sample_count": len(returned),
            "service_mode": service.content_mode,
        }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Structured Model Website Mode Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n", encoding="utf-8")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
