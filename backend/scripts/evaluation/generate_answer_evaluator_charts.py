"""Generate final AnswerEvaluator charts from existing report JSON files."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


JSON_DIR = Path("evaluation_outputs/json")
REPORT_DIR = Path("evaluation_outputs/reports")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = JSON_DIR / "answer_evaluator_visualization_report.json"
MD_REPORT = REPORT_DIR / "answer_evaluator_visualization_report.md"


def load_json(name: str) -> dict[str, Any]:
    path = JSON_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path, rotate: int = 25) -> bool:
    if not labels or not values:
        return False
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotate)
    ax.set_ylim(0, max(1.0, max(values) * 1.15))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    answer = load_json("answer_evaluator_report.json")
    semantic = load_json("semantic_evaluator_report.json")
    benchmark = load_json("semantic_answer_benchmark_report.json")
    created: list[str] = []
    warnings: list[str] = []

    cases = ((answer.get("case_status") or {}).get("cases")) or []
    scores = [float(case.get("score", 0.0) or 0.0) for case in cases]
    if scores:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(scores, bins=min(8, max(3, len(scores))))
        ax.set_title("AnswerEvaluator Score Distribution")
        ax.set_xlabel("Score")
        ax.set_ylabel("Case count")
        fig.tight_layout()
        fig.savefig(CHART_DIR / "answer_evaluator_score_distribution.png")
        plt.close(fig)
        created.append("answer_evaluator_score_distribution.png")
    else:
        warnings.append("AnswerEvaluator case scores were unavailable.")

    labels = Counter(case.get("label", "unknown") for case in cases)
    if not labels:
        labels.update(semantic.get("label_distribution") or benchmark.get("label_distribution") or {})
    if save_bar(list(labels.keys()), [float(v) for v in labels.values()], "AnswerEvaluator Label Distribution", "Case count", CHART_DIR / "answer_evaluator_label_distribution.png"):
        created.append("answer_evaluator_label_distribution.png")
    else:
        warnings.append("AnswerEvaluator label data was unavailable.")

    quality_metrics = {
        "answer_case_success_rate": 0.0,
        "semantic_avg_score": float(semantic.get("average_final_score", 0.0) or 0.0),
        "benchmark_accuracy": float(benchmark.get("accuracy", 0.0) or 0.0),
        "benchmark_weighted_f1": float(benchmark.get("weighted_f1", 0.0) or 0.0),
    }
    if cases:
        quality_metrics["answer_case_success_rate"] = sum(1 for case in cases if case.get("status") == "success") / len(cases)
    if save_bar(list(quality_metrics.keys()), list(quality_metrics.values()), "AnswerEvaluator Quality Summary", "Score", CHART_DIR / "answer_evaluator_quality_summary.png", rotate=35):
        created.append("answer_evaluator_quality_summary.png")
    else:
        warnings.append("AnswerEvaluator quality metrics were unavailable.")

    requested = set(((answer.get("support_status") or {}).get("supported_types_requested")) or [])
    observed = set(((answer.get("support_status") or {}).get("observed_task_types")) or [])
    coverage: dict[str, float] = {task: (1.0 if task in observed else 0.0) for task in sorted(requested)}
    if not coverage and benchmark.get("per_task_accuracy"):
        coverage = {task: float(value or 0.0) for task, value in benchmark["per_task_accuracy"].items()}
    if save_bar(list(coverage.keys()), list(coverage.values()), "AnswerEvaluator Task Coverage", "Coverage / accuracy", CHART_DIR / "answer_evaluator_task_coverage.png", rotate=35):
        created.append("answer_evaluator_task_coverage.png")
    else:
        warnings.append("AnswerEvaluator task coverage data was unavailable.")

    route_scores: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        route_scores[case.get("routed_to", "unknown")].append(float(case.get("score", 0.0) or 0.0))

    status = "success" if len(created) >= 3 and not warnings else "warning"
    report = {
        "status": status,
        "module": "answer_evaluator_visualization_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chart_dir": str(CHART_DIR),
        "charts": created,
        "warnings": warnings,
        "case_count": len(cases),
        "task_coverage_count": len(coverage),
        "route_average_scores": {
            route: round(sum(values) / len(values), 6) for route, values in route_scores.items() if values
        },
        "source_reports": [
            "evaluation_outputs/json/answer_evaluator_report.json",
            "evaluation_outputs/json/semantic_evaluator_report.json",
            "evaluation_outputs/json/semantic_answer_benchmark_report.json",
        ],
    }
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT.write_text(
        "# AnswerEvaluator Visualization Report\n\n"
        f"- Status: {status}\n"
        f"- Charts generated: {len(created)}\n"
        + "\n".join(f"- `{chart}`" for chart in created)
        + ("\n\n## Warnings\n" + "\n".join(f"- {w}" for w in warnings) if warnings else "\n"),
        encoding="utf-8",
    )

    print(f"STATUS: {status}")
    print("MODULE: answer_evaluator_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
