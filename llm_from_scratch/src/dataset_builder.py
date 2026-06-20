import json
import sqlite3
from pathlib import Path
from itertools import product


ROOT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "tutor_instruction_dataset.jsonl"

DB_FILES = {
    "Python": "python_learning.db",
    "SQL": "database_sql.db",
    "HTML": "html_web_basics.db",
    "Git": "git_version_control.db",
    "Data Structures": "data_structures.db",
}

DIFFICULTIES = ["easy", "medium", "hard"]

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

TASK_TYPES = [
    "explanation",
    "summary",
    "flashcard",
    "mindmap",
    "mcq",
    "output_prediction",
    "debug_task",
    "transfer_question",
    "challenge_question",
    "hint",
    "feedback",
    "revision_note",

    # NotebookLM-style tutor memory tasks
    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "weakness_review",
    "daily_review",
    "personal_flashcards",
]

TASK_TOKENS = {
    "explanation": "<task_explanation>",
    "summary": "<task_revision>",
    "flashcard": "<task_flashcard>",
    "mindmap": "<task_mindmap>",
    "mcq": "<task_mcq>",
    "output_prediction": "<task_output_prediction>",
    "debug_task": "<task_debug>",
    "transfer_question": "<task_transfer>",
    "challenge_question": "<task_challenge>",
    "hint": "<task_hint>",
    "feedback": "<task_feedback>",
    "revision_note": "<task_revision>",

    # NotebookLM-style tutor memory tasks
    "notebook_summary": "<task_notebook_summary>",
    "mistake_summary": "<task_mistake_summary>",
    "revision_plan": "<task_revision_plan>",
    "weakness_review": "<task_weakness_review>",
    "daily_review": "<task_daily_review>",
    "personal_flashcards": "<task_personal_flashcards>",
}

DIFFICULTY_TOKENS = {
    "easy": "<easy>",
    "medium": "<medium>",
    "hard": "<hard>",
}

STYLE_TOKENS = {
    "simple": "<style_simple>",
    "code_first": "<style_code>",
    "analogy": "<style_analogy>",
    "step_by_step": "<style_step_by_step>",
    "question_based": "<style_question_based>",
    "misconception_correction": "<style_misconception_correction>",
    "challenge_based": "<style_challenge_based>",
    "revision_summary": "<style_revision_summary>",
}


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()

def compact_text(value, max_chars=300):
    text = safe_text(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].strip()


def first_sentence(value, max_chars=180):
    text = safe_text(value)
    if not text:
        return ""
    for sep in [". ", "\n"]:
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    return compact_text(text, max_chars)


def get_primary_key_point(concept, max_chars=140):
    if concept.get("key_points"):
        return compact_text(concept["key_points"][0], max_chars)
    return first_sentence(concept.get("base_content", ""), max_chars)


def get_secondary_key_point(concept, max_chars=140):
    key_points = concept.get("key_points", [])
    if len(key_points) > 1:
        return compact_text(key_points[1], max_chars)
    return get_primary_key_point(concept, max_chars)


def get_primary_misconception(concept, max_chars=90):
    if concept.get("misconceptions"):
        text = compact_text(concept["misconceptions"][0], max_chars)
        text = text.replace("\n", " ").strip()
        return text
    return f"A common mistake is misunderstanding {concept['concept_name']}."


def get_example(concept, max_chars=180):
    if concept.get("examples"):
        return compact_text(concept["examples"][0], max_chars)
    return ""


def make_wrong_option_from_concept(concept):
    return f"{concept['concept_name']} is unrelated to {concept['domain']}."


def make_advanced_only_wrong_option(concept):
    return f"{concept['concept_name']} is only useful in advanced topics."


def split_field(value):
    text = safe_text(value)
    if not text:
        return []

    # Supports common separators used in DB text fields.
    parts = []
    for chunk in text.replace("\r", "\n").split("\n"):
        chunk = chunk.strip(" -•\t")
        if chunk:
            parts.append(chunk)

    if len(parts) <= 1 and "|" in text:
        parts = [p.strip() for p in text.split("|") if p.strip()]

    return parts


