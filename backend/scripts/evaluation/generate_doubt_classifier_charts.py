from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


TRAINING_REPORT = Path("evaluation_outputs/json/doubt_intent_training_report.json")
CLASSIFIER_REPORT = Path("evaluation_outputs/json/doubt_classifier_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/doubt_classifier_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/doubt_classifier_visualization_report.md")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_reports() -> tuple[dict, dict]:
    if not TRAINING_REPORT.exists():
        from scripts.training.doubt.train_doubt_intent_classifier import train_classifier

        train_classifier()
    if not CLASSIFIER_REPORT.exists():
        from scripts.evaluation.check_doubt_classifier_report import build_report, write_reports

        report = build_report()
        write_reports(report)
    return _load_json(TRAINING_REPORT), _load_json(CLASSIFIER_REPORT)


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    training, report = _ensure_reports()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}
    best_model = training.get("best_model")
    metrics = ((training.get("models") or {}).get(best_model) or {}).get("metrics") or {}
    labels = metrics.get("labels") or report.get("intent_classes") or []

    dist_path = CHART_DIR / "doubt_intent_distribution.png"
    distribution = (training.get("dataset") or {}).get("label_distribution") or {}
    plt.figure(figsize=(10, 4.5))
    plt.bar(list(distribution.keys()), list(distribution.values()))
    plt.xticks(rotation=35, ha="right")
    plt.title("Doubt Intent Distribution")
    plt.ylabel("Example count")
    _save(dist_path)
    charts["doubt_intent_distribution"] = str(dist_path)

    cm_path = CHART_DIR / "doubt_classifier_confusion_matrix.png"
    matrix = metrics.get("confusion_matrix") or []
    plt.figure(figsize=(8, 7))
    plt.imshow(matrix, aspect="auto")
    plt.title("Doubt Classifier Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(range(len(labels)), labels)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            plt.text(j, i, str(value), ha="center", va="center", fontsize=7)
    plt.colorbar()
    _save(cm_path)
    charts["doubt_classifier_confusion_matrix"] = str(cm_path)

    f1_path = CHART_DIR / "doubt_per_class_f1.png"
    precision = metrics.get("per_class_precision") or {}
    recall = metrics.get("per_class_recall") or {}
    f1_values = {}
    for label in labels:
        p = float(precision.get(label, 0.0))
        r = float(recall.get(label, 0.0))
        f1_values[label] = 2 * p * r / (p + r) if p + r else 0.0
    plt.figure(figsize=(10, 4.5))
    plt.bar(list(f1_values.keys()), list(f1_values.values()))
    plt.ylim(0, 1)
    plt.xticks(rotation=35, ha="right")
    plt.title("Doubt Per-Class F1")
    _save(f1_path)
    charts["doubt_per_class_f1"] = str(f1_path)

    conf_path = CHART_DIR / "doubt_confidence_distribution.png"
    confidences = [float(item.get("confidence", 0.0)) for item in report.get("sample_outputs", [])]
    plt.figure(figsize=(7, 4))
    plt.hist(confidences, bins=10, range=(0, 1))
    plt.title("Doubt Classifier Confidence Distribution")
    plt.xlabel("Confidence")
    plt.ylabel("Sample count")
    _save(conf_path)
    charts["doubt_confidence_distribution"] = str(conf_path)

    visualization = {
        "status": "success",
        "module": "doubt_classifier_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_reports": [str(TRAINING_REPORT), str(CLASSIFIER_REPORT)],
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Doubt Classifier Visualization Report", "", f"Status: **{report['status']}**", "", f"Chart directory: `{report['chart_dir']}`", "", "## Charts", ""]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: doubt_classifier_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
