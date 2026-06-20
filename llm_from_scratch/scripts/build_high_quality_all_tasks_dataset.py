import json
import random
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]

MAIN_PROJECT_CANDIDATES = [
    ROOT.parent / "cognition_adaptive_AI_tutor",
    ROOT.parent / "cognition_adaptive_ai_tutor",
]

MAIN_PROJECT = next((p for p in MAIN_PROJECT_CANDIDATES if p.exists()), MAIN_PROJECT_CANDIDATES[0])
DB_DIR = MAIN_PROJECT / "external" / "core_data"

OUT_DIR = ROOT / "training_data" / "high_quality_all_tasks"
STRUCTURED_DIR = ROOT / "training_data" / "structured_generation"
REPORT_DIR = ROOT / "outputs" / "final_reports"

OUT_DIR.mkdir(parents=True, exist_ok=True)
STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


SUBJECT_DBS = {
    "Python": "python_learning.db",
    "SQL": "database_sql.db",
    "HTML": "html_web_basics.db",
    "Git": "git_version_control.db",
    "Data Structures": "data_structures.db",
}


ALL_TASK_TYPES = [
    "explanation",
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "comparison_view",
    "real_world_connection_view",

    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",

    "revision_note",
    "revision_summary",
    "weakness_review",
    "daily_review",
    "personal_revision_plan",
    "recommended_revision_views",
    "spaced_repetition_card",

    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",

    "mindmap",
    "concept_mindmap",
    "comparison_mindmap",

    "feedback",
    "correct_answer_feedback",
    "wrong_answer_feedback",
    "partial_answer_feedback",
    "debug_feedback",
    "output_prediction_feedback",
    "next_step_feedback",
    "encouragement_feedback",

    "hint",
    "small_hint",
    "guided_hint",
    "worked_example_hint",
    "debug_hint",
    "syntax_hint",
    "output_prediction_hint",
    "misconception_hint",
    "next_step_hint",
    "analogy_hint",

    "doubt_answer",
    "concept_doubt_answer",
    "syntax_doubt_answer",
    "debug_doubt_answer",
    "output_doubt_answer",
    "example_request_answer",
    "revision_doubt_answer",
    "next_step_doubt_answer",
    "comparison_doubt_answer",

    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "comeback_summary",
    "returning_learner_summary",
    "progress_insight",

    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",

    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
]


