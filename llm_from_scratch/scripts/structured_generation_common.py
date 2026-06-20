import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"

DB_FILES = {
    "Python": "python_learning.db",
    "SQL": "database_sql.db",
    "HTML": "html_web_basics.db",
    "Git": "git_version_control.db",
    "Data Structures": "data_structures.db",
}

TASK_TYPES = [
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "revision_summary",
    "hint",
    "feedback",
    "mindmap",
    "doubt_answer",
    "voice_script",
    "coding_prompt",
    "syntax_completion",
    "transfer_question",
    "notebook_summary",
    "comeback_summary",
]

TASK_TOKENS = {
    "explanation": "<task_explanation>",
    "flashcard": "<task_flashcard>",
    "mcq": "<task_mcq>",
    "debug_task": "<task_debug>",
    "output_prediction": "<task_output_prediction>",
    "challenge_question": "<task_challenge>",
    "revision_summary": "<task_revision>",
    "hint": "<task_hint>",
    "feedback": "<task_feedback>",
    "mindmap": "<task_mindmap>",
    "doubt_answer": "<task_doubt_answer>",
    "voice_script": "<task_voice_script>",
    "coding_prompt": "<task_coding_prompt>",
    "syntax_completion": "<task_syntax_completion>",
    "transfer_question": "<task_transfer_question>",
    "notebook_summary": "<task_notebook_summary>",
    "comeback_summary": "<task_comeback_summary>",
}

STYLE_TOKENS = {
    "step_by_step": "<style_step_by_step>",
    "simple": "<style_simple>",
    "code_first": "<style_code>",
    "challenge_based": "<style_challenge_based>",
    "revision_summary": "<style_revision_summary>",
    "assessment": "<style_assessment>",
}


def clean_text(value: Any, max_chars: int = 240) -> str:
    text = str(value or "").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars].strip()


def prompt_safe_text(value: Any, max_chars: int = 240) -> str:
    return clean_text(value, max_chars).replace("<", "[").replace(">", "]")


def split_items(value: Any, max_items: int = 4) -> List[str]:
    text = str(value or "").replace("\r", "\n")
    items = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if not line:
            continue
        if "|" in line:
            items.extend(part.strip() for part in line.split("|") if part.strip())
        else:
            items.append(line)
    if len(items) <= 1 and ". " in text:
        items = [part.strip() + "." for part in text.split(". ") if part.strip()]
    seen = []
    for item in items:
        item = clean_text(item)
        if item and item not in seen:
            seen.append(item)
    return seen[:max_items]


def load_concepts() -> List[Dict[str, Any]]:
    concepts = []
    for domain, db_name in DB_FILES.items():
        db_path = RAW_DIR / db_name
        if not db_path.exists():
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT concept_id, topic, base_content, examples, key_points,
                   misconceptions, real_world_use, next_concept_link
            FROM concept_resources
            ORDER BY concept_id
            """
        ).fetchall()
        conn.close()
        for row in rows:
            concepts.append(
                {
                    "concept_id": clean_text(row["concept_id"], 80),
                    "concept_name": clean_text(row["topic"], 120),
                    "domain": domain,
                    "base_content": clean_text(row["base_content"], 360),
                    "examples": split_items(row["examples"], 3),
                    "key_points": split_items(row["key_points"], 4),
                    "misconceptions": split_items(row["misconceptions"], 3),
                    "real_world_use": clean_text(row["real_world_use"], 220),
                    "next_concept_link": clean_text(row["next_concept_link"], 160),
                }
            )
    return concepts


def key_point(concept: Dict[str, Any]) -> str:
    return (concept.get("key_points") or [concept.get("base_content") or ""])[0]


def example(concept: Dict[str, Any]) -> str:
    examples = concept.get("examples") or []
    if len(examples) > 1 and examples[0].lower().startswith("example"):
        return examples[1]
    return (examples or [f"Apply {concept['concept_name']} in a small {concept['domain']} example."])[0]


def misconception(concept: Dict[str, Any]) -> str:
    return (concept.get("misconceptions") or [f"A common mistake is misunderstanding {concept['concept_name']}."])[0]


def format_rule(task_type: str) -> str:
    rules = {
        "explanation": "Concept:\nDefinition:\nExample:\nWhy it matters:",
        "flashcard": '{"front": "...", "back": "..."}',
        "mcq": '{"question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "explanation": "..."}',
        "debug_task": '{"buggy_code": "...", "expected_fix": "...", "hint": "...", "explanation": "..."}',
        "output_prediction": '{"code": "...", "question": "What is the output?", "answer": "...", "explanation": "..."}',
        "challenge_question": '{"challenge": "...", "solution_outline": "..."}',
        "revision_summary": "Summary:\nRemember:\nAvoid this mistake:",
        "hint": "Hint:",
        "feedback": "What was correct:\nWhat to improve:\nNext step:",
        "mindmap": '{"center": "...", "branches": ["...", "...", "..."]}',
        "doubt_answer": "Answer:\nReason:\nTry this:",
        "voice_script": "Voice Script:",
        "coding_prompt": "Task:\nStarter Code:\nExpected Outcome:",
        "syntax_completion": '{"incomplete_code": "...", "completion": "...", "explanation": "..."}',
        "transfer_question": "Scenario:\nQuestion:\nExpected Idea:",
        "notebook_summary": "Notebook Summary:\nStrength:\nFocus:",
        "comeback_summary": "Welcome Back:\nLast Topic:\nNext Step:",
    }
    return rules[task_type]


def compact_context(concept: Dict[str, Any]) -> str:
    parts = [
        f"Definition: {prompt_safe_text(concept.get('base_content'), 110)}",
        f"Key point: {prompt_safe_text(key_point(concept), 90)}",
        f"Example: {prompt_safe_text(example(concept), 80)}",
        f"Mistake: {prompt_safe_text(misconception(concept), 90)}",
    ]
    if concept.get("real_world_use"):
        parts.append(f"Use: {prompt_safe_text(concept['real_world_use'], 80)}")
    return "\n".join(parts)


def build_prompt(concept: Dict[str, Any], task_type: str, difficulty: str = "easy", style: str = "step_by_step") -> str:
    if task_type == "mcq":
        key = prompt_safe_text(key_point(concept), 72)
        return f"""<bos>
