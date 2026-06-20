from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


SOURCE_REPORT = Path("evaluation_outputs/json/overall_system_evaluation_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/overall_evaluation_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/overall_evaluation_visualization_report.md")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_report() -> dict:
    if not SOURCE_REPORT.exists():
        from scripts.evaluation.run_overall_system_evaluation import build_report, write_reports

        report = build_report()
        write_reports(report)
        return report
    return _load_json(SOURCE_REPORT)


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path, rotation: int = 30) -> None:
    plt.figure(figsize=(10, 4.8))
    plt.bar(labels, values)
    plt.xticks(rotation=rotation, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    _save(path)


def generate_charts() -> dict:
    report = _ensure_report()
    rows = report.get("module_status_table", [])
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}

    counts = Counter(row.get("status") for row in rows)
    path = CHART_DIR / "module_status_summary.png"
    _bar(list(counts.keys()), list(counts.values()), "Module Status Summary", "Module count", path, rotation=20)
    charts["module_status_summary"] = str(path)

    scorecard = report.get("overall_scorecard", {})
    path = CHART_DIR / "overall_evaluation_scorecard.png"
    _bar(
        ["module_score", "report_availability", "chart_scale"],
        [
            float(scorecard.get("module_score", 0.0)),
            float(scorecard.get("available_requested_report_count", 0)) / max(1.0, float(scorecard.get("requested_report_count", 1))),
            min(1.0, float(scorecard.get("chart_count", 0)) / 30.0),
        ],
        "Overall Evaluation Scorecard",
        "Normalized score",
        path,
        rotation=20,
    )
    charts["overall_evaluation_scorecard"] = str(path)

    availability = report.get("report_availability", {})
    report_labels = [name.replace("_report.json", "").replace(".json", "") for name in availability.keys()]
    report_values = [1 if item.get("json_exists") else 0 for item in availability.values()]
    path = CHART_DIR / "module_report_availability.png"
    _bar(report_labels, report_values, "Module Report Availability", "Available", path, rotation=55)
    charts["module_report_availability"] = str(path)

    module_labels = [row.get("module") for row in rows]
    chart_values = [row.get("chart_count", 0) for row in rows]
    path = CHART_DIR / "module_chart_availability.png"
    _bar(module_labels, chart_values, "Module Chart Availability", "Chart count", path, rotation=55)
    charts["module_chart_availability"] = str(path)

    comparison_rows = [row for row in rows if row.get("status") == "comparison_mode"]
    path = CHART_DIR / "model_comparison_summary.png"
    _bar(
        [row.get("module") for row in comparison_rows] or ["none"],
        [len(row.get("available_reports", [])) for row in comparison_rows] or [0],
        "Model Comparison Summary",
        "Comparison reports",
        path,
        rotation=35,
    )
    charts["model_comparison_summary"] = str(path)

    pending = report.get("remaining_pending_work", [])
    path = CHART_DIR / "remaining_work_summary.png"
    _bar(pending, [1 for _ in pending], "Remaining Work Summary", "Pending", path, rotation=45)
    charts["remaining_work_summary"] = str(path)

    return {
        "status": "success" if charts else "warning",
        "module": "overall_evaluation_charts",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_report": str(SOURCE_REPORT),
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Overall Evaluation Visualization Report",
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
    print("MODULE: overall_evaluation_charts")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