TASK_TOKENS = {
    "explanation": "<task_explanation>",
    "definition_view": "<task_explanation>",
    "simple_example_view": "<task_explanation>",
    "step_by_step_view": "<task_explanation>",
    "analogy_view": "<task_explanation>",
    "code_view": "<task_explanation>",
    "misconception_view": "<task_explanation>",
    "debug_view": "<task_debug>",
    "output_prediction_view": "<task_output_prediction>",
    "transfer_view": "<task_transfer>",
    "challenge_view": "<task_challenge>",
    "revision_summary_view": "<task_revision>",
    "comparison_view": "<task_transfer>",
    "real_world_connection_view": "<task_transfer>",

    "mcq": "<task_mcq>",
    "debug_task": "<task_debug>",
    "output_prediction": "<task_output_prediction>",
    "transfer_question": "<task_transfer>",
    "challenge_question": "<task_challenge>",
    "explanation_check": "<task_explanation>",
    "syntax_completion": "<task_debug>",
    "coding_prompt": "<task_challenge>",
    "code_reasoning_task": "<task_challenge>",
    "fill_in_the_blank": "<task_debug>",
    "true_or_false": "<task_mcq>",

    "revision_note": "<task_revision>",
    "revision_summary": "<task_revision>",
    "weakness_review": "<task_weakness_review>",
    "daily_review": "<task_daily_review>",
    "personal_revision_plan": "<task_revision_plan>",
    "recommended_revision_views": "<task_revision_plan>",
    "spaced_repetition_card": "<task_revision>",

    "flashcard": "<task_flashcard>",
    "concept_recall_flashcard": "<task_flashcard>",
    "misconception_flashcard": "<task_flashcard>",
    "example_flashcard": "<task_flashcard>",
    "debug_flashcard": "<task_flashcard>",
    "personal_flashcards": "<task_flashcard>",
    "syntax_flashcard": "<task_flashcard>",

    "mindmap": "<task_mindmap>",
    "concept_mindmap": "<task_mindmap>",
    "comparison_mindmap": "<task_mindmap>",

    "feedback": "<task_feedback>",
    "correct_answer_feedback": "<task_feedback>",
    "wrong_answer_feedback": "<task_feedback>",
    "partial_answer_feedback": "<task_feedback>",
    "debug_feedback": "<task_feedback>",
    "output_prediction_feedback": "<task_feedback>",
    "next_step_feedback": "<task_feedback>",
    "encouragement_feedback": "<task_feedback>",

    "hint": "<task_hint>",
    "small_hint": "<task_hint>",
    "guided_hint": "<task_hint>",
    "worked_example_hint": "<task_hint>",
    "debug_hint": "<task_hint>",
    "syntax_hint": "<task_hint>",
    "output_prediction_hint": "<task_hint>",
    "misconception_hint": "<task_hint>",
    "next_step_hint": "<task_hint>",
    "analogy_hint": "<task_hint>",

    "doubt_answer": "<task_doubt_answer>",
    "concept_doubt_answer": "<task_doubt_answer>",
    "syntax_doubt_answer": "<task_doubt_answer>",
    "debug_doubt_answer": "<task_doubt_answer>",
    "output_doubt_answer": "<task_doubt_answer>",
    "example_request_answer": "<task_doubt_answer>",
    "revision_doubt_answer": "<task_doubt_answer>",
    "next_step_doubt_answer": "<task_doubt_answer>",
    "comparison_doubt_answer": "<task_doubt_answer>",

    "notebook_summary": "<task_notebook_summary>",
    "mistake_summary": "<task_mistake_summary>",
    "revision_plan": "<task_revision_plan>",
    "comeback_summary": "<task_comeback_summary>",
    "returning_learner_summary": "<task_comeback_summary>",
    "progress_insight": "<task_notebook_summary>",

    "practice_question": "<task_challenge>",
    "transfer_task": "<task_transfer>",
    "real_world_application_question": "<task_transfer>",
    "debug_challenge": "<task_challenge>",
    "output_prediction_challenge": "<task_challenge>",
    "multi_step_challenge": "<task_challenge>",

    "voice_script": "<task_voice_script>",
    "teaching_voice_script": "<task_voice_script>",
    "revision_voice_script": "<task_voice_script>",
    "mistake_feedback_voice_script": "<task_voice_script>",
    "doubt_explanation_voice_script": "<task_voice_script>",
    "encouragement_script": "<task_voice_script>",
    "next_step_guidance_script": "<task_voice_script>",
    "concept_intro_voice_script": "<task_voice_script>",
}


DIFFICULTIES = ["<easy>", "<medium>", "<hard>"]

STYLES = [
    "<style_step_by_step>",
    "<style_code>",
    "<style_analogy>",
    "<style_revision>",
    "<style_misconception>",
    "<style_challenge>",
]


def clean_text(value: Any, max_len: int = 700) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    return text[:max_len].strip()


def strip_bullets(text: str) -> str:
    text = clean_text(text, 1400)
    text = text.replace("•", " ")
    text = text.replace(" - ", "\n- ")
    parts = []

    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if chunk.startswith("-"):
            chunk = chunk[1:].strip()
        if chunk:
            parts.append(chunk)

    return " ".join(parts).strip()


def split_items(text: str, max_items: int = 3) -> List[str]:
    text = clean_text(text, 1600)
    text = text.replace("•", "\n- ")
    text = text.replace(" - ", "\n- ")
    raw_items: List[str] = []

    for part in text.split("\n"):
        part = part.strip()
        if part.startswith("-"):
            part = part[1:].strip()
        if part:
            raw_items.append(part)

    if not raw_items:
        raw_items = [p.strip() for p in text.split(". ") if len(p.strip()) > 10]

    cleaned_items: List[str] = []
    for item in raw_items:
        item = complete_sentence(item, 220)
        if item and item not in cleaned_items:
            cleaned_items.append(item)

    return cleaned_items[:max_items]


def complete_sentence(text: str, max_len: int = 220) -> str:
    text = strip_bullets(text)
    if not text:
        return ""

    text = text[:max_len].strip()

    last_end = max(text.rfind("."), text.rfind("?"), text.rfind("!"))
    if last_end > 45:
        text = text[: last_end + 1].strip()

    broken_suffixes = [
        " def", " def rev", " Exampl", " while co", " affect re",
        " require", " requires", " val", " lo", " left jo", " LEFT JO",
        " ite", " re", " co", " a"
    ]

    lowered = text.lower()
    for suffix in broken_suffixes:
        if lowered.endswith(suffix.lower()):
            text = text[: -len(suffix)].strip()
            break

    if text and text[-1] not in ".!?;:})]\"'":
        text += "."

    return text


