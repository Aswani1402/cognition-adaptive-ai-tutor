from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "training_data" / "llm_tutor"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TRAIN_FILE = DATA_DIR / "tutor_train.jsonl"
VAL_FILE = DATA_DIR / "tutor_val.jsonl"
TEST_FILE = DATA_DIR / "tutor_test.jsonl"


DOMAINS = {

    "Python": [

        "Variables",
        "Loops",
        "Functions",
        "Lists",
        "Dictionaries",
        "Classes",
        "File Handling",
        "Exception Handling",
    ],

    "SQL": [

        "SELECT Queries",
        "WHERE Clause",
        "JOIN Operations",
        "GROUP BY",
        "ORDER BY",
        "Primary Keys",
        "Normalization",
    ],

    "HTML": [

        "HTML Tags",
        "Forms",
        "Tables",
        "Semantic HTML",
        "Lists",
        "Images",
        "Links",
        "HTML Structure",
    ],

    "Git": [

        "Git Commits",
        "Git Branches",
        "Git Merge",
        "Git Pull",
        "Git Push",
        "Git Clone",
        "Git Conflict Resolution",
    ],

    "Data Structures": [

        "Arrays",
        "Stacks",
        "Queues",
        "Linked Lists",
        "Trees",
        "Graphs",
        "Hash Tables",
        "Binary Search",
    ],
}


TASK_TYPES = [

    "explanation",
    "definition_rewrite",
    "syntax_explanation",
    "code_example",
    "summary",
    "flashcard",
    "mindmap",
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "hint",
    "feedback",
    "revision_note",
]


DIFFICULTIES = [
    "easy",
    "medium",
    "hard",
]


TEACHING_STYLES = [

    "simple",
    "code_first",
    "analogy",
    "step_by_step",
    "question_based",
    "misconception_correction",
    "challenge_based",
    "revision_summary",
]


LEARNER_STATES = [

    "slow_learner",
    "low_mastery",
    "weak_output_prediction",
    "weak_debug",
    "low_confidence",
    "stable",
    "ready_for_challenge",
    "review_due",
]


def create_output(task_type, concept, domain):

    if task_type == "explanation":

        return f"""
{concept} is an important concept used in {domain} programming and software development.

Think of it like a tool that helps programmers solve problems efficiently.

Example:

score = 95

Here, the variable score stores the value 95 so it can be reused later in the program.

This concept is commonly used in real-world software projects and applications.
""".strip()

    elif task_type == "definition_rewrite":

        return f"""
{concept} can be understood as a core idea used to organize logic and solve programming tasks more effectively.

It helps developers write cleaner, more efficient, and maintainable code.
""".strip()

    elif task_type == "syntax_explanation":

        return f"""
The syntax of {concept} follows specific programming rules.

Correct syntax is important because even small mistakes can cause program errors or unexpected behavior.
""".strip()

    elif task_type == "code_example":

        return f"""
Example code for {concept}:

x = 10
print(x)

This example demonstrates how the concept works in a simple practical scenario.
""".strip()

    elif task_type == "summary":

        return f"""
Summary of {concept}:

- Used in software development
- Helps organize program logic
- Important for writing efficient code
- Frequently used in real-world applications
""".strip()

    elif task_type == "flashcard":

        return {
            "front": f"What is {concept}?",
            "back": f"{concept} is an important programming concept used to solve coding problems and build software applications."
        }

    elif task_type == "mindmap":

        return {
            "center": concept,
            "branches": [

                f"Definition of {concept}",
                "Real-world applications",
                "Code examples",
                "Common mistakes",
                "Best practices",
            ]
        }

    elif task_type == "mcq":

        return {

            "question": f"What is the main purpose of {concept}?",

            "options": [

                "Programming",
                "Cooking",
                "Painting",
                "Music",
            ],

            "answer": "Programming",

            "explanation": f"{concept} is primarily related to programming and software development."
        }

    elif task_type == "debug_task":

        return {

            "buggy_code":
                "for i in range(5)\n    print(i)",

            "expected_fix":
                "for i in range(5):\n    print(i)",

            "hint":
                "The loop statement is missing a colon (:). Python requires a colon after range(5) to begin the loop block correctly."
        }

    elif task_type == "output_prediction":

        return {

            "code":
                "x = 5\nprint(x)",

            "answer":
                "5"
        }

    elif task_type == "transfer_question":

        return {

            "question":
                f"How is {concept} used in real-world software projects?",

            "answer":
                f"{concept} is commonly used in applications, automation systems, and software development workflows."
        }

    elif task_type == "challenge_question":

        return {

            "challenge":
                f"Explain {concept} using a real-world analogy and provide a short code example.",

            "solution_outline":
                "Explain the concept using a practical scenario, describe why it is useful, and demonstrate a small working example."
        }

    elif task_type == "hint":

        return f"""
Think carefully about the purpose of {concept} and how it is used inside real programs.

Try solving a small example step-by-step before checking the final answer.
""".strip()

    elif task_type == "feedback":

        return f"""
Good attempt.

Your understanding of {concept} is improving, but review the syntax carefully and practice with more examples to strengthen your confidence.
""".strip()

    elif task_type == "revision_note":

        return f"""
Revision Notes for {concept}:

- Understand the core definition
- Practice syntax regularly
- Learn common mistakes
- Try real-world coding examples
- Revise problem-solving approaches
""".strip()

    return f"{concept} is a programming concept."


