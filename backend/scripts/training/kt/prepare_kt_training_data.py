from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


DB_PATH = Path("external/core_data/tutor.db")
CSV_OUTPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
JSON_OUTPUT = Path("evaluation_outputs/json/kt_training_data_summary.json")


def _split_for_position(index: int, length: int) -> str:
    if length <= 1:
        return "train"
    ratio = index / max(1, length)
    if ratio < 0.7:
        return "train"
    if ratio < 0.85:
        return "val"
    return "test"


def _stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"min": 0, "max": 0, "mean": 0, "median": 0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 4),
        "median": median(values),
    }


def load_rows() -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT learner_id, concept_id, is_correct, timestamp, quiz_id
                FROM quiz_results
                WHERE learner_id IS NOT NULL
                  AND concept_id IS NOT NULL
                  AND is_correct IS NOT NULL
                ORDER BY learner_id, timestamp, quiz_id
                """
            ).fetchall()
        ]
    finally:
        conn.close()
    return rows


def prepare_sequences() -> dict[str, Any]:
    rows = load_rows()
    learner_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        learner_rows[str(row["learner_id"])].append(row)

    concepts = sorted({str(row["concept_id"]) for row in rows}, key=lambda item: (len(item), item))
    concept_id_mapping = {concept_id: index + 1 for index, concept_id in enumerate(concepts)}

    output_rows = []
    split_counts = Counter()
    correctness = Counter()
    sequence_lengths = []

    for learner_id, seq in learner_rows.items():
        sequence_lengths.append(len(seq))
        for index, row in enumerate(seq):
            split = _split_for_position(index, len(seq))
            correct = 1 if int(row["is_correct"]) else 0
            split_counts[split] += 1
            correctness[str(correct)] += 1
            output_rows.append(
                {
                    "learner_id": learner_id,
                    "concept_id": str(row["concept_id"]),
                    "concept_idx": concept_id_mapping[str(row["concept_id"])],
                    "is_correct": correct,
                    "timestamp": row["timestamp"] or "",
                    "quiz_id": row["quiz_id"],
                    "sequence_index": index,
                    "split": split,
                }
            )

    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "learner_id",
                "concept_id",
                "concept_idx",
                "is_correct",
                "timestamp",
                "quiz_id",
                "sequence_index",
                "split",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    total = len(output_rows)
    correct_count = correctness.get("1", 0)
    correct_rate = correct_count / total if total else 0.0
    imbalance_warning = (
        "Correctness is highly imbalanced."
        if correct_rate < 0.2 or correct_rate > 0.8
        else ""
    )

    summary = {
        "status": "success",
        "module": "prepare_kt_training_data",
        "source_db": str(DB_PATH),
        "csv_output": str(CSV_OUTPUT),
        "row_count": total,
        "learner_count": len(learner_rows),
        "concept_count": len(concepts),
        "sequence_length_stats": _stats(sequence_lengths),
        "correctness_distribution": {
            "correct": correct_count,
            "incorrect": correctness.get("0", 0),
            "correct_rate": round(correct_rate, 6),
        },
        "train_val_test_split_counts": dict(split_counts),
        "concept_id_mapping": concept_id_mapping,
        "warning": imbalance_warning,
    }

    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    summary = prepare_sequences()
    print("STATUS: success")
    print("MODULE: prepare_kt_training_data")
    print(f"CSV_OUTPUT: {CSV_OUTPUT}")
    print(f"JSON_OUTPUT: {JSON_OUTPUT}")
    if summary.get("warning"):
        print(f"WARNING: {summary['warning']}")


if __name__ == "__main__":
    main()
