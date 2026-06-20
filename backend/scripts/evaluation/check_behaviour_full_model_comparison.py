from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tutor.behaviour.lstm_behaviour_model import META_PATH, MODEL_PATH, run_behaviour_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OLD_COMPARISON = PROJECT_ROOT / "evaluation_outputs" / "json" / "behaviour_model_comparison_report.json"
BASELINE_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "behaviour_baselines_training_report.json"
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "behaviour_full_model_comparison_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "behaviour_full_model_comparison_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _model_row(name: str, status: str, metrics: dict[str, Any] | None = None, note: str = "") -> dict[str, Any]:
    metrics = metrics or {}
    return {
        "model": name,
        "availability": status,
        "accuracy": metrics.get("accuracy"),
        "balanced_accuracy": metrics.get("balanced_accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "weighted_f1": metrics.get("weighted_f1"),
        "per_class_precision": metrics.get("per_class_precision"),
        "per_class_recall": metrics.get("per_class_recall"),
        "silhouette_score": metrics.get("silhouette_score"),
        "cluster_to_label_majority_mapping": metrics.get("cluster_to_label_majority_mapping"),
        "note": note,
    }


def build_report() -> dict[str, Any]:
    old_report = _load_json(OLD_COMPARISON)
    baseline_report = _load_json(BASELINE_REPORT)
    if not baseline_report:
        from scripts.training.behaviour.train_behaviour_baselines import train_baselines

        baseline_report = train_baselines()

    dataset = baseline_report.get("dataset", {})
    supervised = baseline_report.get("supervised_models", {})
    clustering = baseline_report.get("clustering_models", {})
    lstm_meta = _load_json(META_PATH)
    try:
        runtime_output = run_behaviour_model("14")
    except Exception as exc:
        runtime_output = {
            "status": "error",
            "reason": f"{type(exc).__name__}: runtime check failed",
        }

    rows = [
        _model_row(
            "rule_proxy_baseline",
            "available",
            note="Transparent proxy labels and feature rules are available for audit but are not a learned model.",
        )
    ]

    rows.append(
        _model_row(
            "current_lstm_behaviour",
            "available" if MODEL_PATH.exists() and META_PATH.exists() else "missing",
            {
                "accuracy": (lstm_meta.get("history") or [{}])[-1].get("val_acc") if lstm_meta.get("history") else None,
            },
            "Current runtime model; sequence-aware and already integrated with behaviour_state persistence.",
        )
    )

    for key, label in [
        ("logistic_regression", "LogisticRegression"),
        ("random_forest", "RandomForestClassifier"),
    ]:
        result = supervised.get(key, {})
        rows.append(
            _model_row(
                label,
                result.get("status", "pending"),
                result.get("metrics", {}),
                "Supervised baseline trained on proxy labels; report-only until labels improve.",
            )
        )

    for key, label in [("kmeans", "KMeans"), ("gmm", "GaussianMixture")]:
        result = clustering.get(key, {})
        rows.append(
            _model_row(
                label,
                result.get("status", "pending"),
                result.get("metrics", {}),
                result.get("mapping_note", "Clusters are not true labels."),
            )
        )

    rows.append(
        _model_row(
            "LSTM autoencoder",
            "pending",
            note="Not implemented yet; useful future anomaly detector for unusual behaviour sequences.",
        )
    )

    supervised_success = [
        row
        for row in rows
        if row["model"] in {"LogisticRegression", "RandomForestClassifier"}
        and row["availability"] == "success"
        and row["macro_f1"] is not None
    ]
    best_model = max(supervised_success, key=lambda row: row["macro_f1"], default=None)
    best_balanced_model = max(supervised_success, key=lambda row: row["balanced_accuracy"] or 0.0, default=None)
    clustering_success = [
        row for row in rows
        if row["model"] in {"KMeans", "GaussianMixture"}
        and row["availability"] == "success"
        and row["silhouette_score"] is not None
    ]
    best_cluster = max(clustering_success, key=lambda row: row["silhouette_score"] or -1.0, default=None)

    label_distribution = dataset.get("label_distribution") or {}
    row_count = sum(int(value) for value in label_distribution.values()) if label_distribution else 0
    max_count = max(label_distribution.values()) if label_distribution else 0
    imbalance_ratio = max_count / row_count if row_count else 0.0
    severe_imbalance = imbalance_ratio >= 0.9 or any(int(value) < 10 for value in label_distribution.values())

    status = "success" if supervised_success else "warning"
    if severe_imbalance:
        status = "warning"

    return {
        "status": status,
        "module": "behaviour_full_model_comparison_report",
        "model_availability": rows,
        "best_model_under_current_proxy_labels": best_model,
        "best_supervised_by_macro_f1": best_model,
        "best_supervised_by_balanced_accuracy": best_balanced_model,
        "best_clustering_by_silhouette": best_cluster,
        "dataset": dataset,
        "label_imbalance_warning": bool(dataset.get("class_imbalance_warning")),
        "severe_imbalance_warning": severe_imbalance,
        "class_imbalance_ratio": round(imbalance_ratio, 6),
        "old_vs_improved_label_distribution": {
            "old_label_distribution": dataset.get("source_summary", {}).get("old_label_distribution"),
            "improved_label_distribution": label_distribution,
        },
        "metric_interpretation": (
            "Macro-F1 and balanced accuracy matter more than accuracy because stable labels can dominate. "
            "Accuracy can look high even when rare behaviour classes are missed."
        ),
        "current_production_runtime_model": {
            "model": "current_lstm_behaviour",
            "model_path": str(MODEL_PATH),
            "meta_path": str(META_PATH),
            "runtime_output": runtime_output,
        },
        "runtime_decision": (
            "The LSTM remains the runtime model because it is already sequence-aware, integrated, and persisted. "
            "Logistic Regression, Random Forest, KMeans, and GMM are comparison/report-only baselines trained on proxy labels."
        ),
        "final_report_wording": (
            "Behaviour modeling is model-supported and comparison-upgraded, but label quality remains a limitation "
            "because labels are inferred from interaction patterns rather than human annotation."
        ),
        "model_classification": {
            "LSTM runtime": "backend-ready",
            "RandomForest/LogisticRegression": "comparison models",
            "KMeans/GMM": "exploratory behaviour grouping",
            "LSTM autoencoder": "pending",
        },
        "old_comparison_report_status": old_report.get("status"),
        "future_work": [
            "Create better labels from evaluation_fusion, mistake_analysis, repeated wrong attempts, and code/runtime errors.",
            "Train an anomaly detector or LSTM autoencoder for unusual behaviour sequences.",
            "Track long-term behaviour trends per learner instead of only latest-window labels.",
            "Expose behaviour risk, confidence, and trend explanations in teacher/admin dashboards.",
            "Use macro-F1, confusion matrix, and per-class recall as primary metrics under imbalance.",
        ],
        "limitations": [
            "Current labels are proxy/rule-generated, not human-reviewed behaviour labels.",
            "Class imbalance means accuracy can be misleading.",
            "Unsupervised clusters require interpretation before being mapped to learner-facing categories.",
            "Baseline models should not replace runtime LSTM until label quality and online behaviour are validated.",
        ],
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Behaviour Full Model Comparison Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Model Availability and Metrics",
        "",
    ]
    for row in report["model_availability"]:
        lines.append(
            f"- {row['model']}: availability={row['availability']}, accuracy={row['accuracy']}, "
            f"balanced_accuracy={row['balanced_accuracy']}, macro_f1={row['macro_f1']}, weighted_f1={row['weighted_f1']}, "
            f"silhouette={row['silhouette_score']}. {row['note']}"
        )
    lines.extend(
        [
            "",
            "## Best Proxy-Label Model",
            "",
            str(report["best_model_under_current_proxy_labels"]),
            "",
            "## Runtime Decision",
            "",
            report["runtime_decision"],
            "",
            "## Correct Claim",
            "",
            report["final_report_wording"],
            "",
            "## Label Imbalance",
            "",
            f"Warning: {report['label_imbalance_warning']}",
            f"Severe warning: {report['severe_imbalance_warning']}",
            f"Class imbalance ratio: {report['class_imbalance_ratio']}",
            f"Old vs improved distribution: {report['old_vs_improved_label_distribution']}",
            "",
            "## Metric Interpretation",
            "",
            report["metric_interpretation"],
            "",
            "## Model Classification",
            "",
        ]
    )
    for key, value in report["model_classification"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Future Work",
            "",
        ]
    )
    for item in report["future_work"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: behaviour_full_model_comparison_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
