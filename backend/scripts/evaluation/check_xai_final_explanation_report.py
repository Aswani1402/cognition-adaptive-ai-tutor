from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once
from tutor.xai.xai_dashboard_builder import CORE_MODULES, XAIDashboardBuilder


JSON_REPORT = Path("evaluation_outputs/json/xai_final_explanation_report.json")
MD_REPORT = Path("evaluation_outputs/reports/xai_final_explanation_report.md")

SOURCE_REPORTS = {
    "xai_model_explanation_report": Path("evaluation_outputs/json/xai_model_explanation_report.json"),
    "agentic_orchestration_report": Path("evaluation_outputs/json/agentic_orchestration_report.json"),
    "kt_full_model_comparison_report": Path("evaluation_outputs/json/kt_full_model_comparison_report.json"),
    "behaviour_full_model_comparison_report": Path("evaluation_outputs/json/behaviour_full_model_comparison_report.json"),
    "semantic_evaluator_report": Path("evaluation_outputs/json/semantic_evaluator_report.json"),
    "doubt_classifier_report": Path("evaluation_outputs/json/doubt_classifier_report.json"),
    "rag_grounding_report": Path("evaluation_outputs/json/rag_grounding_report.json"),
    "rl_model_comparison_report": Path("evaluation_outputs/json/rl_model_comparison_report.json"),
    "notebook_memory_revision_report": Path("evaluation_outputs/json/notebook_memory_revision_report.json"),
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summaries() -> dict[str, Any]:
    return {
        name: {
            "path": str(path),
            "loaded": bool(_load_json(path)),
        }
        for name, path in SOURCE_REPORTS.items()
    }


def build_report() -> dict[str, Any]:
    summaries = _summaries()
    integrated_output = run_integrated_tutor_once(
        learner_id="14",
        reward_dry_run=True,
    )
    dashboard = XAIDashboardBuilder().build(
        integrated_output=integrated_output,
        learner_id="14",
        latest_report_summaries=summaries,
    )
    cards = dashboard.get("cards", {})
    quality = dashboard.get("explanation_quality", {})
    coverage = dashboard.get("evidence_coverage", {})
    loaded_sources = [name for name, item in summaries.items() if item.get("loaded")]

    metrics = {
        "card_count": len(cards),
        "evidence_source_count": coverage.get("evidence_source_count", 0),
        "top_factor_count": len(dashboard.get("top_factors", [])),
        "counterfactual_count": len(dashboard.get("counterfactuals", [])),
        "evidence_coverage_rate": coverage.get("evidence_coverage_rate", 0.0),
        "explanation_completeness_score": quality.get("explanation_completeness_score", 0.0),
        "missing_evidence_count": coverage.get("missing_evidence_count", len(CORE_MODULES)),
    }
    status = "success" if metrics["card_count"] >= 9 and metrics["top_factor_count"] > 0 else "warning"

    report = {
        "status": status,
        "module": "xai_final_explanation_report",
        "generated_at": _now_iso(),
        "evidence_sources_loaded": summaries,
        "loaded_source_count": len(loaded_sources),
        "dashboard_card_availability": {name: bool(value) for name, value in cards.items()},
        "top_factor_coverage": dashboard.get("top_factors", []),
        "explanation_quality_score": quality,
        "counterfactual_availability": {
            "available": bool(dashboard.get("counterfactuals")),
            "counterfactuals": dashboard.get("counterfactuals", []),
        },
        "learner_facing_explanation_example": cards.get("decision_reason_card", {}).get("explanation"),
        "teacher_facing_explanation_example": cards.get("teacher_evidence_card", {}),
        "module_coverage": coverage.get("module_coverage", {}),
        "metrics": metrics,
        "dashboard": dashboard,
        "limitations": [
            "Dashboard explanations use transparent normalized evidence scoring, not SHAP attribution.",
            "Some optional modules may be absent in dry-run output and are reported as missing evidence.",
            "Contribution calibration should be revisited after collecting production learner outcomes.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    metrics = report["metrics"]
    lines = [
        "# XAI Final Explanation Report",
        "",
        "## Status",
        "",
        f"Status: **{report['status']}**",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Evidence Sources Loaded",
        "",
    ]
    for name, item in report["evidence_sources_loaded"].items():
        lines.append(f"- {name}: {'loaded' if item['loaded'] else 'missing'}")
    lines.extend(
        [
            "",
            "## Dashboard Card Availability",
            "",
        ]
    )
    for name, available in report["dashboard_card_availability"].items():
        lines.append(f"- {name}: {available}")
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            f"- Card count: {metrics['card_count']}",
            f"- Evidence source count: {metrics['evidence_source_count']}",
            f"- Top factor count: {metrics['top_factor_count']}",
            f"- Counterfactual count: {metrics['counterfactual_count']}",
            f"- Evidence coverage rate: {metrics['evidence_coverage_rate']}",
            f"- Explanation completeness score: {metrics['explanation_completeness_score']}",
            f"- Missing evidence count: {metrics['missing_evidence_count']}",
            "",
            "## Learner-Facing Explanation Example",
            "",
            str(report.get("learner_facing_explanation_example")),
            "",
            "## Teacher-Facing Explanation Example",
            "",
            "```json",
            json.dumps(report.get("teacher_facing_explanation_example"), indent=2, default=str),
            "```",
            "",
            "## Module Coverage",
            "",
        ]
    )
    for name, available in report["module_coverage"].items():
        lines.append(f"- {name}: {available}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: xai_final_explanation_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
