from __future__ import annotations

import json
from pathlib import Path

from tutor.llm_finetune.pretrained_generator import (
    generate_tutor_output,
)

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT / "outputs" / "samples"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TASK_TYPES = [

    "explanation",
    "flashcard",
    "mcq",
    "debug",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "hint",
    "feedback",
    "revision_note",
]

CONCEPTS = [

    {
        "concept_name": "Python Variables",
        "definition":
            "Variables are used to store values in Python programs.",
    },

    {
        "concept_name": "Python Loops",
        "definition":
            "Loops are used to repeat actions multiple times.",
    },

    {
        "concept_name": "SQL SELECT",
        "definition":
            "SELECT is used to retrieve data from a database table.",
    },

    {
        "concept_name": "HTML Tags",
        "definition":
            "HTML tags define webpage structure and content.",
    },

    {
        "concept_name": "Git Commits",
        "definition":
            "Git commits save snapshots of project changes.",
    },
]


def generate_samples(output_file):

    samples = []

    for task in TASK_TYPES:

        for concept_resource in CONCEPTS:

            generated = generate_tutor_output(

                concept_resource,

                "easy",

                "slow learner",

                "simple",

                task,
            )

            sample = {

                "task_type": task,

                "concept":
                    concept_resource[
                        "concept_name"
                    ],

                "output": generated,
            }

            samples.append(sample)

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        for sample in samples:

            f.write(
                json.dumps(sample) + "\n"
            )

    return len(samples)


def main():

    print("\nGenerating REAL model samples...\n")

    smollm_path = (
        OUTPUT_DIR
        / "smollm2_135m_samples.jsonl"
    )

    count = generate_samples(
        smollm_path
    )

    print(
        f"Generated samples: {count}"
    )

    print("\nSaved file:")

    print(smollm_path)

    print("\nDONE\n")


if __name__ == "__main__":

    main()