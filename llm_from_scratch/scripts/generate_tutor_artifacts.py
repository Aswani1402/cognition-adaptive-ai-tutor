import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.cognitutor_lm_config import ALL_TASK_TYPES


ROOT_DIR = Path(__file__).resolve().parents[1]

DB_CONFIGS = [
    {
        "path": ROOT_DIR / "data" / "raw" / "python_learning.db",
        "domain": "Python",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "database_sql.db",
        "domain": "SQL",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "html_web_basics.db",
        "domain": "HTML",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "git_version_control.db",
        "domain": "Git",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "data_structures.db",
        "domain": "Data Structures",
    },
]

OUTPUT_DIR = ROOT_DIR / "outputs" / "artifacts"
JSON_OUTPUT_PATH = OUTPUT_DIR / "generated_tutor_artifacts.json"
MD_OUTPUT_PATH = OUTPUT_DIR / "generated_tutor_artifacts.md"

ARTIFACT_TYPES = list(ALL_TASK_TYPES)

TEACHING_TYPES = {
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
}

ASSESSMENT_TYPES = {
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
}

REVISION_TYPES = {
    "revision_note",
    "revision_summary",
    "weakness_review",
    "daily_review",
    "personal_revision_plan",
    "recommended_revision_views",
    "spaced_repetition_card",
}

FLASHCARD_TYPES = {
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
}

MINDMAP_TYPES = {"mindmap", "concept_mindmap", "comparison_mindmap"}
FEEDBACK_TYPES = {
    "feedback",
    "correct_answer_feedback",
    "wrong_answer_feedback",
    "partial_answer_feedback",
    "debug_feedback",
    "output_prediction_feedback",
    "next_step_feedback",
    "encouragement_feedback",
}
HINT_TYPES = {
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
}
DOUBT_TYPES = {
    "doubt_answer",
    "concept_doubt_answer",
    "syntax_doubt_answer",
    "debug_doubt_answer",
    "output_doubt_answer",
    "example_request_answer",
    "revision_doubt_answer",
    "next_step_doubt_answer",
    "comparison_doubt_answer",
}
NOTEBOOK_TYPES = {
    "notebook_summary",
    "mistake_summary",
    "revision_plan",
    "comeback_summary",
    "returning_learner_summary",
    "progress_insight",
}
PRACTICE_TYPES = {
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
}
VOICE_TYPES = {
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
}


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def compact_text(value: Any, max_chars: int = 300) -> str:
    text = safe_text(value).replace("\r", "\n").strip()
    text = " ".join(text.split())

    if len(text) <= max_chars:
        return text

    return text[:max_chars].strip()


def first_sentence(value: Any, max_chars: int = 220) -> str:
    text = safe_text(value).replace("\r", "\n").strip()

    if not text:
        return ""

    # Prefer first paragraph.
    if "\n\n" in text:
        text = text.split("\n\n", 1)[0].strip()

    # Then first sentence if possible.
    for sep in [". ", "\n"]:
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break

    if text and not text.endswith("."):
        text += "."

    return compact_text(text, max_chars)


def split_items(value: Any, max_items: int = 5) -> List[str]:
    text = safe_text(value)

    if not text:
        return []

    # Handle common separators.
    raw_parts = []
    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue

        # Remove bullets.
        line = line.lstrip("-•* ").strip()

        # Split pipe-separated content.
        if "|" in line:
            raw_parts.extend([p.strip() for p in line.split("|") if p.strip()])
        else:
            raw_parts.append(line)

    # If still one very long item, split by sentence.
    if len(raw_parts) <= 1 and ". " in text:
        raw_parts = [p.strip() + "." for p in text.split(". ") if p.strip()]

    cleaned = []
    for item in raw_parts:
        item = compact_text(item, 180)
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned[:max_items]


def primary_key_point(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("key_points", ""), max_items=3)
    if items:
        return items[0]
    return first_sentence(concept.get("base_content", ""), 180)


def primary_example(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("examples", ""), max_items=3)
    if items:
        return items[0]
    return ""


def primary_misconception(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("misconceptions", ""), max_items=3)
    if items:
        return items[0]
    return f"A common mistake is misunderstanding {concept['concept_name']}."


def primary_real_use(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("real_world_use", ""), max_items=3)
    if items:
        return items[0]
    return f"{concept['concept_name']} is used in real-world problem solving."


def task_family(artifact_type: str) -> str:
    if artifact_type in TEACHING_TYPES:
        return "teaching"
    if artifact_type in ASSESSMENT_TYPES:
        return "assessment"
    if artifact_type in REVISION_TYPES:
        return "revision"
    if artifact_type in FLASHCARD_TYPES:
        return "flashcard"
    if artifact_type in MINDMAP_TYPES:
        return "mindmap"
    if artifact_type in FEEDBACK_TYPES:
        return "feedback"
    if artifact_type in HINT_TYPES:
        return "hint"
    if artifact_type in DOUBT_TYPES:
        return "doubt"
    if artifact_type in NOTEBOOK_TYPES:
        return "notebook"
    if artifact_type in PRACTICE_TYPES:
        return "practice_challenge"
    if artifact_type in VOICE_TYPES:
        return "voice"
    return "other"


def concept_brief(concept: Dict[str, Any]) -> Dict[str, Any]:
    key_points = split_items(concept.get("key_points", ""), max_items=4)
    examples = split_items(concept.get("examples", ""), max_items=3)
    misconceptions = split_items(concept.get("misconceptions", ""), max_items=3)
    return {
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "definition": first_sentence(concept.get("base_content", ""), 360),
        "key_points": key_points or [primary_key_point(concept)],
        "examples": examples or [primary_example(concept) or f"Apply {concept['concept_name']} in {concept['domain']}."],
        "misconceptions": misconceptions or [primary_misconception(concept)],
        "real_world_use": primary_real_use(concept),
        "next_concept_link": compact_text(concept.get("next_concept_link", ""), 260),
    }


