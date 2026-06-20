"""Create a final inventory of generated evaluation charts.

This script scans evaluation_outputs/charts and prepares a report-handoff
checklist for final writing/Overleaf placement. It does not compute model
decisions; it summarizes existing chart artifacts and flags expected gaps.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/final_chart_inventory_report.json")
MD_REPORT = Path("evaluation_outputs/reports/final_chart_inventory_report.md")


MODULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "KT": {
        "prefixes": ["kt_"],
        "expected": [
            "kt_calibration_curve.png",
            "kt_correctness_distribution.png",
            "kt_loss_curve.png",
            "kt_mastery_distribution.png",
            "kt_model_comparison.png",
            "kt_sequence_length_histogram.png",
        ],
        "section": "Knowledge Tracing Evaluation",
        "caption": "KT charts summarize mastery distribution, sequence coverage, model comparison, training loss, correctness distribution, and calibration.",
    },
    "Behaviour": {
        "prefixes": ["behaviour_"],
        "expected": [
            "behaviour_cluster_distribution.png",
            "behaviour_confusion_matrix.png",
            "behaviour_feature_importance.png",
            "behaviour_feature_summary.png",
            "behaviour_label_distribution.png",
            "behaviour_model_comparison.png",
            "behaviour_risk_distribution.png",
        ],
        "section": "Behaviour Modeling Evaluation",
        "caption": "Behaviour charts show risk labels, model quality, feature evidence, clustering, and learner risk distribution.",
    },
    "Semantic evaluator": {
        "prefixes": ["semantic_"],
        "expected": [
            "semantic_benchmark_confusion_matrix.png",
            "semantic_benchmark_label_distribution.png",
            "semantic_benchmark_per_task_accuracy.png",
            "semantic_benchmark_score_error.png",
            "semantic_component_scores.png",
            "semantic_label_distribution.png",
            "semantic_score_distribution.png",
        ],
        "section": "Answer/Semantic Evaluation",
        "caption": "Semantic evaluator charts report benchmark validity, score distributions, task-level accuracy, label quality, and component score behaviour.",
    },
    "Doubt classifier": {
        "prefixes": ["doubt_"],
        "expected": [
            "doubt_classifier_confusion_matrix.png",
            "doubt_confidence_distribution.png",
            "doubt_intent_distribution.png",
            "doubt_per_class_f1.png",
        ],
        "section": "Learner Doubt Intent Classification",
        "caption": "Doubt classifier charts summarize intent coverage, confusion patterns, per-class F1, and classifier confidence distribution.",
    },
    "XAI": {
        "prefixes": ["xai_"],
        "expected": [
            "xai_counterfactual_summary.png",
            "xai_dashboard_card_availability.png",
            "xai_decision_pressure_distribution.png",
            "xai_feature_contribution_example.png",
            "xai_module_evidence_coverage.png",
            "xai_top_factor_distribution.png",
        ],
        "section": "Explainability and Dashboard Evidence",
        "caption": "XAI charts show factor contributions, decision pressure, counterfactual coverage, module evidence coverage, and dashboard card availability.",
    },
    "Reward/gamification": {
        "prefixes": ["reward_"],
        "expected": [
            "reward_badge_distribution.png",
            "reward_concept_unlock_status.png",
            "reward_daily_goal_progress.png",
            "reward_streak_distribution.png",
            "reward_xp_distribution.png",
        ],
        "section": "Reward, Progression, and Gamification",
        "caption": "Reward charts summarize badge awards, daily goal progress, concept unlock state, XP distribution, and streak evidence.",
    },
    "Generation comparison": {
        "prefixes": ["generation_"],
        "expected": [
            "generation_service_fallback_rate.png",
            "generation_service_grounding_comparison.png",
            "generation_service_latency_comparison.png",
            "generation_service_quality_comparison.png",
            "generation_service_task_coverage.png",
        ],
        "section": "Generation Service Comparison",
        "caption": "Generation charts compare service quality, grounding, latency, task coverage, and fallback behaviour across available generation paths.",
    },
    "Overall evaluation": {
        "prefixes": ["module_", "overall_", "model_comparison_summary", "remaining_work_"],
        "expected": [
            "module_status_summary.png",
            "overall_evaluation_scorecard.png",
            "module_report_availability.png",
            "module_chart_availability.png",
            "model_comparison_summary.png",
            "remaining_work_summary.png",
        ],
        "section": "Overall Backend Evaluation",
        "caption": "Overall charts consolidate module status, report availability, chart coverage, model comparison availability, and remaining work.",
    },
    "Multi-user evaluation": {
        "prefixes": ["multi_user_"],
        "expected": [
            "multi_user_mastery_distribution.png",
            "multi_user_behaviour_risk_distribution.png",
            "multi_user_teaching_view_distribution.png",
            "multi_user_strategy_distribution.png",
            "multi_user_mistake_type_distribution.png",
            "multi_user_reward_xp_distribution.png",
        ],
        "section": "Multi-User Integrated Evaluation",
        "caption": "Multi-user charts demonstrate learner-wise variation in mastery, behaviour risk, selected teaching views, strategy, mistakes, and reward outputs.",
    },
    "RAG": {
        "prefixes": ["rag_"],
        "expected": [
            "rag_retrieval_quality_comparison.png",
            "rag_grounding_score_distribution.png",
            "rag_unsupported_terms_distribution.png",
            "rag_source_coverage.png",
        ],
        "section": "RAG Retrieval and Grounding",
        "caption": "RAG charts should document retrieval quality, grounding score, source coverage, and unsupported-term risk where generated.",
    },
    "RL": {
        "prefixes": ["rl_", "policy_"],
        "expected": [
            "rl_model_comparison.png",
            "rl_safe_action_masking_summary.png",
            "rl_reward_distribution.png",
            "rl_action_distribution.png",
        ],
        "section": "RL/Policy Safety Evaluation",
        "caption": "RL charts should summarize policy comparison, safe action masking, reward distribution, and action coverage where generated.",
    },
    "Answer evaluator": {
        "prefixes": ["answer_"],
        "expected": [
            "answer_evaluator_score_distribution.png",
            "answer_evaluator_label_distribution.png",
            "answer_evaluator_quality_summary.png",
        ],
        "section": "Answer Evaluator",
        "caption": "Answer evaluator charts should summarize score distributions, labels, and quality-readiness where generated separately from the semantic evaluator.",
    },
    "Puzzle / Gamified Assessment": {
        "prefixes": ["puzzle_"],
        "expected": [
            "puzzle_type_distribution.png",
            "puzzle_score_distribution.png",
            "puzzle_label_distribution.png",
            "puzzle_frontend_component_coverage.png",
        ],
        "section": "Puzzle / Gamified Assessment Evaluation",
        "caption": "Puzzle charts summarize supported puzzle activity types, scoring distribution, label quality, and frontend component coverage for gamified assessment.",
    },
}


def ensure_dirs() -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)


def classify_chart(filename: str) -> str:
    for module, definition in MODULE_DEFINITIONS.items():
        for prefix in definition["prefixes"]:
            if filename.startswith(prefix):
                return module
    return "Unclassified"


def detect_duplicate_or_old_warnings(chart_paths: list[Path]) -> list[str]:
    warnings: list[str] = []
    stems: dict[str, list[str]] = defaultdict(list)
    for path in chart_paths:
        normalized = path.stem.lower().replace("_chart", "").replace("_plot", "")
        stems[normalized].append(path.name)

    duplicate_groups = {stem: names for stem, names in stems.items() if len(names) > 1}
    for stem, names in duplicate_groups.items():
        warnings.append(f"Potential duplicate chart group '{stem}': {', '.join(sorted(names))}")

    if chart_paths:
        newest = max(path.stat().st_mtime for path in chart_paths)
        old_paths = [
            path.name
            for path in chart_paths
            if newest - path.stat().st_mtime > 30 * 24 * 60 * 60
        ]
        if old_paths:
            warnings.append(
                "Charts older than 30 days relative to the latest chart: "
                + ", ".join(sorted(old_paths))
            )
    return warnings


def build_report() -> dict[str, Any]:
    chart_paths = sorted(CHART_DIR.glob("*.png")) if CHART_DIR.exists() else []
    charts_by_module: dict[str, list[str]] = {module: [] for module in MODULE_DEFINITIONS}
    charts_by_module["Unclassified"] = []

    for path in chart_paths:
        charts_by_module[classify_chart(path.name)].append(path.name)

    missing_expected: dict[str, list[str]] = {}
    for module, definition in MODULE_DEFINITIONS.items():
        present = set(charts_by_module.get(module, []))
        missing = [name for name in definition["expected"] if name not in present]
        if missing:
            missing_expected[module] = missing

    module_usage = {
        module: {
            "overleaf_section": definition["section"],
            "suggested_caption_usage": definition["caption"],
            "chart_count": len(charts_by_module.get(module, [])),
            "charts": charts_by_module.get(module, []),
        }
        for module, definition in MODULE_DEFINITIONS.items()
    }

    duplicate_old_warnings = detect_duplicate_or_old_warnings(chart_paths)
    status = "warning" if missing_expected or charts_by_module["Unclassified"] else "success"

    return {
        "status": status,
        "module": "final_chart_inventory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chart_dir": str(CHART_DIR),
        "total_chart_count": len(chart_paths),
        "chart_list_by_module": charts_by_module,
        "missing_expected_charts": missing_expected,
        "duplicate_old_charts_warning": duplicate_old_warnings,
        "recommended_overleaf_section_placement": {
            module: definition["section"] for module, definition in MODULE_DEFINITIONS.items()
        },
        "captions_suggested_usage": {
            module: definition["caption"] for module, definition in MODULE_DEFINITIONS.items()
        },
        "module_usage": module_usage,
    }


def write_json(report: dict[str, Any]) -> None:
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_markdown(report: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Final Chart Inventory and Report-Handoff Checklist",
        "",
        f"- Status: {report['status']}",
        f"- Total chart count: {report['total_chart_count']}",
        f"- Chart directory: `{report['chart_dir']}`",
        "",
        "## Chart List by Module",
    ]

    for module, charts in report["chart_list_by_module"].items():
        if module == "Unclassified" and not charts:
            continue
        lines.extend(["", f"### {module}", f"- Chart count: {len(charts)}"])
        if charts:
            lines.extend([f"- `{chart}`" for chart in charts])
        else:
            lines.append("- No charts found.")

    lines.extend(["", "## Missing Expected Charts"])
    if report["missing_expected_charts"]:
        for module, missing in report["missing_expected_charts"].items():
            lines.append(f"- {module}: {', '.join(f'`{name}`' for name in missing)}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Duplicate or Old Chart Warnings"])
    if report["duplicate_old_charts_warning"]:
        lines.extend([f"- {warning}" for warning in report["duplicate_old_charts_warning"]])
    else:
        lines.append("- No duplicate or old chart warnings detected.")

    lines.extend(["", "## Recommended Overleaf Placement and Captions"])
    for module, usage in report["module_usage"].items():
        lines.extend(
            [
                "",
                f"### {module}",
                f"- Section: {usage['overleaf_section']}",
                f"- Suggested usage/caption: {usage['suggested_caption_usage']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Handoff Notes",
            "- Use KT, Behaviour, Semantic, Doubt, RAG, RL, Generation, Reward, XAI, Puzzle, and Multi-user figures in their corresponding evaluation subsections.",
            "- Use Overall evaluation figures in the final evaluation summary chapter.",
            "- Missing RAG/RL/Answer-evaluator charts may be represented by their JSON/Markdown reports if chart scripts were not generated for those modules.",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    report = build_report()
    write_json(report)
    write_markdown(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: final_chart_inventory")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
