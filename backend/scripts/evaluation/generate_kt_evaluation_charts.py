from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib.pyplot as plt


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
DB_PATH = Path("external/core_data/tutor.db")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/kt_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/kt_visualization_report.md")
KT_SUMMARY = Path("evaluation_outputs/json/kt_training_data_summary.json")
FULL_COMPARISON = Path("evaluation_outputs/json/kt_full_model_comparison_report.json")
DKT_REPORT = Path("evaluation_outputs/json/dkt_runtime_training_report.json")
SAKT_REPORT = Path("evaluation_outputs/json/sakt_training_report.json")


def _ensure_training_data() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()


def _load_rows() -> list[dict[str, Any]]:
    _ensure_training_data()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _save_plot(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _chart_correctness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter("correct" if _safe_int(row.get("is_correct")) else "incorrect" for row in rows)
    path = CHART_DIR / "kt_correctness_distribution.png"
    plt.figure(figsize=(6, 4))
    plt.bar(list(counts.keys()), list(counts.values()))
    plt.title("KT Correctness Distribution")
    plt.ylabel("Interactions")
    _save_plot(path)
    return {"path": str(path), "counts": dict(counts)}


def _chart_sequence_lengths(rows: list[dict[str, Any]]) -> dict[str, Any]:
    learner_lengths = Counter(str(row.get("learner_id")) for row in rows)
    lengths = list(learner_lengths.values())
    path = CHART_DIR / "kt_sequence_length_histogram.png"
    plt.figure(figsize=(7, 4))
    plt.hist(lengths, bins=30)
    plt.title("KT Sequence Lengths per Learner")
    plt.xlabel("Interactions per learner")
    plt.ylabel("Learner count")
    _save_plot(path)
    return {
        "path": str(path),
        "learner_count": len(lengths),
        "min": min(lengths) if lengths else 0,
        "max": max(lengths) if lengths else 0,
        "mean": round(mean(lengths), 4) if lengths else 0,
    }


def _chart_model_comparison() -> dict[str, Any]:
    report = _load_json(FULL_COMPARISON)
    models = report.get("models") or {}
    metrics = ["log_loss", "brier_score", "rmse"]
    labels = []
    values_by_metric = {metric: [] for metric in metrics}
    for model_name, data in models.items():
        if not isinstance(data, dict):
            continue
        if all(data.get(metric) is None for metric in metrics):
            continue
        labels.append(model_name)
        for metric in metrics:
            values_by_metric[metric].append(float(data.get(metric) or 0.0))

    path = CHART_DIR / "kt_model_comparison.png"
    plt.figure(figsize=(9, 4.8))
    x_positions = list(range(len(labels)))
    width = 0.25
    for offset, metric in enumerate(metrics):
        shifted = [x + (offset - 1) * width for x in x_positions]
        plt.bar(shifted, values_by_metric[metric], width=width, label=metric)
    plt.title("KT Model Comparison")
    plt.ylabel("Metric value")
    plt.xticks(x_positions, labels, rotation=20, ha="right")
    plt.legend()
    _save_plot(path)
    return {"path": str(path), "models": labels, "metrics": metrics}


def _latest_mastery_values() -> list[float]:
    if not DB_PATH.exists():
        return []
    values: list[float] = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT state_json
                FROM knowledge_state
                WHERE state_json IS NOT NULL
                """
            ).fetchall()
        for (state_json,) in rows:
            try:
                state = json.loads(state_json)
            except Exception:
                continue
            concepts = state.get("concepts") or {}
            if isinstance(concepts, dict):
                for concept_state in concepts.values():
                    if isinstance(concept_state, dict) and concept_state.get("mastery") is not None:
                        values.append(float(concept_state["mastery"]))
    except Exception:
        return []
    return [value for value in values if 0.0 <= value <= 1.0]


def _chart_mastery_distribution() -> dict[str, Any]:
    values = _latest_mastery_values()
    path = CHART_DIR / "kt_mastery_distribution.png"
    plt.figure(figsize=(7, 4))
    if values:
        plt.hist(values, bins=20, range=(0, 1))
    else:
        plt.text(0.5, 0.5, "No persisted mastery values available", ha="center", va="center")
        plt.xlim(0, 1)
        plt.ylim(0, 1)
    plt.title("KT Mastery Distribution")
    plt.xlabel("Mastery")
    plt.ylabel("Count")
    _save_plot(path)
    return {"path": str(path), "mastery_count": len(values), "mean_mastery": round(mean(values), 6) if values else None}


def _extract_history_losses(report: dict[str, Any]) -> list[float]:
    history = report.get("training_history")
    if isinstance(history, dict):
        epochs = history.get("epochs") or []
    elif isinstance(history, list):
        epochs = history
    else:
        epochs = []
    losses = []
    for item in epochs:
        if not isinstance(item, dict):
            continue
        value = item.get("train_loss")
        if value is not None:
            losses.append(float(value))
    return losses


def _chart_loss_curve() -> dict[str, Any]:
    dkt_losses = _extract_history_losses(_load_json(DKT_REPORT))
    sakt_losses = _extract_history_losses(_load_json(SAKT_REPORT))
    path = CHART_DIR / "kt_loss_curve.png"
    plt.figure(figsize=(7, 4))
    plotted = []
    if dkt_losses:
        plt.plot(range(1, len(dkt_losses) + 1), dkt_losses, marker="o", label="DKT train loss")
        plotted.append("dkt")
    if sakt_losses:
        plt.plot(range(1, len(sakt_losses) + 1), sakt_losses, marker="o", label="SAKT train loss")
        plotted.append("sakt")
    if not plotted:
        plt.text(0.5, 0.5, "No KT training history available", ha="center", va="center")
    plt.title("KT Training Loss Curve")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    if plotted:
        plt.legend()
    _save_plot(path)
    return {"path": str(path), "series": plotted}


def _fallback_test_predictions(rows: list[dict[str, Any]]) -> tuple[list[int], list[float]]:
    learner_concept_stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    global_seen = [0, 0]
    y_true: list[int] = []
    y_prob: list[float] = []
    for row in rows:
        learner_id = str(row.get("learner_id"))
        concept_id = str(row.get("concept_id"))
        correct = _safe_int(row.get("is_correct"))
        key = (learner_id, concept_id)
        seen_correct, seen_total = learner_concept_stats[key]
        global_correct, global_total = global_seen
        if row.get("split") == "test":
            if seen_total:
                prob = (seen_correct + 1) / (seen_total + 2)
            else:
                prob = (global_correct + 1) / (global_total + 2) if global_total else 0.5
            y_true.append(correct)
            y_prob.append(prob)
        learner_concept_stats[key][0] += correct
        learner_concept_stats[key][1] += 1
        global_seen[0] += correct
        global_seen[1] += 1
    return y_true, y_prob


def _chart_calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y_true, y_prob = _fallback_test_predictions(rows)
    path = CHART_DIR / "kt_calibration_curve.png"
    if not y_true:
        return {"path": None, "status": "skipped", "reason": "No test labels available for calibration."}
    bins = [[] for _ in range(10)]
    for label, prob in zip(y_true, y_prob):
        idx = min(9, max(0, int(math.floor(prob * 10))))
        bins[idx].append((label, prob))
    expected = []
    observed = []
    for bucket in bins:
        if not bucket:
            continue
        labels = [item[0] for item in bucket]
        probs = [item[1] for item in bucket]
        expected.append(mean(probs))
        observed.append(mean(labels))

    plt.figure(figsize=(5.5, 5))
    plt.plot([0, 1], [0, 1], linestyle="--", label="perfect calibration")
    plt.plot(expected, observed, marker="o", label="fallback test bins")
    plt.title("KT Calibration Curve")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed correctness")
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.legend()
    _save_plot(path)
    return {"path": str(path), "status": "success", "bin_count": len(expected)}


def build_charts() -> dict[str, Any]:
    rows = _load_rows()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "correctness_distribution": _chart_correctness(rows),
        "sequence_length_histogram": _chart_sequence_lengths(rows),
        "model_comparison": _chart_model_comparison(),
        "mastery_distribution": _chart_mastery_distribution(),
        "loss_curve": _chart_loss_curve(),
        "calibration_curve": _chart_calibration(rows),
    }
    warnings = []
    if charts["calibration_curve"].get("status") == "skipped":
        warnings.append(str(charts["calibration_curve"].get("reason")))
    if not charts["mastery_distribution"].get("mastery_count"):
        warnings.append("No persisted mastery values were available for mastery distribution.")

    report = {
        "status": "warning" if warnings else "success",
        "module": "kt_evaluation_charts",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "data_sources": {
            "training_csv": str(CSV_INPUT),
            "kt_summary": str(KT_SUMMARY),
            "full_comparison_report": str(FULL_COMPARISON),
            "dkt_training_report": str(DKT_REPORT),
            "sakt_training_report": str(SAKT_REPORT),
        },
        "notes": [
            "Charts use current tutor.db-derived KT data, not old EdNet/ASSISTments artifacts.",
            "Calibration curve uses chronological cumulative fallback probabilities because raw DKT test probabilities are not persisted.",
        ],
        "warnings": warnings,
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# KT Visualization Report",
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
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: kt_evaluation_charts")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
