from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


SOURCE_REPORT = Path("evaluation_outputs/json/generation_service_comparison_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/generation_comparison_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/generation_comparison_visualization_report.md")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_report() -> dict:
    if not SOURCE_REPORT.exists():
        from scripts.evaluation.check_generation_service_comparison import build_report, write_reports

        report = build_report()
        write_reports(report)
        return report
    return _load_json(SOURCE_REPORT)


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _bar(metric_table: dict, metric: str, title: str, ylabel: str, path: Path) -> None:
    services = list(metric_table.keys())
    values = [float(metric_table[service].get(metric, 0.0)) for service in services]
    plt.figure(figsize=(9, 4.5))
    plt.bar(services, values)
    plt.xticks(rotation=25, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    _save(path)


def generate_charts() -> dict:
    report = _ensure_report()
    metric_table = report.get("metric_comparison_table", {})
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}

    path = CHART_DIR / "generation_service_quality_comparison.png"
    _bar(metric_table, "avg_quality_score", "Generation Service Quality Comparison", "Average quality score", path)
    charts["generation_service_quality_comparison"] = str(path)

    path = CHART_DIR / "generation_service_grounding_comparison.png"
    _bar(metric_table, "avg_grounding_score", "Generation Service Grounding Comparison", "Average grounding score", path)
    charts["generation_service_grounding_comparison"] = str(path)

    path = CHART_DIR / "generation_service_latency_comparison.png"
    _bar(metric_table, "avg_latency_ms", "Generation Service Latency Comparison", "Average latency ms", path)
    charts["generation_service_latency_comparison"] = str(path)

    path = CHART_DIR / "generation_service_task_coverage.png"
    _bar(metric_table, "task_coverage", "Generation Service Task Coverage", "Task coverage", path)
    charts["generation_service_task_coverage"] = str(path)

    path = CHART_DIR / "generation_service_fallback_rate.png"
    _bar(metric_table, "fallback_rate", "Generation Service Fallback Rate", "Fallback rate", path)
    charts["generation_service_fallback_rate"] = str(path)

    visualization = {
        "status": "success" if charts else "warning",
        "module": "generation_comparison_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_report": str(SOURCE_REPORT),
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Generation Comparison Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: generation_comparison_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