def first_sentence(text: str, fallback: str) -> str:
    cleaned = complete_sentence(text, 240)
    return cleaned if cleaned else fallback


def load_concepts() -> List[Dict[str, Any]]:
    concepts: List[Dict[str, Any]] = []

    for domain, db_name in SUBJECT_DBS.items():
        db_path = DB_DIR / db_name

        if not db_path.exists():
            print(f"WARNING: missing DB: {db_path}")
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        try:
            rows = conn.execute(
                """
                SELECT concept_id, topic, base_content, examples, key_points,
                       misconceptions, real_world_use, next_concept_link
                FROM concept_resources
                """
            ).fetchall()
        except sqlite3.OperationalError as exc:
            print(f"WARNING: concept_resources missing in {db_path}: {exc}")
            conn.close()
            continue

        for row in rows:
            concepts.append({
                "domain": domain,
                "concept_id": clean_text(row["concept_id"], 80),
                "concept_name": clean_text(row["topic"], 120),
                "definition": clean_text(row["base_content"], 1400),
                "examples": clean_text(row["examples"], 1400),
                "key_points": clean_text(row["key_points"], 1400),
                "misconceptions": clean_text(row["misconceptions"], 1400),
                "real_world_use": clean_text(row["real_world_use"], 1400),
                "next_concept_link": clean_text(row["next_concept_link"], 350),
            })

        conn.close()

    return concepts


def definition(c: Dict[str, Any]) -> str:
    return first_sentence(c["definition"], f"{c['concept_name']} is a core concept.")


def key(c: Dict[str, Any]) -> str:
    items = split_items(c["key_points"], 1)
    return items[0] if items else f"{c['concept_name']} has an important rule learners must apply."


def key_items(c: Dict[str, Any], n: int = 3) -> List[str]:
    items = split_items(c["key_points"], n)
    return items if items else [key(c)]


def concept_specific_example(c: Dict[str, Any]) -> str:
    name = c["concept_name"].lower()
    domain = c["domain"]

    if domain == "Data Structures" and "stack" in name:
        return "stack.append('A'); stack.append('B'); stack.pop() returns 'B' because Stack follows LIFO."

    if domain == "Data Structures" and "queue" in name:
        return "queue.append('A'); queue.append('B'); queue.pop(0) returns 'A' because Queue follows FIFO."

    if domain == "Data Structures" and "linked" in name:
        return "first.next = second connects the first node to the second node."

    if domain == "Python" and "loop" in name:
        return "for i in range(3): print(i) prints 0, 1, and 2."

    if domain == "Python" and "variable" in name:
        return "score = 10 stores the value 10 using the name score."

    if domain == "Python" and "function" in name:
        return "def greet(name): return 'Hello ' + name creates a reusable function."

    if domain == "SQL" and "join" in name:
        return "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id returns matching customer-order rows."

    if domain == "SQL" and "select" in name:
        return "SELECT name FROM students returns the name column from the students table."

    if domain == "SQL" and "where" in name:
        return "SELECT name FROM students WHERE age > 18 returns only students older than 18."

    if domain == "SQL" and "index" in name:
        return "CREATE INDEX idx_users_email ON users(email) helps speed up searches by email."

    if domain == "SQL" and "window" in name:
        return "RANK() OVER (PARTITION BY department ORDER BY salary DESC) ranks employees inside each department."

    if domain == "SQL" and ("cte" in name or "common table" in name):
        return "WITH high_earners AS (...) SELECT * FROM high_earners creates a temporary named result for one query."

    if domain == "HTML" and ("tag" in name or "element" in name):
        return "<p>Hello</p> creates a paragraph element."

    if domain == "Git" and "commit" in name:
        return "git commit -m \"Add login page\" saves staged changes with a message."

    return ""


def example(c: Dict[str, Any]) -> str:
    specific = concept_specific_example(c)
    if specific:
        return specific

    items = split_items(c["examples"], 1)
    return items[0] if items else f"Example of {c['concept_name']}."


def example_items(c: Dict[str, Any], n: int = 2) -> List[str]:
    first = example(c)
    items = split_items(c["examples"], n)
    clean_items = [first]

    for item in items:
        if item not in clean_items and "print(stack." not in item and "Exampl" not in item and "while co" not in item:
            clean_items.append(item)

    return clean_items[:n]

def mistake(c: Dict[str, Any]) -> str:
    items = split_items(c["misconceptions"], 1)
    return items[0] if items else f"A common mistake is misunderstanding {c['concept_name']}."


def use_case(c: Dict[str, Any]) -> str:
    items = split_items(c["real_world_use"], 1)
    return items[0] if items else f"{c['concept_name']} is useful in practical coding and learning tasks."