def rich_teaching_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    title = f"{brief['concept_name']} - {artifact_type.replace('_', ' ').title()}"
    return {
        "title": title,
        "teaching_view": artifact_type,
        "beginner_explanation": (
            f"{brief['concept_name']} is a {brief['domain']} concept best learned by connecting the definition, "
            f"a concrete example, and one common mistake. {brief['definition']} The main point is: "
            f"{brief['key_points'][0]} Study the example, then explain why it follows the rule instead of memorizing only the words."
        ),
        "definition": brief["definition"],
        "key_points": brief["key_points"],
        "step_by_step": [
            f"Name the concept and domain: {brief['concept_name']} in {brief['domain']}.",
            f"State the main rule: {brief['key_points'][0]}",
            f"Trace the example: {brief['examples'][0]}",
            f"Check the mistake to avoid: {brief['misconceptions'][0]}",
        ],
        "example": brief["examples"][0],
        "common_mistake": brief["misconceptions"][0],
        "real_world_use": brief["real_world_use"],
        "quick_check": f"Explain which part of the example demonstrates {brief['concept_name']}.",
        "revision_line": f"Remember {brief['concept_name']}: {brief['key_points'][0]}",
    }


def assessment_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    name = brief["concept_name"]
    correct = brief["key_points"][0]
    base = {
        "question": f"How does {name} apply to the taught example?",
        "correct_answer": correct,
        "answer": correct,
        "explanation": f"The answer is grounded in the concept resource key point: {correct}",
        "linked_concept_resource": {
            "definition_used": brief["definition"],
            "example_used": brief["examples"][0],
            "misconception_used": brief["misconceptions"][0],
        },
    }
    if artifact_type == "mcq":
        options = [
            correct,
            brief["misconceptions"][0],
            f"{name} is mainly a formatting choice.",
            f"{name} can be used without considering the example or rule.",
        ]
        return {**base, "question": f"Which statement best matches {name}?", "options": options}
    if artifact_type == "debug_task":
        return {
            **base,
            "buggy_code": f"# Buggy or mistaken example for {name}\n{brief['examples'][0]}",
            "expected_fix": f"Revise the example so it follows this rule: {correct}",
            "hint": f"Compare the example with the key point for {name}.",
        }
    if artifact_type == "output_prediction":
        return {
            **base,
            "code": brief["examples"][0],
            "question": f"What should this example show about {name}?",
        }
    if artifact_type == "syntax_completion":
        return {
            **base,
            "incomplete_syntax": f"Complete an example that demonstrates {name}: ____",
            "completion": brief["examples"][0],
        }
    if artifact_type == "fill_in_the_blank":
        return {
            **base,
            "question": f"Fill in the blank: {name} is best remembered as ____.",
        }
    if artifact_type == "true_or_false":
        return {
            **base,
            "statement": f"{brief['misconceptions'][0]}",
            "correct_answer": False,
            "answer": False,
            "explanation": f"False. The corrected idea is: {correct}",
        }
    if artifact_type in {"coding_prompt", "code_reasoning_task"}:
        return {
            **base,
            "prompt": f"Create or reason about a small {brief['domain']} example that demonstrates {name}.",
            "success_criteria": [correct, "Use one example.", "Name one mistake to avoid."],
        }
    return {
        **base,
        "question": f"Apply {name} in a new {brief['domain']} situation and explain the result.",
    }


def revision_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "summary": f"{brief['concept_name']}: {brief['key_points'][0]}",
        "review_points": brief["key_points"],
        "mistakes_to_review": brief["misconceptions"],
        "practice_again": f"Use this example and explain it aloud: {brief['examples'][0]}",
        "next_step": brief["next_concept_link"] or f"Try a mixed practice question for {brief['concept_name']}.",
        "artifact_type": artifact_type,
    }


def flashcard_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    cards = [
        {
            "front": f"What is {brief['concept_name']}?",
            "back": brief["key_points"][0],
            "explanation": brief["definition"],
        },
        {
            "front": f"Give an example of {brief['concept_name']}.",
            "back": brief["examples"][0],
            "explanation": "This example comes from concept_resources.",
        },
        {
            "front": f"What mistake should you avoid with {brief['concept_name']}?",
            "back": brief["misconceptions"][0],
            "explanation": "This card targets misconception repair.",
        },
    ]
    return {"cards": cards, "artifact_type": artifact_type}


def mindmap_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "center": brief["concept_name"],
        "branches": [
            {"name": "Definition", "items": [brief["definition"]]},
            {"name": "Key points", "items": brief["key_points"][:3]},
            {"name": "Examples", "items": brief["examples"][:2]},
            {"name": "Misconceptions", "items": brief["misconceptions"][:2]},
            {"name": "Real-world use", "items": [brief["real_world_use"]]},
        ],
        "artifact_type": artifact_type,
    }


def feedback_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "correct": f"Correct. You used the key idea for {brief['concept_name']}: {brief['key_points'][0]}",
        "partial": f"Partly correct. Add the example connection: {brief['examples'][0]}",
        "wrong": f"Review this misconception: {brief['misconceptions'][0]}",
        "next_step": f"Try one aligned question, then revise: {brief['key_points'][0]}",
        "artifact_type": artifact_type,
    }


def hint_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "hint": f"Start from the rule for {brief['concept_name']}: {brief['key_points'][0]}",
        "guided_hint": f"Now compare that rule with this example: {brief['examples'][0]}",
        "not_full_answer": True,
        "artifact_type": artifact_type,
    }


def doubt_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "answer": f"{brief['concept_name']} means: {brief['key_points'][0]}",
        "explanation": brief["definition"],
        "example": brief["examples"][0],
        "common_confusion": brief["misconceptions"][0],
        "next_step": brief["next_concept_link"],
        "artifact_type": artifact_type,
    }


def voice_payload(concept: Dict[str, Any], artifact_type: str) -> Dict[str, Any]:
    brief = concept_brief(concept)
    return {
        "script": (
            f"Today we learn {brief['concept_name']}. First, remember this: {brief['key_points'][0]} "
            f"Here is an example: {brief['examples'][0]} A common mistake is: {brief['misconceptions'][0]} "
            f"Your quick check is to explain why the example follows the rule."
        ),
        "beats": ["intro", "definition", "example", "mistake", "quick_check", "next_step"],
        "artifact_type": artifact_type,
    }


