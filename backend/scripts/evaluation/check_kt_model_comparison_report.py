from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.knowledge_state.update import update_knowledge_state


DB_PATH = Path("external/core_data/tutor.db")
DATASET_REPORT_PATH = Path("evaluation_outputs/json/kt_behaviour_dataset_readiness_report.json")
SCHEMA_REPORT_PATH = Path("evaluation_outputs/json/kt_state_schema_runtime_report.json")
OUTPUT_JSON = Path("evaluation_outputs/json/kt_model_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/kt_model_comparison_report.md")

DKT_ARTIFACT_CANDIDATES = [
    Path("models/dkt/model.pt"),
    Path("models/dkt/id_map.json"),
    Path("external/models/dkt/skillbuilder_v1/model.pt"),
    Path("external/models/dkt/skillbuilder_v1/id_map.json"),
    Path("external/models/dkt/model.pt"),
    Path("external/models/dkt/id_map.json"),
]
SEARCH_ROOTS = [
    Path("tutor/knowledge_state"),
    Path("scripts/training/dkt"),
    Path("models"),
    Path("external/models"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("exists", True)
            return data
        return {"exists": True, "value": data}
    except Exception as exc:
        return {"exists": True, "status": "error", "error": str(exc)}


def _connect_readonly() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _runtime_status() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {
            "status": "error",
            "error": "tutor.db not found",
        }
    try:
        with sqlite3.connect(DB_PATH) as conn:
            output = update_knowledge_state(conn, learner_id="14")
        data = output.get("data", {}) if isinstance(output, dict) else {}
        return {
            "status": output.get("status", "error") if isinstance(output, dict) else "error",
            "learner_id": output.get("learner_id", "14") if isinstance(output, dict) else "14",
            "schema_version": data.get("schema_version"),
            "source": data.get("source"),
            "model_used": data.get("model_used"),
            "fallback_used": data.get("fallback_used"),
            "sequence_length": data.get("sequence_length"),
            "predicted_mastery_last": data.get("predicted_mastery_last"),
            "written_state": data.get("written_state"),
            "inference_error": data.get("inference_error"),
            "state_json_schema_version": (data.get("state_json") or {}).get("schema_version")
            if isinstance(data.get("state_json"), dict)
            else None,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


def _dataset_status() -> dict[str, Any]:
    existing_report = _load_json(DATASET_REPORT_PATH)
    status = {
        "readiness_report": existing_report,
        "assistments_csv_exists": Path("external/dataset/assistments.csv").exists(),
        "tutor_db_exists": DB_PATH.exists(),
        "quiz_results_rows": None,
        "learner_count": None,
        "concept_count": None,
        "sequence_length_stats": {},
        "required_runtime_columns": [],
        "missing_runtime_columns": [],
    }
    if not DB_PATH.exists():
        return status

    required_columns = ["learner_id", "concept_id", "is_correct"]
    with _connect_readonly() as conn:
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(quiz_results)").fetchall()]
        status["required_runtime_columns"] = required_columns
        status["missing_runtime_columns"] = [col for col in required_columns if col not in cols]
        status["quiz_results_rows"] = conn.execute("SELECT COUNT(*) AS n FROM quiz_results").fetchone()["n"]
        status["learner_count"] = conn.execute(
            "SELECT COUNT(DISTINCT learner_id) AS n FROM quiz_results"
        ).fetchone()["n"]
        status["concept_count"] = conn.execute(
            "SELECT COUNT(DISTINCT concept_id) AS n FROM quiz_results"
        ).fetchone()["n"]
        seq_rows = conn.execute(
            """
            SELECT learner_id, COUNT(*) AS n
            FROM quiz_results
            GROUP BY learner_id
            """
        ).fetchall()

    lengths = [int(row["n"]) for row in seq_rows]
    if lengths:
        status["sequence_length_stats"] = {
            "min": min(lengths),
            "avg": round(sum(lengths) / len(lengths), 4),
            "max": max(lengths),
        }
    return status


def _schema_status() -> dict[str, Any]:
    return _load_json(SCHEMA_REPORT_PATH)


def _artifact_status() -> dict[str, Any]:
    dkt_dir = Path("models/dkt")
    discovered = _discover_kt_files()
    return {
        "dkt_expected_paths": [str(path) for path in DKT_ARTIFACT_CANDIDATES],
        "dkt_expected_paths_exist": {
            str(path): path.exists()
            for path in DKT_ARTIFACT_CANDIDATES
        },
        "models_dkt_dir_exists": dkt_dir.exists(),
        "models_dkt_files": sorted(str(path) for path in dkt_dir.rglob("*") if path.is_file())
        if dkt_dir.exists()
        else [],
        "training_script_exists": Path("scripts/training/dkt/train_dkt_trackA.py").exists(),
        "discovered_kt_files": discovered,
    }


def _discover_kt_files() -> dict[str, list[str]]:
    keywords = ("bkt", "dkt", "sakt", "kt")
    found: dict[str, list[str]] = {keyword: [] for keyword in keywords}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lowered = str(path).lower()
            for keyword in keywords:
                if keyword in lowered:
                    found[keyword].append(str(path))
    return {key: sorted(value)[:100] for key, value in found.items()}


def _implementation_status(artifact_status: dict[str, Any]) -> dict[str, str]:
    discovered = artifact_status.get("discovered_kt_files", {})
    dkt_model_ready = bool(
        artifact_status["dkt_expected_paths_exist"].get("models/dkt/model.pt")
        and artifact_status["dkt_expected_paths_exist"].get("models/dkt/id_map.json")
    )
    return {
        "fallback_cumulative": "backend_ready",
        "bkt": "implemented" if discovered.get("bkt") else "pending",
        "dkt": "model_ready" if dkt_model_ready else "wrapper_ready_artifact_missing",
        "sakt": "implemented" if discovered.get("sakt") else "pending",
        "kt_comparison": "pending",
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _baseline_metrics(limit_rows: int = 50000) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"status": "error", "error": "tutor.db missing"}
    with _connect_readonly() as conn:
        rows = conn.execute(
            """
            SELECT learner_id, concept_id, is_correct
            FROM quiz_results
            WHERE learner_id IS NOT NULL
              AND concept_id IS NOT NULL
              AND is_correct IS NOT NULL
            ORDER BY learner_id, quiz_id
            LIMIT ?
            """,
            (limit_rows,),
        ).fetchall()

    total = len(rows)
    if total < 2:
        return {"status": "warning", "interaction_count": total, "reason": "Not enough rows for baseline metric."}

    attempts: dict[tuple[str, str], list[int]] = {}
    global_correct = 0
    evaluated = 0
    correct_predictions = 0
    squared_error_sum = 0.0
    brier_sum = 0.0
    log_loss_sum = 0.0

    for row in rows:
        learner = str(row["learner_id"])
        concept = str(row["concept_id"])
        actual = 1 if int(row["is_correct"] or 0) else 0
        history = attempts.get((learner, concept), [])

        if history:
            prediction = sum(history) / len(history)
        else:
            prediction = global_correct / evaluated if evaluated else 0.5

        pred_label = 1 if prediction >= 0.5 else 0
        if pred_label == actual:
            correct_predictions += 1
        squared_error_sum += (prediction - actual) ** 2
        brier_sum += (prediction - actual) ** 2
        clipped = min(1.0 - 1e-9, max(1e-9, prediction))
        log_loss_sum += -(actual * math.log(clipped) + (1 - actual) * math.log(1 - clipped))
        evaluated += 1
        global_correct += actual
        attempts.setdefault((learner, concept), []).append(actual)

    concept_ids = {str(row["concept_id"]) for row in rows}
    learner_ids = {str(row["learner_id"]) for row in rows}
    return {
        "status": "success",
        "metric_note": "Transparent cumulative-correctness baseline on ordered runtime quiz_results; not a DKT metric.",
        "interaction_count_used": total,
        "learner_count_used": len(learner_ids),
        "concept_count_used": len(concept_ids),
        "average_correctness": round(global_correct / evaluated, 4) if evaluated else 0.0,
        "cumulative_baseline_accuracy": round(correct_predictions / evaluated, 4) if evaluated else 0.0,
        "rmse": round(math.sqrt(squared_error_sum / evaluated), 4) if evaluated else None,
        "brier_score": round(brier_sum / evaluated, 4) if evaluated else None,
        "log_loss": round(log_loss_sum / evaluated, 4) if evaluated else None,
    }


def _overall_status(report: dict[str, Any]) -> str:
    if report["runtime_status"].get("status") != "success":
        return "error"
    if report["runtime_status"].get("fallback_used"):
        return "warning"
    if report["model_status"].get("dkt") != "model_ready":
        return "warning"
    if report["model_status"].get("bkt") == "pending" or report["model_status"].get("sakt") == "pending":
        return "warning"
    return "success"


def build_report() -> dict[str, Any]:
    runtime = _runtime_status()
    dataset = _dataset_status()
    schema = _schema_status()
    artifacts = _artifact_status()
    model_status = _implementation_status(artifacts)
    report = {
        "status": "warning",
        "module": "KTModelComparisonReport",
        "generated_at": _now_iso(),
        "runtime_status": runtime,
        "dataset_status": dataset,
        "schema_status": schema,
        "artifact_status": artifacts,
        "model_status": model_status,
        "current_baseline_metrics": _baseline_metrics(),
        "research_upgrade_plan": [
            "Prepare ASSISTments CSV or standardize tutor.db quiz_results for KT training.",
            "Standardize learner_id, concept_id/skill_id, correctness, and timestamp/order columns.",
            "Normalize system/content concept mapping before model training.",
            "Train BKT baseline per concept/skill.",
            "Train DKT/LSTM KT model and persist model.pt plus id_map.json.",
            "Train SAKT/attention KT model if enough sequence data is available.",
            "Compare accuracy, AUC, log loss, RMSE/Brier score, calibration, and sequence prediction quality.",
            "Integrate best model through dkt_inference.py while retaining fallback_cumulative safety.",
            "Continue writing KT v2 state_json with source, confidence, model_used, and fallback_used.",
            "Expose dashboard fields: concept-wise mastery vector, mastery_before/mastery_after, confidence, and source label.",
        ],
        "limitations": [
            "Runtime currently uses fallback_cumulative because no usable DKT model artifact was found.",
            "ASSISTments CSV is missing, so current training evidence depends on tutor.db logs.",
            "BKT and SAKT implementations were not found in the current KT module scan.",
            "Current baseline metrics are simple cumulative correctness metrics, not research-grade KT evaluation.",
            "Calibration and sequence-prediction quality require held-out model predictions from trained KT models.",
        ],
    }
    report["status"] = _overall_status(report)
    return report


def _build_markdown(report: dict[str, Any]) -> str:
    runtime = report["runtime_status"]
    dataset = report["dataset_status"]
    metrics = report["current_baseline_metrics"]
    lines = [
        "# KT Model Comparison Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        "## Runtime KT Status",
        "",
        f"- schema_version: `{runtime.get('schema_version')}`",
        f"- source: `{runtime.get('source')}`",
        f"- model_used: `{runtime.get('model_used')}`",
        f"- fallback_used: `{runtime.get('fallback_used')}`",
        f"- sequence_length: `{runtime.get('sequence_length')}`",
        f"- predicted_mastery_last: `{runtime.get('predicted_mastery_last')}`",
        f"- inference_error: `{runtime.get('inference_error')}`",
        f"- written_state: `{runtime.get('written_state')}`",
        "",
        "## Dataset Readiness",
        "",
        f"- ASSISTments CSV exists: `{dataset.get('assistments_csv_exists')}`",
        f"- tutor.db exists: `{dataset.get('tutor_db_exists')}`",
        f"- quiz_results rows: `{dataset.get('quiz_results_rows')}`",
        f"- learner count: `{dataset.get('learner_count')}`",
        f"- concept count: `{dataset.get('concept_count')}`",
        f"- sequence length stats: `{dataset.get('sequence_length_stats')}`",
        f"- missing runtime columns: `{dataset.get('missing_runtime_columns')}`",
        "",
        "## Model Status",
        "",
    ]
    for model_name, status in report["model_status"].items():
        lines.append(f"- {model_name}: `{status}`")
    lines.extend(
        [
            "",
            "## Current Baseline Metrics",
            "",
            f"- status: `{metrics.get('status')}`",
            f"- note: {metrics.get('metric_note')}",
            f"- interactions used: `{metrics.get('interaction_count_used')}`",
            f"- average correctness: `{metrics.get('average_correctness')}`",
            f"- cumulative baseline accuracy: `{metrics.get('cumulative_baseline_accuracy')}`",
            f"- RMSE: `{metrics.get('rmse')}`",
            f"- Brier score: `{metrics.get('brier_score')}`",
            f"- log loss: `{metrics.get('log_loss')}`",
            "",
            "## Artifact Status",
            "",
            f"- DKT expected paths: `{report['artifact_status']['dkt_expected_paths_exist']}`",
            f"- models/dkt exists: `{report['artifact_status']['models_dkt_dir_exists']}`",
            f"- DKT training script exists: `{report['artifact_status']['training_script_exists']}`",
            "",
            "## Research Upgrade Plan",
            "",
        ]
    )
    for item in report["research_upgrade_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['status']}",
            "MODULE: kt_model_comparison_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['status']}")
    print("MODULE: kt_model_comparison_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
