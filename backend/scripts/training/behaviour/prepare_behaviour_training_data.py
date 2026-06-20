from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, quantiles
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")
CSV_OUTPUT = Path("evaluation_outputs/csv/behaviour_training_dataset.csv")
JSON_OUTPUT = Path("evaluation_outputs/json/behaviour_training_data_summary.json")

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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for item in values if item) / len(values), 6)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _percentile(values: list[float], fallback: float) -> float:
    clean = sorted(float(value) for value in values)
    if len(clean) < 4:
        return fallback
    try:
        return float(quantiles(clean, n=5)[3])
    except Exception:
        index = min(len(clean) - 1, int(len(clean) * 0.8))
        return clean[index]


def _pattern_scores(features: dict[str, float]) -> dict[str, float]:
    wrong_score = _clamp(features["wrong_rate"] / 0.4)
    slow_score = _clamp(max(features["slow_rate"], features["avg_time_taken_sec"] / 60.0))
    low_confidence_score = _clamp(max(features["low_confidence_rate"], (5.0 - features["avg_confidence"]) / 5.0))
    hint_score = _clamp(max(features["hint_rate"], features["avg_hint_count"] / 3.0))
    option_change_score = _clamp(features["option_change_rate"] / 0.3)
    fast_wrong_score = _clamp(features["wrong_rate"] * (1.0 - slow_score) * 2.0)
    repeated_attempt_score = _clamp(max(features["recent_wrong_rate"], features["repeated_attempt_rate"]))

    confused_score = (
        0.35 * low_confidence_score
        + 0.25 * slow_score
        + 0.20 * hint_score
        + 0.20 * wrong_score
    )
    guessing_score = (
        0.35 * option_change_score
        + 0.25 * fast_wrong_score
        + 0.20 * low_confidence_score
        + 0.20 * wrong_score
    )
    struggling_score = (
        0.40 * wrong_score
        + 0.25 * slow_score
        + 0.20 * hint_score
        + 0.15 * repeated_attempt_score
    )
    stable_score = _clamp(1.0 - max(confused_score, guessing_score, struggling_score))
    return {
        "stable": round(stable_score, 6),
        "confused": round(_clamp(confused_score), 6),
        "guessing": round(_clamp(guessing_score), 6),
        "struggling": round(_clamp(struggling_score), 6),
    }


def _label_from_scores(scores: dict[str, float]) -> tuple[str, float]:
    label, score = max(scores.items(), key=lambda item: item[1])
    ordered = sorted(scores.values(), reverse=True)
    margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
    confidence = _clamp(0.5 * score + 0.5 * margin)
    return label, round(confidence, 6)


def _window_features(window: list[dict[str, Any]]) -> dict[str, float]:
    n = len(window)
    times = [_safe_float(row.get("time_taken_sec")) for row in window]
    confidences = [_safe_float(row.get("confidence")) for row in window]
    hint_counts = [_safe_float(row.get("hint_count")) for row in window]
    recent = window[-5:] if len(window) >= 5 else window
    return {
        "wrong_rate": _rate([_safe_int(row.get("is_correct")) == 0 for row in window]),
        "slow_rate": _rate([_safe_float(row.get("time_taken_sec")) > 30.0 for row in window]),
        "low_confidence_rate": _rate([_safe_float(row.get("confidence")) <= 2.0 for row in window]),
        "hint_rate": _rate([
            _safe_int(row.get("hint_used")) == 1 or _safe_int(row.get("hint_count")) > 0
            for row in window
        ]),
        "option_change_rate": _rate([_safe_int(row.get("option_changes_count")) > 0 for row in window]),
        "avg_time_taken_sec": round(mean(times), 6) if times else 0.0,
        "avg_confidence": round(mean(confidences), 6) if confidences else 0.0,
        "attempt_count": float(n),
        "recent_wrong_rate": _rate([_safe_int(row.get("is_correct")) == 0 for row in recent]),
        "repeated_attempt_rate": _rate([_safe_int(row.get("attempt_no"), 1) > 1 for row in window]),
        "fast_wrong_rate": _rate([
            _safe_int(row.get("is_correct")) == 0 and _safe_float(row.get("time_taken_sec")) <= 15.0
            for row in window
        ]),
        "avg_hint_count": round(mean(hint_counts), 6) if hint_counts else 0.0,
    }