def load_concepts() -> List[Dict[str, Any]]:
    concepts = []

    for config in DB_CONFIGS:
        db_path = config["path"]
        domain = config["domain"]

        if not db_path.exists():
            print(f"WARNING: Missing DB: {db_path}")
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

        print(f"{domain}: {len(rows)} concepts loaded")

        for row in rows:
            concepts.append(
                {
                    "concept_id": safe_text(row["concept_id"]),
                    "concept_name": safe_text(row["topic"]),
                    "domain": domain,
                    "base_content": safe_text(row["base_content"]),
                    "examples": safe_text(row["examples"]),
                    "key_points": safe_text(row["key_points"]),
                    "misconceptions": safe_text(row["misconceptions"]),
                    "real_world_use": safe_text(row["real_world_use"]),
                    "next_concept_link": safe_text(row["next_concept_link"]),
                }
            )

    return concepts


def make_definition_view(concept: Dict[str, Any]) -> str:
    definition = first_sentence(concept["base_content"], 220)
    key = primary_key_point(concept)

    return (
        f"{concept['concept_name']} — Definition\n\n"
        f"{definition}\n\n"
        f"Key idea: {key}"
    )


def make_simple_example_view(concept: Dict[str, Any]) -> str:
    definition = first_sentence(concept["base_content"], 180)
    example = primary_example(concept)

    if example:
        return (
            f"{concept['concept_name']} in simple terms:\n\n"
            f"{definition}\n\n"
            f"Simple example:\n{example}"
        )

    return (
        f"{concept['concept_name']} in simple terms:\n\n"
        f"{definition}\n\n"
        f"Try making one small example that uses this idea."
    )


def make_step_by_step_view(concept: Dict[str, Any]) -> str:
    key = primary_key_point(concept)
    example = primary_example(concept)
    example_line = example or f"Example: apply {concept['concept_name']} to a tiny practice case in {concept['domain']}."

    return (
        f"Step-by-step view for {concept['concept_name']}:\n\n"
        f"Step 1: Identify the rule — {key}\n"
        f"Step 2: Trace this example — {example_line}\n"
        f"Step 3: State the result and why the rule produced it."
    )


def make_code_view(concept: Dict[str, Any]) -> str:
    example = primary_example(concept)
    key = primary_key_point(concept)
    name = concept["concept_name"]
    domain = concept["domain"]
    lower_name = name.lower()

    if domain == "Git":
        if "version control" in lower_name:
            snippet = "git init\ngit status\ngit log --oneline"
        elif "repositories" in lower_name:
            snippet = "git init\ngit remote add origin https://github.com/user/project.git\ngit status"
        elif "commit" in lower_name or "history" in lower_name:
            snippet = "git add file.py\ngit commit -m \"Describe the change\"\ngit log --oneline"
        elif "branch" in lower_name:
            snippet = "git checkout -b feature/login\ngit status\ngit branch"
        elif "merge" in lower_name or "conflict" in lower_name:
            snippet = "git checkout main\ngit merge feature/login\n# Resolve conflict markers, then: git add . && git commit"
        elif "rebase" in lower_name:
            snippet = "git log --oneline\ngit rebase -i HEAD~3\ngit rebase --continue"
        elif "submodule" in lower_name:
            snippet = "git submodule add https://github.com/user/library.git vendor/library\ngit submodule update --init --recursive"
        else:
            snippet = "git status\ngit add .\ngit commit -m \"Save work\""

        return (
            f"Code-focused view for {name}:\n\n"
            f"Command example:\n{snippet}\n\n"
            f"What to notice: {key}"
        )

    if example:
        return (
            f"Code-focused view for {concept['concept_name']}:\n\n"
            f"{example}\n\n"
            f"What to notice: {key}"
        )

    return (
        f"Code-focused view for {concept['concept_name']}:\n\n"
        f"Main rule: {key}\n\n"
        f"Now create a short code or command example that applies this rule."
    )


def make_analogy_view(concept: Dict[str, Any]) -> str:
    name = concept["concept_name"]
    domain = concept["domain"]
    key = primary_key_point(concept)
    lower_name = name.lower()

    analogy_by_concept = {
        "variables": "Think of variables like labels on storage boxes: the label lets you find the value later.",
        "data types": "Think of data types like container shapes: a bottle, box, and envelope each fit different contents.",
        "conditionals": "Think of conditionals like a traffic signal: each condition decides which path is allowed.",
        "loops": "Think of loops like repeating a checklist for every item in a bag.",
        "functions": "Think of functions like a kitchen recipe: give ingredients, follow steps, get a result.",
        "object-oriented programming": "Think of OOP like a blueprint and houses: the class defines the design, each object is one built house.",
        "decorators and generators": "Think of decorators like gift wrap around a function and generators like a ticket dispenser that gives one ticket at a time.",
        "file handling": "Think of file handling like borrowing a notebook: open it, read or write, then close it properly.",
        "database basics": "Think of a database like a well-organized school office with separate folders for students, courses, and grades.",
        "sql select queries": "Think of SELECT like asking a librarian for specific columns from a catalog card.",
        "where and filters": "Think of WHERE like a sieve that keeps only rows matching the condition.",
        "join operations": "Think of JOIN like matching student ID cards with course enrollment sheets.",
        "indexes": "Think of indexes like the index at the back of a textbook: they help find pages faster without changing the words.",
        "window functions": "Think of window functions like ranking runners inside each age group while still showing every runner.",
        "common table expressions": "Think of a CTE like a named scratchpad result you use in the next SQL query.",
        "what is html": "Think of HTML like the skeleton of a web page: it gives each part a role.",
        "html tags and elements": "Think of tags like labels on document parts: heading, paragraph, list, image.",
        "attributes and links": "Think of attributes like settings on a form field or address on a link.",
        "images and lists": "Think of lists like grocery lists and images like labeled pictures in a textbook.",
        "forms and inputs": "Think of forms like paper application forms: labels tell what each box should collect.",
        "web accessibility": "Think of accessibility like adding ramps, signs, and captions so more people can use the same page.",
        "service workers": "Think of a service worker like a helpful clerk between the browser and network cache.",
        "web components": "Think of Web Components like reusable LEGO blocks for web UI.",
        "what is version control": "Think of version control like a project timeline with checkpoints you can revisit.",
        "git repositories": "Think of a repository like a project folder with a hidden history notebook inside.",
        "commits and history": "Think of a commit like saving a named checkpoint in a game.",
        "branches": "Think of branches like separate work lanes where features can move without blocking the main road.",
        "merge and conflict": "Think of merging like combining two edited documents and resolving places where both changed the same line.",
        "interactive rebase": "Think of interactive rebase like editing a draft timeline before sharing the final story.",
        "submodules": "Think of submodules like a project that keeps a precise reference to another project it depends on.",
        "introduction to data structures": "Think of data structures like choosing shelves, boxes, or maps depending on how you need to find items.",
        "arrays": "Think of arrays like numbered lockers in a row.",
        "linked list": "Think of a linked list like a treasure hunt where each clue points to the next clue.",
        "stack": "Think of a stack like a pile of plates: the last plate placed is the first one removed.",
        "queue": "Think of a queue like a ticket line: the first person in line is served first.",
        "trees": "Think of a tree like a folder hierarchy or family tree with parent-child relationships.",
        "sets": "Think of a set like a guest list where duplicate names are written only once.",
        "graphs": "Think of a graph like a map of cities connected by roads.",
    }

    analogy = analogy_by_concept.get(
        lower_name,
        f"Think of {name} like a specific classroom tool for organizing one kind of work in {domain}.",
    )

    return (
        f"Analogy view for {name}:\n\n"
        f"{analogy}\n\n"
        f"Connection to the actual concept: {key}"
    )


