from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.evaluation.semantic_answer_evaluator import SemanticAnswerEvaluator


CSV_INPUT = Path("evaluation_outputs/csv/semantic_answer_benchmark.csv")
JSON_REPORT = Path("evaluation_outputs/json/semantic_answer_benchmark_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_answer_benchmark_report.md")
LABELS = ["strong", "partial", "weak"]


def _load_rows() -> list[dict[str, Any]]:
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _key_points(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _confusion_matrix(y_true: list[str], y_pred: list[str]) -> list[list[int]]:
    index = {label: idx for idx, label in enumerate(LABELS)}
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for true, pred in zip(y_true, y_pred):
        if true in index and pred in index:
            matrix[index[true]][index[pred]] += 1
    return matrix


def _precision_recall_f1(matrix: list[list[int]]) -> dict[str, Any]:
    per_label = {}
    f1_values = []
    weighted_f1_values = []
    supports = []
    for idx, label in enumerate(LABELS):
        tp = matrix[idx][idx]
        fp = sum(matrix[row][idx] for row in range(len(LABELS)) if row != idx)
        fn = sum(matrix[idx][col] for col in range(len(LABELS)) if col != idx)
        support = sum(matrix[idx])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": support,
        }
        f1_values.append(f1)
        weighted_f1_values.append(f1 * support)
        supports.append(support)
    macro_f1 = sum(f1_values) / len(f1_values) if f1_values else 0.0
    weighted_f1 = sum(weighted_f1_values) / sum(supports) if sum(supports) else 0.0
    return {
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "per_label": per_label,
    }


def evaluate_benchmark() -> dict[str, Any]:
    rows = _load_rows()
    evaluator = SemanticAnswerEvaluator()
    results = []
    for row in rows:
        output = evaluator.evaluate(
            learner_answer=row.get("learner_answer"),
            expected_answer=row.get("reference_answer"),
            key_points=_key_points(row.get("key_points", "")),
            concept_name=row.get("concept_name"),
            task_type=row.get("task_type") or "explanation",
        )
        expected_label = str(row.get("expected_label") or "").strip()
        expected_score = _safe_float(row.get("expected_score"))
        results.append(
            {
                **row,
                "expected_score": expected_score,
                "predicted_label": output["label"],
                "predicted_score": output["score"],
                "semantic_similarity": output["semantic_similarity"],
                "key_point_coverage": output["key_point_coverage"],
                "rubric_score": output["rubric_score"],
                "structure_score": output["structure_score"],
                "method": output["method"],
                "label_correct": output["label"] == expected_label,
                "absolute_score_error": round(abs(float(output["score"]) - expected_score), 6),
            }
        )

    y_true = [item["expected_label"] for item in results]
    y_pred = [item["predicted_label"] for item in results]
    matrix = _confusion_matrix(y_true, y_pred)
    f1 = _precision_recall_f1(matrix)
    accuracy = sum(1 for true, pred in zip(y_true, y_pred) if true == pred) / len(y_true) if y_true else 0.0
    per_task = {}
    task_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        task_buckets[item["task_type"]].append(item)
    for task_type, task_rows in task_buckets.items():
        per_task[task_type] = round(
            sum(1 for item in task_rows if item["label_correct"]) / len(task_rows),
            6,
        )

    accuracy = round(accuracy, 6)
    report = {
        "status": "warning" if accuracy < 0.6 else "success",
        "module": "semantic_answer_benchmark",
        "benchmark_csv": str(CSV_INPUT),
        "case_count": len(results),
        "accuracy": accuracy,
        "macro_f1": f1["macro_f1"],
        "weighted_f1": f1["weighted_f1"],
        "per_label_metrics": f1["per_label"],
        "confusion_matrix": matrix,
        "labels": LABELS,
        "average_absolute_score_error": round(mean([item["absolute_score_error"] for item in results]), 6) if results else 0.0,
        "label_distribution": {
            "expected": dict(Counter(y_true)),
            "predicted": dict(Counter(y_pred)),
        },
        "method_distribution": dict(Counter(item["method"] for item in results)),
        "per_task_accuracy": per_task,
        "results": results,
        "limitations": [
            "Benchmark examples are curated project-specific examples, not a large human-annotated dataset.",
            "Expected scores are approximate review targets and should be calibrated with more labeled answers.",
            "The evaluator may be stricter for short partially correct answers because key-point coverage is explicit.",
        ],
        "calibration_note": (
            "Low benchmark accuracy means the current SemanticAnswerEvaluator is conservative against this curated "
            "benchmark. This should drive threshold/key-point calibration instead of being hidden."
        ),
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Answer Benchmark Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Cases: {report['case_count']}",
        f"- Accuracy: {report['accuracy']}",
        f"- Macro-F1: {report['macro_f1']}",
        f"- Weighted-F1: {report['weighted_f1']}",
        f"- Average absolute score error: {report['average_absolute_score_error']}",
        f"- Label distribution: {report['label_distribution']}",
        f"- Method distribution: {report['method_distribution']}",
        "",
        "## Per-Task Accuracy",
        "",
    ]
    for task_type, value in report["per_task_accuracy"].items():
        lines.append(f"- {task_type}: {value}")
    lines.extend(["", "## Confusion Matrix", "", f"Labels: {report['labels']}", "", str(report["confusion_matrix"]), "", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.extend(["", "## Calibration Note", "", report["calibration_note"]])
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = evaluate_benchmark()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: semantic_answer_benchmark")
    print(f"ACCURACY: {report['accuracy']}")
    print(f"MACRO_F1: {report['macro_f1']}")
    print(f"WEIGHTED_F1: {report['weighted_f1']}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
