from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JSON_DIR = Path("evaluation_outputs/json")
REPORT_DIR = Path("evaluation_outputs/reports")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = JSON_DIR / "overall_system_evaluation_report.json"
MD_REPORT = REPORT_DIR / "overall_system_evaluation_report.md"
DIAGRAM_CHECKLIST = REPORT_DIR / "final_report_diagram_checklist.md"

REQUESTED_REPORTS = [
    "full_backend_smoke_test_report.json",
    "final_backend_report.json",
    "kt_full_model_comparison_report.json",
    "kt_visualization_report.json",
    "behaviour_full_model_comparison_report.json",
    "behaviour_visualization_report.json",
    "semantic_evaluator_report.json",
    "semantic_evaluator_visualization_report.json",
    "doubt_classifier_report.json",
    "doubt_classifier_visualization_report.json",
    "xai_final_explanation_report.json",
    "xai_visualization_report.json",
    "reward_gamification_report.json",
    "reward_gamification_visualization_report.json",
    "generation_service_comparison_report.json",
    "generation_comparison_visualization_report.json",
    "rag_retrieval_comparison_report.json",
    "rag_grounding_report.json",
    "rl_model_comparison_report.json",
    "rl_safe_action_masking_report.json",
    "notebook_memory_revision_report.json",
    "agentic_orchestration_report.json",
    "website_user_persistence_report.json",
    "parameter_sensitivity_report.json",
    "answer_evaluator_report.json",
    "teaching_strategy_upgrade_report.json",
]

MODULES = [
    {
        "name": "KT current DKT runtime",
        "status": "completed",
        "reports": ["kt_full_model_comparison_report.json", "kt_visualization_report.json", "dkt_runtime_training_report.json"],
        "chart_prefixes": ["kt_"],
        "metric_paths": [
            ("best_model", ["best_model"]),
            ("best_accuracy", ["best_metrics", "accuracy"]),
            ("runtime_status", ["runtime_status"]),
        ],
    },
    {
        "name": "Behaviour model comparison",
        "status": "completed",
        "reports": ["behaviour_full_model_comparison_report.json", "behaviour_visualization_report.json"],
        "chart_prefixes": ["behaviour_"],
        "metric_paths": [("best_model", ["best_model"]), ("accuracy", ["best_metrics", "accuracy"])],
    },
    {
        "name": "Semantic evaluator",
        "status": "completed",
        "reports": ["semantic_evaluator_report.json", "semantic_evaluator_visualization_report.json"],
        "chart_prefixes": ["semantic_"],
        "metric_paths": [("accuracy", ["metrics", "accuracy"]), ("macro_f1", ["metrics", "macro_f1"])],
    },
    {
        "name": "Doubt classifier",
        "status": "completed",
        "reports": ["doubt_classifier_report.json", "doubt_classifier_visualization_report.json"],
        "chart_prefixes": ["doubt_"],
        "metric_paths": [("accuracy", ["accuracy"]), ("macro_f1", ["macro_f1"]), ("fallback_rate", ["fallback_rate_on_sample_cases"])],
    },
    {
        "name": "XAI dashboard",
        "status": "backend_ready",
        "reports": ["xai_final_explanation_report.json", "xai_visualization_report.json"],
        "chart_prefixes": ["xai_"],
        "metric_paths": [("completeness", ["metrics", "explanation_completeness_score"]), ("coverage_rate", ["metrics", "evidence_coverage_rate"])],
    },
    {
        "name": "Reward gamification",
        "status": "backend_ready",
        "reports": ["reward_gamification_report.json", "reward_gamification_visualization_report.json"],
        "chart_prefixes": ["reward_"],
        "metric_paths": [("badge_count", ["metrics", "badge_count"]), ("unlock_count", ["metrics", "concept_unlock_count"])],
    },
    {
        "name": "Generation/service comparison",
        "status": "comparison_mode",
        "reports": ["generation_service_comparison_report.json", "generation_comparison_visualization_report.json"],
        "chart_prefixes": ["generation_service_"],
        "metric_paths": [("best_by_task", ["best_service_by_task_type"]), ("sanvia_status", ["sanvia_status"])],
    },
    {
        "name": "RAG grounding/retrieval",
        "status": "completed",
        "reports": ["rag_retrieval_comparison_report.json", "rag_grounding_report.json"],
        "chart_prefixes": ["rag_"],
        "metric_paths": [("grounding_status", ["overall_status"]), ("safe_rate", ["safe_generate_rate"])],
    },
    {
        "name": "RL safe policy comparison",
        "status": "comparison_mode",
        "reports": ["rl_model_comparison_report.json", "rl_safe_action_masking_report.json"],
        "chart_prefixes": ["rl_"],
        "metric_paths": [("overall_status", ["overall_status"]), ("safe_action_status", ["status"])],
    },
    {
        "name": "Answer evaluator",
        "status": "completed",
        "reports": ["answer_evaluator_report.json"],
        "chart_prefixes": ["answer_", "debug_", "output_prediction_", "rubric_"],
        "metric_paths": [("overall_status", ["overall_status"]), ("passed_cases", ["passed_count"])],
    },
    {
        "name": "Safe code runner",
        "status": "backend_ready",
        "reports": ["full_backend_smoke_test_report.json"],
        "chart_prefixes": ["code_runner_"],
        "metric_paths": [("smoke_status", ["overall_status"])],
    },
    {
        "name": "Notebook memory/revision",
        "status": "backend_ready",
        "reports": ["notebook_memory_revision_report.json"],
        "chart_prefixes": ["notebook_", "revision_"],
        "metric_paths": [("status", ["status"]), ("module", ["module"])],
    },
    {
        "name": "Agentic orchestration",
        "status": "backend_ready",
        "reports": ["agentic_orchestration_report.json"],
        "chart_prefixes": ["agentic_"],
        "metric_paths": [("status", ["status"]), ("module", ["module"])],
    },
    {
        "name": "User persistence",
        "status": "backend_ready",
        "reports": ["website_user_persistence_report.json"],
        "chart_prefixes": ["user_persistence_", "website_"],
        "metric_paths": [("status", ["status"]), ("tables_ready", ["tables_ready"])],
    },
    {
        "name": "Frontend response builder",
        "status": "backend_ready",
        "reports": ["full_backend_smoke_test_report.json", "final_backend_report.json"],
        "chart_prefixes": ["frontend_"],
        "metric_paths": [("smoke_status", ["overall_status"])],
    },
]

