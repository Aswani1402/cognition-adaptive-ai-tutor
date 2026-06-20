from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tutor.doubt.doubt_intent_classifier import DoubtIntentClassifier, META_PATH, MODEL_PATH, VECTORIZER_PATH


TRAINING_REPORT = Path("evaluation_outputs/json/doubt_intent_training_report.json")
JSON_REPORT = Path("evaluation_outputs/json/doubt_classifier_report.json")
MD_REPORT = Path("evaluation_outputs/reports/doubt_classifier_report.md")

SAMPLE_CASES = [
    "I don't understand SELECT",
    "Why is this loop syntax invalid?",
    "My stack pop code gives an error",
    "What will this code print?",
    "Give me another HTML form example",
    "What is the difference between commit and branch?",
    "Where do we use branches in projects?",
    "I forgot variables, recap it",
    "Give me a harder loop problem",
    "What should I study after arrays?",
    "I am confused",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_report() -> dict[str, Any]:
    if not TRAINING_REPORT.exists():
        from scripts.training.doubt.train_doubt_intent_classifier import train_classifier

        train_classifier()
    training = _load_json(TRAINING_REPORT)
    meta = _load_json(META_PATH)
    best_model = training.get("best_model")
    best_metrics = ((training.get("models") or {}).get(best_model) or {}).get("metrics") or {}

    clf = DoubtIntentClassifier().load()
    sample_outputs = [clf.predict(text) for text in SAMPLE_CASES]
    fallback_rate = sum(1 for item in sample_outputs if item.get("fallback_used")) / len(sample_outputs)

    report = {
        "status": "success" if MODEL_PATH.exists() and VECTORIZER_PATH.exists() else "warning",
        "module": "doubt_classifier_report",
        "model_availability": {
            "model": MODEL_PATH.exists(),
            "vectorizer": VECTORIZER_PATH.exists(),
            "meta": META_PATH.exists(),
        },
        "best_model": best_model,
        "dataset_size": (training.get("dataset") or {}).get("row_count"),
        "intent_classes": meta.get("labels") or best_metrics.get("labels"),
        "accuracy": best_metrics.get("accuracy"),
        "macro_f1": best_metrics.get("macro_f1"),
        "weighted_f1": best_metrics.get("weighted_f1"),
        "per_class_precision": best_metrics.get("per_class_precision"),
        "per_class_recall": best_metrics.get("per_class_recall"),
        "confusion_matrix": best_metrics.get("confusion_matrix"),
        "confidence_threshold": meta.get("confidence_threshold", 0.55),
        "fallback_rate_on_sample_cases": round(fallback_rate, 6),
        "sample_outputs": sample_outputs,
        "current_integration_status": "Classifier is available and can be attached to CogniTutorLM doubt responses additively.",
        "limitations": [
            "Dataset is curated, not collected from real learner production traffic.",
            "Confidence threshold should be recalibrated after real doubt logs are available.",
            "Fallback routing is retained only for low confidence or missing-model safety.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Doubt Classifier Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Best model: {report['best_model']}",
        f"- Dataset size: {report['dataset_size']}",
        f"- Accuracy: {report['accuracy']}",
        f"- Macro-F1: {report['macro_f1']}",
        f"- Weighted-F1: {report['weighted_f1']}",
        f"- Confidence threshold: {report['confidence_threshold']}",
        f"- Sample fallback rate: {report['fallback_rate_on_sample_cases']}",
        "",
        "## Limitations",
        "",
    ]
    for item in report["limitations"]:
        lines.append(f"- {item}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: doubt_classifier_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
