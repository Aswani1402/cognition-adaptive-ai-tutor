from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "evaluation_outputs" / "json" / "cognitutor_vs_sanvia_comparison_report.json"
CHART_DIR = ROOT / "evaluation_outputs" / "charts"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "cognitutor_vs_sanvia_visualization_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "cognitutor_vs_sanvia_visualization_report.md"

CHARTS = {
    "quality_score": "llm_comparison_quality.png",
    "grounding_score": "llm_comparison_grounding.png",
    "format_validity": "llm_comparison_format_validity.png",
    "task_success": "llm_comparison_task_success.png",
    "latency_ms": "llm_comparison_latency.png",
    "fallback_rate": "llm_comparison_fallback_rate.png",
}


def _plot_metric(averages: Dict[str, Dict[str, float]], metric: str, output: Path) -> None:
    services = list(averages.keys())
    values = [float(averages[service].get(metric, 0.0) or 0.0) for service in services]
    labels = [service.replace("_", "\n") for service in services]
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title(metric.replace("_", " ").title())
    plt.ylabel("Milliseconds" if metric == "latency_ms" else "Score")
    plt.xticks(rotation=0, fontsize=8)
    plt.tight_layout()
    plt.savefig(output)
    plt.close()


def main() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        report = {
            "status": "warning",
            "module": "cognitutor_vs_sanvia_visualization_report",
            "reason": "comparison_report_missing",
            "charts": [],
        }
        JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        MD_REPORT.write_text("# CogniTutorLM vs Sanvia Visualization Report\n\nComparison report missing.\n", encoding="utf-8")
        print("STATUS: warning")
        print("MODULE: cognitutor_vs_sanvia_visualization_report")
        print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
        print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
        print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
        return

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    averages = data.get("service_averages", {})
    charts = []
    for metric, filename in CHARTS.items():
        path = CHART_DIR / filename
        _plot_metric(averages, metric, path)
        charts.append({"metric": metric, "path": str(path.relative_to(ROOT))})

    report = {
        "status": "success",
        "module": "cognitutor_vs_sanvia_visualization_report",
        "input_report": str(INPUT.relative_to(ROOT)),
        "chart_dir": str(CHART_DIR.relative_to(ROOT)),
        "charts": charts,
    }
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_REPORT.write_text(
        "# CogniTutorLM vs Sanvia Visualization Report\n\n"
        + "\n".join(f"- {item['metric']}: `{item['path']}`" for item in charts)
        + "\n",
        encoding="utf-8",
    )
    print("STATUS: success")
    print("MODULE: cognitutor_vs_sanvia_visualization_report")
    print(f"CHART_DIR: {CHART_DIR.relative_to(ROOT)}")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