def build_dataset():

    rows = []

    concept_id = 1

    for domain, concepts in DOMAINS.items():

        for concept in concepts:

            current_id = f"C{concept_id}"

            concept_id += 1

            for difficulty in DIFFICULTIES:

                for teaching_style in TEACHING_STYLES:

                    for learner_state in LEARNER_STATES:

                        for task_type in TASK_TYPES:

                            row = {

                                "instruction":
                                    "Generate adaptive tutor content.",

                                "input": {

                                    "concept_id":
                                        current_id,

                                    "concept_name":
                                        concept,

                                    "domain":
                                        domain,

                                    "difficulty":
                                        difficulty,

                                    "learner_state":
                                        learner_state,

                                    "teaching_style":
                                        teaching_style,

                                    "task_type":
                                        task_type,

                                    "base_content":
                                        f"{concept} is an important topic in {domain}.",

                                    "examples":
                                        f"Example related to {concept}.",

                                    "key_points": [

                                        f"Understand the basics of {concept}",
                                        "Practice coding regularly",
                                        "Avoid common mistakes",
                                    ],

                                    "misconceptions": [

                                        f"{concept} is difficult to learn",
                                        "Syntax is optional",
                                    ],

                                    "real_world_use":
                                        f"{concept} is widely used in software projects and technical interviews.",
                                },

                                "output":
                                    create_output(
                                        task_type,
                                        concept,
                                        domain
                                    )
                            }

                            rows.append(row)

    return rows


def save_jsonl(rows, path):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        for i, row in enumerate(rows, start=1):

            if i % 5000 == 0:
                print(
                    f"  writing {path.name}: "
                    f"{i} / {len(rows)} rows"
                )

            f.write(
                json.dumps(row) + "\n"
            )


def main():

    print("\nGenerating tutor dataset...\n")

    rows = build_dataset()

    random.shuffle(rows)

    total = len(rows)

    train_end = int(total * 0.8)

    val_end = int(total * 0.9)

    train_rows = rows[:train_end]

    val_rows = rows[train_end:val_end]

    test_rows = rows[val_end:]

    save_jsonl(train_rows, TRAIN_FILE)

    save_jsonl(val_rows, VAL_FILE)

    save_jsonl(test_rows, TEST_FILE)

    total_concepts = sum(
        len(v)
        for v in DOMAINS.values()
    )

    print(f"Loaded concepts: {total_concepts}")

    print(f"Total samples: {total}")

    print(f"Train rows: {len(train_rows)}")

    print(f"Val rows: {len(val_rows)}")

    print(f"Test rows: {len(test_rows)}")

    print("\nSTATUS: PASS\n")


if __name__ == "__main__":

    main()