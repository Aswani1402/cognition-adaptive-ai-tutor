from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/semantic_answer_benchmark_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/semantic_benchmark_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_benchmark_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.evaluation.check_semantic_answer_benchmark import evaluate_benchmark, write_reports

        report = evaluate_benchmark()
        write_reports(report)
        return report
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}
    labels = report.get("labels") or ["strong", "partial", "weak"]

    confusion_path = CHART_DIR / "semantic_benchmark_confusion_matrix.png"
    matrix = report.get("confusion_matrix") or []
    plt.figure(figsize=(6, 5))
    plt.imshow(matrix, aspect="auto")
    plt.title("Semantic Benchmark Confusion Matrix")
    plt.xlabel("Predicted label")
    plt.ylabel("Expected label")
    plt.xticks(range(len(labels)), labels)
    plt.yticks(range(len(labels)), labels)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            plt.text(j, i, str(value), ha="center", va="center")
    plt.colorbar()
    _save(confusion_path)
    charts["semantic_benchmark_confusion_matrix"] = str(confusion_path)

    label_path = CHART_DIR / "semantic_benchmark_label_distribution.png"
    expected = report.get("label_distribution", {}).get("expected", {})
    predicted = report.get("label_distribution", {}).get("predicted", {})
    x = list(range(len(labels)))
    width = 0.35
    plt.figure(figsize=(7, 4))
    plt.bar([i - width / 2 for i in x], [expected.get(label, 0) for label in labels], width=width, label="expected")
    plt.bar([i + width / 2 for i in x], [predicted.get(label, 0) for label in labels], width=width, label="predicted")
    plt.xticks(x, labels)
    plt.ylabel("Case count")
    plt.title("Semantic Benchmark Label Distribution")
    plt.legend()
    _save(label_path)
    charts["semantic_benchmark_label_distribution"] = str(label_path)

    error_path = CHART_DIR / "semantic_benchmark_score_error.png"
    errors = [float(item.get("absolute_score_error", 0.0)) for item in report.get("results", [])]
    plt.figure(figsize=(7, 4))
    plt.hist(errors, bins=12, range=(0, 1))
    plt.title("Semantic Benchmark Score Error")
    plt.xlabel("Absolute score error")
    plt.ylabel("Case count")
    _save(error_path)
    charts["semantic_benchmark_score_error"] = str(error_path)

    task_path = CHART_DIR / "semantic_benchmark_per_task_accuracy.png"
    per_task = report.get("per_task_accuracy") or {}
    task_labels = list(per_task.keys())
    plt.figure(figsize=(8, 4))
    plt.bar(task_labels, [per_task[label] for label in task_labels])
    plt.ylim(0, 1)
    plt.xticks(rotation=20, ha="right")
    plt.ylabel("Accuracy")
    plt.title("Semantic Benchmark Per-Task Accuracy")
    _save(task_path)
    charts["semantic_benchmark_per_task_accuracy"] = str(task_path)

    visualization_report = {
        "status": "success",
        "module": "semantic_benchmark_charts",
        "chart_dir": str(CHART_DIR),
        "source_report": str(REPORT_PATH),
        "charts": charts,
    }
    return visualization_report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Benchmark Charts Report",
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
    print("MODULE: semantic_benchmark_charts")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
