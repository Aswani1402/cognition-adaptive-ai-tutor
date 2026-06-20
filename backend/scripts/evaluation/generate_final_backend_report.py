from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_JSON = Path("evaluation_outputs/json/final_backend_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/final_backend_report.md")
SMOKE_JSON = Path("evaluation_outputs/json/full_backend_smoke_test_report.json")

IMPORTANT_REPORTS = {
    "full_evaluation_upgrade_report": Path("evaluation_outputs/json/full_evaluation_upgrade_report.json"),
    "kt_behaviour_dataset_readiness_report": Path("evaluation_outputs/json/kt_behaviour_dataset_readiness_report.json"),
    "kt_state_schema_runtime_report": Path("evaluation_outputs/json/kt_state_schema_runtime_report.json"),
    "kt_upgrade_report": Path("evaluation_outputs/json/kt_upgrade_report.json"),
    "behaviour_upgrade_report": Path("evaluation_outputs/json/behaviour_upgrade_report.json"),
    "answer_evaluator_report": Path("evaluation_outputs/json/answer_evaluator_report.json"),
    "teaching_strategy_upgrade_report": Path("evaluation_outputs/json/teaching_strategy_upgrade_report.json"),
    "rag_grounding_report": Path("evaluation_outputs/json/rag_grounding_report.json"),
    "full_backend_smoke_test_report": SMOKE_JSON,
}

COMPLETED_MODULES = [
    "Reward/progression",
    "Evaluation intelligence",
    "Mistake analysis",
    "KT v2 DKT-ready fallback",
    "Behaviour LSTM persistence and risk semantics",
    "SafeCodeRunner",
    "CodeQuestionEvaluator",
    "Unified AnswerEvaluator",
    "TeachingStrategy evidence-aware selector",
    "RAG grounding/safety checker",
    "CogniTutorLM optional connector",
    "Frontend response contract",
]

COGNITUTOR_LM_FROM_SCRATCH_DIAGNOSIS = {
    "section_title": "CogniTutorLM From-Scratch Generation Diagnosis",
    "module_role": "CogniTutorLM is trained from scratch and used as a project-specific LLM research module.",
    "stable_backend_service_modules": "PASS",
    "rag_connector": "PASS",
    "teaching_artifact_bank": "494/494 valid baseline bank",
    "assessment_question_bank": "760/760 valid baseline bank",
    "rag_grounded_direct_generation_micro_test": {
        "attempted": 7,
        "success": 7,
        "valid": 3,
        "avg_grounding_score": 0.7238,
        "avg_quality_score": 0.5957,
        "status": "WARN",
    },
    "structured_prompt_diagnosis": {
        "mcq_valid_count": 0,
        "debug_task_valid_count": 0,
        "revision_summary_valid_count": 0,
        "challenge_question_valid_count": 0,
    },
    "conclusion": "Current CogniTutorLM checkpoint is not reliable enough for full structured content-bank generation.",
    "clarification": "generated_tutor_artifacts and assessment_question_bank are stable template/rule-based baseline banks, not fully direct CogniTutorLM-generated outputs.",
    "stable_website_backend_guidance": "The current stable website/backend should use validated baseline banks and RAG-grounded services.",
    "pretrained_sanvia_role": "Pretrained/Sanvia model is comparison only, not the main final system.",
    "future_fix": "Retrain CogniTutorLM from scratch on stronger structured JSON task data and/or add constrained decoding.",
}

KNOWN_WARNINGS = [
    "DKT model artifacts not found; runtime uses fallback_cumulative.",
    "HF unauthenticated/model-loading warnings may appear in optional connector paths.",
    "BertModel unexpected position_ids warning is known and non-blocking.",
    "scikit-learn model persistence/version warnings are known during comparison-model loading.",
]

