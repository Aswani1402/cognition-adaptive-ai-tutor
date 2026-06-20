from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt

from scripts.evaluation.check_puzzle_assessment_report import build_report, write_reports


CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/puzzle_assessment_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/puzzle_assessment_visualization_report.md")


def _bar_chart(labels: list[str], values: list[float], title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _histogram(values: list[float], title: str, xlabel: str, path: Path) -> None:
    plt.figure(figsize=(7, 4.5))
    plt.hist(values, bins=5)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def build_visualization_report() -> dict:
    report = build_report()
    write_reports(report)
    results = report["evaluator_test_cases"]
    type_counts = Counter(result["puzzle_type"] for result in results)
    label_counts = Counter(result["label"] for result in results)
    scores = [float(result["score"]) for result in results]
    component_coverage = {
        puzzle_type: 1
        for puzzle_type in report["frontend_components_mapped"]
        if puzzle_type not in report["missing_or_mismatched_components"]
    }

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "puzzle_type_distribution": CHART_DIR / "puzzle_type_distribution.png",
        "puzzle_score_distribution": CHART_DIR / "puzzle_score_distribution.png",
        "puzzle_label_distribution": CHART_DIR / "puzzle_label_distribution.png",
        "puzzle_frontend_component_coverage": CHART_DIR / "puzzle_frontend_component_coverage.png",
    }
    _bar_chart(list(type_counts), list(type_counts.values()), "Puzzle Type Distribution", "Count", charts["puzzle_type_distribution"])
    _histogram(scores, "Puzzle Score Distribution", "Score", charts["puzzle_score_distribution"])
    _bar_chart(list(label_counts), list(label_counts.values()), "Puzzle Label Distribution", "Count", charts["puzzle_label_distribution"])
    _bar_chart(
        list(component_coverage),
        list(component_coverage.values()),
        "Puzzle Frontend Component Coverage",
        "Mapped",
        charts["puzzle_frontend_component_coverage"],
    )
    status = "success" if all(path.exists() for path in charts.values()) else "warning"
    return {
        "status": status,
        "module": "puzzle_assessment_visualization_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chart_paths": {key: str(path) for key, path in charts.items()},
        "chart_count": sum(1 for path in charts.values() if path.exists()),
        "source_report": "evaluation_outputs/json/puzzle_assessment_report.json",
    }


def write_visualization_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Puzzle Assessment Visualization Report",
        "",
        f"Status: `{report['status']}`",
        "",
        f"Chart count: `{report['chart_count']}`",
        "",
        "## Charts",
        "",
        *[f"- `{name}`: {path}" for name, path in report["chart_paths"].items()],
        "",
    ]
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_visualization_report()
    write_visualization_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: puzzle_assessment_visualization_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
