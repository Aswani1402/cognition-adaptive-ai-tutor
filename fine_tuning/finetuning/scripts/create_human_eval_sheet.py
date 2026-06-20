from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORT_DIR = ROOT / "evaluation_outputs" / "reports"
JSON_DIR = ROOT / "evaluation_outputs" / "json"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = REPORT_DIR / "human_eval_sheet.csv"

INSTRUCTION_PATH = (
    REPORT_DIR / "human_eval_instructions.md"
)

MAPPING_PATH = (
    JSON_DIR / "human_eval_mapping_private.json"
)


SAMPLES = [

    {
        "sample_id": "S1",
        "concept": "Variables",
        "task_type": "explanation",
        "system_label": "System A",
        "generated_output":
            "Variables store values in programming."
    },

    {
        "sample_id": "S2",
        "concept": "Loops",
        "task_type": "debug_task",
        "system_label": "System B",
        "generated_output":
            "Buggy code: for i in range(5)"
    },

    {
        "sample_id": "S3",
        "concept": "SQL SELECT",
        "task_type": "flashcard",
        "system_label": "System C",
        "generated_output":
            "Front: SELECT Back: Retrieves data."
    },

    {
        "sample_id": "S4",
        "concept": "Git",
        "task_type": "challenge_question",
        "system_label": "System D",
        "generated_output":
            "Challenge: Explain git commit."
    },
]


CSV_COLUMNS = [

    "sample_id",
    "concept",
    "task_type",
    "system_label",
    "generated_output",

    "concept_correctness_1_to_5",
    "concept_relevance_1_to_5",
    "teaching_clarity_1_to_5",
    "task_fit_1_to_5",
    "usefulness_1_to_5",
    "hallucination_safety_1_to_5",
    "format_quality_1_to_5",
    "overall_score_1_to_5",

    "comments",
]


SYSTEM_MAPPING = {

    "System A": "template_rule_baseline",
    "System B": "cognitutor_lm_from_scratch",
    "System C": "pretrained_pretrained_finetuned_llm",
    "System D": "rag_grounded_service",
}


def create_csv():

    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=CSV_COLUMNS
        )

        writer.writeheader()

        for sample in SAMPLES:

            row = dict(sample)

            for col in CSV_COLUMNS:

                if col not in row:
                    row[col] = ""

            writer.writerow(row)


def create_mapping():

    with open(
        MAPPING_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            SYSTEM_MAPPING,
            f,
            indent=2
        )


def create_instructions():

    content = """
# Human Evaluation Instructions

Please rate each generated tutor output.

Scoring:
1 = very poor
5 = excellent

Evaluate:
- concept correctness
- concept relevance
- teaching clarity
- task fit
- usefulness
- hallucination safety
- format quality

Do not leave scores empty.
"""

    with open(
        INSTRUCTION_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content.strip())


def main():

    create_csv()
    create_mapping()
    create_instructions()

    print("\nHuman evaluation files created.\n")

    print("CSV:")
    print(CSV_PATH)

    print("\nInstructions:")
    print(INSTRUCTION_PATH)

    print("\nMapping:")
    print(MAPPING_PATH)


if __name__ == "__main__":
    main()