def make_misconception_view(concept: Dict[str, Any]) -> str:
    misconception = primary_misconception(concept)
    key = primary_key_point(concept)

    return (
        f"Misconception view for {concept['concept_name']}:\n\n"
        f"Common mistake: {misconception}\n\n"
        f"Correction: {key}\n\n"
        f"Remember: focus on the rule, not just the surface example."
    )


def concept_debug_cases(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lower_name = name.lower()

    if domain == "Python":
        if "variable" in lower_name:
            return [
                {
                    "buggy_code": "print(name)\nname = \"Alice\"",
                    "expected_fix": "name = \"Alice\"\nprint(name)",
                    "hint": "Fix the reference-before-assignment bug by binding the variable first.",
                }
            ]
        if "data type" in lower_name:
            return [
                {
                    "buggy_code": "age = \"20\"\nprint(age + 1)",
                    "expected_fix": "age = \"20\"\nprint(int(age) + 1)",
                    "hint": "Fix the type mismatch by converting the string before arithmetic.",
                }
            ]
        if "conditional" in lower_name:
            return [
                {
                    "buggy_code": "score = 80\nif score = 80:\n    print(\"pass\")",
                    "expected_fix": "score = 80\nif score == 80:\n    print(\"pass\")",
                    "hint": "Fix the condition by using comparison, not assignment.",
                }
            ]
        if "loop" in lower_name:
            return [
                {
                    "buggy_code": "for i in range(3)\n    print(i)",
                    "expected_fix": "for i in range(3):\n    print(i)",
                    "hint": "Fix the loop header by adding the required colon.",
                }
            ]
        if "function" in lower_name:
            return [
                {
                    "buggy_code": "def add(a, b):\n    a + b\n\nresult = add(2, 3)",
                    "expected_fix": "def add(a, b):\n    return a + b\n\nresult = add(2, 3)",
                    "hint": "Fix the function so it returns the computed value.",
                }
            ]
        if "object-oriented" in lower_name or "oop" in lower_name:
            return [
                {
                    "buggy_code": "class User:\n    def set_name(name):\n        self.name = name",
                    "expected_fix": "class User:\n    def set_name(self, name):\n        self.name = name",
                    "hint": "Fix the instance method by including self as the first parameter.",
                }
            ]
        if "decorator" in lower_name or "generator" in lower_name:
            return [
                {
                    "buggy_code": "def numbers():\n    return 1\n    return 2",
                    "expected_fix": "def numbers():\n    yield 1\n    yield 2",
                    "hint": "Fix the generator by yielding each value instead of returning once.",
                }
            ]
        if "file" in lower_name:
            return [
                {
                    "buggy_code": "file = open(\"notes.txt\")\nfile.write(\"hello\")",
                    "expected_fix": "with open(\"notes.txt\", \"w\") as file:\n    file.write(\"hello\")",
                    "hint": "Fix the file mode and use with so the file is closed safely.",
                }
            ]

    if domain == "SQL":
        if "select" in lower_name:
            return [
                {
                    "buggy_code": "SELECT name students;",
                    "expected_fix": "SELECT name FROM students;",
                    "hint": "Fix the SELECT query by adding FROM before the table name.",
                }
            ]
        if "where" in lower_name or "filter" in lower_name:
            return [
                {
                    "buggy_code": "SELECT * FROM students WHERE grade;",
                    "expected_fix": "SELECT * FROM students WHERE grade = 'A';",
                    "hint": "Fix the WHERE clause by writing a complete filter condition.",
                }
            ]
        if "join" in lower_name:
            return [
                {
                    "buggy_code": "SELECT students.name, courses.title\nFROM students\nJOIN courses;",
                    "expected_fix": "SELECT students.name, courses.title\nFROM students\nJOIN enrollments ON enrollments.student_id = students.student_id\nJOIN courses ON courses.course_id = enrollments.course_id;",
                    "hint": "Fix the JOIN by connecting tables with matching key columns.",
                }
            ]
        if "index" in lower_name:
            return [
                {
                    "buggy_code": "CREATE INDEX idx_students_name ON students(age);\nSELECT * FROM students WHERE name = 'Alice';",
                    "expected_fix": "CREATE INDEX idx_students_name ON students(name);\nSELECT * FROM students WHERE name = 'Alice';",
                    "hint": "Fix the index by indexing the column used by the query filter.",
                }
            ]
        if "window" in lower_name:
            return [
                {
                    "buggy_code": "SELECT name, salary, RANK() ORDER BY salary DESC FROM employees;",
                    "expected_fix": "SELECT name, salary, RANK() OVER (ORDER BY salary DESC) FROM employees;",
                    "hint": "Fix the window function by adding the OVER clause.",
                }
            ]
        if "cte" in lower_name or "common table" in lower_name:
            return [
                {
                    "buggy_code": "recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;",
                    "expected_fix": "WITH recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;",
                    "hint": "Fix the CTE by starting the temporary result with WITH.",
                }
            ]
        return [
            {
                "buggy_code": "SELECT * students;",
                "expected_fix": "SELECT * FROM students;",
                "hint": f"Fix the {name} query by using complete SQL syntax.",
            }
        ]

    if domain == "HTML":
        if "accessibility" in lower_name:
            return [
                {
                    "buggy_code": "<label>Email</label>\n<input id=\"email\" type=\"email\">",
                    "expected_fix": "<label for=\"email\">Email</label>\n<input id=\"email\" name=\"email\" type=\"email\">",
                    "hint": "Fix the accessibility bug by connecting the label to the input.",
                }
            ]
        if "component" in lower_name:
            return [
                {
                    "buggy_code": "class UserCard extends HTMLElement {}\n<user-card></user-card>",
                    "expected_fix": "class UserCard extends HTMLElement {}\ncustomElements.define(\"user-card\", UserCard);\n<user-card></user-card>",
                    "hint": "Fix the Web Component by registering the custom element.",
                }
            ]
        if "form" in lower_name or "input" in lower_name:
            return [
                {
                    "buggy_code": "<form><input id=\"email\"><button>Send</button></form>",
                    "expected_fix": "<form><label for=\"email\">Email</label><input id=\"email\" name=\"email\"><button type=\"submit\">Send</button></form>",
                    "hint": "Fix the form by giving the input a label and name.",
                }
            ]
        if "attribute" in lower_name or "link" in lower_name:
            return [
                {
                    "buggy_code": "<a src=\"about.html\">About</a>",
                    "expected_fix": "<a href=\"about.html\">About</a>",
                    "hint": "Fix the link by using href for the destination.",
                }
            ]
        if "image" in lower_name or "list" in lower_name:
            return [
                {
                    "buggy_code": "<img src=\"logo.png\">",
                    "expected_fix": "<img src=\"logo.png\" alt=\"Company logo\">",
                    "hint": "Fix the image by adding meaningful alt text.",
                }
            ]
        if "service worker" in lower_name:
            return [
                {
                    "buggy_code": "navigator.serviceWorker.register();",
                    "expected_fix": "navigator.serviceWorker.register(\"/service-worker.js\");",
                    "hint": "Fix the registration by passing the service worker file path.",
                }
            ]
        return [
            {
                "buggy_code": "<strong><em>Hello</strong></em>",
                "expected_fix": "<strong><em>Hello</em></strong>",
                "hint": f"Fix the {name} markup by closing nested tags in reverse order.",
            }
        ]

    if domain == "Git":
        if "repository" in lower_name:
            return [
                {
                    "buggy_code": "git remote add origin\n git status",
                    "expected_fix": "git remote add origin https://github.com/user/project.git\ngit status",
                    "hint": "Fix the repository setup by giving the remote a URL.",
                }
            ]
        if "commit" in lower_name or "history" in lower_name:
            return [
                {
                    "buggy_code": "git commit -m \"save login fix\"",
                    "expected_fix": "git add app.py\ngit commit -m \"save login fix\"",
                    "hint": "Fix the commit flow by staging the changed file first.",
                }
            ]
        if "branch" in lower_name:
            return [
                {
                    "buggy_code": "git checkout feature/login\ngit commit -m \"fix login\"",
                    "expected_fix": "git checkout -b feature/login\ngit add .\ngit commit -m \"fix login\"",
                    "hint": "Fix the branch workflow by creating/switching to the feature branch before committing.",
                }
            ]
        if "merge" in lower_name or "conflict" in lower_name:
            return [
                {
                    "buggy_code": "<<<<<<< HEAD\nold title\n=======\nnew title\n>>>>>>> feature",
                    "expected_fix": "new title",
                    "hint": "Fix the merge conflict by choosing the correct content and removing conflict markers.",
                }
            ]
        if "rebase" in lower_name:
            return [
                {
                    "buggy_code": "git rebase main\n# conflict fixed\ngit commit -m \"fix conflict\"",
                    "expected_fix": "git rebase main\n# conflict fixed\ngit add .\ngit rebase --continue",
                    "hint": "Fix the rebase flow by staging the resolution and continuing the rebase.",
                }
            ]
        if "submodule" in lower_name:
            return [
                {
                    "buggy_code": "git clone https://github.com/user/app.git\ncd app\nls vendor/library",
                    "expected_fix": "git clone https://github.com/user/app.git\ncd app\ngit submodule update --init --recursive",
                    "hint": "Fix the submodule checkout by initializing and updating submodules.",
                }
            ]
        return [
            {
                "buggy_code": "git add\ngit commit -m \"save work\"",
                "expected_fix": "git add .\ngit commit -m \"save work\"",
                "hint": f"Fix the {name} workflow by staging a specific path or all changes.",
            }
        ]

    if domain == "Data Structures":
        if "array" in lower_name:
            return [
                {
                    "buggy_code": "items = [10, 20, 30]\nlast = items[len(items)]",
                    "expected_fix": "items = [10, 20, 30]\nlast = items[len(items) - 1]",
                    "hint": "Fix the array bug by using the last valid zero-based index.",
                }
            ]
        if "linked" in lower_name:
            return [
                {
                    "buggy_code": "new_node.next = head.next\nhead = new_node",
                    "expected_fix": "new_node.next = head\nhead = new_node",
                    "hint": "Fix the linked list insertion by preserving the old head pointer.",
                }
            ]
        if "stack" in lower_name:
            return [
                {
                    "buggy_code": "stack = [\"first\", \"second\"]\nremoved = stack.pop(0)",
                    "expected_fix": "stack = [\"first\", \"second\"]\nremoved = stack.pop()",
                    "hint": "Fix the stack operation by removing the most recent item.",
                }
            ]
        if "queue" in lower_name:
            return [
                {
                    "buggy_code": "queue = [\"first\", \"second\"]\nremoved = queue.pop()",
                    "expected_fix": "queue = [\"first\", \"second\"]\nremoved = queue.pop(0)",
                    "hint": "Fix the queue operation by removing the oldest item first.",
                }
            ]
        if "tree" in lower_name:
            return [
                {
                    "buggy_code": "def inorder(node):\n    visit(node)\n    inorder(node.left)\n    inorder(node.right)",
                    "expected_fix": "def inorder(node):\n    inorder(node.left)\n    visit(node)\n    inorder(node.right)",
                    "hint": "Fix the traversal order so inorder visits left, root, then right.",
                }
            ]
        if "set" in lower_name:
            return [
                {
                    "buggy_code": "seen = set([\"A\", \"A\", \"B\"])\nprint(len(seen) == 3)",
                    "expected_fix": "seen = set([\"A\", \"A\", \"B\"])\nprint(len(seen) == 2)",
                    "hint": "Fix the set expectation because duplicate values are removed.",
                }
            ]
        if "graph" in lower_name:
            return [
                {
                    "buggy_code": "def dfs(node):\n    for neighbor in graph[node]:\n        dfs(neighbor)",
                    "expected_fix": "def dfs(node):\n    if node in visited:\n        return\n    visited.add(node)\n    for neighbor in graph[node]:\n        dfs(neighbor)",
                    "hint": "Fix the graph traversal by tracking visited nodes.",
                }
            ]
        return [
            {
                "buggy_code": "remove_item(structure)",
                "expected_fix": "if not is_empty(structure):\n    remove_item(structure)",
                "hint": f"Fix the {name} operation by checking the structure state first.",
            }
        ]

    return [
        {
            "buggy_code": "remove_item()",
            "expected_fix": "if item_exists:\n    remove_item()",
            "hint": f"Fix the bug by checking the main rule of {name} before acting.",
        }
    ]


def make_debug_view(concept: Dict[str, Any]) -> Dict[str, str]:
    return concept_debug_cases(concept)[0]


def make_output_prediction_view(concept: Dict[str, Any]) -> Dict[str, str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lower_name = name.lower()

    if domain == "Python":
        if "variable" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "x = 10\nx = 20\nprint(x)",
                "answer": "20",
                "explanation": "The second assignment changes what x refers to.",
            }

        if "data type" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "age = \"20\"\nprint(int(age) + 1)",
                "answer": "21",
                "explanation": "int(age) converts the string to a number before addition.",
            }

        if "conditional" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "score = 82\nif score >= 80:\n    print(\"pass\")\nelse:\n    print(\"retry\")",
                "answer": "pass",
                "explanation": "The condition is true, so the if branch runs.",
            }

        if "loop" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "for i in range(3):\n    print(i)",
                "answer": "0\n1\n2",
                "explanation": "range(3) produces 0, 1, and 2.",
            }

        if "function" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))",
                "answer": "5",
                "explanation": "The function returns 2 + 3, then print displays it.",
            }

        if "object-oriented" in lower_name or "oop" in lower_name:
            return {
                "question": "What is the output of this code?",
                "code": "class Counter:\n    def __init__(self):\n        self.count = 0\n\nc = Counter()\nc.count += 1\nprint(c.count)",
                "answer": "1",
                "explanation": "The instance attribute count starts at 0 and is increased once.",
            }

        if "decorator" in lower_name or "generator" in lower_name:
            return {
                "question": "What is the output of this decorator example?",
                "code": "def deco(fn):\n    def wrapper():\n        print(\"before\")\n        fn()\n    return wrapper\n\n@deco\ndef greet():\n    print(\"hello\")\n\ngreet()",
                "answer": "before\nhello",
                "explanation": "The decorator wrapper prints before, then calls greet.",
            }

        if "file" in lower_name:
            return {
                "question": "What does this file-handling code print after writing and reading?",
                "code": "with open(\"note.txt\", \"w\") as f:\n    f.write(\"done\")\nwith open(\"note.txt\", \"r\") as f:\n    print(f.read())",
                "answer": "done",
                "explanation": "The first block writes text; the second block reads it back.",
            }

        return {
            "question": "What is the output of this code?",
            "code": f"print(\"{name}\")",
            "answer": name,
            "explanation": f"The example prints the concept name {name}.",
        }

    if domain == "SQL":
        if "where" in lower_name or "filter" in lower_name:
            code = "SELECT name FROM students WHERE grade = 'A';"
            answer = "It returns names for students whose grade is A."
            explanation = "WHERE filters rows before the selected column is returned."
        elif "join" in lower_name:
            code = "SELECT students.name, courses.title\nFROM students\nJOIN enrollments ON enrollments.student_id = students.student_id\nJOIN courses ON courses.course_id = enrollments.course_id;"
            answer = "It returns matched student names with their course titles."
            explanation = "JOIN combines related rows through matching key columns."
        elif "index" in lower_name:
            code = "CREATE INDEX idx_students_name ON students(name);\nSELECT * FROM students WHERE name = 'Alice';"
            answer = "The query result is the same, but lookup can be faster."
            explanation = "An index improves retrieval; it does not change returned rows."
        elif "window" in lower_name:
            code = "SELECT department, name, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank\nFROM employees;"
            answer = "It ranks employees within each department."
            explanation = "PARTITION BY creates a separate ranking window per department."
        elif "cte" in lower_name or "common table" in lower_name:
            code = "WITH recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;"
            answer = "It returns rows from the temporary recent_orders result."
            explanation = "The CTE names a temporary result used by the following SELECT."
        else:
            code = "SELECT name FROM students;"
            answer = "It returns values from the name column."
            explanation = "SELECT chooses which column to display."
        return {
            "question": "What does this query return?",
            "code": code,
            "answer": answer,
            "explanation": explanation,
        }

    if domain == "HTML":
        if "accessibility" in lower_name:
            code = "<label for=\"email\">Email</label>\n<input id=\"email\" name=\"email\">"
            answer = "The label is associated with the email input."
            explanation = "The for and id values match, helping assistive technology."
        elif "service worker" in lower_name:
            code = "navigator.serviceWorker.register(\"/sw.js\")"
            answer = "The browser attempts to register the service worker file."
            explanation = "register receives the service worker script path."
        elif "component" in lower_name:
            code = "customElements.define(\"user-card\", UserCard)"
            answer = "The custom element name is valid because it contains a hyphen."
            explanation = "Custom element names must include a hyphen."
        elif "attribute" in lower_name or "link" in lower_name:
            code = "<a href=\"about.html\">About</a>"
            answer = "About"
            explanation = "The link text appears, and href stores the destination."
        elif "image" in lower_name or "list" in lower_name:
            code = "<ul><li>A</li><li>B</li></ul>"
            answer = "A and B"
            explanation = "The unordered list renders both list items."
        else:
            code = "<h1>Welcome</h1>\n<p>Hello</p>"
            answer = "Welcome and Hello"
            explanation = "The heading and paragraph text appear on the page."
        return {
            "question": "What appears on the page?",
            "code": code,
            "answer": answer,
            "explanation": explanation,
        }

    if domain == "Git":
        if "commit" in lower_name or "history" in lower_name:
            code = "git add app.py\ngit commit -m \"Fix login\"\ngit log --oneline"
            answer = "It stages a file, creates a commit, then shows short commit history."
            explanation = "The commands show the normal commit/history flow."
        elif "branch" in lower_name:
            code = "git checkout -b feature/login\ngit branch"
            answer = "It creates/switches to feature/login and lists branches."
            explanation = "The -b flag creates the new branch."
        elif "merge" in lower_name:
            code = "git checkout main\ngit merge feature/login"
            answer = "It merges the feature branch into main."
            explanation = "Merge combines changes from one branch into the current branch."
        elif "rebase" in lower_name:
            code = "git log --oneline\ngit rebase -i HEAD~3"
            answer = "It opens the last three commits for interactive editing."
            explanation = "Interactive rebase lets you reorder, squash, or edit recent commits."
        elif "submodule" in lower_name:
            code = "git submodule update --init --recursive"
            answer = "It initializes and updates nested submodule repositories."
            explanation = "Submodules need a separate update step after clone or pull."
        elif "repository" in lower_name:
            code = "git init\ngit remote add origin https://github.com/user/project.git\ngit status"
            answer = "It creates a repository, connects a remote, and shows repository state."
            explanation = "These commands set up and inspect a Git repository."
        else:
            code = "git status"
            answer = "It shows the working tree status."
            explanation = "git status shows changed, staged, and untracked files."
        return {
            "question": "What does this command show?",
            "code": code,
            "answer": answer,
            "explanation": explanation,
        }

    if domain == "Data Structures":
        if "array" in lower_name:
            code, answer, explanation = "arr = [10, 20, 30]\nprint(arr[1])", "20", "Index 1 reads the second array element."
        elif "linked" in lower_name:
            code, answer, explanation = "head -> A -> B -> None\ninsert C after A", "head -> A -> C -> B -> None", "The new node points to B, and A points to the new node."
        elif "stack" in lower_name:
            code, answer, explanation = "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop())", "B", "A stack removes the last item pushed."
        elif "queue" in lower_name:
            code, answer, explanation = "queue = ['A', 'B']\nprint(queue.pop(0))", "A", "A queue removes the first item added."
        elif "tree" in lower_name:
            code, answer, explanation = "inorder(left=A, root=B, right=C)", "A, B, C", "Inorder traversal visits left, root, then right."
        elif "set" in lower_name:
            code, answer, explanation = "items = {1, 1, 2}\nprint(len(items))", "2", "A set keeps unique values only."
        elif "graph" in lower_name:
            code, answer, explanation = "A -> B\nB -> C\nvisited = {A, B, C}", "Each node is visited once.", "A visited set prevents repeated traversal."
        else:
            code, answer, explanation = "choose structure based on access, insert, delete, and traversal needs", "The best structure matches the operation pattern.", primary_key_point(concept)
        return {
            "question": f"What result should you predict for this {name} example?",
            "code": code,
            "answer": answer,
            "explanation": explanation,
        }

    example = primary_example(concept)
    return {
        "question": f"What happens when {name} is used correctly?",
        "code": example,
        "answer": f"It applies the main idea of {name}.",
        "explanation": primary_key_point(concept),
    }


