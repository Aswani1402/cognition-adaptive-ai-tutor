from __future__ import annotations

import csv
import json
import pickle
from collections import Counter
from pathlib import Path
from typing import Any


CSV_INPUT = Path("evaluation_outputs/csv/doubt_intent_dataset.csv")
MODEL_DIR = Path("models/doubt")
MODEL_PATH = MODEL_DIR / "doubt_intent_classifier.pkl"
VECTORIZER_PATH = MODEL_DIR / "doubt_intent_vectorizer.pkl"
META_PATH = MODEL_DIR / "doubt_intent_meta.json"
JSON_REPORT = Path("evaluation_outputs/json/doubt_intent_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/doubt_intent_training_report.md")


def _ensure_dataset() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.doubt.build_doubt_intent_dataset import build_dataset

        build_dataset()


def _load_rows() -> tuple[list[str], list[str], list[dict[str, Any]]]:
    _ensure_dataset()
    rows = []
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    texts = [row["doubt_text"] for row in rows]
    labels = [row["intent_label"] for row in rows]
    return texts, labels, rows


def _metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

    precision, recall, _, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 6),
        "weighted_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)), 6),
        "per_class_precision": {label: round(float(value), 6) for label, value in zip(labels, precision)},
        "per_class_recall": {label: round(float(value), 6) for label, value in zip(labels, recall)},
        "per_class_support": {label: int(value) for label, value in zip(labels, support)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
    }


def _save_pickle(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(obj, handle)


def train_classifier() -> dict[str, Any]:
    texts, y, rows = _load_rows()
    label_counts = Counter(y)
    labels = sorted(label_counts)
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.svm import LinearSVC
    except Exception as exc:
        report = {
            "status": "warning",
            "module": "doubt_intent_classifier_training",
            "reason": f"sklearn unavailable: {type(exc).__name__}",
            "label_distribution": dict(label_counts),
        }
        _write_reports(report)
        return report

    stratify = y if min(label_counts.values()) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    candidates: dict[str, Any] = {
        "tfidf_logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", C=10.0, random_state=42),
        "tfidf_linear_svc": LinearSVC(class_weight="balanced", random_state=42),
        "tfidf_multinomial_nb": MultinomialNB(),
    }
    results = {}
    best_name = None
    best_model = None
    best_score = -1.0
    best_prob_name = None
    best_prob_model = None
    best_prob_score = -1.0
    for name, model in candidates.items():
        try:
            model.fit(x_train_vec, y_train)
            predictions = list(model.predict(x_test_vec))
            metrics = _metrics(y_test, predictions, labels)
            results[name] = {"status": "success", "metrics": metrics}
            if metrics["macro_f1"] > best_score:
                best_name = name
                best_model = model
                best_score = metrics["macro_f1"]
            if hasattr(model, "predict_proba") and metrics["macro_f1"] > best_prob_score:
                best_prob_name = name
                best_prob_model = model
                best_prob_score = metrics["macro_f1"]
        except Exception as exc:
            results[name] = {"status": "skipped", "reason": f"{type(exc).__name__}: {exc}"}

    runtime_model = best_prob_model or best_model
    runtime_name = best_prob_name or best_name

    if runtime_model is not None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        _save_pickle(MODEL_PATH, runtime_model)
        _save_pickle(VECTORIZER_PATH, vectorizer)

    meta = {
        "model_type": runtime_name,
        "best_comparison_model": best_name,
        "runtime_selection_reason": "Prefer best predict_proba model for confidence-threshold fallback; non-probabilistic SVC remains comparison-only.",
        "confidence_threshold": 0.55,
        "labels": labels,
        "model_path": str(MODEL_PATH),
        "vectorizer_path": str(VECTORIZER_PATH),
        "dataset": str(CSV_INPUT),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    report = {
        "status": "success" if runtime_model is not None else "warning",
        "module": "doubt_intent_classifier_training",
        "dataset": {
            "path": str(CSV_INPUT),
            "row_count": len(rows),
            "label_distribution": dict(label_counts),
            "train_count": len(y_train),
            "test_count": len(y_test),
        },
        "models": results,
        "best_model": runtime_name,
        "best_comparison_model": best_name,
        "artifacts": {
            "model": str(MODEL_PATH),
            "vectorizer": str(VECTORIZER_PATH),
            "meta": str(META_PATH),
        },
        "confidence_calibration_note": "LogisticRegression probabilities are used when available; threshold 0.55 triggers fallback below confidence.",
    }
    _write_reports(report)
    return report


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Doubt Intent Classifier Training Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Best model: {report.get('best_model')}",
        f"- Dataset: {report.get('dataset', {}).get('path')}",
        "",
        "## Models",
        "",
    ]
    for name, result in (report.get("models") or {}).items():
        lines.append(f"- {name}: {result.get('status')} {result.get('metrics', result.get('reason', ''))}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = train_classifier()
    print(f"STATUS: {report['status']}")
    print("MODULE: doubt_intent_classifier_training")
    print(f"BEST_MODEL: {report.get('best_model')}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
