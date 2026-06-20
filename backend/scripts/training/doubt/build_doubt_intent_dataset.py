from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


CSV_OUTPUT = Path("evaluation_outputs/csv/doubt_intent_dataset.csv")
JSON_OUTPUT = Path("evaluation_outputs/json/doubt_intent_dataset_summary.json")
MD_OUTPUT = Path("evaluation_outputs/reports/doubt_intent_dataset_summary.md")

FIELDS = [
    "doubt_text",
    "intent_label",
    "domain",
    "concept_id",
    "concept_name",
    "difficulty",
    "expected_route",
    "needs_code_context",
    "needs_rag_context",
    "recommended_followup_type",
]

INTENT_META = {
    "concept_doubt": ("rag_concept_explanation", 0, 1, "concept_check"),
    "syntax_doubt": ("syntax_help", 1, 1, "syntax_fix"),
    "debug_doubt": ("debug_help", 1, 1, "debug_trace"),
    "output_prediction_doubt": ("trace_output_help", 1, 1, "output_trace"),
    "example_request": ("example_generation", 0, 1, "example_check"),
    "difference_doubt": ("comparison_explanation", 0, 1, "compare_check"),
    "real_world_request": ("real_world_application", 0, 1, "application_check"),
    "revision_doubt": ("revision_recap", 0, 1, "recall_check"),
    "challenge_help": ("challenge_support", 0, 1, "hint_or_step"),
    "next_step_doubt": ("adaptive_next_step", 0, 1, "path_choice"),
    "low_confidence_doubt": ("supportive_reteach", 0, 1, "confidence_check"),
}

CONCEPTS = [
    ("Python", "PY_VAR", "Python Variables"),
    ("Python", "PY_LOOP", "Loops"),
    ("SQL", "SQL_SELECT", "SQL SELECT/WHERE"),
    ("HTML", "HTML_FORM", "HTML Tags/Forms"),
    ("Git", "GIT_BRANCH", "Git Commits/Branches"),
    ("Data Structures", "DS_STACK", "Data Structures Arrays/Stacks"),
]

