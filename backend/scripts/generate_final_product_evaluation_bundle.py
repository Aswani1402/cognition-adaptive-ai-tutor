from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
COGNITUTOR = ROOT / "CogniTutor_LM_from_scratch"
FRONTEND = ROOT / "frontend_ui" / "KP-UI"
OUT = BACKEND / "evaluation_outputs" / "final_evaluation"
JSON_OUT = OUT / "json" / "final_product_evaluation_bundle.json"
MD_OUT = OUT / "reports" / "final_product_evaluation_bundle.md"
COG_JSON_OUT = COGNITUTOR / "outputs" / "final_evaluation" / "json" / "final_product_evaluation_bundle.json"
COG_MD_OUT = COGNITUTOR / "outputs" / "final_evaluation" / "md" / "final_product_evaluation_bundle.md"

SOURCES = {
    "cognitutor_generation": COGNITUTOR / "outputs" / "final_evaluation" / "json" / "cognitutor_generation_final_evaluation.json",
    "level_coverage": COGNITUTOR / "outputs" / "final_evaluation" / "json" / "level_coverage_final_evaluation.json",
    "backend_bridge": BACKEND / "evaluation_outputs" / "final_evaluation" / "json" / "cognitutor_backend_bridge_final_evaluation.json",
    "integrated_tutor": BACKEND / "evaluation_outputs" / "final_evaluation" / "json" / "integrated_tutor_cognitutor_final_evaluation.json",
    "frontend_feature": FRONTEND / "outputs" / "final_evaluation" / "json" / "frontend_feature_final_evaluation.json",
    "frontend_build": FRONTEND / "outputs" / "final_evaluation" / "json" / "frontend_build_final_evaluation.json",
}


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "MANUAL_REQUIRED", "missing_file": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def status_of(report: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = report.get(key)
        if value:
            return str(value).upper()
    return str(report.get("status", "WARN")).upper()


def main() -> None:
    for directory in [OUT / "json", OUT / "reports", COG_JSON_OUT.parent, COG_MD_OUT.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    reports = {name: load(path) for name, path in SOURCES.items()}

    generation_status = "PASS" if (
        reports["cognitutor_generation"].get("all_task_output_count") == 3382
        and reports["cognitutor_generation"].get("expected_all_task_outputs") == 3382
        and reports["cognitutor_generation"].get("missing_task_count") == 0
        and status_of(reports["cognitutor_generation"], "generation_status") == "PASS"
    ) else "FAIL"
    rag_status = status_of(reports["cognitutor_generation"], "rag_status")
    backend_bridge_status = status_of(reports["backend_bridge"])
    integrated_status = status_of(reports["integrated_tutor"])
    frontend_feature_status = status_of(reports["frontend_feature"])
    frontend_build_status = status_of(reports["frontend_build"], "build_status", "status")
    manual_browser_status = "MANUAL_REQUIRED"

    completed = [
        name for name, report in reports.items()
        if not report.get("missing_file") and status_of(report) in {"PASS", "WARN", "FAIL"}
    ]
    pending = [name for name, report in reports.items() if report.get("missing_file")]
    manual_required = ["frontend browser interaction checklist"] if manual_browser_status == "MANUAL_REQUIRED" else []
    warnings = []
    for name, report in reports.items():
        if status_of(report) == "WARN":
            warnings.append(name)
    if manual_browser_status == "MANUAL_REQUIRED":
        warnings.append("manual_browser_verification")

    critical_statuses = [generation_status, rag_status, backend_bridge_status, integrated_status, frontend_build_status]
    if any(status == "FAIL" for status in critical_statuses):
        overall_status = "FAIL"
    elif frontend_feature_status == "WARN" or manual_browser_status == "MANUAL_REQUIRED" or warnings:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    final_report_claim = (
        "production-ready for backend/generation demo use; frontend build-ready with feature verification pending"
        if overall_status != "FAIL"
        else "not demo-ready until failing critical checks are fixed"
    )
    metrics = {
        "concept_count": reports["cognitutor_generation"].get("concept_count"),
        "task_type_count": reports["cognitutor_generation"].get("task_type_count"),
        "all_task_output_count": reports["cognitutor_generation"].get("all_task_output_count"),
        "learning_packet_count": reports["cognitutor_generation"].get("learning_packet_count"),
        "backend_bridge_cases": reports["backend_bridge"].get("case_count"),
        "integrated_product_assessment_count": reports["integrated_tutor"].get("cognitutor_lm_assessment_count"),
        "frontend_feature_status": frontend_feature_status,
        "frontend_build_status": frontend_build_status,
        "manual_browser_verification_status": manual_browser_status,
    }
    bundle = {
        "evaluation_name": "final_product_evaluation_bundle",
        "overall_status": overall_status,
        "final_report_claim": final_report_claim,
        "statuses": {
            "generation_status": generation_status,
            "rag_status": rag_status,
            "backend_bridge_status": backend_bridge_status,
            "integrated_tutor_status": integrated_status,
            "frontend_build_status": frontend_build_status,
            "frontend_feature_status": frontend_feature_status,
            "manual_browser_verification_status": manual_browser_status,
        },
        "completed_evaluations": completed,
        "pending_evaluations": pending,
        "manual_required_checks": manual_required,
        "warnings": warnings,
        "saved_file_paths": {name: str(path) for name, path in SOURCES.items()},
        "metrics": metrics,
        "honest_limitations": [
            "Frontend browser click-through and visual checks are MANUAL_REQUIRED unless separately recorded.",
            "Frontend feature status is based on source/contract evidence, not a live browser run.",
            "No production-ready frontend claim is made while manual browser verification is missing.",
        ],
        "what_can_be_claimed": [
            final_report_claim,
            "CogniTutorLM generation can be claimed PASS only where the final generation metrics are PASS.",
            "Backend bridge/integrated claims are limited to the saved connector and integrated-run outputs.",
        ],
        "what_should_not_be_claimed": [
            "Do not claim fully production-ready end-to-end frontend without browser verification.",
            "Do not claim manual UI buttons passed unless a browser checklist or script output is recorded.",
            "Do not claim new training, external APIs, or pretrained model use.",
        ],
        "source_reports": reports,
    }
    JSON_OUT.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    COG_JSON_OUT.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    lines = [
        "# Final Product Evaluation Bundle",
        "",
        f"- overall_status: {overall_status}",
        f"- final_report_claim: {final_report_claim}",
        "",
        "## Completed Evaluations",
        *[f"- {item}" for item in completed],
        "",
        "## Pending Evaluations",
        *([f"- {item}" for item in pending] or ["- none"]),
        "",
        "## Manual Required Checks",
        *[f"- {item}" for item in manual_required],
        "",
        "## Warnings",
        *([f"- {item}" for item in warnings] or ["- none"]),
        "",
        "## Metrics Table",
        "| Metric | Value |",
        "| --- | --- |",
        *[f"| {key} | {value} |" for key, value in metrics.items()],
        "",
        "## PASS/WARN/FAIL Summary",
        *[f"- {key}: {value}" for key, value in bundle["statuses"].items()],
        "",
        "## Honest Limitations",
        *[f"- {item}" for item in bundle["honest_limitations"]],
        "",
        "## What Can Be Claimed",
        *[f"- {item}" for item in bundle["what_can_be_claimed"]],
        "",
        "## What Should Not Be Claimed",
        *[f"- {item}" for item in bundle["what_should_not_be_claimed"]],
        "",
        "## Saved File Paths",
        *[f"- {name}: {path}" for name, path in bundle["saved_file_paths"].items()],
    ]
    text = "\n".join(lines) + "\n"
    MD_OUT.write_text(text, encoding="utf-8")
    COG_MD_OUT.write_text(text, encoding="utf-8")
    print(json.dumps({"overall_status": overall_status, "json": str(JSON_OUT)}, indent=2))


if __name__ == "__main__":
    main()
