from __future__ import annotations

import csv
import json
import pickle
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib.pyplot as plt


CSV_INPUT = Path("evaluation_outputs/csv/behaviour_training_dataset.csv")
SUMMARY_INPUT = Path("evaluation_outputs/json/behaviour_training_data_summary.json")
BASELINE_REPORT = Path("evaluation_outputs/json/behaviour_baselines_training_report.json")
FULL_REPORT = Path("evaluation_outputs/json/behaviour_full_model_comparison_report.json")
DB_PATH = Path("external/core_data/tutor.db")
RF_MODEL = Path("models/behaviour/random_forest_behaviour.pkl")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/behaviour_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/behaviour_visualization_report.md")

FEATURE_COLUMNS = [
    "wrong_rate",
    "slow_rate",
    "low_confidence_rate",
    "hint_rate",
    "option_change_rate",
    "avg_time_taken_sec",
    "avg_confidence",
    "attempt_count",
    "recent_wrong_rate",
    "repeated_attempt_rate",
    "fast_wrong_rate",
    "avg_hint_count",
]


def _ensure_inputs() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.behaviour.prepare_behaviour_training_data import prepare_dataset

        prepare_dataset()
    if not BASELINE_REPORT.exists():
        from scripts.training.behaviour.train_behaviour_baselines import train_baselines

        train_baselines()
    if not FULL_REPORT.exists():
        from scripts.evaluation.check_behaviour_full_model_comparison import build_report, write_reports

        report = build_report()
        write_reports(report)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_rows() -> list[dict[str, Any]]:
    _ensure_inputs()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _label_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row.get("behaviour_label") or row.get("proxy_label") or "unknown" for row in rows)
    path = CHART_DIR / "behaviour_label_distribution.png"
    plt.figure(figsize=(7, 4))
    labels = list(counts.keys())
    plt.bar(labels, [counts[label] for label in labels])
    plt.title("Behaviour Label Distribution")
    plt.ylabel("Window count")
    plt.xticks(rotation=20, ha="right")
    _save(path)
    return {"path": str(path), "counts": dict(counts)}


def _model_comparison() -> dict[str, Any]:
    report = _load_json(FULL_REPORT)
    rows = report.get("model_availability") or []
    labels = []
    macro_f1 = []
    balanced = []
    for row in rows:
        if row.get("macro_f1") is None and row.get("balanced_accuracy") is None:
            continue
        labels.append(row.get("model"))
        macro_f1.append(float(row.get("macro_f1") or 0.0))
        balanced.append(float(row.get("balanced_accuracy") or 0.0))
    path = CHART_DIR / "behaviour_model_comparison.png"
    plt.figure(figsize=(8, 4.5))
    x = list(range(len(labels)))
    width = 0.35
    plt.bar([i - width / 2 for i in x], macro_f1, width=width, label="macro-F1")
    plt.bar([i + width / 2 for i in x], balanced, width=width, label="balanced accuracy")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylim(0, 1)
    plt.title("Behaviour Model Comparison")
    plt.legend()
    _save(path)
    return {"path": str(path), "models": labels}


def _best_supervised_metrics() -> tuple[str | None, dict[str, Any] | None]:
    baseline = _load_json(BASELINE_REPORT)
    supervised = baseline.get("supervised_models") or {}
    best_name = None
    best_metrics = None
    best_score = -1.0
    for name, result in supervised.items():
        metrics = result.get("metrics") or {}
        score = float(metrics.get("macro_f1") or -1.0)
        if result.get("status") == "success" and score > best_score:
            best_name = name
            best_metrics = metrics
            best_score = score
    return best_name, best_metrics


def _confusion_matrix_chart() -> dict[str, Any]:
    model_name, metrics = _best_supervised_metrics()
    path = CHART_DIR / "behaviour_confusion_matrix.png"
    if not metrics or not metrics.get("confusion_matrix"):
        return {"path": None, "status": "skipped", "reason": "No supervised confusion matrix available."}
    matrix = metrics["confusion_matrix"]
    labels = metrics.get("labels") or []
    plt.figure(figsize=(6, 5))
    plt.imshow(matrix, aspect="auto")
    plt.title(f"Behaviour Confusion Matrix ({model_name})")
    plt.xlabel("Predicted label")
    plt.ylabel("True proxy label")
    plt.xticks(range(len(labels)), labels, rotation=25, ha="right")
    plt.yticks(range(len(labels)), labels)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            plt.text(j, i, str(value), ha="center", va="center")
    plt.colorbar()
    _save(path)
    return {"path": str(path), "status": "success", "model": model_name}


def _risk_values_from_db() -> list[float]:
    if not DB_PATH.exists():
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT state_json FROM behaviour_state WHERE state_json IS NOT NULL")
            values = []
            for (state_json,) in cursor.fetchall():
                try:
                    state = json.loads(state_json)
                except Exception:
                    continue
                for key in ["behaviour_risk", "risk", "risk_score"]:
                    if state.get(key) is not None:
                        values.append(_safe_float(state.get(key)))
                        break
            return [value for value in values if 0.0 <= value <= 1.0]
    except Exception:
        return []