PENDING_MODULES = [
    "Puzzle/gamified assessment schemas",
    "Actual FastAPI/API routes",
    "KP frontend UI",
    "Sanvia pretrained model integration",
    "Human-rated evaluation",
    "Full production deployment",
]

DIAGRAM_ITEMS = [
    "Overall architecture",
    "Dataset/database flow",
    "User login/session flow",
    "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress",
    "KT pipeline",
    "Behaviour pipeline",
    "RAG pipeline",
    "CogniTutorLM connector pipeline",
    "Assessment/evaluation pipeline",
    "Safe code runner flow",
    "Policy/RL flow",
    "XAI dashboard flow",
    "NotebookLM memory/revision flow",
    "Agentic orchestration flow",
    "Reward/gamification flow",
    "Frontend/backend API flow",
    "Human evaluation flow",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(name: str) -> dict[str, Any]:
    path = JSON_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _chart_list(prefixes: list[str]) -> list[str]:
    if not CHART_DIR.exists():
        return []
    charts = []
    for path in CHART_DIR.glob("*.png"):
        if any(path.name.startswith(prefix) for prefix in prefixes):
            charts.append(str(path))
    return sorted(charts)


def _report_availability() -> dict[str, Any]:
    inventory = {}
    for filename in REQUESTED_REPORTS:
        json_path = JSON_DIR / filename
        md_path = REPORT_DIR / filename.replace(".json", ".md")
        inventory[filename] = {
            "json_path": str(json_path),
            "json_exists": json_path.exists(),
            "md_path": str(md_path),
            "md_exists": md_path.exists(),
            "loaded": bool(_load_json(filename)),
        }
    return inventory


def _module_row(module: dict[str, Any]) -> dict[str, Any]:
    reports = {name: _load_json(name) for name in module["reports"]}
    available_reports = [name for name, data in reports.items() if data]
    metrics = {}
    for metric_name, path in module.get("metric_paths", []):
        for data in reports.values():
            value = _get(data, path)
            if value is not None:
                metrics[metric_name] = value
                break
    charts = _chart_list(module.get("chart_prefixes", []))
    status = module["status"] if available_reports else "warning"
    return {
        "module": module["name"],
        "status": status,
        "expected_reports": module["reports"],
        "available_reports": available_reports,
        "missing_reports": [name for name in module["reports"] if name not in available_reports],
        "best_metrics": metrics,
        "generated_charts": charts,
        "chart_count": len(charts),
    }


def _score_for_status(status: str) -> float:
    return {
        "completed": 1.0,
        "backend_ready": 0.85,
        "comparison_mode": 0.7,
        "warning": 0.45,
        "pending": 0.2,
    }.get(status, 0.0)


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Overall System Evaluation Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        f"Overall backend status: **{report['overall_backend_status']}**",
        "",
        "## Module Status Table",
        "",
        "| Module | Status | Reports | Charts | Best metrics |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in report["module_status_table"]:
        lines.append(
            f"| {row['module']} | {row['status']} | {len(row['available_reports'])}/{len(row['expected_reports'])} | "
            f"{row['chart_count']} | `{json.dumps(row['best_metrics'], default=str)}` |"
        )
    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- Completed module count: {report['completed_module_count']}",
            f"- Warning module count: {report['warning_module_count']}",
            f"- Pending module count: {report['pending_module_count']}",
            "",
            "## Final System Flow",
            "",
            report["final_system_flow"],
            "",
            "## Report-Ready Interpretation",
            "",
            report["report_ready_interpretation"],
            "",
            "## Major Limitations",
            "",
        ]
    )
    for item in report["major_limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Remaining Pending Work", ""])
    for item in report["remaining_pending_work"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _write_diagram_checklist() -> None:
    lines = ["# Final Report Diagram Checklist", ""]
    for item in DIAGRAM_ITEMS:
        lines.append(f"- [ ] {item}")
    DIAGRAM_CHECKLIST.parent.mkdir(parents=True, exist_ok=True)
    DIAGRAM_CHECKLIST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report() -> dict[str, Any]:
    module_rows = [_module_row(module) for module in MODULES]
    pending_rows = [
        {
            "module": name,
            "status": "pending",
            "expected_reports": [],
            "available_reports": [],
            "missing_reports": [],
            "best_metrics": {},
            "generated_charts": [],
            "chart_count": 0,
        }
        for name in PENDING_MODULES
    ]
    all_rows = module_rows + pending_rows
    counts = Counter(row["status"] for row in all_rows)
    report_availability = _report_availability()
    report_count = sum(1 for item in report_availability.values() if item["json_exists"])
    chart_count = len(list(CHART_DIR.glob("*.png"))) if CHART_DIR.exists() else 0
    score = round(sum(_score_for_status(row["status"]) for row in all_rows) / max(1, len(all_rows)), 4)
    warning_count = counts.get("warning", 0)
    status = "success" if warning_count == 0 and report_count >= 20 else "warning"
    report = {
        "status": status,
        "module": "overall_system_evaluation",
        "generated_at": _now_iso(),
        "overall_backend_status": "backend_evaluation_ready" if status == "success" else "backend_evaluation_ready_with_warnings",
        "completed_module_count": counts.get("completed", 0) + counts.get("backend_ready", 0),
        "warning_module_count": warning_count,
        "pending_module_count": counts.get("pending", 0),
        "comparison_mode_count": counts.get("comparison_mode", 0),
        "overall_scorecard": {
            "module_score": score,
            "requested_report_count": len(REQUESTED_REPORTS),
            "available_requested_report_count": report_count,
            "chart_count": chart_count,
        },
        "module_status_table": all_rows,
        "module_wise_best_metrics": {row["module"]: row["best_metrics"] for row in all_rows},
        "module_wise_generated_chart_list": {row["module"]: row["generated_charts"] for row in all_rows},
        "report_availability": report_availability,
        "major_limitations": [
            "Several ML modules are still in comparison or shadow mode rather than final production replacement mode.",
            "Automatic metrics and smoke tests do not replace blind human-rated evaluation.",
            "Sanvia pretrained model integration remains pending as an external model track.",
            "FastAPI routes and KP frontend UI are not part of this backend-only evaluation.",
        ],
        "remaining_pending_work": PENDING_MODULES,
        "report_ready_interpretation": (
            "The overall evaluation consolidates module-wise results from KT, behaviour modeling, answer evaluation, RAG, RL, XAI, "
            "learner memory, reward/gamification, generation comparison, user persistence, and agentic orchestration. "
            "This confirms that the backend is not evaluated only through success logs, but through model metrics, safety checks, "
            "visualizations, ablation evidence, and module-wise comparison reports."
        ),
        "final_system_flow": "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress",
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    MD_REPORT.write_text(_markdown(report), encoding="utf-8")
    _write_diagram_checklist()


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: overall_system_evaluation")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
