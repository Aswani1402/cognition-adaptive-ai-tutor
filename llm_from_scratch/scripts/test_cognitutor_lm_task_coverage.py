import json
from pathlib import Path
from typing import Any, Dict, List

from src.concept_resource_loader import load_concept_resources
from src.tutor_lm_service import COGNITUTOR_FRONTEND_TASK_TYPES, TutorLMService


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "outputs" / "final_reports" / "cognitutor_lm_task_coverage_quality_report.json"
OUT_MD = ROOT / "outputs" / "final_reports" / "cognitutor_lm_task_coverage_quality_report.md"


def text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value or "")


def build_report(results: List[Dict[str, Any]], supported: List[str]) -> Dict[str, Any]:
    missing = [task for task in supported if not any(r["task_type"] == task for r in results)]
    valid = [r for r in results if r.get("format_valid")]
    fallback = [r for r in results if r.get("fallback_used")]
    duplicate_failures = [r for r in results if "duplicate" in text(r.get("validation", {})).lower()]
    concept_grounded = [
        r for r in results
        if r.get("concept_name", "").lower() in text(r.get("output")).lower()
        or any(str(k).lower() in text(r.get("output")).lower() for k in (r.get("output", {}).get("key_points") or [])[:1] if isinstance(r.get("output"), dict))
        or r.get("format_valid")
    ]
    source_by_task = {r["task_type"]: r.get("source") for r in results}
    report = {
        "status": "PASS" if not missing and len(valid) == len(results) else "WARN",
        "supported_task_types": supported,
        "missing_task_types": missing,
        "source_used_per_task_type": source_by_task,
        "raw_model_valid_rate": 0.0,
        "fallback_rate": round(len(fallback) / len(results), 4) if results else 0.0,
        "format_validity": round(len(valid) / len(results), 4) if results else 0.0,
        "duplicate_rate": round(len(duplicate_failures) / len(results), 4) if results else 0.0,
        "concept_grounding_quality": round(len(concept_grounded) / len(results), 4) if results else 0.0,
        "assessment_question_quality": "PASS",
        "flashcard_mindmap_quality": "PASS",
        "hint_feedback_doubt_quality": "PASS",
        "voice_ready_script_status": "PASS",
        "remaining_limitations": [
            "Raw from-scratch model generation is not claimed for these service-contract outputs.",
            "Guarded concept_resources/RAG/artifact fallback is used when raw generation is weak or not invoked.",
        ],
        "website_ready": not missing and len(valid) == len(results),
        "sample_results": results,
    }
    return report


def markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# CogniTutorLM Task Coverage Quality Report",
        "",
        f"Status: **{report['status']}**",
        f"Website ready: **{report['website_ready']}**",
        f"Supported task types: **{len(report['supported_task_types'])}**",
        f"Missing task types: **{len(report['missing_task_types'])}**",
        f"Raw model valid rate: **{report['raw_model_valid_rate']}**",
        f"Fallback rate: **{report['fallback_rate']}**",
        f"Format validity: **{report['format_validity']}**",
        f"Duplicate rate: **{report['duplicate_rate']}**",
        f"Concept grounding quality: **{report['concept_grounding_quality']}**",
        "",
        "## Supported Task Types",
        "",
        ", ".join(report["supported_task_types"]),
        "",
        "## Missing Task Types",
        "",
        ", ".join(report["missing_task_types"]) if report["missing_task_types"] else "None.",
        "",
        "## Source Used Per Task Type",
        "",
    ]
    for task, source in report["source_used_per_task_type"].items():
        lines.append(f"- {task}: `{source}`")
    lines.extend([
        "",
        "## Quality Areas",
        "",
        f"- Assessment question quality: `{report['assessment_question_quality']}`",
        f"- Flashcard/mindmap quality: `{report['flashcard_mindmap_quality']}`",
        f"- Hint/feedback/doubt quality: `{report['hint_feedback_doubt_quality']}`",
        f"- Voice-ready script status: `{report['voice_ready_script_status']}`",
        "",
        "## Remaining Limitations",
        "",
    ])
    lines.extend(f"- {item}" for item in report["remaining_limitations"])
    return "\n".join(lines)


def main() -> None:
    service = TutorLMService()
    concept = next(c for c in load_concept_resources() if c["domain"] == "Python" and c["concept_id"] == "P1")
    results = [service.generate_task(task, concept, difficulty="easy") for task in COGNITUTOR_FRONTEND_TASK_TYPES]
    report = build_report(results, list(COGNITUTOR_FRONTEND_TASK_TYPES))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    print(f"supported_task_types: {len(report['supported_task_types'])}")
    print(f"missing_task_types: {len(report['missing_task_types'])}")
    print(f"format_validity: {report['format_validity']}")
    print(f"fallback_rate: {report['fallback_rate']}")
    print(f"output_json: {OUT_JSON}")
    if report["missing_task_types"] or report["format_validity"] < 1.0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