def _risk_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = _risk_values_from_db()
    source = "behaviour_state"
    if not values:
        values = [
            max(
                _safe_float(row.get("confused_score")),
                _safe_float(row.get("guessing_score")),
                _safe_float(row.get("struggling_score")),
            )
            for row in rows
        ]
        source = "computed_pattern_risk"
    path = CHART_DIR / "behaviour_risk_distribution.png"
    plt.figure(figsize=(7, 4))
    plt.hist(values, bins=20, range=(0, 1))
    plt.title("Behaviour Risk Distribution")
    plt.xlabel("Risk score")
    plt.ylabel("Count")
    _save(path)
    return {"path": str(path), "source": source, "count": len(values)}


def _feature_importance() -> dict[str, Any]:
    path = CHART_DIR / "behaviour_feature_importance.png"
    if not RF_MODEL.exists():
        return {"path": None, "status": "skipped", "reason": "RandomForest model not found."}
    try:
        with RF_MODEL.open("rb") as handle:
            model = pickle.load(handle)
        importances = list(getattr(model, "feature_importances_", []))
        if not importances:
            return {"path": None, "status": "skipped", "reason": "RandomForest has no feature_importances_."}
        pairs = sorted(zip(FEATURE_COLUMNS, importances), key=lambda item: item[1], reverse=True)
        plt.figure(figsize=(8, 5))
        plt.barh([item[0] for item in reversed(pairs)], [item[1] for item in reversed(pairs)])
        plt.title("RandomForest Behaviour Feature Importance")
        plt.xlabel("Importance")
        _save(path)
        return {"path": str(path), "status": "success", "top_features": pairs[:5]}
    except Exception as exc:
        return {"path": None, "status": "skipped", "reason": f"{type(exc).__name__}: {exc}"}


def _cluster_distribution() -> dict[str, Any]:
    baseline = _load_json(BASELINE_REPORT)
    clustering = baseline.get("clustering_models") or {}
    path = CHART_DIR / "behaviour_cluster_distribution.png"
    labels = []
    values = []
    for model_name in ["kmeans", "gmm"]:
        distribution = ((clustering.get(model_name) or {}).get("metrics") or {}).get("cluster_distribution") or {}
        for cluster, count in distribution.items():
            labels.append(f"{model_name}:{cluster}")
            values.append(int(count))
    if not labels:
        return {"path": None, "status": "skipped", "reason": "No clustering distributions available."}
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.xticks(rotation=25, ha="right")
    plt.title("Behaviour Cluster Distribution")
    plt.ylabel("Window count")
    _save(path)
    return {"path": str(path), "status": "success", "clusters": dict(zip(labels, values))}


def _feature_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("behaviour_label") or row.get("proxy_label") or "unknown"].append(row)
    features = ["wrong_rate", "slow_rate", "low_confidence_rate", "hint_rate", "option_change_rate"]
    labels = list(grouped.keys())
    path = CHART_DIR / "behaviour_feature_summary.png"
    plt.figure(figsize=(9, 5))
    x = list(range(len(labels)))
    width = 0.15
    for idx, feature in enumerate(features):
        means = [mean([_safe_float(row.get(feature)) for row in grouped[label]]) for label in labels]
        plt.bar([pos + (idx - 2) * width for pos in x], means, width=width, label=feature)
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylim(0, 1)
    plt.title("Behaviour Feature Summary by Label")
    plt.legend()
    _save(path)
    return {"path": str(path), "labels": labels, "features": features}


def build_report() -> dict[str, Any]:
    rows = _load_rows()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "behaviour_label_distribution": _label_distribution(rows),
        "behaviour_model_comparison": _model_comparison(),
        "behaviour_confusion_matrix": _confusion_matrix_chart(),
        "behaviour_risk_distribution": _risk_distribution(rows),
        "behaviour_feature_importance": _feature_importance(),
        "behaviour_cluster_distribution": _cluster_distribution(),
        "behaviour_feature_summary": _feature_summary(rows),
    }
    skipped = {name: data.get("reason") for name, data in charts.items() if data.get("status") == "skipped"}
    report = {
        "status": "warning" if skipped else "success",
        "module": "behaviour_evaluation_charts",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "skipped_charts": skipped,
        "source_files": {
            "dataset": str(CSV_INPUT),
            "summary": str(SUMMARY_INPUT),
            "baseline_report": str(BASELINE_REPORT),
            "full_comparison_report": str(FULL_REPORT),
        },
        "interpretation_for_report": (
            "Behaviour charts should be interpreted as model comparison over improved proxy labels. "
            "Macro-F1, balanced accuracy, per-class recall, confusion matrix, and cluster distributions are "
            "more meaningful than accuracy alone under class imbalance."
        ),
        "limitations": [
            "Labels are inferred from interaction patterns, not human annotation.",
            "Class imbalance remains possible even after score-based labeling.",
            "KMeans and GMM clusters are exploratory groupings, not ground-truth behaviour labels.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Behaviour Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, data in report["charts"].items():
        lines.append(f"- {name}: `{data.get('path')}`")
    if report["skipped_charts"]:
        lines.extend(["", "## Skipped Charts", ""])
        for name, reason in report["skipped_charts"].items():
            lines.append(f"- {name}: {reason}")
    lines.extend(["", "## Interpretation", "", report["interpretation_for_report"], "", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: behaviour_evaluation_charts")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