def _load_rows() -> dict[str, list[dict[str, Any]]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT learner_id,
                       concept_id,
                       is_correct,
                       confidence,
                       time_taken_sec,
                       hint_used,
                       hint_count,
                       option_changes_count,
                       attempt_no,
                       timestamp,
                       quiz_id
                FROM quiz_results
                WHERE learner_id IS NOT NULL
                ORDER BY learner_id, timestamp, quiz_id
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    by_learner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_learner[str(row["learner_id"])].append(row)
    return by_learner


def prepare_dataset(window_size: int = 20, stride: int = 10) -> dict[str, Any]:
    by_learner = _load_rows()
    window_records: list[dict[str, Any]] = []

    for learner_id, rows in by_learner.items():
        if not rows:
            continue
        if len(rows) < window_size:
            windows = [(0, rows)]
        else:
            starts = list(range(0, len(rows) - window_size + 1, stride))
            if starts[-1] != len(rows) - window_size:
                starts.append(len(rows) - window_size)
            windows = [(start, rows[start : start + window_size]) for start in starts]

        for window_index, (start, window) in enumerate(windows):
            features = _window_features(window)
            scores = _pattern_scores(features)
            label, confidence = _label_from_scores(scores)
            sorted_scores = sorted(scores.values(), reverse=True)
            stable_score = float(scores.get("stable", 0.0))
            confused_score = float(scores.get("confused", 0.0))
            guessing_score = float(scores.get("guessing", 0.0))
            struggling_score = float(scores.get("struggling", 0.0))
            window_records.append(
                {
                    "learner_id": learner_id,
                    "window_index": window_index,
                    "start_sequence_index": start,
                    "end_sequence_index": start + len(window) - 1,
                    "start_timestamp": window[0].get("timestamp") or "",
                    "end_timestamp": window[-1].get("timestamp") or "",
                    **features,
                    "proxy_label": label,
                    "behaviour_label": label,
                    "label_confidence": confidence,
                    "proxy_label_confidence": confidence,
                    "stable_score": stable_score,
                    "confused_score": confused_score,
                    "guessing_score": guessing_score,
                    "struggling_score": struggling_score,
                    "label_scores_json": json.dumps(scores, sort_keys=True),
                }
            )

    old_label_distribution = dict(Counter(row["proxy_label"] for row in window_records))
    _apply_percentile_rescue(window_records)
    output_rows = window_records

    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "learner_id",
        "window_index",
        "start_sequence_index",
        "end_sequence_index",
        "start_timestamp",
        "end_timestamp",
        *FEATURE_COLUMNS,
        "proxy_label",
        "behaviour_label",
        "label_confidence",
        "proxy_label_confidence",
        "stable_score",
        "confused_score",
        "guessing_score",
        "struggling_score",
        "label_scores_json",
    ]
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    label_distribution = Counter(row["proxy_label"] for row in output_rows)
    row_count = len(output_rows)
    max_ratio = max(label_distribution.values()) / row_count if row_count else 0.0
    summary = {
        "status": "warning" if max_ratio >= 0.75 else "success",
        "module": "prepare_behaviour_training_data",
        "source_db": str(DB_PATH),
        "csv_output": str(CSV_OUTPUT),
        "row_count": row_count,
        "learner_count": len(by_learner),
        "window_size": window_size,
        "stride": stride,
        "feature_columns": FEATURE_COLUMNS,
        "label_column": "proxy_label",
        "label_distribution": dict(label_distribution),
        "old_label_distribution": old_label_distribution,
        "class_imbalance_ratio": round(max_ratio, 6) if row_count else 0.0,
        "class_imbalance_warning": max_ratio >= 0.75,
        "score_formula_used": {
            "confused_score": "0.35*low_confidence_score + 0.25*slow_score + 0.20*hint_score + 0.20*wrong_score",
            "guessing_score": "0.35*option_change_score + 0.25*fast_wrong_score + 0.20*low_confidence_score + 0.20*wrong_score",
            "struggling_score": "0.40*wrong_score + 0.25*slow_score + 0.20*hint_score + 0.15*repeated_attempt_score",
            "stable_score": "max(0, 1 - max(confused_score, guessing_score, struggling_score))",
            "label": "argmax(stable_score, confused_score, guessing_score, struggling_score)",
        },
        "limitations": [
            "Labels are transparent proxy labels derived from behaviour rules, not human annotations.",
            "High correctness in quiz_results can make stable/confused classes dominate.",
            "Accuracy alone is not enough under imbalance; macro-F1 and confusion matrix matter more.",
            "Future labels should use evaluation_fusion, mistake_analysis, repeated wrong attempts, and code/runtime errors.",
        ],
    }
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _apply_percentile_rescue(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    labels = Counter(row["proxy_label"] for row in rows)
    thresholds = {
        "struggling": {
            "wrong_rate": _percentile([row["wrong_rate"] for row in rows], 0.2),
            "slow_rate": _percentile([row["slow_rate"] for row in rows], 0.5),
            "hint_rate": _percentile([row["hint_rate"] for row in rows], 0.2),
            "recent_wrong_rate": _percentile([row["recent_wrong_rate"] for row in rows], 0.2),
        },
        "guessing": {
            "option_change_rate": _percentile([row["option_change_rate"] for row in rows], 0.1),
            "fast_wrong_signal": _percentile(
                [row["wrong_rate"] * max(0.0, 1.0 - row["slow_rate"]) for row in rows],
                0.1,
            ),
        },
        "confused": {
            "low_confidence_rate": _percentile([row["low_confidence_rate"] for row in rows], 0.2),
            "slow_rate": _percentile([row["slow_rate"] for row in rows], 0.5),
        },
    }

    def rescue(row: dict[str, Any], label: str, score_boost: float) -> None:
        scores = json.loads(row["label_scores_json"])
        scores[label] = max(float(scores.get(label, 0.0)), score_boost)
        row["proxy_label"] = label
        row["behaviour_label"] = label
        row["label_confidence"] = round(max(float(row["proxy_label_confidence"]), score_boost), 6)
        row["proxy_label_confidence"] = round(max(float(row["proxy_label_confidence"]), score_boost), 6)
        row["stable_score"] = float(scores.get("stable", 0.0))
        row["confused_score"] = float(scores.get("confused", 0.0))
        row["guessing_score"] = float(scores.get("guessing", 0.0))
        row["struggling_score"] = float(scores.get("struggling", 0.0))
        row["label_scores_json"] = json.dumps(scores, sort_keys=True)

    if labels.get("struggling", 0) < max(10, int(0.02 * len(rows))):
        candidates = [
            row for row in rows
            if row["wrong_rate"] >= thresholds["struggling"]["wrong_rate"]
            and (
                row["slow_rate"] >= thresholds["struggling"]["slow_rate"]
                or row["hint_rate"] >= thresholds["struggling"]["hint_rate"]
                or row["recent_wrong_rate"] >= thresholds["struggling"]["recent_wrong_rate"]
            )
        ]
        for row in sorted(candidates, key=lambda item: (item["wrong_rate"], item["recent_wrong_rate"]), reverse=True)[: max(10, int(0.04 * len(rows)))]:
            rescue(row, "struggling", 0.62)

    labels = Counter(row["proxy_label"] for row in rows)
    if labels.get("guessing", 0) < max(10, int(0.01 * len(rows))):
        candidates = [
            row for row in rows
            if row["option_change_rate"] >= thresholds["guessing"]["option_change_rate"]
            or row["wrong_rate"] * max(0.0, 1.0 - row["slow_rate"]) >= thresholds["guessing"]["fast_wrong_signal"]
        ]
        for row in sorted(candidates, key=lambda item: (item["option_change_rate"], item["wrong_rate"] * max(0.0, 1.0 - item["slow_rate"])), reverse=True)[: max(10, int(0.02 * len(rows)))]:
            fast_wrong = row["wrong_rate"] * max(0.0, 1.0 - row["slow_rate"])
            if row["proxy_label"] == "struggling" and row["option_change_rate"] <= 0 and fast_wrong < thresholds["guessing"]["fast_wrong_signal"]:
                continue
            rescue(row, "guessing", 0.58)

    labels = Counter(row["proxy_label"] for row in rows)
    if labels.get("confused", 0) < max(10, int(0.05 * len(rows))):
        candidates = [
            row for row in rows
            if row["low_confidence_rate"] >= thresholds["confused"]["low_confidence_rate"]
            or row["slow_rate"] >= thresholds["confused"]["slow_rate"]
        ]
        for row in sorted(candidates, key=lambda item: (item["low_confidence_rate"], item["slow_rate"]), reverse=True)[: max(10, int(0.12 * len(rows)))]:
            if row["proxy_label"] in {"struggling", "guessing"}:
                continue
            rescue(row, "confused", 0.56)


def main() -> None:
    summary = prepare_dataset()
    print(f"STATUS: {summary['status']}")
    print("MODULE: prepare_behaviour_training_data")
    print(f"CSV_OUTPUT: {CSV_OUTPUT}")
    print(f"JSON_OUTPUT: {JSON_OUTPUT}")
    if summary["class_imbalance_warning"]:
        print("WARNING: proxy label classes are imbalanced; use macro-F1, not accuracy alone.")


if __name__ == "__main__":
    main()