def make_transfer_view(concept: Dict[str, Any]) -> str:
    real_use = compact_text(primary_real_use(concept), 180)

    return (
        f"Transfer view for {concept['concept_name']}:\n\n"
        f"Example scenario: {real_use}\n\n"
        f"Question: How would you apply {concept['concept_name']} in a similar situation?"
    )


def make_challenge_view(concept: Dict[str, Any]) -> str:
    key = primary_key_point(concept)

    return (
        f"Challenge view for {concept['concept_name']}:\n\n"
        f"Design a non-trivial {concept['domain']} example, explain why it works, and identify one edge case for this rule:\n"
        f"{key}\n\n"
        f"Justify the choice you made and compare it with one weaker alternative."
    )


def make_revision_summary_view(concept: Dict[str, Any]) -> str:
    key_points = split_items(concept["key_points"], max_items=4)
    misconceptions = split_items(concept["misconceptions"], max_items=2)

    lines = [f"Revision summary for {concept['concept_name']}:", ""]

    lines.append("Remember:")
    for item in key_points:
        lines.append(f"- {item}")

    if misconceptions:
        lines.append("")
        lines.append("Avoid:")
        for item in misconceptions:
            lines.append(f"- {item}")

    return "\n".join(lines)


def make_flashcard_view(concept: Dict[str, Any]) -> Dict[str, str]:
    return {
        "front": f"What should you remember about {concept['concept_name']}?",
        "back": primary_key_point(concept),
    }