def read_concept_resources(db_path, domain):
    rows = []

    if not db_path.exists():
        print(f"[WARNING] Missing DB: {db_path}")
        return rows

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='concept_resources'
        """
    )
    table_exists = cursor.fetchone()

    if not table_exists:
        print(f"[WARNING] concept_resources table not found in {db_path.name}")
        conn.close()
        return rows

    cursor.execute("PRAGMA table_info(concept_resources)")
    columns = [row["name"] for row in cursor.fetchall()]

    required = [
        "concept_id",
        "topic",
        "base_content",
        "examples",
        "key_points",
        "misconceptions",
        "real_world_use",
        "next_concept_link",
    ]

    missing = [col for col in required if col not in columns]
    if missing:
        print(f"[WARNING] Missing columns in {db_path.name}: {missing}")

    select_cols = ", ".join([col for col in required if col in columns])
    cursor.execute(f"SELECT {select_cols} FROM concept_resources")

    for row in cursor.fetchall():
        item = dict(row)

        rows.append(
            {
                "concept_id": safe_text(item.get("concept_id")),
                "concept_name": safe_text(item.get("topic")),
                "domain": domain,
                "base_content": safe_text(item.get("base_content")),
                "examples": split_field(item.get("examples")),
                "key_points": split_field(item.get("key_points")),
                "misconceptions": split_field(item.get("misconceptions")),
                "real_world_use": safe_text(item.get("real_world_use")),
                "next_concept_link": safe_text(item.get("next_concept_link")),
            }
        )

    conn.close()
    return rows


def make_explanation(concept, difficulty, style):
    name = concept["concept_name"]
    base = concept["base_content"]
    examples = concept["examples"]
    example = examples[0] if examples else f"Example related to {name}."

    if difficulty == "easy":
        return (
            f"{name} means {base}\n\n"
            f"Example:\n{example}\n\n"
            f"Quick check: Can you explain {name} in one sentence?"
        )

    if difficulty == "medium":
        return (
            f"{name} is an important concept because it helps solve practical problems.\n\n"
            f"Core idea:\n{base}\n\n"
            f"Example:\n{example}\n\n"
            f"Quick check: Where would you use {name} in a real program?"
        )

    return (
        f"{name} is used when you need to apply the concept in a more flexible or advanced situation.\n\n"
        f"Core idea:\n{base}\n\n"
        f"Example:\n{example}\n\n"
        f"Quick check: Can you modify this example for a different use case?"
    )


def make_summary(concept):
    key_points = concept["key_points"][:3]
    if not key_points:
        key_points = [concept["base_content"]]

    lines = [f"Revision summary for {concept['concept_name']}:"]
    for point in key_points:
        lines.append(f"- {point}")
    return "\n".join(lines)


def make_flashcard(concept):
    answer = (
        compact_text(concept["key_points"][0], 140)
        if concept["key_points"]
        else first_sentence(concept["base_content"], 140)
    )

    return {
        "front": f"What should you remember about {concept['concept_name']}?",
        "back": answer or f"{concept['concept_name']} is a key concept in {concept['domain']}.",
    }


def make_mindmap(concept):
    branches = []

    if concept["key_points"]:
        branches.append({"name": "Key Points", "items": concept["key_points"][:4]})

    if concept["examples"]:
        branches.append({"name": "Examples", "items": concept["examples"][:2]})

    if concept["misconceptions"]:
        branches.append({"name": "Misconceptions", "items": concept["misconceptions"][:3]})

    if concept["real_world_use"]:
        branches.append({"name": "Real World Use", "items": [concept["real_world_use"]]})

    if not branches:
        branches.append({"name": "Core Idea", "items": [concept["base_content"]]})

    return {
        "center": concept["concept_name"],
        "branches": branches,
    }


def make_mcq(concept):
    name = concept["concept_name"]

    correct = get_primary_key_point(concept, 130)
    misconception = get_primary_misconception(concept, 90)

    if not correct:
        correct = f"{name} is an important concept in {concept['domain']}."

    return {
        "question": f"Which statement best describes {name}?",
        "options": [
            correct,
            misconception,
            make_wrong_option_from_concept(concept),
            make_advanced_only_wrong_option(concept),
        ],
        "answer": correct,
        "explanation": f"The correct answer matches the main rule of {name}.",
    }


def make_misconception_mcq(concept):
    name = concept["concept_name"]

    correct = get_primary_key_point(concept, 130)
    misconception = get_primary_misconception(concept, 130)

    return {
        "question": f"Which idea about {name} is correct?",
        "options": [
            correct,
            misconception,
            f"{name} does not affect practical work.",
            f"{name} should be skipped by beginners.",
        ],
        "answer": correct,
        "explanation": f"This avoids the common misconception about {name}.",
    }


def make_debug_task(concept):
    name = concept["concept_name"]
    domain = concept["domain"]
    misconception = get_primary_misconception(concept, 120)

    if domain == "Python":
        if "Variable" in name or "Variables" in name:
            return {
                "buggy_code": "print(name)\nname = \"Alice\"",
                "expected_fix": "name = \"Alice\"\nprint(name)",
                "hint": "Assign the variable before using it.",
            }

        if "Loop" in name or "Loops" in name:
            return {
                "buggy_code": "for i in range(3)\n    print(i)",
                "expected_fix": "for i in range(3):\n    print(i)",
                "hint": "A Python loop header needs a colon.",
            }

        if "Function" in name or "Functions" in name:
            return {
                "buggy_code": "def greet(name)\n    print(name)",
                "expected_fix": "def greet(name):\n    print(name)",
                "hint": "A function definition needs a colon.",
            }

        return {
            "buggy_code": "name = Alice\nprint(name)",
            "expected_fix": "name = \"Alice\"\nprint(name)",
            "hint": "String values need quotation marks.",
        }

    if domain == "SQL":
        return {
            "buggy_code": "SELEC name FROM students;",
            "expected_fix": "SELECT name FROM students;",
            "hint": "Check the spelling of SELECT.",
        }

    if domain == "HTML":
        return {
            "buggy_code": "<p>Hello",
            "expected_fix": "<p>Hello</p>",
            "hint": "Close the paragraph tag.",
        }

    if domain == "Git":
        return {
            "buggy_code": "git comit -m \"save\"",
            "expected_fix": "git commit -m \"save\"",
            "hint": "Check the spelling of commit.",
        }

    return {
        "buggy_code": "wrong_example",
        "expected_fix": "correct_example",
        "hint": f"Review this idea: {misconception}",
    }


def make_output_prediction(concept):
    name = concept["concept_name"]
    domain = concept["domain"]

    if domain == "Python":
        if "Variable" in name or "Variables" in name:
            return {
                "question": "What is the output of this code?",
                "code": "x = 10\nx = 20\nprint(x)",
                "answer": "20",
                "explanation": "The second assignment changes what x refers to.",
            }

        if "Loop" in name or "Loops" in name:
            return {
                "question": "What is the output of this code?",
                "code": "for i in range(3):\n    print(i)",
                "answer": "0\n1\n2",
                "explanation": "range(3) produces 0, 1, and 2.",
            }

        if "Function" in name or "Functions" in name:
            return {
                "question": "What is the output of this code?",
                "code": "def add(a, b):\n    return a + b\nprint(add(2, 3))",
                "answer": "5",
                "explanation": "The function returns 2 + 3.",
            }

        return {
            "question": "What is the output of this code?",
            "code": "x = 5\nprint(x)",
            "answer": "5",
            "explanation": "x stores 5, so print(x) displays 5.",
        }

    if domain == "SQL":
        return {
            "question": "What does this query return?",
            "code": "SELECT name FROM students;",
            "answer": "It returns values from the name column.",
            "explanation": "SELECT chooses which column to display.",
        }

    if domain == "HTML":
        return {
            "question": "What appears on the page?",
            "code": "<p>Hello</p>",
            "answer": "Hello",
            "explanation": "The paragraph element displays the text Hello.",
        }

    if domain == "Git":
        return {
            "question": "What does this command do?",
            "code": "git status",
            "answer": "It shows the working tree status.",
            "explanation": "git status shows changed, staged, and untracked files.",
        }

    return {
        "question": f"What happens when {name} is used correctly?",
        "code": get_example(concept, 120),
        "answer": f"It applies the main idea of {name}.",
        "explanation": get_primary_key_point(concept, 120),
    }


def make_transfer_question(concept):
    name = concept["concept_name"]
    real_use = compact_text(concept.get("real_world_use", ""), 100)

    if real_use:
        return f"Transfer question: How would you apply {name} in this real situation: {real_use}?"

    return f"Transfer question: How would you use {name} in a new real-world example?"


def make_challenge_question(concept):
    name = concept["concept_name"]
    key = get_primary_key_point(concept, 90)

    return (
        f"Challenge: Create one example using {name}. "
        f"Your example should show this rule: {key}"
    )


def make_hint(concept):
    key = get_primary_key_point(concept, 120)
    return f"Hint: Focus on this rule — {key}"


def make_feedback(concept):
    key = get_primary_key_point(concept, 120)
    misconception = get_primary_misconception(concept, 120)

    return (
        f"What was correct: You worked on {concept['concept_name']}.\n\n"
        f"What was missing: Remember this rule — {key}\n\n"
        f"Common mistake to avoid: {misconception}\n\n"
        f"Next step: Try one example that applies the rule correctly."
    )


def make_revision_note(concept):
    key_points = concept["key_points"][:3]
    points = "\n".join([f"- {p}" for p in key_points]) if key_points else f"- {concept['base_content']}"

    return (
        f"Revision note for {concept['concept_name']}:\n"
        f"{points}\n\n"
        f"Remember: connect the concept with an example."
    )


def make_notebook_summary(concept):
    return (
        f"Notebook summary for {concept['concept_name']}:\n\n"
        f"You are currently reviewing {concept['concept_name']} in {concept['domain']}.\n"
        f"Core idea: {concept['base_content']}\n\n"
        f"Focus on understanding the concept through examples and correcting repeated mistakes."
    )


def make_mistake_summary(concept):
    misconception = (
        concept["misconceptions"][0]
        if concept["misconceptions"]
        else f"A common mistake is misunderstanding the main rule of {concept['concept_name']}."
    )

    return (
        f"Mistake summary for {concept['concept_name']}:\n\n"
        f"Common mistake: {misconception}\n\n"
        f"Why it matters: This mistake can affect your ability to solve questions correctly.\n"
        f"Next step: Review one example and explain the correct rule in your own words."
    )


def make_revision_plan(concept):
    return (
        f"Revision plan for {concept['concept_name']}:\n\n"
        f"1. Read the short explanation.\n"
        f"2. Study one simple example.\n"
        f"3. Try one output prediction or debug question.\n"
        f"4. Review your mistake and write the corrected rule.\n"
        f"5. Attempt a slightly harder question."
    )


def make_weakness_review(concept):
    key = concept["key_points"][0] if concept["key_points"] else concept["base_content"]

    return (
        f"Weakness review for {concept['concept_name']}:\n\n"
        f"You need more practice with this idea:\n"
        f"{key}\n\n"
        f"Practice focus: explain the concept, then solve one question without looking at the answer."
    )


def make_daily_review(concept):
    return (
        f"Daily review note:\n\n"
        f"Today, revise {concept['concept_name']}.\n"
        f"Start with the definition, then look at one example, then answer one quick check question.\n\n"
        f"Goal: remember the main idea and avoid the common mistake."
    )


def make_personal_flashcards(concept):
    answer = (
        compact_text(concept["key_points"][0], 140)
        if concept["key_points"]
        else first_sentence(concept["base_content"], 140)
    )

    return {
        "front": f"What is my weak point in {concept['concept_name']}?",
        "back": answer or f"Review the main rule of {concept['concept_name']}.",
    }


def build_output(concept, task_type, difficulty, teaching_style):
    if task_type == "explanation":
        return make_explanation(concept, difficulty, teaching_style)

    if task_type == "summary":
        return make_summary(concept)

    if task_type == "flashcard":
        return make_flashcard(concept)

    if task_type == "mindmap":
        return make_mindmap(concept)

    if task_type == "mcq":
        return make_mcq(concept)

    if task_type == "debug_task":
        return make_debug_task(concept)

    if task_type == "output_prediction":
        return make_output_prediction(concept)

    if task_type == "transfer_question":
        return make_transfer_question(concept)

    if task_type == "challenge_question":
        return make_challenge_question(concept)

    if task_type == "hint":
        return make_hint(concept)

    if task_type == "feedback":
        return make_feedback(concept)

    if task_type == "revision_note":
        return make_revision_note(concept)

    if task_type == "notebook_summary":
        return make_notebook_summary(concept)

    if task_type == "mistake_summary":
        return make_mistake_summary(concept)

    if task_type == "revision_plan":
        return make_revision_plan(concept)

    if task_type == "weakness_review":
        return make_weakness_review(concept)

    if task_type == "daily_review":
        return make_daily_review(concept)

    if task_type == "personal_flashcards":
        return make_personal_flashcards(concept)

    return f"Generate tutor content for {concept['concept_name']}."

def build_training_text(row):
    input_data = row["input"]

    task_type = input_data["task_type"]
    difficulty = input_data["difficulty"]
    teaching_style = input_data["teaching_style"]

    task_token = TASK_TOKENS.get(task_type, f"<task_{task_type}>")
    difficulty_token = DIFFICULTY_TOKENS.get(difficulty, f"<{difficulty}>")
    style_token = STYLE_TOKENS.get(teaching_style, f"<style_{teaching_style}>")

    output = row["output"]
    if isinstance(output, dict):
        # Structured outputs must remain valid JSON.
        output_text = json.dumps(output, ensure_ascii=False)
    else:
        output_text = compact_text(str(output).strip(), 500)

    key_points_list = input_data.get("key_points", [])[:1]
    misconceptions_list = input_data.get("misconceptions", [])[:1]
    examples_list = input_data.get("examples", [])[:1]

    key_points = " | ".join([compact_text(x, 100) for x in key_points_list])
    misconceptions = " | ".join([compact_text(x, 100) for x in misconceptions_list])
    examples = " | ".join([compact_text(x, 120) for x in examples_list])

    base_content = compact_text(input_data.get("base_content", ""), 120)

    if task_type == "mcq":
        format_rule = "JSON only: question, options, answer, explanation. Exactly 4 options."

    elif task_type == "debug_task":
        format_rule = "JSON only: buggy_code, expected_fix, hint."

    elif task_type in {"flashcard", "personal_flashcards"}:
        format_rule = "JSON only: front, back."

    elif task_type == "mindmap":
        format_rule = "JSON only: center, branches."

    elif task_type == "output_prediction":
        format_rule = "JSON only: question, code, answer, explanation."

    else:
        format_rule = "Plain text only."

    return f"""<bos>
