from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


SEMANTIC_REPORT = Path("evaluation_outputs/json/semantic_evaluator_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/semantic_evaluator_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_evaluator_visualization_report.md")


def _ensure_report() -> dict:
    if not SEMANTIC_REPORT.exists():
        from scripts.evaluation.check_semantic_evaluator_report import build_report, write_reports

        report = build_report()
        write_reports(report)
        return report
    return json.loads(SEMANTIC_REPORT.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def build_charts() -> dict:
    report = _ensure_report()
    results = report.get("results") or []
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}

    score_path = CHART_DIR / "semantic_score_distribution.png"
    plt.figure(figsize=(7, 4))
    plt.hist([float(item.get("semantic_score", 0.0)) for item in results], bins=10, range=(0, 1))
    plt.title("Semantic Score Distribution")
    plt.xlabel("Final semantic score")
    plt.ylabel("Case count")
    _save(score_path)
    charts["semantic_score_distribution"] = str(score_path)

    component_path = CHART_DIR / "semantic_component_scores.png"
    components = ["semantic_similarity", "key_point_coverage", "rubric_score_used", "structure_score"]
    values = [
        sum(float(item.get(component, 0.0)) for item in results) / max(1, len(results))
        for component in components
    ]
    plt.figure(figsize=(8, 4))
    plt.bar(components, values)
    plt.ylim(0, 1)
    plt.title("Average Semantic Component Scores")
    plt.xticks(rotation=20, ha="right")
    _save(component_path)
    charts["semantic_component_scores"] = str(component_path)

    label_path = CHART_DIR / "semantic_label_distribution.png"
    counts = Counter(item.get("semantic_label", "unknown") for item in results)
    plt.figure(figsize=(6, 4))
    labels = list(counts.keys())
    plt.bar(labels, [counts[label] for label in labels])
    plt.title("Semantic Label Distribution")
    plt.ylabel("Case count")
    _save(label_path)
    charts["semantic_label_distribution"] = str(label_path)

    return {
        "status": "success",
        "module": "semantic_evaluator_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_report": str(SEMANTIC_REPORT),
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Evaluator Visualization Report",
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
    report = build_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: semantic_evaluator_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