def prompt_for(c: Dict[str, Any], task_type: str, difficulty: str, style: str) -> str:
    token = TASK_TOKENS.get(task_type, "<task_explanation>")

    return (
        "<bos>\n"
        "<instruction> Generate project-specific tutor learning output.\n"
        f"{token}\n"
        f"{difficulty}\n"
        f"{style}\n"
        f"<task_type> {task_type}\n"
        f"<concept> {c['concept_name']}\n"
        f"<domain> {c['domain']}\n"
        "<context>\n"
        f"Definition: {definition(c)}\n"
        f"Key points: {' '.join(key_items(c, 3))}\n"
        f"Examples: {' '.join(example_items(c, 2))}\n"
        f"Misconceptions: {mistake(c)}\n"
        f"Real-world use: {use_case(c)}\n"
        "</context>\n"
        "<answer>"
    )


def debug_payload(c: Dict[str, Any]) -> Dict[str, str]:
    name = c["concept_name"].lower()
    domain = c["domain"]

    if domain == "Python" and "variable" in name:
        return {
            "buggy_code": "2score = 10\nprint(2score)",
            "expected_fix": "score2 = 10\nprint(score2)",
            "hint": "Variable names cannot start with a digit.",
            "explanation": "Python identifiers must start with a letter or underscore, not a number.",
        }

    if domain == "Python" and "loop" in name:
        return {
            "buggy_code": "for i in range(3)\n    print(i)",
            "expected_fix": "for i in range(3):\n    print(i)",
            "hint": "A loop header needs a colon.",
            "explanation": "Python uses a colon after loop headers to start the indented block.",
        }

    if domain == "Python" and "function" in name:
        return {
            "buggy_code": "def greet(name)\n    return 'Hello ' + name",
            "expected_fix": "def greet(name):\n    return 'Hello ' + name",
            "hint": "A function definition needs a colon.",
            "explanation": "A def statement must end with a colon before the function body.",
        }

    if domain == "SQL" and "select" in name:
        return {
            "buggy_code": "SELEC name FROM students;",
            "expected_fix": "SELECT name FROM students;",
            "hint": "Check the SELECT keyword spelling.",
            "explanation": "SELECT retrieves columns from a table.",
        }

    if domain == "SQL" and "where" in name:
        return {
            "buggy_code": "SELECT name FROM students WHERE age = NULL;",
            "expected_fix": "SELECT name FROM students WHERE age IS NULL;",
            "hint": "NULL must be checked with IS NULL.",
            "explanation": "SQL does not compare NULL using =.",
        }

    if domain == "SQL" and "join" in name:
        return {
            "buggy_code": "SELECT customers.name, orders.amount FROM customers JOIN orders;",
            "expected_fix": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;",
            "hint": "A JOIN needs an ON condition.",
            "explanation": "JOIN combines matching rows using a related column.",
        }

    if domain == "SQL" and "index" in name:
        return {
            "buggy_code": "SELECT * FROM users WHERE email = 'a@test.com'; -- slow lookup with no index",
            "expected_fix": "CREATE INDEX idx_users_email ON users(email);\nSELECT * FROM users WHERE email = 'a@test.com';",
            "hint": "Indexes speed up repeated lookups.",
            "explanation": "An index helps the database avoid scanning every row.",
        }

    if domain == "SQL" and "window" in name:
        return {
            "buggy_code": "SELECT department, MAX(salary) FROM employees;",
            "expected_fix": "SELECT name, department, salary, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank FROM employees;",
            "hint": "Use a window function for row-level output with group-based ranking.",
            "explanation": "Window functions compute across related rows without collapsing rows.",
        }

    if domain == "SQL" and ("cte" in name or "common table" in name):
        return {
            "buggy_code": "high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
            "expected_fix": "WITH high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
            "hint": "A CTE starts with WITH.",
            "explanation": "A Common Table Expression is defined with WITH and exists for that query.",
        }

    if domain == "HTML" and ("tag" in name or "element" in name):
        return {
            "buggy_code": "<p>Hello",
            "expected_fix": "<p>Hello</p>",
            "hint": "Most HTML elements need closing tags.",
            "explanation": "The paragraph element should be closed with </p>.",
        }

    if domain == "Git" and "commit" in name:
        return {
            "buggy_code": "git commit -m",
            "expected_fix": "git commit -m \"Describe the change\"",
            "hint": "A commit message is required after -m.",
            "explanation": "Git commits should include a meaningful message.",
        }

    if domain == "Data Structures" and "stack" in name:
        return {
            "buggy_code": "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop(0))",
            "expected_fix": "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop())",
            "hint": "A stack removes the last inserted item.",
            "explanation": "Stack follows LIFO, so pop() removes the last pushed value.",
        }

    if domain == "Data Structures" and "linked" in name:
        return {
            "buggy_code": "first.next = None\nsecond = Node(20)",
            "expected_fix": "first.next = second",
            "hint": "A linked list connects nodes using next references.",
            "explanation": "Each node should point to the next node in the list.",
        }

    if domain == "Data Structures" and "queue" in name:
        return {
            "buggy_code": "queue = []\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop())",
            "expected_fix": "queue = []\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop(0))",
            "hint": "A queue removes the first inserted item.",
            "explanation": "Queue follows FIFO, so dequeue removes from the front.",
        }

    return {
        "buggy_code": f"# Buggy example for {c['concept_name']}\nwrong_step = 'misapplied concept'",
        "expected_fix": f"Apply the key rule correctly: {key(c)}",
        "hint": f"Use the key rule of {c['concept_name']} instead of a generic guess.",
        "explanation": f"The fix should follow this idea: {key(c)}",
    }