def make_mindmap_view(concept: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "center": concept["concept_name"],
        "branches": [
            {
                "name": "Core idea",
                "items": [primary_key_point(concept)],
            },
            {
                "name": "Example",
                "items": [primary_example(concept) or "Create a simple example."],
            },
            {
                "name": "Common mistake",
                "items": [primary_misconception(concept)],
            },
            {
                "name": "Real-world use",
                "items": [primary_real_use(concept)],
            },
        ],
    }


def generate_artifact_output(concept: Dict[str, Any], artifact_type: str) -> Any:
    if artifact_type == "explanation":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "definition_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "simple_example_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "step_by_step_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "code_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "analogy_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "misconception_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "debug_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "output_prediction_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "transfer_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "challenge_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type == "revision_summary_view":
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type in {"comparison_view", "real_world_connection_view"}:
        return rich_teaching_payload(concept, artifact_type)

    if artifact_type in ASSESSMENT_TYPES:
        return assessment_payload(concept, artifact_type)

    if artifact_type in REVISION_TYPES or artifact_type in NOTEBOOK_TYPES:
        return revision_payload(concept, artifact_type)

    if artifact_type in FLASHCARD_TYPES:
        return flashcard_payload(concept, artifact_type)

    if artifact_type in MINDMAP_TYPES:
        return mindmap_payload(concept, artifact_type)

    if artifact_type in FEEDBACK_TYPES:
        return feedback_payload(concept, artifact_type)

    if artifact_type in HINT_TYPES:
        return hint_payload(concept, artifact_type)

    if artifact_type in DOUBT_TYPES:
        return doubt_payload(concept, artifact_type)

    if artifact_type in PRACTICE_TYPES:
        return assessment_payload(concept, artifact_type)

    if artifact_type in VOICE_TYPES:
        return voice_payload(concept, artifact_type)

    return rich_teaching_payload(concept, artifact_type)