<instruction> Generate tutor output.
<format_rule> {format_rule}
{task_token}
{difficulty_token}
{style_token}
<concept> {input_data["concept_name"]}
<domain> {input_data["domain"]}
<learner_state> {input_data["learner_state"]}
<task> {task_type}
<content> {base_content}
<key_points> {key_points}
<misconceptions> {misconceptions}
<examples> {examples}
<answer> {output_text}
<eos>"""

def build_dataset():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_concepts = []

    for domain, db_file in DB_FILES.items():
        db_path = RAW_DIR / db_file
        concepts = read_concept_resources(db_path, domain)
        print(f"{domain}: {len(concepts)} concepts loaded")
        all_concepts.extend(concepts)

    if not all_concepts:
        raise RuntimeError(
            "No concepts loaded. Check whether DB files exist in data/raw/ "
            "and contain concept_resources table."
        )

    rows = []

    for concept in all_concepts:
        for difficulty, learner_state, teaching_style, task_type in product(
            DIFFICULTIES,
            LEARNER_STATES,
            TEACHING_STYLES,
            TASK_TYPES,
        ):
            output = build_output(concept, task_type, difficulty, teaching_style)

            row = {
                "instruction": "Generate tutor content for the given learner state and task type.",
                "input": {
                    "concept_id": concept["concept_id"],
                    "concept_name": concept["concept_name"],
                    "domain": concept["domain"],
                    "difficulty": difficulty,
                    "learner_state": learner_state,
                    "teaching_style": teaching_style,
                    "task_type": task_type,
                    "base_content": concept["base_content"],
                    "key_points": concept["key_points"],
                    "misconceptions": concept["misconceptions"],
                    "examples": concept["examples"],
                    "real_world_use": concept["real_world_use"],
                    "next_concept_link": concept["next_concept_link"],
                },
                "output": output,
            }

            row["training_text"] = build_training_text(row)
            rows.append(row)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\nDataset created successfully.")
    print(f"Path: {OUTPUT_PATH}")
    print(f"Total concepts: {len(all_concepts)}")
    print(f"Total rows: {len(rows)}")

    print("\nSample row:")
    print(json.dumps(rows[0], indent=2, ensure_ascii=False)[:2500])


if __name__ == "__main__":
    build_dataset()