def output_prediction_payload(c: Dict[str, Any]) -> Dict[str, str]:
    name = c["concept_name"].lower()
    domain = c["domain"]

    if domain == "Data Structures" and "stack" in name:
        return {
            "code": "stack=[]\nstack.append('A')\nstack.append('B')\nprint(stack.pop())",
            "question": "What is printed?",
            "answer": "B",
            "explanation": "A stack removes the last pushed item first.",
        }

    if domain == "Data Structures" and "queue" in name:
        return {
            "code": "queue=[]\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop(0))",
            "question": "What is printed?",
            "answer": "A",
            "explanation": "A queue removes the first inserted item first.",
        }

    if domain == "Python" and "loop" in name:
        return {
            "code": "for i in range(3):\n    print(i)",
            "question": "What is printed?",
            "answer": "0\n1\n2",
            "explanation": "range(3) produces 0, 1, and 2.",
        }

    if domain == "SQL" and "join" in name:
        return {
            "code": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;",
            "question": "What does this query return?",
            "answer": "Customer names with matching order amounts.",
            "explanation": "The JOIN connects matching customer and order rows.",
        }

    if domain == "SQL" and "where" in name:
        return {
            "code": "SELECT name FROM students WHERE age > 18;",
            "question": "What does this query return?",
            "answer": "Names of students whose age is greater than 18.",
            "explanation": "WHERE filters rows using the condition.",
        }

    return {
        "code": example(c),
        "question": f"What key idea does this example show about {c['concept_name']}?",
        "answer": key(c),
        "explanation": f"The example demonstrates the main rule of {c['concept_name']}.",
    }


def options_for(c: Dict[str, Any]) -> List[str]:
    correct = key(c)
    domain = c["domain"]

    distractors = {
        "Python": [
            "It ignores indentation rules.",
            "It only works inside SQL queries.",
            "It permanently stores values in CPU cache.",
        ],
        "SQL": [
            "It permanently edits every table row.",
            "It replaces all SQL clauses.",
            "It only works without a database table.",
        ],
        "HTML": [
            "It directly modifies database rows.",
            "It trains machine learning models.",
            "It replaces browser rendering.",
        ],
        "Git": [
            "It changes programming language syntax.",
            "It deletes the need for project history.",
            "It stores SQL rows instead of version history.",
        ],
        "Data Structures": [
            "It ignores insertion and removal rules.",
            "It is always identical to every other structure.",
            "It is only used for SQL queries.",
        ],
    }.get(domain, [
        "It is unrelated to the current concept.",
        "It removes the need for examples.",
        "It always changes stored data permanently.",
    ])

    return [correct] + distractors[:3]