def validate_artifact_output(output: Any) -> bool:
    if output is None:
        return False

    if isinstance(output, str):
        return len(output.strip()) >= 40

    if isinstance(output, dict):
        text = json.dumps(output, ensure_ascii=False)
        if len(text.strip()) < 80:
            return False
        if "C2" in text or "apply concept" in text.lower():
            return False
        return len(output) > 0

    return False


def source_fields_for_artifact(artifact_type: str) -> List[str]:
    mapping = {
        "definition_view": ["base_content", "key_points"],
        "simple_example_view": ["base_content", "examples"],
        "step_by_step_view": ["base_content", "key_points", "examples"],
        "code_view": ["examples", "key_points"],
        "analogy_view": ["concept_name", "domain", "key_points"],
        "misconception_view": ["misconceptions", "key_points"],
        "debug_view": ["misconceptions", "examples", "domain"],
        "output_prediction_view": ["examples", "key_points", "domain"],
        "transfer_view": ["real_world_use", "key_points"],
        "challenge_view": ["key_points", "examples"],
        "revision_summary_view": ["key_points", "misconceptions"],
        "flashcard_view": ["concept_name", "key_points"],
        "mindmap_view": ["key_points", "examples", "misconceptions", "real_world_use"],
    }
    return mapping.get(
        artifact_type,
        ["base_content", "examples", "key_points", "misconceptions", "real_world_use", "next_concept_link"],
    )