EXAMPLES = {
    "concept_doubt": [
        "I don't understand variables",
        "What does SELECT mean?",
        "Can you explain HTML forms?",
        "What is a stack?",
        "I am not clear about Git commits",
        "What does a loop do?",
        "Explain WHERE in SQL",
        "What is an array in data structures?",
        "I need the meaning of branch in Git",
        "What is a Python data type?",
    ],
    "syntax_doubt": [
        "Why is 2score = 10 invalid?",
        "What is wrong with this tag syntax?",
        "Why does my for loop syntax fail?",
        "Is SELECT name FROM valid SQL syntax?",
        "Why does this HTML input tag look wrong?",
        "Why is if x = 5 invalid?",
        "What syntax error is in this Python line?",
        "Why does git commit -m need quotes?",
        "How should I write a stack push statement?",
        "Why is my WHERE clause syntax wrong?",
    ],
    "debug_doubt": [
        "My code gives an error, can you debug it?",
        "Why does this print wrong output?",
        "This loop never stops, help me debug",
        "My SQL query returns too many rows",
        "My form is not submitting correctly",
        "Git says branch not found, what is wrong?",
        "My stack pop crashes",
        "This Python variable is undefined",
        "Can you find the bug in my code?",
        "Why is my array index error happening?",
    ],
    "output_prediction_doubt": [
        "What will this code print?",
        "How do I trace this loop output?",
        "Predict the output of this Python snippet",
        "What rows will this SELECT return?",
        "What appears on the page from this HTML?",
        "What will happen after this stack pop?",
        "Trace the value of x after the loop",
        "What output comes from this print statement?",
        "How do I know the final total?",
        "Can you walk through the output?",
    ],
    "example_request": [
        "Give me another example of JOIN",
        "Show me a simple stack example",
        "Can I see an example of variables?",
        "Give an HTML form example",
        "Show a Git branch example",
        "Give me one more loop example",
        "Show an example of WHERE",
        "Can you give an array example?",
        "Give a real Python data type example",
        "Show me a commit message example",
    ],
    "difference_doubt": [
        "What is the difference between list and array?",
        "What is the difference between WHERE and HAVING?",
        "Difference between commit and branch?",
        "How is for loop different from while loop?",
        "What is the difference between div and form?",
        "How are stack and queue different?",
        "Difference between string and integer?",
        "What is SELECT versus WHERE?",
        "How is push different from pop?",
        "What is the difference between label and input?",
    ],
    "real_world_request": [
        "Where do we use Git branches in real projects?",
        "Where are SQL SELECT queries used in real life?",
        "How are loops used in apps?",
        "Where do websites use HTML forms?",
        "When do programmers use stacks?",
        "How are variables used in billing software?",
        "Real world use of arrays?",
        "Where do data types matter in projects?",
        "How do commits help a team?",
        "Where do we use WHERE filters?",
    ],
    "revision_doubt": [
        "Can you revise variables quickly?",
        "I forgot SQL SELECT, recap it",
        "Review loops for me",
        "Give me a quick revision of HTML tags",
        "Revise Git commits and branches",
        "I need a recap of stacks",
        "Can you summarize arrays again?",
        "Quickly revise WHERE clause",
        "I forgot Python data types",
        "Review form inputs again",
    ],
    "challenge_help": [
        "Give me a harder problem",
        "Help me solve this challenge",
        "Can you give a challenge on loops?",
        "I need a hint for this stack challenge",
        "Make this SQL task harder",
        "Give me an advanced Git problem",
        "Help with the challenge question",
        "Can I try a difficult HTML form task?",
        "Give me a variable challenge",
        "What is a hard array exercise?",
    ],
    "next_step_doubt": [
        "What should I study after variables?",
        "What comes after SELECT?",
        "What should I learn next in HTML?",
        "After loops what topic should I do?",
        "What comes after Git branches?",
        "What is the next data structure after stacks?",
        "Where should I go next?",
        "Which concept should I study now?",
        "What is the next lesson?",
        "What should I practice after arrays?",
    ],
    "low_confidence_doubt": [
        "I am confused",
        "I don't know if I understood this",
        "I am not confident",
        "This topic feels difficult",
        "I think I am lost",
        "I don't understand anything",
        "Can you explain more slowly?",
        "I am unsure about my answer",
        "I still feel weak in this concept",
        "I need simpler help",
    ],
}


def build_dataset() -> dict:
    rows = []
    for intent, examples in EXAMPLES.items():
        route, needs_code, needs_rag, followup = INTENT_META[intent]
        for idx, text in enumerate(examples):
            domain, concept_id, concept_name = CONCEPTS[idx % len(CONCEPTS)]
            rows.append(
                {
                    "doubt_text": text,
                    "intent_label": intent,
                    "domain": domain,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "difficulty": ["easy", "medium", "hard"][idx % 3],
                    "expected_route": route,
                    "needs_code_context": needs_code,
                    "needs_rag_context": needs_rag,
                    "recommended_followup_type": followup,
                }
            )

    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    label_counts = Counter(row["intent_label"] for row in rows)
    summary = {
        "status": "success",
        "module": "doubt_intent_dataset_builder",
        "csv_output": str(CSV_OUTPUT),
        "row_count": len(rows),
        "intent_count": len(label_counts),
        "label_distribution": dict(label_counts),
        "domains": sorted({row["domain"] for row in rows}),
        "limitations": ["Curated project-specific dataset; future work should add real learner doubts."],
    }
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    MD_OUTPUT.write_text(
        "# Doubt Intent Dataset Summary\n\n"
        f"Status: **{summary['status']}**\n\n"
        f"- Rows: {summary['row_count']}\n"
        f"- Intents: {summary['intent_count']}\n"
        f"- Label distribution: {summary['label_distribution']}\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = build_dataset()
    print("STATUS: success")
    print("MODULE: doubt_intent_dataset_builder")
    print(f"CSV_OUTPUT: {CSV_OUTPUT}")
    print(f"JSON_REPORT: {JSON_OUTPUT}")
    print(f"MD_REPORT: {MD_OUTPUT}")


if __name__ == "__main__":
    main()