def build_output(c: Dict[str, Any], task_type: str) -> str:
    concept = c["concept_name"]
    k = key(c)
    d = definition(c)
    ex = example(c)
    mis = mistake(c)
    use = use_case(c)

    if task_type in ["explanation", "definition_view"]:
        return f"Concept: {concept}\nDefinition: {d}\nExample: {ex}\nWhy it matters: {k}"

    if task_type == "simple_example_view":
        return f"Concept: {concept}\nSimple example: {ex}\nExplanation: This example shows the idea: {k}"

    if task_type == "step_by_step_view":
        return (
            f"Concept: {concept}\n"
            f"Step 1: Understand the definition: {d}\n"
            f"Step 2: Study this example: {ex}\n"
            f"Step 3: Remember the key rule: {k}\n"
            f"Step 4: Avoid this mistake: {mis}"
        )

    if task_type == "analogy_view":
        return (
            f"Concept: {concept}\n"
            f"Analogy: Think of {concept} as a tool with one important rule.\n"
            f"Mapping: The rule is: {k}\n"
            f"Example: {ex}"
        )

    if task_type == "code_view":
        return f"Concept: {concept}\nCode or example: {ex}\nWhat it shows: {k}"

    if task_type == "misconception_view":
        return f"Concept: {concept}\nCommon mistake: {mis}\nCorrection: Use the key rule: {k}"

    if task_type in ["debug_view", "debug_task"]:
        return json.dumps(debug_payload(c), ensure_ascii=False)

    if task_type in ["output_prediction_view", "output_prediction"]:
        return json.dumps(output_prediction_payload(c), ensure_ascii=False)

    if task_type in ["transfer_view", "transfer_question", "transfer_task", "real_world_application_question", "real_world_connection_view"]:
        return json.dumps({
            "question": f"How can {concept} be applied in a real-world or coding situation?",
            "answer_outline": f"Use this key rule: {k}. Connect it with this use case: {use}",
            "explanation": f"Transfer means using {concept} beyond the first example.",
        }, ensure_ascii=False)

    if task_type in ["challenge_view", "challenge_question", "practice_question", "debug_challenge", "output_prediction_challenge", "multi_step_challenge"]:
        return json.dumps({
            "challenge": f"Solve a small task using {concept}. Include the key rule, one example, and one common mistake to avoid.",
            "solution_outline": f"Use this key idea: {k}. Example: {ex}. Avoid: {mis}",
        }, ensure_ascii=False)

    if task_type == "comparison_view":
        return (
            f"Comparison: {concept} compared with a related concept.\n"
            f"Main rule: {k}\n"
            f"Common confusion: {mis}\n"
            f"How to tell them apart: Focus on the operation or rule being used."
        )

    if task_type == "comparison_mindmap":
        return json.dumps({
            "center": f"{concept} comparison",
            "branches": [
                f"{concept}: {k}",
                f"Related idea: {complete_sentence(c.get('next_concept_link', ''), 180) or 'next related concept'}",
                "Difference: compare the rule, operation, or purpose.",
                f"Example: {ex}",
                f"Common mistake: {mis}",
            ],
        }, ensure_ascii=False)

    if task_type == "mcq":
        opts = options_for(c)
        correct = opts[0]
        random.shuffle(opts)
        return json.dumps({
            "question": f"Which statement best describes {concept}?",
            "options": opts,
            "answer": correct,
            "explanation": f"The correct answer matches the main rule of {concept}: {correct}",
        }, ensure_ascii=False)

    if task_type == "true_or_false":
        return json.dumps({
            "statement": f"{concept} mainly follows this idea: {k}",
            "answer": True,
            "explanation": "This is true because it matches the source concept rule.",
        }, ensure_ascii=False)

    if task_type == "fill_in_the_blank":
        return json.dumps({
            "prompt": f"Fill in the blank: The key idea of {concept} is ____.",
            "answer": k,
            "hint": f"Look at the main rule for {concept}.",
        }, ensure_ascii=False)

    if task_type == "explanation_check":
        return json.dumps({
            "question": f"Explain {concept} in your own words.",
            "expected_points": [d, k],
            "rubric": "Full credit if the learner explains the definition and the key rule.",
        }, ensure_ascii=False)

    if task_type == "syntax_completion":
        dbg = debug_payload(c)
        return json.dumps({
            "prompt": f"Complete or correct the syntax for {concept}.",
            "incomplete_code": dbg["buggy_code"],
            "answer": dbg["expected_fix"],
            "hint": dbg["hint"],
        }, ensure_ascii=False)

    if task_type in ["coding_prompt", "code_reasoning_task"]:
        return json.dumps({
            "prompt": f"Write or reason through a small example that demonstrates {concept}.",
            "requirements": [
                f"Use the key idea: {k}",
                "Include one explanation line.",
                f"Avoid this mistake: {mis}",
            ],
            "expected_solution_outline": ex,
        }, ensure_ascii=False)

    if task_type in ["revision_note", "revision_summary", "revision_summary_view"]:
        return f"Summary: {concept} means {d}\nRemember: {k}\nAvoid this mistake: {mis}"

    if task_type in ["weakness_review", "mistake_summary"]:
        return f"Weakness Review: If you struggle with {concept}, focus on this rule: {k}\nCommon mistake: {mis}\nPractice next: Explain this example: {ex}"

    if task_type == "daily_review":
        return f"Daily Review: Review {concept} quickly.\nRecall: {k}\nTry: Give one example similar to this: {ex}"

    if task_type in ["personal_revision_plan", "revision_plan", "recommended_revision_views"]:
        return json.dumps({
            "concept": concept,
            "revision_steps": [
                f"Read the definition: {d}",
                f"Practice this example: {ex}",
                 f"Check this misconception: {mis}",
                "Try one debug or challenge question.",
            ],
            "recommended_views": ["definition_view", "simple_example_view", "misconception_view", "practice_question"],
        }, ensure_ascii=False)

    if task_type == "spaced_repetition_card":
        return json.dumps({
            "front": f"Recall the key rule of {concept}.",
            "back": k,
            "review_after": "1 day, 3 days, 7 days",
        }, ensure_ascii=False)

    if task_type in ["flashcard", "concept_recall_flashcard"]:
        return json.dumps({"front": f"What is {concept}?", "back": k}, ensure_ascii=False)

    if task_type == "misconception_flashcard":
        return json.dumps({"front": f"What mistake should you avoid in {concept}?", "back": mis}, ensure_ascii=False)

    if task_type == "example_flashcard":
        return json.dumps({"front": f"Give an example of {concept}.", "back": ex}, ensure_ascii=False)

    if task_type == "debug_flashcard":
        dbg = debug_payload(c)
        return json.dumps({"front": dbg["buggy_code"], "back": dbg["expected_fix"]}, ensure_ascii=False)

    if task_type == "personal_flashcards":
        return json.dumps([
            {"front": f"What is {concept}?", "back": k},
            {"front": f"What mistake should you avoid in {concept}?", "back": mis},
        ], ensure_ascii=False)

    if task_type == "syntax_flashcard":
        dbg = debug_payload(c)
        return json.dumps({"front": f"Correct this syntax: {dbg['buggy_code']}", "back": dbg["expected_fix"]}, ensure_ascii=False)

    if task_type in ["mindmap", "concept_mindmap"]:
        return json.dumps({
            "center": concept,
            "branches": [
                f"Definition: {d}",
                f"Key point: {k}",
                f"Example: {ex}",
                f"Common mistake: {mis}",
                f"Real-world use: {use}",
            ],
        }, ensure_ascii=False)

    if task_type in [
        "feedback",
        "correct_answer_feedback",
        "wrong_answer_feedback",
        "partial_answer_feedback",
        "debug_feedback",
        "output_prediction_feedback",
        "next_step_feedback",
        "encouragement_feedback",
    ]:
        return (
            f"What was correct: You focused on {concept}.\n"
            f"What to improve: Connect your answer to this rule: {k}\n"
            f"Next step: Try one example and avoid this mistake: {mis}"
        )

    if task_type in [
        "hint",
        "small_hint",
        "guided_hint",
        "worked_example_hint",
        "debug_hint",
        "syntax_hint",
        "output_prediction_hint",
        "misconception_hint",
        "next_step_hint",
        "analogy_hint",
    ]:
        return f"Hint: Start from the rule for {concept}: {k}. Compare your answer with this example: {ex}"

    if task_type in [
        "doubt_answer",
        "concept_doubt_answer",
        "syntax_doubt_answer",
        "debug_doubt_answer",
        "output_doubt_answer",
        "example_request_answer",
        "revision_doubt_answer",
        "next_step_doubt_answer",
        "comparison_doubt_answer",
    ]:
        return (
            f"Answer: {concept} is mainly about {k}\n"
            f"Reason: {d}\n"
            f"Example: {ex}\n"
            f"Try this: Explain why this common mistake is wrong: {mis}"
        )

    if task_type in ["notebook_summary", "comeback_summary", "returning_learner_summary", "progress_insight"]:
        return (
            f"Notebook Summary: You studied {concept}.\n"
            f"Key memory: {k}\n"
            f"Example to remember: {ex}\n"
            f"Next review: Practice one question and check this misconception: {mis}"
        )

    if task_type in [
        "voice_script",
        "teaching_voice_script",
        "revision_voice_script",
        "mistake_feedback_voice_script",
        "doubt_explanation_voice_script",
        "encouragement_script",
        "next_step_guidance_script",
        "concept_intro_voice_script",
    ]:
        return (
            f"Voice Script: Today we learn {concept}. "
            f"The main idea is {k} "
            f"For example, {ex} "
            f"One mistake to avoid is this: {mis}"
        )

    return f"Concept: {concept}\nDefinition: {d}\nExample: {ex}\nWhy it matters: {k}"


