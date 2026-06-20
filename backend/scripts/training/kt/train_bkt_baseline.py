from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.knowledge_state.bkt.bkt_baseline import BKTModel, BKTParams, fit_bkt_params_grid


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
MODEL_OUTPUT = Path("models/kt/bkt_baseline.json")
JSON_REPORT = Path("evaluation_outputs/json/bkt_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/bkt_training_report.md")


def _load_rows() -> list[dict[str, Any]]:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()

    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _auc(y_true: list[int], y_prob: list[float]) -> float | None:
    try:
        from sklearn.metrics import roc_auc_score

        if len(set(y_true)) < 2:
            return None
        return float(roc_auc_score(y_true, y_prob))
    except Exception:
        return None


def _metrics(y_true: list[int], y_prob: list[float]) -> dict[str, Any]:
    if not y_true:
        return {
            "accuracy": None,
            "auc": None,
            "log_loss": None,
            "brier_score": None,
            "rmse": None,
        }
    eps = 1e-6
    y_prob = [max(eps, min(1.0 - eps, float(p))) for p in y_prob]
    labels = [1 if p >= 0.5 else 0 for p in y_prob]
    accuracy = sum(1 for y, pred in zip(y_true, labels) if y == pred) / len(y_true)
    log_loss = mean([-(y * math.log(p) + (1 - y) * math.log(1 - p)) for y, p in zip(y_true, y_prob)])
    brier = mean([(p - y) ** 2 for y, p in zip(y_true, y_prob)])
    return {
        "accuracy": round(accuracy, 6),
        "auc": None if _auc(y_true, y_prob) is None else round(_auc(y_true, y_prob), 6),
        "log_loss": round(log_loss, 6),
        "brier_score": round(brier, 6),
        "rmse": round(math.sqrt(brier), 6),
    }


def _train_params(rows: list[dict[str, Any]]) -> BKTModel:
    train_by_concept: dict[str, list[int]] = defaultdict(list)
    global_correctness: list[int] = []
    for row in rows:
        if row.get("split") != "train":
            continue
        correct = _safe_int(row.get("is_correct"))
        concept_id = str(row.get("concept_id"))
        train_by_concept[concept_id].append(correct)
        global_correctness.append(correct)

    global_params = fit_bkt_params_grid(_bounded_sample(global_correctness, max_items=5000))
    concept_params: dict[str, BKTParams] = {}
    for concept_id, correctness in train_by_concept.items():
        if len(correctness) >= 100:
            concept_params[concept_id] = fit_bkt_params_grid(_bounded_sample(correctness, max_items=1500))
        else:
            concept_params[concept_id] = global_params
    return BKTModel(concept_params=concept_params, global_params=global_params)


def _bounded_sample(values: list[int], max_items: int) -> list[int]:
    if len(values) <= max_items:
        return values
    stride = max(1, len(values) // max_items)
    sampled = values[::stride][:max_items]
    return sampled or values[-max_items:]


def _evaluate(model: BKTModel, rows: list[dict[str, Any]], split: str) -> dict[str, Any]:
    y_true: list[int] = []
    y_prob: list[float] = []
    eval_model = BKTModel(model.concept_params, model.global_params)

    for row in rows:
        learner_id = str(row.get("learner_id"))
        concept_id = str(row.get("concept_id"))
        correct = _safe_int(row.get("is_correct"))
        if row.get("split") == split:
            y_true.append(correct)
            y_prob.append(eval_model.predict(learner_id, concept_id))
        eval_model.update(learner_id, concept_id, correct)

    output = _metrics(y_true, y_prob)
    output["row_count"] = len(y_true)
    return output


def train_bkt() -> dict[str, Any]:
    rows = _load_rows()
    model = _train_params(rows)
    report = {
        "status": "success",
        "module": "train_bkt_baseline",
        "model_output": str(MODEL_OUTPUT),
        "train_metrics": _evaluate(model, rows, "train"),
        "val_metrics": _evaluate(model, rows, "val"),
        "test_metrics": _evaluate(model, rows, "test"),
        "global_params": model.global_params.to_dict(),
        "concept_count": len(model.concept_params),
    }

    MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MODEL_OUTPUT.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")

    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# BKT Baseline Training Report",
        "",
        f"Status: **{report['status']}**",
        f"Model: `{MODEL_OUTPUT}`",
        "",
        "## Metrics",
        "",
    ]
    for split in ["train", "val", "test"]:
        metrics = report[f"{split}_metrics"]
        lines.append(
            f"- {split}: accuracy={metrics['accuracy']}, auc={metrics['auc']}, "
            f"log_loss={metrics['log_loss']}, brier={metrics['brier_score']}, rmse={metrics['rmse']}, rows={metrics['row_count']}"
        )
    lines.extend(
        [
            "",
            "## Parameters",
            "",
            f"- Global params: `{report['global_params']}`",
            f"- Concept-specific parameter sets: {report['concept_count']}",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    train_bkt()
    print("STATUS: success")
    print("MODULE: train_bkt_baseline")
    print(f"MODEL_OUTPUT: {MODEL_OUTPUT}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
