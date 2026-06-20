from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.knowledge_state.bkt.bkt_baseline import BKTModel


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
BKT_MODEL = Path("models/kt/bkt_baseline.json")
DKT_MODEL = Path("models/dkt/model.pt")
DKT_ID_MAP = Path("models/dkt/id_map.json")
DKT_REPORT = Path("evaluation_outputs/json/dkt_runtime_training_report.json")
SAKT_MODEL = Path("models/kt/sakt_model.pt")
SAKT_META = Path("models/kt/sakt_meta.json")
JSON_REPORT = Path("evaluation_outputs/json/kt_full_model_comparison_report.json")
MD_REPORT = Path("evaluation_outputs/reports/kt_full_model_comparison_report.md")


def _ensure_inputs() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()
    if not BKT_MODEL.exists():
        from scripts.training.kt.train_bkt_baseline import train_bkt

        train_bkt()


def _load_rows() -> list[dict[str, Any]]:
    _ensure_inputs()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
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
            "rmse": None,
            "brier_score": None,
            "row_count": 0,
        }
    eps = 1e-6
    y_prob = [max(eps, min(1.0 - eps, float(p))) for p in y_prob]
    y_pred = [1 if p >= 0.5 else 0 for p in y_prob]
    accuracy = sum(1 for y, pred in zip(y_true, y_pred) if y == pred) / len(y_true)
    log_loss = mean([-(y * math.log(p) + (1 - y) * math.log(1 - p)) for y, p in zip(y_true, y_prob)])
    brier = mean([(p - y) ** 2 for y, p in zip(y_true, y_prob)])
    auc = _auc(y_true, y_prob)
    return {
        "accuracy": round(accuracy, 6),
        "auc": None if auc is None else round(auc, 6),
        "log_loss": round(log_loss, 6),
        "rmse": round(math.sqrt(brier), 6),
        "brier_score": round(brier, 6),
        "row_count": len(y_true),
    }


def _evaluate_fallback(rows: list[dict[str, Any]]) -> dict[str, Any]:
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
    metrics = _metrics(y_true, y_prob)
    metrics["model_status"] = "available"
    metrics["runtime_integration_readiness"] = "already_runtime_fallback"
    return metrics


def _evaluate_bkt(rows: list[dict[str, Any]]) -> dict[str, Any]:
    model_data = json.loads(BKT_MODEL.read_text(encoding="utf-8"))
    model = BKTModel.from_dict(model_data)
    y_true: list[int] = []
    y_prob: list[float] = []
    for row in rows:
        learner_id = str(row.get("learner_id"))
        concept_id = str(row.get("concept_id"))
        correct = _safe_int(row.get("is_correct"))
        if row.get("split") == "test":
            y_true.append(correct)
            y_prob.append(model.predict(learner_id, concept_id))
        model.update(learner_id, concept_id, correct)
    metrics = _metrics(y_true, y_prob)
    metrics["model_status"] = "trained"
    metrics["runtime_integration_readiness"] = "runtime_priority_2_when_dkt_missing_or_fails"
    return metrics


def _artifact_status(model_path: Path, id_map_path: Path | None = None) -> dict[str, Any]:
    exists = model_path.exists() and (id_map_path is None or id_map_path.exists())
    return {
        "model_status": "artifact_available" if exists else "artifact_missing",
        "accuracy": None,
        "auc": None,
        "log_loss": None,
        "rmse": None,
        "brier_score": None,
        "row_count": 0,
        "runtime_integration_readiness": "ready_for_runtime_check" if exists else "pending",
    }


def _evaluate_dkt_artifact() -> dict[str, Any]:
    status = _artifact_status(DKT_MODEL, DKT_ID_MAP)
    if status["model_status"] == "artifact_missing":
        return status
    if not DKT_REPORT.exists():
        status["model_status"] = "artifact_available_report_missing"
        status["runtime_integration_readiness"] = "artifact_ready_runtime_priority_1"
        return status

    try:
        report = json.loads(DKT_REPORT.read_text(encoding="utf-8"))
        test_metrics = (report.get("metrics") or {}).get("test") or {}
        return {
            "model_status": "trained_current_tutor_artifact",
            "accuracy": test_metrics.get("accuracy"),
            "auc": test_metrics.get("auc"),
            "log_loss": test_metrics.get("log_loss"),
            "rmse": test_metrics.get("rmse"),
            "brier_score": test_metrics.get("brier_score"),
            "row_count": test_metrics.get("row_count", 0),
            "runtime_integration_readiness": "runtime_priority_1_dkt_current_tutor_runtime",
            "artifact": {"model": str(DKT_MODEL), "id_map": str(DKT_ID_MAP)},
        }
    except Exception as exc:
        status["model_status"] = "artifact_available_report_unreadable"
        status["runtime_integration_readiness"] = f"artifact_ready_but_report_unreadable: {exc}"
        return status