def build_rows(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for c in concepts:
        for task_type in ALL_TASK_TYPES:
            for difficulty in DIFFICULTIES:
                style = random.choice(STYLES)
                output = build_output(c, task_type)
                prompt = prompt_for(c, task_type, difficulty, style)

                rows.append({
                    "instruction": prompt,
                    "input": {
                        "concept_id": c["concept_id"],
                        "concept_name": c["concept_name"],
                        "domain": c["domain"],
                        "difficulty": difficulty,
                        "style": style,
                    },
                    "output": output,
                    "task_type": task_type,
                    "concept_id": c["concept_id"],
                    "concept_name": c["concept_name"],
                    "domain": c["domain"],
                    "difficulty": difficulty.replace("<", "").replace(">", ""),
                    "style": style.replace("<", "").replace(">", ""),
                    "source": "high_quality_all_tasks_training_from_concept_resources",
                })

    random.shuffle(rows)
    return rows


def split_rows(rows: List[Dict[str, Any]]):
    n = len(rows)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    return rows[:train_end], rows[train_end:val_end], rows[val_end:]


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    random.seed(42)

    concepts = load_concepts()
    if not concepts:
        raise RuntimeError(f"No concepts loaded. Check DB_DIR: {DB_DIR}")

    rows = build_rows(concepts)
    train, val, test = split_rows(rows)

    write_jsonl(OUT_DIR / "tutor_train.jsonl", train)
    write_jsonl(OUT_DIR / "tutor_val.jsonl", val)
    write_jsonl(OUT_DIR / "tutor_test.jsonl", test)

    write_jsonl(STRUCTURED_DIR / "tutor_train.jsonl", train)
    write_jsonl(STRUCTURED_DIR / "tutor_val.jsonl", val)
    write_jsonl(STRUCTURED_DIR / "tutor_test.jsonl", test)

    by_task: Dict[str, int] = {}
    by_domain: Dict[str, int] = {}

    for row in rows:
        by_task[row["task_type"]] = by_task.get(row["task_type"], 0) + 1
        by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1

    missing_tasks = [task for task in ALL_TASK_TYPES if task not in by_task]

    report = {
        "status": "PASS" if not missing_tasks else "WARN",
        "total_rows": len(rows),
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "concept_count": len(concepts),
        "task_type_count": len(by_task),
        "expected_task_type_count": len(ALL_TASK_TYPES),
        "missing_tasks": missing_tasks,
        "rows_by_task_type": by_task,
        "rows_by_domain": by_domain,
        "source": "concept_resources",
        "note": "This is supervised training data for CogniTutorLM from scratch, not final manual website output.",
        "high_quality_dir": str(OUT_DIR),
        "active_training_dir": str(STRUCTURED_DIR),
    }

    (REPORT_DIR / "high_quality_all_tasks_dataset_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    md_lines = [
        "# High Quality All Tasks Dataset Report",
        "",
        f"- status: {report['status']}",
        f"- total_rows: {len(rows)}",
        f"- train_rows: {len(train)}",
        f"- val_rows: {len(val)}",
        f"- test_rows: {len(test)}",
        f"- concept_count: {len(concepts)}",
        f"- task_type_count: {len(by_task)} / {len(ALL_TASK_TYPES)}",
        f"- source: concept_resources",
        "",
        "This is training data only. It is not final manual website output.",
        "",
        "## Rows by task type",
    ]

    for task in sorted(by_task):
        md_lines.append(f"- {task}: {by_task[task]}")

    md_lines.extend(["", "## Rows by domain"])
    for domain in sorted(by_domain):
        md_lines.append(f"- {domain}: {by_domain[domain]}")

    if missing_tasks:
        md_lines.extend(["", "## Missing tasks"])
        for task in missing_tasks:
            md_lines.append(f"- {task}")

    (REPORT_DIR / "high_quality_all_tasks_dataset_report.md").write_text(
        "\n".join(md_lines),
        encoding="utf-8",
    )

    print("status:", report["status"])
    print("total_rows:", len(rows))
    print("train_rows:", len(train))
    print("val_rows:", len(val))
    print("test_rows:", len(test))
    print("concept_count:", len(concepts))
    print("task_type_count:", len(by_task), "/", len(ALL_TASK_TYPES))
    print("missing_tasks:", missing_tasks)
    print("rows_by_domain:", by_domain)
    print("high_quality_dir:", OUT_DIR)
    print("active_training_dir:", STRUCTURED_DIR)


if __name__ == "__main__":
    main()