<task_mcq>
<easy>
<style_assessment>
Concept: {concept['concept_name']}
Domain: {concept['domain']}
Key: {key}
JSON only. Fields: question, options, answer, explanation.
Rules: exactly 4 options; answer equals one option; no duplicate options.
<answer>"""
    style_token = STYLE_TOKENS.get(style, f"<style_{style}>")
    return f"""<bos>
<instruction> Generate tutor output.
{TASK_TOKENS[task_type]}
<{difficulty}>
{style_token}
<concept> {concept['concept_name']}
<domain> {concept['domain']}
<context>
{compact_context(concept)}
</context>
<format_rule>
{format_rule(task_type)}
</format_rule>
<answer>"""


def build_training_prompt(concept: Dict[str, Any], task_type: str, difficulty: str = "easy", style: str = "step_by_step") -> str:
    return build_prompt(concept, task_type, difficulty=difficulty, style=style)


def debug_case(concept: Dict[str, Any]) -> Dict[str, str]:
    name = concept["concept_name"].lower()
    domain = concept["domain"]
    if domain == "Python" and "loop" in name:
        return {"buggy_code": "for i in range(3) print(i)", "expected_fix": "for i in range(3): print(i)", "hint": "Add the missing colon.", "explanation": "Python loop headers must end with a colon."}
    if domain == "Python":
        return {"buggy_code": "print(name); name = 'Alice'", "expected_fix": "name = 'Alice'; print(name)", "hint": "Assign before use.", "explanation": "Python names must be bound before they are read."}
    if domain == "SQL":
        return {"buggy_code": "SELEC name FROM students;", "expected_fix": "SELECT name FROM students;", "hint": "Check the SELECT keyword spelling.", "explanation": "SQL uses SELECT to choose columns from a table."}
    if domain == "HTML":
        return {"buggy_code": "<p>Hello", "expected_fix": "<p>Hello</p>", "hint": "Close the paragraph element.", "explanation": "Most HTML elements need a closing tag."}
    if domain == "Git":
        return {"buggy_code": "git comit -m \"save\"", "expected_fix": "git commit -m \"save\"", "hint": "Check the command spelling.", "explanation": "git commit records staged changes."}
    concept_name = concept["concept_name"]
    return {
        "buggy_code": f"{concept_name.lower().replace(' ', '_')}.remove_wrong()",
        "expected_fix": f"Use the valid operation for {concept_name}.",
        "hint": f"Check the rule for {concept_name}.",
        "explanation": f"The fix must follow the main Data Structures rule for {concept_name}.",
    }


def output_prediction(concept: Dict[str, Any]) -> Dict[str, str]:
    name = concept["concept_name"].lower()
    domain = concept["domain"]
    if domain == "Python" and "loop" in name:
        return {"code": "for i in range(3):\n    print(i)", "question": "What is the output?", "answer": "0\n1\n2", "explanation": "range(3) produces 0, 1, and 2."}
    if domain == "Python":
        return {"code": "x = 10\nx = 20\nprint(x)", "question": "What is the output?", "answer": "20", "explanation": "The second assignment changes x to 20."}
    if domain == "SQL":
        return {"code": "SELECT name FROM students;", "question": "What is the output?", "answer": "The query returns the name column from students.", "explanation": "SELECT chooses which columns to retrieve."}
    if domain == "HTML":
        return {"code": "<p>Hello</p>", "question": "What is the output?", "answer": "Hello", "explanation": "The paragraph displays its text content."}
    if domain == "Git":
        return {"code": "git status", "question": "What is the output?", "answer": "It shows repository working tree status.", "explanation": "git status reports changed, staged, and untracked files."}
    return {"code": "stack.push('A')\nstack.push('B')\nstack.pop()", "question": "What is the output?", "answer": "B", "explanation": "A stack pops the last item pushed."}


def concise_mcq_answer(concept: Dict[str, Any], key: str) -> str:
    name = concept["concept_name"]
    domain = concept["domain"]
    lowered = name.lower()
    exact = {
        "data types": "Data types classify Python values",
        "conditionals": "Conditionals choose code using tests",
        "object-oriented programming": "Classes create objects with related data",
        "decorators and generators": "Decorators wrap functions and generators yield values",
        "file handling": "File handling reads and writes files safely",
        "join": "JOIN combines related rows from tables",
        "indexes": "Indexes speed up row lookup",
        "group by": "GROUP BY summarizes rows into groups",
        "window": "Window functions calculate across related rows",
        "cte": "CTEs name temporary query results",
        "attributes": "Attributes add extra information to elements",
        "css": "CSS selectors target elements for styling",
        "accessibility": "Accessibility helps all users use a page",
        "service workers": "Service workers enable offline web behavior",
        "web components": "Web components define reusable custom elements",
        "merge": "Merge combines branch changes",
        "rebase": "Rebase replays commits onto a new base",
        "submodules": "Submodules link another repository inside a repository",
        "log": "Git log shows commit history",
        "queue": "A queue removes the first item added",
        "trees": "Trees organize nodes hierarchically",
        "sets": "Sets store unique elements",
        "graphs": "Graphs connect vertices with edges",
    }
    for needle, answer in exact.items():
        if needle in lowered:
            return answer
    return clean_text(key, 64).rstrip(" ,;:.")


def mcq_options(concept: Dict[str, Any], key: str, mis: str) -> List[str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lowered = name.lower()
    answer = concise_mcq_answer(concept, key)
    if domain == "Python":
        if "variable" in lowered:
            return [
                answer,
                "A variable directly contains the object value",
                "A variable must declare a fixed type first",
                "A variable name cannot be reused",
            ]
        if "loop" in lowered:
            return [
                answer,
                "A loop always requires a manual index",
                "A while loop never checks a condition",
                "break always exits every nested loop at once",
            ]
        if "function" in lowered:
            return [
                answer,
                "A function must always print a value",
                "A function cannot accept input values",
                "A function always changes global data",
            ]
        return [answer, f"{name} requires manual memory control", f"{name} works only with print statements", f"{name} cannot be used in Python code"]
    if domain == "SQL":
        if "select" in lowered:
            return [
                answer,
                "SELECT permanently changes table rows",
                "SELECT runs only after DELETE",
                "SELECT creates new database tables",
            ]
        if "where" in lowered:
            return [
                answer,
                "WHERE sorts rows after SELECT",
                "WHERE creates new table columns",
                "WHERE permanently edits stored rows",
            ]
        if "database" in lowered:
            return [
                answer,
                "A database is only plain text",
                "A DBMS blocks all queries",
                "Database tables cannot relate data",
            ]
        return [answer, f"{name} always edits stored rows", f"{name} replaces SELECT in every query", f"{name} cannot be used with tables"]
    if domain == "HTML":
        if "tag" in lowered or "element" in lowered:
            return [
                answer,
                "A tag always displays as typed",
                "Every element must contain text",
                "Void elements always need closing tags",
            ]
        if "form" in lowered:
            return [
                answer,
                "Forms require JavaScript for every field",
                "The method attribute controls color",
                "All form data is always visible",
            ]
        return [answer, f"{name} only changes page color", f"{name} cannot affect page structure", f"{name} works only inside script tags"]
    if domain == "Git":
        if "commit" in lowered:
            return [
                answer,
                "A commit uploads to remote hosting",
                "Staging alone saves project history",
                "A commit removes all older snapshots",
            ]
        if "branch" in lowered:
            return [
                answer,
                "A branch copies every file",
                "A branch exists only after push",
                "Deleting a branch deletes every commit",
            ]
        return [answer, f"{name} always uploads to GitHub", f"{name} deletes local history", f"{name} cannot work without a remote"]
    if "stack" in lowered:
        return [
            answer,
            "A stack removes the first item inserted",
            "A stack removes only from the bottom",
            "A stack and queue remove items alike",
        ]
    if "linked" in lowered:
        return [
            answer,
            "A linked list stores nodes contiguously",
            "A linked list gives instant index access",
            "A linked list node has no reference",
        ]
    if "array" in lowered:
        return [
            answer,
            "An array stores items in random places",
            "An array cannot be indexed by position",
            "An array resizes with no tradeoff",
        ]
    return [answer, f"{name} ignores ordering rules", f"{name} cannot store values", f"{name} has no access rule"]


def target_output(concept: Dict[str, Any], task_type: str) -> str:
    name = concept["concept_name"]
    domain = concept["domain"]
    key = clean_text(key_point(concept), 110)
    ex = clean_text(example(concept), 90)
    mis = clean_text(misconception(concept), 100)
    if task_type == "explanation":
        return f"Concept: {name}\nDefinition: {clean_text(concept['base_content'], 120)}\nExample: {ex}\nWhy it matters: {key}"
    if task_type == "flashcard":
        return json.dumps({"front": f"What is {name}?", "back": key}, ensure_ascii=False)
    if task_type == "mcq":
        mcq_key = clean_text(key_point(concept), 58).rstrip(" ,;:.")
        options = mcq_options(concept, mcq_key, mis)
        answer = options[0]
        return json.dumps(
            {
                "question": f"Which statement best describes {name}?",
                "options": options,
                "answer": answer,
                "explanation": f"It matches the main rule for {name}.",
            },
            ensure_ascii=False,
        )
    if task_type == "debug_task":
        return json.dumps(debug_case(concept), ensure_ascii=False)
    if task_type == "output_prediction":
        return json.dumps(output_prediction(concept), ensure_ascii=False)
    if task_type == "challenge_question":
        return json.dumps({"challenge": f"Create a small {domain} example that uses {name}.", "solution_outline": f"Use this rule: {key}. Then explain one edge case or common mistake."}, ensure_ascii=False)
    if task_type == "revision_summary":
        return f"Summary: {name} means {clean_text(concept['base_content'], 110)}\nRemember: {key}\nAvoid this mistake: {mis}"
    if task_type == "hint":
        return f"Hint: Focus on {name}: {key}"
    if task_type == "feedback":
        return f"What was correct: You worked on {name}.\nWhat to improve: {key}\nNext step: Try one example and explain why it follows the rule."
    if task_type == "mindmap":
        return json.dumps({"center": name, "branches": [key, ex, mis]}, ensure_ascii=False)
    if task_type == "doubt_answer":
        return f"Answer: {name} is about {key}\nReason: {clean_text(concept['base_content'], 110)}\nTry this: Review this example: {ex}"
    if task_type == "voice_script":
        return f"Voice Script: Today we will learn {name}. The key idea is {key}. For example, {ex}. Avoid this mistake: {mis}."
    if task_type == "coding_prompt":
        return f"Task: Write a small {domain} example for {name}.\nStarter Code: {ex}\nExpected Outcome: The example should show this rule: {key}"
    if task_type == "syntax_completion":
        case = output_prediction(concept)
        return json.dumps({"incomplete_code": case["code"].splitlines()[0], "completion": case["code"], "explanation": case["explanation"]}, ensure_ascii=False)
    if task_type == "transfer_question":
        return f"Scenario: You need to use {name} in a new {domain} problem.\nQuestion: How would you apply the main rule?\nExpected Idea: {key}"
    if task_type == "notebook_summary":
        return f"Notebook Summary: {name} focuses on {key}\nStrength: The learner can connect it to {ex}\nFocus: Avoid this mistake: {mis}"
    if task_type == "comeback_summary":
        return f"Welcome Back: Continue with {name}.\nLast Topic: {key}\nNext Step: Try this example: {ex}"
    raise ValueError(task_type)


def training_text(concept: Dict[str, Any], task_type: str) -> str:
    return build_training_prompt(concept, task_type) + " " + target_output(concept, task_type) + "\n<eos>"


def write_jsonl(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
