from __future__ import annotations

import csv
import json
import pickle
from collections import Counter
from pathlib import Path
from typing import Any


CSV_INPUT = Path("evaluation_outputs/csv/behaviour_training_dataset.csv")
SUMMARY_INPUT = Path("evaluation_outputs/json/behaviour_training_data_summary.json")
MODEL_DIR = Path("models/behaviour")
JSON_REPORT = Path("evaluation_outputs/json/behaviour_baselines_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/behaviour_baselines_training_report.md")

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


def _ensure_dataset() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.behaviour.prepare_behaviour_training_data import prepare_dataset

        prepare_dataset()


def _load_dataset() -> tuple[list[list[float]], list[str]]:
    _ensure_dataset()
    x_rows: list[list[float]] = []
    y_rows: list[str] = []
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                x_rows.append([float(row.get(column, 0.0) or 0.0) for column in FEATURE_COLUMNS])
                y_rows.append(str(row.get("proxy_label") or "stable"))
            except Exception:
                continue
    return x_rows, y_rows


def _save_pickle(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(obj, handle)


def _supervised_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

    precision, recall, _, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 6),
        "weighted_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)), 6),
        "per_class_precision": {label: round(float(value), 6) for label, value in zip(labels, precision)},
        "per_class_recall": {label: round(float(value), 6) for label, value in zip(labels, recall)},
        "per_class_support": {label: int(value) for label, value in zip(labels, support)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
        "label_distribution": dict(Counter(y_true)),
    }


def _train_supervised_models(x_rows: list[list[float]], y_rows: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        return {
            "logistic_regression": {"status": "skipped", "reason": f"sklearn import failed: {type(exc).__name__}"},
            "random_forest": {"status": "skipped", "reason": f"sklearn import failed: {type(exc).__name__}"},
        }

    labels = sorted(set(y_rows))
    class_counts = Counter(y_rows)
    if len(labels) < 2:
        return {
            "logistic_regression": {"status": "skipped", "reason": "Need at least two labels."},
            "random_forest": {"status": "skipped", "reason": "Need at least two labels."},
        }

    too_few_classes = {
        label: count
        for label, count in class_counts.items()
        if count < 5
    }
    stratify = y_rows if min(class_counts.values()) >= 2 else None
    split_note = "stratified split" if stratify is not None else "non-stratified split because one or more classes had too few samples"
    x_train, x_test, y_train, y_test = train_test_split(
        x_rows,
        y_rows,
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )

    model_specs = {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150,
            random_state=42,
            class_weight="balanced",
            min_samples_leaf=2,
            n_jobs=-1,
        ),
    }
    output_paths = {
        "logistic_regression": MODEL_DIR / "logistic_regression_behaviour.pkl",
        "random_forest": MODEL_DIR / "random_forest_behaviour.pkl",
    }

    for model_name, model in model_specs.items():
        try:
            model.fit(x_train, y_train)
            y_pred = list(model.predict(x_test))
            metrics = _supervised_metrics(y_test, y_pred, labels)
            _save_pickle(output_paths[model_name], model)
            results[model_name] = {
                "status": "success",
                "model_path": str(output_paths[model_name]),
                "metrics": metrics,
                "too_few_class_warning": too_few_classes,
                "split_note": split_note,
                "note": "Trained on transparent proxy labels; do not overclaim real behaviour validity.",
            }
        except Exception as exc:
            results[model_name] = {
                "status": "skipped",
                "reason": f"{type(exc).__name__}: training failed",
            }

    return results