def _evaluate_sakt_artifact() -> dict[str, Any]:
    status = _artifact_status(SAKT_MODEL)
    if status["model_status"] == "artifact_missing":
        return status
    if not SAKT_META.exists():
        status["model_status"] = "artifact_available_meta_missing"
        status["runtime_integration_readiness"] = "comparison_artifact_only_meta_missing"
        return status
    try:
        meta = json.loads(SAKT_META.read_text(encoding="utf-8"))
        test_metrics = (meta.get("metrics") or {}).get("test") or {}
        return {
            "model_status": "trained_comparison_artifact",
            "accuracy": test_metrics.get("accuracy"),
            "auc": test_metrics.get("auc"),
            "log_loss": test_metrics.get("log_loss"),
            "rmse": test_metrics.get("rmse"),
            "brier_score": test_metrics.get("brier_score"),
            "row_count": test_metrics.get("row_count", 0),
            "runtime_integration_readiness": "comparison_only_not_runtime_default",
            "artifact": {"model": str(SAKT_MODEL), "meta": str(SAKT_META)},
        }
    except Exception as exc:
        status["model_status"] = "artifact_available_meta_unreadable"
        status["runtime_integration_readiness"] = f"comparison_artifact_unreadable: {exc}"
        return status


def build_report() -> dict[str, Any]:
    rows = _load_rows()
    fallback = _evaluate_fallback(rows)
    bkt = _evaluate_bkt(rows)
    dkt = _evaluate_dkt_artifact()
    sakt = _evaluate_sakt_artifact()

    missing = []
    if dkt["model_status"] == "artifact_missing":
        missing.append("DKT artifact missing: models/dkt/model.pt and/or models/dkt/id_map.json")
    if sakt["model_status"] == "artifact_missing":
        missing.append("SAKT artifact missing: models/kt/sakt_model.pt")

    status = "warning" if missing else "success"
    return {
        "status": status,
        "module": "kt_full_model_comparison_report",
        "models": {
            "fallback_cumulative": fallback,
            "bkt_baseline": bkt,
            "dkt": dkt,
            "sakt": sakt,
        },
        "calibration_note": (
            "Brier score and log loss are used as calibration-sensitive metrics. "
            "A dedicated reliability curve should be added after DKT/SAKT artifacts exist."
        ),
        "sequence_prediction_quality_note": (
            "Fallback and BKT are evaluated chronologically on held-out tail interactions per learner. "
            "DKT is evaluated with its current-project runtime artifact when present. "
            "SAKT is evaluated as a comparison model when its artifact and metadata are present."
        ),
        "runtime_integration_readiness": {
            "current_runtime": "dkt_inference.py uses current tutor DKT artifacts first, BKT second, and fallback_cumulative last.",
            "bkt": "trained baseline artifact is runtime priority 2 when DKT is unavailable or fails.",
            "dkt": dkt["runtime_integration_readiness"],
            "sakt": sakt["runtime_integration_readiness"],
        },
        "final_recommendation": {
            "primary_runtime_model": "current tutor DKT if models/dkt/model.pt and id_map.json are available and stable",
            "baseline": "BKT baseline",
            "safety_fallback": "fallback_cumulative",
            "sakt": "comparison model if trained; future runtime candidate after stability checks",
        },
        "dataset_source": str(CSV_INPUT),
        "old_phase1_dkt_note": (
            "Old AI_TUTOR EdNet/ASSISTments DKT artifacts are Phase-1 external artifacts only. "
            "They are not direct current-runtime models because their skill mappings do not match current tutor concepts."
        ),
        "warnings": missing,
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# KT Full Model Comparison Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Model Metrics",
        "",
    ]
    for model_name, metrics in report["models"].items():
        lines.append(
            f"- {model_name}: status={metrics.get('model_status')}, accuracy={metrics.get('accuracy')}, "
            f"auc={metrics.get('auc')}, log_loss={metrics.get('log_loss')}, "
            f"rmse={metrics.get('rmse')}, brier={metrics.get('brier_score')}, rows={metrics.get('row_count')}"
        )
    lines.extend(
        [
            "",
            "## Calibration",
            "",
            report["calibration_note"],
            "",
            "## Sequence Prediction",
            "",
            report["sequence_prediction_quality_note"],
            "",
            "## Runtime Integration Readiness",
            "",
        ]
    )
    for key, value in report["runtime_integration_readiness"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Final Recommendation",
            "",
            f"- Primary runtime model: {report['final_recommendation']['primary_runtime_model']}",
            f"- Baseline: {report['final_recommendation']['baseline']}",
            f"- Safety fallback: {report['final_recommendation']['safety_fallback']}",
            f"- SAKT: {report['final_recommendation']['sakt']}",
            "",
            "## Phase-1 External DKT Note",
            "",
            report["old_phase1_dkt_note"],
        ]
    )
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: kt_full_model_comparison_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
