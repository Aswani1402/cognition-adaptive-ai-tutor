from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.behaviour.lstm_behaviour_model import run_behaviour_model


DB_PATH = Path("external/core_data/tutor.db")
DATASET_REPORT_PATH = Path("evaluation_outputs/json/kt_behaviour_dataset_readiness_report.json")
UPGRADE_REPORT_PATH = Path("evaluation_outputs/json/behaviour_upgrade_report.json")
OUTPUT_JSON = Path("evaluation_outputs/json/behaviour_model_comparison_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/behaviour_model_comparison_report.md")

BEHAVIOUR_MODEL_DIR = Path("models/behaviour_lstm")
BEHAVIOUR_MODEL_PATH = BEHAVIOUR_MODEL_DIR / "model.pt"
BEHAVIOUR_META_PATH = BEHAVIOUR_MODEL_DIR / "meta.json"
SEARCH_ROOTS = [
    Path("tutor/behaviour"),
    Path("tutor/knowledge_state"),
    Path("scripts/system/behaviour"),
    Path("scripts/evaluation"),
    Path("models"),
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
    try:
        output = run_behaviour_model("14")
        keys = [
            "status",
            "module",
            "learner_id",
            "behavior_label",
            "behavior_score",
            "behavior_confidence",
            "behavior_risk",
            "behavior_risk_label",
            "wrong_rate",
            "slow_rate",
            "low_confidence_rate",
            "hint_rate",
            "option_change_rate",
            "sequence_length",
            "model_used",
            "behavior_source",
        ]
        return {key: output.get(key) for key in keys}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _dataset_status() -> dict[str, Any]:
    report = _load_json(DATASET_REPORT_PATH)
    status = {
        "readiness_report": report,
        "tutor_db_exists": DB_PATH.exists(),
        "quiz_results_rows": None,
        "learner_count": None,
        "feature_availability": {},
        "proxy_label_distribution": {},
        "proxy_label_imbalance_warning": False,
    }
    if isinstance(report, dict):
        status["proxy_label_distribution"] = _extract_proxy_distribution(report)
        status["feature_availability"] = _extract_feature_availability(report)
    if not DB_PATH.exists():
        return status

    with _connect_readonly() as conn:
        status["quiz_results_rows"] = conn.execute("SELECT COUNT(*) AS n FROM quiz_results").fetchone()["n"]
        status["learner_count"] = conn.execute(
            "SELECT COUNT(DISTINCT learner_id) AS n FROM quiz_results"
        ).fetchone()["n"]
    distribution = status["proxy_label_distribution"] or _proxy_label_distribution(limit_rows=50000)
    status["proxy_label_distribution"] = distribution
    status["proxy_label_imbalance_warning"] = _is_imbalanced(distribution)
    return status


def _extract_proxy_distribution(report: dict[str, Any]) -> dict[str, int]:
    candidates = [
        report.get("proxy_label_distribution"),
        report.get("behaviour_dataset_status", {}).get("proxy_label_distribution")
        if isinstance(report.get("behaviour_dataset_status"), dict)
        else None,
        report.get("behaviour_proxy_label_readiness", {}).get("proxy_label_distribution")
        if isinstance(report.get("behaviour_proxy_label_readiness"), dict)
        else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return {str(key): int(value or 0) for key, value in candidate.items()}
    return {}


def _extract_feature_availability(report: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        report.get("behaviour_feature_availability"),
        report.get("behaviour_dataset_status", {}).get("feature_availability")
        if isinstance(report.get("behaviour_dataset_status"), dict)
        else None,
        report.get("behaviour_dataset_status", {}).get("feature_columns")
        if isinstance(report.get("behaviour_dataset_status"), dict)
        else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate
    return {}


def _schema_report_status() -> dict[str, Any]:
    return _load_json(UPGRADE_REPORT_PATH)


def _discover_files() -> dict[str, list[str]]:
    keywords = ("lstm", "behaviour", "behavior", "random_forest", "logistic", "kmeans", "gmm", "autoencoder")
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


def _artifact_status() -> dict[str, Any]:
    return {
        "behaviour_lstm_model_exists": BEHAVIOUR_MODEL_PATH.exists(),
        "behaviour_lstm_meta_exists": BEHAVIOUR_META_PATH.exists(),
        "behaviour_lstm_meta": _load_json(BEHAVIOUR_META_PATH),
        "discovered_files": _discover_files(),
    }


def _model_status(artifact_status: dict[str, Any], runtime_status: dict[str, Any]) -> dict[str, str]:
    discovered = artifact_status.get("discovered_files", {})
    return {
        "rule_proxy_baseline": "backend_ready",
        "lstm_behaviour": "backend_ready"
        if artifact_status.get("behaviour_lstm_model_exists") and runtime_status.get("status") == "success"
        else "pending",
        "random_forest": "implemented" if _has_behaviour_specific(discovered, "random_forest") else "pending",
        "logistic_regression": "implemented" if _has_behaviour_specific(discovered, "logistic") else "pending",
        "kmeans": "implemented" if _has_behaviour_specific(discovered, "kmeans") else "pending",
        "gmm": "implemented" if _has_behaviour_specific(discovered, "gmm") else "pending",
        "lstm_autoencoder": "implemented" if _has_behaviour_specific(discovered, "autoencoder") else "pending",
        "behaviour_comparison": "pending",
    }


def _has_behaviour_specific(discovered: dict[str, list[str]], keyword: str) -> bool:
    return any(
        ("behaviour" in path.lower() or "behavior" in path.lower())
        for path in discovered.get(keyword, [])
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _feature_summary(limit_rows: int = 50000) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"status": "error", "error": "tutor.db missing"}
    columns = [
        "is_correct",
        "time_taken_sec",
        "confidence",
        "hint_used",
        "hint_count",
        "option_changes_count",
    ]
    with _connect_readonly() as conn:
        rows = conn.execute(
            f"""
            SELECT {', '.join(columns)}
            FROM quiz_results
            LIMIT ?
            """,
            (limit_rows,),
        ).fetchall()
    if not rows:
        return {"status": "warning", "row_count": 0}

    wrong = []
    times = []
    confidence = []
    hints = []
    hint_counts = []
    option_changes = []
    for row in rows:
        wrong.append(1.0 - _safe_float(row["is_correct"]))
        times.append(_safe_float(row["time_taken_sec"]))
        confidence.append(_safe_float(row["confidence"]))
        hints.append(_safe_float(row["hint_used"]))
        hint_counts.append(_safe_float(row["hint_count"]))
        option_changes.append(_safe_float(row["option_changes_count"]))

    positive_times = [value for value in times if value > 0]
    avg_time = sum(positive_times) / len(positive_times) if positive_times else 0.0
    slow_rate = sum(1 for value in times if avg_time and value > avg_time) / len(times)
    low_conf_rate = sum(1 for value in confidence if value <= 2.0) / len(confidence)
    option_change_rate = sum(1 for value in option_changes if value > 0.0) / len(option_changes)
    return {
        "status": "success",
        "row_count_used": len(rows),
        "wrong_rate": round(sum(wrong) / len(wrong), 4),
        "avg_time_taken_sec": round(avg_time, 4),
        "slow_rate": round(slow_rate, 4),
        "avg_confidence": round(sum(confidence) / len(confidence), 4),
        "low_confidence_rate": round(low_conf_rate, 4),
        "hint_rate": round(sum(hints) / len(hints), 4),
        "avg_hint_count": round(sum(hint_counts) / len(hint_counts), 4),
        "option_change_rate": round(option_change_rate, 4),
        "proxy_label_distribution": _proxy_label_distribution_from_features(
            wrong_rates=wrong,
            slow_flags=[1.0 if avg_time and value > avg_time else 0.0 for value in times],
            low_conf_flags=[1.0 if value <= 2.0 else 0.0 for value in confidence],
            hint_flags=hints,
            option_change_flags=[1.0 if value > 0.0 else 0.0 for value in option_changes],
        ),
    }


def _proxy_label_distribution(limit_rows: int = 50000) -> dict[str, int]:
    summary = _feature_summary(limit_rows=limit_rows)
    return summary.get("proxy_label_distribution", {}) if isinstance(summary, dict) else {}


def _proxy_label_distribution_from_features(
    wrong_rates: list[float],
    slow_flags: list[float],
    low_conf_flags: list[float],
    hint_flags: list[float],
    option_change_flags: list[float],
) -> dict[str, int]:
    labels: Counter[str] = Counter()
    for wrong, slow, low_conf, hint, option_change in zip(
        wrong_rates,
        slow_flags,
        low_conf_flags,
        hint_flags,
        option_change_flags,
    ):
        if wrong >= 1.0 and (slow or hint):
            labels["struggling"] += 1
        elif wrong >= 1.0 and option_change:
            labels["guessing"] += 1
        elif low_conf or hint:
            labels["confused"] += 1
        else:
            labels["stable"] += 1
    for label in ("stable", "confused", "guessing", "struggling"):
        labels.setdefault(label, 0)
    return dict(labels)


def _is_imbalanced(distribution: dict[str, int]) -> bool:
    total = sum(int(value or 0) for value in distribution.values())
    if total <= 0:
        return True
    largest = max(int(value or 0) for value in distribution.values())
    non_zero = sum(1 for value in distribution.values() if int(value or 0) > 0)
    return largest / total >= 0.90 or non_zero <= 2


def _overall_status(report: dict[str, Any]) -> str:
    if report["runtime_status"].get("status") != "success":
        return "error"
    if report["proxy_label_warning"]:
        return "warning"
    pending_models = [
        status
        for name, status in report["model_status"].items()
        if name not in {"rule_proxy_baseline", "lstm_behaviour"}
    ]
    if any(status == "pending" for status in pending_models):
        return "warning"
    return "success"


def build_report() -> dict[str, Any]:
    runtime = _runtime_status()
    dataset = _dataset_status()
    schema = _schema_report_status()
    artifacts = _artifact_status()
    model_status = _model_status(artifacts, runtime)
    feature_summary = _feature_summary()
    proxy_distribution = dataset.get("proxy_label_distribution") or feature_summary.get("proxy_label_distribution", {})
    proxy_warning = _is_imbalanced(proxy_distribution)

    report = {
        "status": "warning",
        "module": "BehaviourModelComparisonReport",
        "generated_at": _now_iso(),
        "runtime_status": runtime,
        "dataset_status": dataset,
        "behaviour_upgrade_report_status": schema,
        "artifact_status": artifacts,
        "model_status": model_status,
        "current_feature_summary": feature_summary,
        "proxy_label_warning": proxy_warning,
        "research_upgrade_plan": [
            "Improve labels using evaluation_fusion_output, mistake_analysis, repeated wrong attempts, confidence/time/hint patterns, code/runtime errors, and engagement signals.",
            "Train and compare rule baseline, LogisticRegression, RandomForest, KMeans, GMM, LSTM classifier, and LSTM/sequence autoencoder anomaly detector.",
            "Evaluate supervised models with accuracy, macro-F1, weighted-F1, confusion matrix, and ROC-AUC for binary risk if applicable.",
            "Evaluate clustering with silhouette score and cluster stability; avoid overclaiming labels for unsupervised clusters.",
            "Evaluate anomaly detection with precision/recall when validated labels are available.",
            "Keep behavior_confidence and behavior_risk separate in runtime output.",
            "Persist behaviour_state with behavior_risk_label and fallback-safe source labels.",
            "Fallback to transparent feature/rule baseline if a model fails.",
            "Expose frontend/dashboard fields: behaviour_label, behaviour_risk, behaviour_confidence, explanation, and engagement/risk trend.",
        ],
        "limitations": [
            "Current behaviour labels are proxy/rule-generated and highly imbalanced.",
            "Current LSTM is model-based and runtime-ready, but label quality limits research claims.",
            "RF/LogReg/KMeans/GMM/autoencoder behaviour-specific comparison artifacts were not found.",
            "Accuracy-like metrics are not meaningful until labels are improved and class balance is addressed.",
            "Unsupervised clustering needs careful interpretation before using clusters as learner-facing labels.",
        ],
    }
    report["status"] = _overall_status(report)
    return report


def _build_markdown(report: dict[str, Any]) -> str:
    runtime = report["runtime_status"]
    dataset = report["dataset_status"]
    features = report["current_feature_summary"]
    lines = [
        "# Behaviour Model Comparison Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['status']}`",
        "",
        "## Runtime Behaviour Status",
        "",
        f"- behavior_label: `{runtime.get('behavior_label')}`",
        f"- behavior_score: `{runtime.get('behavior_score')}`",
        f"- behavior_confidence: `{runtime.get('behavior_confidence')}`",
        f"- behavior_risk: `{runtime.get('behavior_risk')}`",
        f"- behavior_risk_label: `{runtime.get('behavior_risk_label')}`",
        f"- wrong_rate: `{runtime.get('wrong_rate')}`",
        f"- slow_rate: `{runtime.get('slow_rate')}`",
        f"- low_confidence_rate: `{runtime.get('low_confidence_rate')}`",
        f"- hint_rate: `{runtime.get('hint_rate')}`",
        f"- option_change_rate: `{runtime.get('option_change_rate')}`",
        f"- sequence_length: `{runtime.get('sequence_length')}`",
        f"- model_used: `{runtime.get('model_used')}`",
        f"- behavior_source: `{runtime.get('behavior_source')}`",
        "",
        "## Dataset And Label Status",
        "",
        f"- quiz_results rows: `{dataset.get('quiz_results_rows')}`",
        f"- learner count: `{dataset.get('learner_count')}`",
        f"- proxy label distribution: `{dataset.get('proxy_label_distribution')}`",
        f"- proxy label warning: `{report.get('proxy_label_warning')}`",
        "",
        "## Model Status",
        "",
    ]
    for name, status in report["model_status"].items():
        lines.append(f"- {name}: `{status}`")
    lines.extend(
        [
            "",
            "## Current Feature Summary",
            "",
            f"- rows used: `{features.get('row_count_used')}`",
            f"- wrong_rate: `{features.get('wrong_rate')}`",
            f"- avg_time_taken_sec: `{features.get('avg_time_taken_sec')}`",
            f"- slow_rate: `{features.get('slow_rate')}`",
            f"- avg_confidence: `{features.get('avg_confidence')}`",
            f"- low_confidence_rate: `{features.get('low_confidence_rate')}`",
            f"- hint_rate: `{features.get('hint_rate')}`",
            f"- option_change_rate: `{features.get('option_change_rate')}`",
            f"- transparent proxy distribution on sampled features: `{features.get('proxy_label_distribution')}`",
            "",
            "## Artifact Status",
            "",
            f"- behaviour LSTM model exists: `{report['artifact_status']['behaviour_lstm_model_exists']}`",
            f"- behaviour LSTM meta exists: `{report['artifact_status']['behaviour_lstm_meta_exists']}`",
            f"- behaviour LSTM meta: `{report['artifact_status']['behaviour_lstm_meta']}`",
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
            "MODULE: behaviour_model_comparison_report",
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
    print("MODULE: behaviour_model_comparison_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