def _train_clustering_models(x_rows: list[list[float]], y_rows: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    try:
        from sklearn.cluster import KMeans
        from sklearn.mixture import GaussianMixture
        from sklearn.metrics import silhouette_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        return {
            "kmeans": {"status": "skipped", "reason": f"sklearn import failed: {type(exc).__name__}"},
            "gmm": {"status": "skipped", "reason": f"sklearn import failed: {type(exc).__name__}"},
        }

    n_clusters = max(2, min(4, len(set(y_rows)) or 2))
    sample_x = x_rows[:5000] if len(x_rows) > 5000 else x_rows

    kmeans_path = MODEL_DIR / "kmeans_behaviour.pkl"
    try:
        kmeans = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", KMeans(n_clusters=n_clusters, random_state=42, n_init=10)),
            ]
        )
        clusters = list(kmeans.fit_predict(x_rows))
        mapping = _cluster_majority_mapping(clusters, y_rows)
        sample_clusters = clusters[: len(sample_x)]
        silhouette = None
        if len(set(sample_clusters)) > 1 and len(sample_x) > n_clusters:
            silhouette = round(float(silhouette_score(sample_x, sample_clusters)), 6)
        _save_pickle(kmeans_path, kmeans)
        results["kmeans"] = {
            "status": "success",
            "model_path": str(kmeans_path),
            "metrics": {
                "silhouette_score": silhouette,
                "cluster_distribution": dict(Counter(str(item) for item in clusters)),
                "cluster_to_label_majority_mapping": mapping,
                "cluster_count": n_clusters,
            },
            "mapping_note": "Clusters are not true behaviour labels; they require interpretation against learner evidence.",
        }
    except Exception as exc:
        results["kmeans"] = {"status": "skipped", "reason": f"{type(exc).__name__}: training failed"}

    gmm_path = MODEL_DIR / "gmm_behaviour.pkl"
    try:
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_rows)
        gmm = GaussianMixture(n_components=n_clusters, random_state=42, covariance_type="full")
        clusters = list(gmm.fit_predict(x_scaled))
        mapping = _cluster_majority_mapping(clusters, y_rows)
        sample_clusters = clusters[: len(sample_x)]
        silhouette = None
        sample_scaled = x_scaled[: len(sample_x)]
        if len(set(sample_clusters)) > 1 and len(sample_x) > n_clusters:
            silhouette = round(float(silhouette_score(sample_scaled, sample_clusters)), 6)
        model_obj = {"scaler": scaler, "model": gmm}
        _save_pickle(gmm_path, model_obj)
        results["gmm"] = {
            "status": "success",
            "model_path": str(gmm_path),
            "metrics": {
                "silhouette_score": silhouette,
                "cluster_distribution": dict(Counter(str(item) for item in clusters)),
                "cluster_to_label_majority_mapping": mapping,
                "cluster_count": n_clusters,
            },
            "mapping_note": "GMM clusters are unsupervised groups, not validated learner labels.",
        }
    except Exception as exc:
        results["gmm"] = {"status": "skipped", "reason": f"{type(exc).__name__}: training failed"}

    return results


def _cluster_majority_mapping(clusters: list[int], labels: list[str]) -> dict[str, Any]:
    buckets: dict[int, Counter[str]] = {}
    for cluster, label in zip(clusters, labels):
        buckets.setdefault(int(cluster), Counter())[str(label)] += 1
    mapping = {}
    for cluster, counter in buckets.items():
        majority_label, majority_count = counter.most_common(1)[0]
        total = sum(counter.values())
        mapping[str(cluster)] = {
            "majority_label": majority_label,
            "majority_count": majority_count,
            "cluster_size": total,
            "purity": round(majority_count / total, 6) if total else 0.0,
            "label_counts": dict(counter),
        }
    return mapping


def train_baselines() -> dict[str, Any]:
    x_rows, y_rows = _load_dataset()
    dataset_summary = {}
    if SUMMARY_INPUT.exists():
        dataset_summary = json.loads(SUMMARY_INPUT.read_text(encoding="utf-8"))

    supervised = _train_supervised_models(x_rows, y_rows)
    clustering = _train_clustering_models(x_rows, y_rows)
    label_distribution = dict(Counter(y_rows))
    row_count = len(y_rows)
    max_ratio = max(label_distribution.values()) / row_count if row_count else 0.0

    skipped_count = sum(1 for result in {**supervised, **clustering}.values() if result.get("status") != "success")
    report = {
        "status": "warning" if skipped_count else "success",
        "module": "train_behaviour_baselines",
        "dataset": {
            "path": str(CSV_INPUT),
            "row_count": row_count,
            "feature_columns": FEATURE_COLUMNS,
            "label_distribution": label_distribution,
            "class_imbalance_ratio": round(max_ratio, 6) if row_count else 0.0,
            "class_imbalance_warning": max_ratio >= 0.75,
            "source_summary": dataset_summary,
        },
        "supervised_models": supervised,
        "clustering_models": clustering,
        "limitations": [
            "Labels are proxy labels, so high performance mostly confirms rule mimicry.",
            "Accuracy is not enough under class imbalance; macro-F1 and confusion matrix are more informative.",
            "Clustering outputs need qualitative interpretation before learner-facing use.",
        ],
    }

    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Behaviour Baselines Training Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Dataset",
        "",
        f"- Rows: {row_count}",
        f"- Label distribution: {label_distribution}",
        f"- Class imbalance warning: {report['dataset']['class_imbalance_warning']}",
        "",
        "## Supervised Models",
        "",
    ]
    for name, result in supervised.items():
        lines.append(f"- {name}: {result.get('status')} {result.get('metrics', result.get('reason', ''))}")
    lines.extend(["", "## Clustering Models", ""])
    for name, result in clustering.items():
        lines.append(f"- {name}: {result.get('status')} {result.get('metrics', result.get('reason', ''))}")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = train_baselines()
    print(f"STATUS: {report['status']}")
    print("MODULE: train_behaviour_baselines")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
