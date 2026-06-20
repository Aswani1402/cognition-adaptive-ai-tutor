from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from tutor.generation.cognitutor_lm_connector import (
    get_cognitutor_all_task_outputs,
    get_cognitutor_api_service,
    get_cognitutor_audio_overview,
    get_cognitutor_notebook_packet,
    get_cognitutor_session_packet,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation_outputs" / "final_evaluation"
JSON_OUT = OUT / "json" / "cognitutor_backend_bridge_final_evaluation.json"
MD_OUT = OUT / "reports" / "cognitutor_backend_bridge_final_evaluation.md"
CSV_OUT = OUT / "csv" / "cognitutor_backend_bridge_cases.csv"

CASES = [
    ("Python", "Variables"),
    ("SQL", "JOIN Operations"),
    ("HTML", "Forms and Inputs"),
    ("Git", "Branches"),
    ("Data Structures", "Trees"),
]
DIFFICULTIES = ["easy", "medium", "hard", "revision"]
TEACHING_VIEWS = [
    "definition_view", "simple_example_view", "step_by_step_view", "analogy_view",
    "code_view", "debug_view", "output_prediction_view", "misconception_view",
    "transfer_view", "challenge_view", "revision_view", "flashcard_view",
    "mindmap_view", "voice_script_view",
]


def word_count(value: Any) -> int:
    return len(str(value or "").split())


def has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def check_packet(domain: str, concept: str, difficulty: str, view: str) -> dict[str, Any]:
    api = get_cognitutor_api_service()
    packet = api.get_learning_packet(domain, concept_name=concept, difficulty=difficulty, teaching_view=view)
    product_ok = packet.get("status") == "success"
    teaching = packet.get("teaching_content") or {}
    assessments = packet.get("aligned_assessments") or []
    bank = packet.get("assessment_bank") or assessments
    checks = {
        "packet_status_success": product_ok,
        "teaching_content_exists": isinstance(teaching, dict) and bool(teaching),
        "beginner_explanation_gt_50_words": word_count(teaching.get("beginner_explanation")) > 50 if teaching else False,
        "aligned_assessments_exists": bool(assessments),
        "assessment_bank_count_ge_5": len(bank) >= 5,
        "source_level_exists": has_text(packet.get("source_level")),
        "difficulty_exists": has_text(packet.get("difficulty")),
        "teaching_view_exists": has_text(packet.get("teaching_view")),
        "frontend_ready_true": packet.get("frontend_ready") is True or packet.get("website_ready") is True,
    }
    status = "PASS" if all(checks.values()) else "WARN"
    return {
        "scope": "view",
        "domain": domain,
        "concept": concept,
        "difficulty": difficulty,
        "teaching_view": view,
        "status": status,
        "assessment_bank_count": len(bank),
        "beginner_explanation_words": word_count(teaching.get("beginner_explanation")) if teaching else 0,
        "checks": checks,
    }


def check_concept(domain: str, concept: str) -> dict[str, Any]:
    packet = get_cognitutor_session_packet(domain, concept, learner_id="demo_learner_001", difficulty="easy", teaching_view="definition_view")
    tasks = get_cognitutor_all_task_outputs(domain, concept_name=concept)
    notebook = get_cognitutor_notebook_packet(domain, concept_name=concept, learner_state={"learner_id": "demo_learner_001"})
    audio = get_cognitutor_audio_overview(domain, concept_name=concept, learner_state={"difficulty": "easy", "teaching_view": "definition_view"})
    task_rows = tasks.get("tasks", []) if isinstance(tasks, dict) else []
    checks = {
        "product_packet_success": packet.get("status") == "success",
        "assessment_bank_count_ge_17": len(packet.get("assessment_bank") or []) >= 17,
        "flashcards_count_ge_7": len(packet.get("flashcards") or []) >= 7,
        "mindmap_exists": bool(packet.get("mindmap") or packet.get("mindmaps")),
        "notebook_exists": notebook.get("status") == "success" or bool(packet.get("notebook")),
        "voice_audio_overview_exists": audio.get("status") == "success" or bool(packet.get("audio_overview") or packet.get("voice_script")),
        "all_task_count_89": len(task_rows) == 89 or packet.get("all_task_count") == 89,
        "frontend_ready_true": packet.get("frontend_ready") is True,
    }
    status = "PASS" if all(checks.values()) else ("WARN" if checks["product_packet_success"] else "FAIL")
    return {
        "scope": "concept",
        "domain": domain,
        "concept": concept,
        "difficulty": "all",
        "teaching_view": "product_packet",
        "status": status,
        "assessment_bank_count": len(packet.get("assessment_bank") or []),
        "flashcard_count": len(packet.get("flashcards") or []),
        "all_task_count": len(task_rows) or packet.get("all_task_count"),
        "checks": checks,
    }


def main() -> None:
    for directory in [OUT / "json", OUT / "reports", OUT / "csv"]:
        directory.mkdir(parents=True, exist_ok=True)
    case_reports = []
    for domain, concept in CASES:
        case_reports.append(check_concept(domain, concept))
        for difficulty in DIFFICULTIES:
            for view in TEACHING_VIEWS:
                case_reports.append(check_packet(domain, concept, difficulty, view))

    failures = [c for c in case_reports if c["scope"] == "concept" and c["status"] == "FAIL"]
    warnings = [c for c in case_reports if c["status"] == "WARN"]
    status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    report = {
        "evaluation_name": "cognitutor_backend_bridge_final_evaluation",
        "status": status,
        "case_count": len(case_reports),
        "passed": sum(1 for c in case_reports if c["status"] == "PASS"),
        "warned": len(warnings),
        "failed": len(failures),
        "warning_cases": [f"{c['domain']} / {c['concept']} / {c['difficulty']} / {c['teaching_view']}" for c in warnings],
        "failed_cases": [f"{c['domain']} / {c['concept']} / {c['difficulty']} / {c['teaching_view']}" for c in failures],
        "status_rule": "PASS if all sample cases pass; WARN if optional route/data is missing but core product packet works; FAIL if connector cannot return product packet.",
        "cases": case_reports,
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["scope", "domain", "concept", "difficulty", "teaching_view", "status", "assessment_bank_count"])
        writer.writeheader()
        for row in case_reports:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
    MD_OUT.write_text(
        "\n".join([
            "# CogniTutor Backend Bridge Final Evaluation",
            "",
            f"- status: {status}",
            f"- case_count: {len(case_reports)}",
            f"- passed: {report['passed']}",
            f"- warned: {len(warnings)}",
            f"- failed: {len(failures)}",
            f"- failed_cases: {report['failed_cases']}",
            f"- warning_cases: {report['warning_cases'][:20]}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "json": str(JSON_OUT)}, indent=2))


if __name__ == "__main__":
    main()
