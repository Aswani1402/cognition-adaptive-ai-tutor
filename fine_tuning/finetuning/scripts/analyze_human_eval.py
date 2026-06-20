from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSV_PATH = (
    ROOT
    / "evaluation_outputs"
    / "reports"
    / "human_eval_filled.csv"
)


def main():

    print("\nAnalyzing human evaluation...\n")

    if not CSV_PATH.exists():

        print(
            "Filled human eval CSV not found. "
            "Please collect ratings first."
        )

        return

    rows = []

    with open(
        CSV_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    print(f"Loaded rows: {len(rows)}")

    score_fields = [

        "concept_correctness_1_to_5",
        "concept_relevance_1_to_5",
        "teaching_clarity_1_to_5",
        "task_fit_1_to_5",
        "usefulness_1_to_5",
        "hallucination_safety_1_to_5",
        "format_quality_1_to_5",
        "overall_score_1_to_5",
    ]

    totals = {
        field: 0.0
        for field in score_fields
    }

    valid_rows = 0

    for row in rows:

        try:

            for field in score_fields:

                totals[field] += float(
                    row.get(field, 0)
                )

            valid_rows += 1

        except Exception:
            continue

    if valid_rows == 0:

        print(
            "\nNo scored rows found yet."
        )

        return

    print("\nAverage Scores:\n")

    for field in score_fields:

        avg = totals[field] / valid_rows

        print(f"{field}: {avg:.2f}")


if __name__ == "__main__":
    main()