def generate_all_artifacts(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    artifacts = []
    created_at = datetime.now().isoformat(timespec="seconds")

    for concept in concepts:
        for artifact_type in ARTIFACT_TYPES:
            output = generate_artifact_output(concept, artifact_type)
            valid = validate_artifact_output(output)

            artifact = {
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "domain": concept["domain"],
                "artifact_type": artifact_type,
                "task_type": artifact_type,
                "task_family": task_family(artifact_type),
                "difficulty": "adaptive",
                "teaching_style": artifact_type.replace("_view", ""),
                "source_fields": source_fields_for_artifact(artifact_type),
                "output": output,
                "valid": valid,
                "quality_score": 0.95 if valid else 0.0,
                "raw_valid": False,
                "fallback_applied": True,
                "fallback_source": "concept_resources_artifact_generator",
                "generation_source": "guarded_artifact_mode_not_raw_model_generation",
                "created_at": created_at,
            }

            artifacts.append(artifact)

    return artifacts


def build_markdown_report(artifacts: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("# Generated Tutor Artifacts")
    lines.append("")
    lines.append(f"Total artifacts: **{len(artifacts)}**")
    lines.append("")

    grouped = {}
    for artifact in artifacts:
        key = (artifact["domain"], artifact["concept_id"], artifact["concept_name"])
        grouped.setdefault(key, []).append(artifact)

    for (domain, concept_id, concept_name), items in grouped.items():
        lines.append(f"## {domain} — {concept_id}: {concept_name}")
        lines.append("")

        for artifact in items:
            lines.append(f"### {artifact['artifact_type']}")
            lines.append("")
            lines.append(f"- Valid: `{artifact['valid']}`")
            lines.append(f"- Source fields: `{', '.join(artifact['source_fields'])}`")
            lines.append("")

            output = artifact["output"]

            if isinstance(output, dict):
                lines.append("```json")
                lines.append(json.dumps(output, indent=2, ensure_ascii=False))
                lines.append("```")
            else:
                lines.append(str(output))

            lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nGenerating tutor artifacts...")
    print("=" * 80)

    concepts = load_concepts()
    artifacts = generate_all_artifacts(concepts)

    with JSON_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2, ensure_ascii=False)

    with MD_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        f.write(build_markdown_report(artifacts))

    valid_count = sum(1 for item in artifacts if item["valid"])

    print("\nGeneration complete.")
    print(f"Concepts processed: {len(concepts)}")
    print(f"Artifacts per concept: {len(ARTIFACT_TYPES)}")
    print(f"Generated artifacts: {len(artifacts)}")
    print(f"Valid artifacts: {valid_count}/{len(artifacts)}")
    print(f"Output JSON: {JSON_OUTPUT_PATH}")
    print(f"Output Markdown: {MD_OUTPUT_PATH}")

    expected = len(concepts) * len(ARTIFACT_TYPES)
    if len(artifacts) == expected and valid_count == len(artifacts):
        print("STATUS: PASS")
    else:
        print("STATUS: CHECK")


if __name__ == "__main__":
    main()
