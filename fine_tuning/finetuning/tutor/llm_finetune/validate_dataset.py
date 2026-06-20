from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "training_data" / "llm_tutor"

TRAIN_FILE = DATA_DIR / "tutor_train.jsonl"
VAL_FILE = DATA_DIR / "tutor_val.jsonl"
TEST_FILE = DATA_DIR / "tutor_test.jsonl"


REQUIRED_FIELDS = [

    "instruction",
    "input",
    "output",
]


EXPECTED_DOMAINS = {

    "Python",
    "SQL",
    "HTML",
    "Git",
    "Data Structures",
}


KNOWN_CONCEPTS = [

    "Variables",
    "Loops",
    "Functions",
    "SQL SELECT",
    "JOIN",
    "HTML Tags",
    "Git Commits",
    "Stack",
    "Queue",
    "Array",
]


def load_jsonl(path):

    rows = []

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:

                rows.append(
                    json.loads(line)
                )

            except Exception:
                continue

    return rows


def detect_domain(text):

    lower = text.lower()

    if "python" in lower:
        return "Python"

    elif "sql" in lower:
        return "SQL"

    elif "html" in lower:
        return "HTML"

    elif "git" in lower:
        return "Git"

    elif (
        "stack" in lower
        or "array" in lower
        or "queue" in lower
        or "tree" in lower
        or "linked list" in lower
    ):
        return "Data Structures"

    return None


def detect_concept(text):

    lower = text.lower()

    # ==========================================
    # EXTRACT FROM:
    # Concept: XYZ
    # ==========================================

    if "concept:" in lower:

        try:

            after = text.split(
                "Concept:",
                1
            )[1]

            concept_line = (
                after.strip()
                .splitlines()[0]
                .strip()
            )

            if concept_line:
                return concept_line

        except Exception:
            pass

    # ==========================================
    # FALLBACK KNOWN CONCEPTS
    # ==========================================

    for concept in KNOWN_CONCEPTS:

        if concept.lower() in lower:
            return concept

    # ==========================================
    # LAST FALLBACK
    # ==========================================

    return text[:50]


def validate_rows(rows):

    missing_field_count = 0

    concepts = set()

    domains = set()

    empty_output_count = 0

    invalid_rows = 0

    for row in rows:

        if not isinstance(row, dict):

            invalid_rows += 1
            continue

        # ==========================================
        # REQUIRED FIELD CHECK
        # ==========================================

        for field in REQUIRED_FIELDS:

            if field not in row:

                missing_field_count += 1

        input_data = row.get("input", {})

        output_data = row.get("output", "")

        concept = None

        domain = None

        # ==========================================
        # CASE 1 — INPUT IS DICT
        # ==========================================

        if isinstance(input_data, dict):

            concept = input_data.get(
                "concept_name"
            )

            domain = input_data.get(
                "domain"
            )

            if not concept:

                concept = detect_concept(
                    json.dumps(input_data)
                )

            if not domain:

                domain = detect_domain(
                    json.dumps(input_data)
                )

        # ==========================================
        # CASE 2 — INPUT IS STRING
        # ==========================================

        elif isinstance(input_data, str):

            concept = detect_concept(
                input_data
            )

            domain = detect_domain(
                input_data
            )

        # ==========================================
        # OUTPUT VALIDATION
        # ==========================================

        if not str(output_data).strip():

            empty_output_count += 1

        # ==========================================
        # STORE RESULTS
        # ==========================================

        if concept:

            concepts.add(str(concept))

        if domain:

            domains.add(str(domain))

    return {

        "missing_field_count":
            missing_field_count,

        "concepts":
            concepts,

        "domains":
            domains,

        "empty_output_count":
            empty_output_count,

        "invalid_rows":
            invalid_rows,
    }


def main():

    print("\nRunning dataset validation...\n")

    missing_files = []

    for path in [

        TRAIN_FILE,
        VAL_FILE,
        TEST_FILE,
    ]:

        if not path.exists():

            missing_files.append(
                str(path)
            )

    # ==========================================
    # MISSING FILE CHECK
    # ==========================================

    if missing_files:

        print("STATUS: FAIL\n")

        print("Missing files:\n")

        for file in missing_files:

            print(file)

        return

    # ==========================================
    # LOAD DATASETS
    # ==========================================

    train_rows = load_jsonl(
        TRAIN_FILE
    )

    val_rows = load_jsonl(
        VAL_FILE
    )

    test_rows = load_jsonl(
        TEST_FILE
    )

    total_rows = (

        len(train_rows)

        + len(val_rows)

        + len(test_rows)
    )

    combined = (

        train_rows

        + val_rows

        + test_rows
    )

    # ==========================================
    # VALIDATE
    # ==========================================

    results = validate_rows(
        combined
    )

    concepts = results["concepts"]

    domains = results["domains"]

    # ==========================================
    # PRINT SUMMARY
    # ==========================================

    print(f"Train rows: {len(train_rows)}")

    print(f"Val rows: {len(val_rows)}")

    print(f"Test rows: {len(test_rows)}")

    print(f"Total rows: {total_rows}")

    print(f"\nUnique concepts: {len(concepts)}")

    print(f"Domains found: {len(domains)}")

    print("\nDomains:\n")

    for domain in sorted(domains):

        print("-", domain)

    # ==========================================
    # WARNINGS
    # ==========================================

    if results["missing_field_count"] > 0:

        print("\nMissing fields detected:")

        print(
            results[
                "missing_field_count"
            ]
        )

    if results["empty_output_count"] > 0:

        print("\nEmpty outputs detected:")

        print(
            results[
                "empty_output_count"
            ]
        )

    if results["invalid_rows"] > 0:

        print("\nInvalid rows detected:")

        print(
            results[
                "invalid_rows"
            ]
        )

    missing_domains = (

        EXPECTED_DOMAINS
        - domains
    )

    if missing_domains:

        print("\nMissing expected domains:\n")

        for domain in missing_domains:

            print("-", domain)

    # ==========================================
    # FINAL STATUS
    # ==========================================

    if (
        len(missing_domains) == 0
        and results["invalid_rows"] == 0
    ):

        print("\nSTATUS: PASS")

    else:

        print("\nSTATUS: WARN")


if __name__ == "__main__":

    main()