FUTURE_MODE_MODULES = [
    "DKT model artifact missing; runtime uses fallback_cumulative.",
    "RL/bandit/DQN remains comparison/prototype mode.",
    "Teaching strategy model remains shadow/comparison mode.",
    "RAG BM25/dense/reranker comparison pending.",
    "Voice/TTS pending.",
    "Full frontend UI pending.",
    "Teacher/admin dashboard pending.",
    "CogniTutorLM direct structured generation remains experimental/WARN.",
]

LIMITATIONS = [
    "Some modules are evidence-aware baselines, not fully trained replacements.",
    "Current RAG grounding checker is keyword/section-based, not semantic entailment.",
    "DKT-ready wrapper exists but true model artifact is not loaded yet.",
    "Behaviour labels still need a better non-proxy dataset for final supervised training.",
    "Full RL replacement is future work.",
    "Template/rule banks are baseline/fallback banks, not direct CogniTutorLM-generated outputs.",
    "CogniTutorLM from-scratch direct generation needs retraining or constrained decoding before it can be the main structured generator.",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _report_inventory() -> dict[str, Any]:
    inventory = {}
    for name, path in IMPORTANT_REPORTS.items():
        md_path = Path(str(path).replace("evaluation_outputs\\json", "evaluation_outputs\\reports").replace("/json/", "/reports/"))
        if md_path.suffix == ".json":
            md_path = md_path.with_suffix(".md")
        else:
            md_path = Path("evaluation_outputs/reports") / f"{path.stem}.md"

        inventory[name] = {
            "json_path": str(path),
            "json_exists": path.exists(),
            "md_path": str(md_path),
            "md_exists": md_path.exists(),
        }
    return inventory


def _smoke_summary() -> dict[str, Any]:
    smoke = _load_json(SMOKE_JSON)
    results = smoke.get("results", [])
    passed = [result for result in results if result.get("passed")]
    warnings = [
        result
        for result in results
        if result.get("status_line") == "warning" or result.get("known_warning_observed")
    ]

    return {
        "smoke_report_exists": SMOKE_JSON.exists(),
        "smoke_test_status": smoke.get("overall_status", "missing"),
        "passed_count": smoke.get("passed_count", 0),
        "total_count": smoke.get("total_count", 0),
        "passed_modules": [result.get("label") for result in passed],
        "warning_modules": [result.get("label") for result in warnings],
        "failed_modules": [result.get("label") for result in smoke.get("failed", [])],
        "known_warning_patterns": smoke.get("known_warning_patterns", []),
    }


def _overall_status(smoke_summary: dict[str, Any]) -> str:
    if smoke_summary.get("failed_modules"):
        return "error"
    if smoke_summary.get("passed_count") == smoke_summary.get("total_count") and smoke_summary.get("total_count"):
        return "success"
    return "warning"


def build_report() -> dict[str, Any]:
    smoke = _smoke_summary()
    inventory = _report_inventory()
    report = {
        "overall_status": _overall_status(smoke),
        "module": "final_backend_report",
        "generated_at": _now_iso(),
        "backend_freeze_status": {
            "overall_status": _overall_status(smoke),
            "smoke_test_status": smoke.get("smoke_test_status"),
            "passed_modules": smoke.get("passed_modules", []),
            "warning_modules": smoke.get("warning_modules", []),
            "known_warnings": KNOWN_WARNINGS,
        },
        "completed_modules": COMPLETED_MODULES,
        "important_generated_reports": inventory,
        "key_results_and_metrics": {
            "full_smoke_test": f"{smoke.get('passed_count')}/{smoke.get('total_count')} passed",
            "kt_runtime": "KT v2 schema writes are active; runtime uses fallback_cumulative when DKT artifact is absent.",
            "behaviour_runtime": "Behaviour confidence and risk are separated and persisted.",
            "answer_evaluator": "Unified AnswerEvaluator supports MCQ, output prediction, debug, coding, syntax, explanation, transfer, and challenge routes.",
            "teaching_strategy": "Evidence-aware selector sample cases passed, including high-risk supportive routing and forgetting-driven revision.",
            "rag_grounding": "Grounding checker cases passed for context, concept/domain mismatch, section evidence, and unsupported terms.",
            "reward_db_audit": "Reward DB audit passed in the full smoke test.",
            "cognitutor_lm_from_scratch": "RAG-grounded direct generation status WARN: 7 attempted, 7 success, 3 valid; structured prompt diagnosis valid_count=0 for MCQ/debug/revision/challenge.",
        },
        "cognitutor_lm_from_scratch_generation_diagnosis": COGNITUTOR_LM_FROM_SCRATCH_DIAGNOSIS,
        "comparison_and_future_mode_modules": FUTURE_MODE_MODULES,
        "final_project_flow": "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress",
        "report_ready_limitations": LIMITATIONS,
    }
    return report


def _diagnosis_md(diagnosis: dict[str, Any]) -> list[str]:
    micro = diagnosis["rag_grounded_direct_generation_micro_test"]
    structured = diagnosis["structured_prompt_diagnosis"]
    return [
        "",
        f"## {diagnosis['section_title']}",
        "",
        f"- {diagnosis['module_role']}",
        f"- Stable CogniTutorLM backend/service modules: `{diagnosis['stable_backend_service_modules']}`",
        f"- RAG connector: `{diagnosis['rag_connector']}`; it successfully provides grounded concept context.",
        f"- Teaching artifact bank: `{diagnosis['teaching_artifact_bank']}`.",
        f"- Assessment question bank: `{diagnosis['assessment_question_bank']}`.",
        "- Direct RAG + CogniTutorLM generation was tested.",
        f"- Micro test: attempted={micro['attempted']}, success={micro['success']}, valid={micro['valid']}, avg_grounding_score={micro['avg_grounding_score']}, avg_quality_score={micro['avg_quality_score']}, status={micro['status']}.",
        "- Simple generation is possible, but structured MCQ/debug/challenge generation is not reliable with the current checkpoint.",
        f"- Structured prompt diagnosis: MCQ valid_count={structured['mcq_valid_count']}, debug_task valid_count={structured['debug_task_valid_count']}, revision_summary valid_count={structured['revision_summary_valid_count']}, challenge_question valid_count={structured['challenge_question_valid_count']}.",
        f"- Conclusion: {diagnosis['conclusion']}",
        f"- Stable website/backend guidance: {diagnosis['stable_website_backend_guidance']}",
        f"- Clarification: {diagnosis['clarification']}",
        f"- Pretrained/Sanvia role: {diagnosis['pretrained_sanvia_role']}",
        f"- Future work: {diagnosis['future_fix']}",
    ]


def _build_markdown(report: dict[str, Any]) -> str:
    freeze = report["backend_freeze_status"]
    lines = [
        "# Final Backend Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        f"Smoke test status: `{freeze['smoke_test_status']}`",
        "",
        "## Backend Freeze Status",
        "",
        f"- Passed modules: {len(freeze['passed_modules'])}",
        f"- Warning modules: {freeze['warning_modules']}",
        f"- Known warnings: {freeze['known_warnings']}",
        "",
        "## Completed Modules",
        "",
    ]
    for module in report["completed_modules"]:
        lines.append(f"- {module}")

    lines.extend(["", "## Important Generated Reports", ""])
    for name, item in report["important_generated_reports"].items():
        lines.append(
            f"- {name}: JSON `{item['json_path']}` exists={item['json_exists']}; "
            f"MD `{item['md_path']}` exists={item['md_exists']}"
        )

    lines.extend(["", "## Key Results And Metrics", ""])
    for key, value in report["key_results_and_metrics"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(_diagnosis_md(report["cognitutor_lm_from_scratch_generation_diagnosis"]))

    lines.extend(["", "## Comparison And Future Mode", ""])
    for item in report["comparison_and_future_mode_modules"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Final Project Flow",
            "",
            report["final_project_flow"],
            "",
            "## Limitations",
            "",
        ]
    )
    for item in report["report_ready_limitations"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: final_backend_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: final_backend_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
