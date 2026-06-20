from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path
from typing import Any
import re


ROOT = Path(__file__).resolve().parents[2]
CORE_DATA = ROOT / "external" / "core_data"

SUBJECT_ALIASES = {
    "python": "Python",
    "sql": "SQL / Database",
    "sql-database": "SQL / Database",
    "sql / database": "SQL / Database",
    "database": "SQL / Database",
    "html": "HTML/Web Basics",
    "html-web-basics": "HTML/Web Basics",
    "html/web basics": "HTML/Web Basics",
    "web": "HTML/Web Basics",
    "git": "Git",
    "data structures": "Data Structures",
    "data-structures": "Data Structures",
}

SUBJECT_DBS = {
    "Python": "python_learning.db",
    "SQL / Database": "database_sql.db",
    "HTML/Web Basics": "html_web_basics.db",
    "Git": "git_version_control.db",
    "Data Structures": "data_structures.db",
}

FIRST_CONCEPT = {
    "Python": ("P1", "Variables"),
    "SQL / Database": ("S1", "Database Basics"),
    "HTML/Web Basics": ("H1", "What is HTML"),
    "Git": ("G1", "Version Control"),
    "Data Structures": ("D1", "Arrays"),
}

TEACHING_VIEWS = [
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
]

ASSESSMENT_TYPES = [
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
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
]

HINT_TYPES = [
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
]

FEEDBACK_TYPES = [
    "feedback",
    "correct_answer_feedback",
    "wrong_answer_feedback",
    "partial_answer_feedback",
    "debug_feedback",
    "output_prediction_feedback",
    "next_step_feedback",
    "encouragement_feedback",
    "mistake_feedback",
]

FLASHCARD_TYPES = [
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "syntax_flashcard",
    "personal_flashcards",
    "spaced_repetition_card",
]

DOUBT_TYPES = [
    "doubt_answer",
    "concept_doubt_answer",
    "syntax_doubt_answer",
    "debug_doubt_answer",
    "output_doubt_answer",
    "example_request_answer",
    "revision_doubt_answer",
    "next_step_doubt_answer",
    "comparison_doubt_answer",
]


def normalize_subject(subject: str | None) -> str:
    key = (subject or "Python").strip().lower()
    return SUBJECT_ALIASES.get(key, SUBJECT_ALIASES.get(key.replace("-", " "), subject or "Python"))


def _split_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
    parts = [part.strip(" -\t") for part in text.replace("\r", "\n").replace(";", "\n").split("\n")]
    return [part for part in parts if part]


def _clean_concept_title(name: str) -> str:
    text = str(name or "").strip()
    return text[8:].strip() if text.lower().startswith("what is ") else text


def _sentence_limit(value: Any, max_sentences: int = 3, max_chars: int = 300) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    limited = " ".join(sentences[:max_sentences]) if sentences else text
    if len(limited) > max_chars:
        limited = limited[: max_chars - 3].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return limited


def _short_definition(content: dict[str, Any]) -> str:
    name = _clean_concept_title(content["concept_name"]).lower()
    subject = str(content["subject"])
    base = _sentence_limit(content.get("base_content"), 1, 180)
    if "git" in subject.lower() and "version control" in name:
        return "Version control records changes over time so you can track history, restore earlier versions, and collaborate safely."
    return base or f"{_clean_concept_title(content['concept_name'])} is a core idea in {subject}."


def _expected_points(*items: Any, limit: int = 4) -> list[str]:
    points: list[str] = []
    for item in items:
        if isinstance(item, list):
            candidates = item
        else:
            candidates = [item]
        for candidate in candidates:
            text = _sentence_limit(candidate, 1, 140)
            if text and text not in points:
                points.append(text)
            if len(points) >= limit:
                return points
    return points


def _db_row(subject: str, concept_id: str) -> dict[str, Any] | None:
    db_path = CORE_DATA / SUBJECT_DBS[subject]
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM concept_resources WHERE concept_id = ? LIMIT 1", (concept_id,)).fetchone()
        if row is None:
            row = conn.execute("SELECT * FROM concept_resources ORDER BY concept_id LIMIT 1").fetchone()
        resource = dict(row) if row else None
        if resource:
            concept = conn.execute("SELECT * FROM concepts WHERE concept_id = ? LIMIT 1", (resource["concept_id"],)).fetchone()
            if concept:
                resource["concept_name"] = dict(concept).get("name") or resource.get("topic")
        return resource
    finally:
        conn.close()


def resolve_concept_content(subject: str | None, concept_id: str | None) -> dict[str, Any]:
    normalized_subject = normalize_subject(subject)
    first_id, first_name = FIRST_CONCEPT.get(normalized_subject, FIRST_CONCEPT["Python"])
    raw_id = str(concept_id or first_id).strip()
    if not raw_id or raw_id.upper().startswith("C") or raw_id.lower() in {"undefined", "none", "null"}:
        raw_id = first_id
    row = _db_row(normalized_subject, raw_id)
    if row is None:
        row = {
            "concept_id": raw_id,
            "concept_name": first_name,
            "topic": first_name,
            "base_content": f"{first_name} is a core concept in {normalized_subject}.",
            "examples": f"Practice {first_name} with one focused example.",
            "key_points": [f"Understand {first_name}.", "Try one example.", "Check the result."],
            "misconceptions": ["Do not memorize syntax without checking the meaning."],
            "real_world_use": f"{first_name} appears in real {normalized_subject} work.",
            "next_concept_link": "",
        }
    actual_id = str(row.get("concept_id") or raw_id)
    concept_name = str(row.get("concept_name") or row.get("topic") or FIRST_CONCEPT.get(normalized_subject, (actual_id, actual_id))[1])
    base = str(row.get("base_content") or "").strip() or f"{concept_name} is a core concept in {normalized_subject}."
    examples = str(row.get("examples") or "").strip() or f"Practice {concept_name} with one focused example."
    key_points = _split_text(row.get("key_points")) or [f"Understand {concept_name}.", "Try one example.", "Check the result."]
    misconceptions = _split_text(row.get("misconceptions")) or ["Do not memorize syntax without checking the meaning."]
    return {
        "subject": normalized_subject,
        "concept_id": actual_id,
        "concept_name": concept_name,
        "topic": str(row.get("topic") or concept_name),
        "base_content": base,
        "examples": examples,
        "key_points": key_points,
        "misconceptions": misconceptions,
        "real_world_use": str(row.get("real_world_use") or f"{concept_name} appears in practical {normalized_subject} tasks."),
        "next_concept_link": str(row.get("next_concept_link") or ""),
        "resource_source": "concept_resources" if row else "fallback",
        "db_name": SUBJECT_DBS[normalized_subject],
    }


def _python_variable_code() -> str:
    return "\n".join(
        [
            "x = 10",
            "name = 'Alice'",
            "a = b = c = 5",
            "x, y, z = 1, 2, 3",
            "score = 10",
            "score = 20",
            "print(score)",
        ]
    )


def build_teaching_views(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    name = content["concept_name"]
    subject = content["subject"]
    base = content["base_content"]
    examples = content["examples"]
    points = content["key_points"]
    mistakes = content["misconceptions"]
    real = content["real_world_use"]
    code = _python_variable_code() if subject == "Python" and name.lower() == "variables" else examples
    return {
        "explanation": {"title": f"{name}: full explanation", "explanation": f"{base}\n\nWhy it matters: {real}\n\nExample: {examples}\n\nKey points: {' '.join(points)}\n\nCommon mistakes: {' '.join(mistakes)}", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "definition_view": {"title": f"{name}: definition", "explanation": f"Definition: {base}\n\nImportant terms: {content['topic']}, value, example, result.\n\nUse this definition with the examples below.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "simple_example_view": {"title": f"{name}: simple example", "explanation": f"Start with one beginner example for {name}. Read the example, identify the important part, then check the result.\n\nExample explained: {examples}", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "step_by_step_view": {"title": f"{name}: step by step", "explanation": f"Step 1: identify the idea. Step 2: connect it to the example. Step 3: predict the result. Step 4: check against the key points. Mini check: explain {name} in your own words.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "analogy_view": {"title": f"{name}: analogy", "explanation": f"Analogy: think of {name} as a labeled container or contact name that helps you find the right information. In code or data work, the label points you to the value you need.\n\nMap it back: {examples}", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "code_view": {"title": f"{name}: code and syntax", "explanation": f"Use the syntax carefully and trace what each line means for {name}. Start with the basic pattern, compare each example with the definition, then check the final printed or returned result.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "misconception_view": {"title": f"{name}: misconceptions", "explanation": f"Common wrong ideas about {name}: {' '.join(mistakes)}\n\nCorrect idea: {base}", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "debug_view": {"title": f"{name}: debug view", "explanation": f"Debug {name} by finding the concept rule being broken, explaining why it fails, and writing the corrected version.", "example": "Buggy example:\n2score = 10\nprint(2score)\n\nCorrected:\nscore = 10\nprint(score)" if subject == "Python" else examples, "code": "2score = 10\nprint(2score)\n\n# corrected\nscore = 10\nprint(score)" if subject == "Python" else code, "key_points": points, "common_mistakes": mistakes},
        "output_prediction_view": {"title": f"{name}: output prediction", "explanation": f"Use {name} to trace line by line. Ask what value or result exists after each step, then write the final output.", "example": "score = 10\nscore = 20\nprint(score)\nOutput: 20" if subject == "Python" else examples, "code": "score = 10\nscore = 20\nprint(score)" if subject == "Python" else code, "key_points": points, "common_mistakes": mistakes},
        "transfer_view": {"title": f"{name}: transfer", "explanation": f"Transfer {name} to a practical situation: shopping bills, student marks, scores, login status, reports, or stored records depending on the subject.\n\nReal use: {real}", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "challenge_view": {"title": f"{name}: challenge", "explanation": f"Challenge: use {name} to solve a small practical task, then explain why your answer works.", "example": "Create variables for price and quantity, then print price * quantity." if subject == "Python" else f"Create a practical task using {name}.", "code": code, "key_points": points, "common_mistakes": mistakes},
        "revision_summary_view": {"title": f"{name}: revision summary", "explanation": f"Summary: {base}\n\nRemember: {' '.join(points)}\n\nAvoid: {' '.join(mistakes)}\n\nQuick check: give one example of {name}.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "comparison_view": {"title": f"{name}: comparison", "explanation": f"Compare {name} with nearby ideas. For variables: variable vs value, variable vs constant, assignment vs comparison. For other subjects, compare the concept with its related operation or artifact.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
        "real_world_connection_view": {"title": f"{name}: real-world connection", "explanation": f"Real-world connection: {real}\n\nUse {name} when you need a clear way to represent, retrieve, update, or reason about information.", "example": examples, "code": code, "key_points": points, "common_mistakes": mistakes},
    }


def choose_teaching_view(difficulty: str, previous_view: str | None = None, mistake_type: str | None = None, retention_need: bool = False) -> str:
    cycle = ["explanation", "definition_view", "simple_example_view", "step_by_step_view", "analogy_view", "misconception_view", "code_view", "debug_view", "output_prediction_view"]
    if retention_need:
        preferred = "revision_summary_view"
    elif mistake_type in {"wrong_output", "output_prediction"}:
        preferred = "output_prediction_view"
    elif mistake_type in {"syntax_misunderstanding", "debug"}:
        preferred = "debug_view"
    elif difficulty == "hard":
        preferred = "challenge_view"
    elif difficulty == "medium":
        preferred = "code_view"
    else:
        preferred = "explanation"
    if previous_view and previous_view == preferred:
        idx = cycle.index(preferred) if preferred in cycle else 0
        return cycle[(idx + 1) % len(cycle)]
    return preferred


def build_lesson_payload(subject: str | None, concept_id: str | None, difficulty: str = "easy", view: str | None = None, previous_view: str | None = None, mistake_type: str | None = None) -> dict[str, Any]:
    content = resolve_concept_content(subject, concept_id)
    content_by_view = build_teaching_views(content)
    selected = view if view in TEACHING_VIEWS else choose_teaching_view(difficulty, previous_view, mistake_type)
    selected_content = {
        **content_by_view[selected],
        "concept_intro": f"Start with {content['concept_name']} in {content['subject']}.",
        "definition": content["base_content"],
        "examples": content["examples"],
        "syntax": content_by_view[selected]["code"],
        "code_example": content_by_view[selected]["code"],
        "misconception_correction": "; ".join(content["misconceptions"]),
        "output_tracing_explanation": "Trace each step, then compare the final value or output with the expected result.",
        "real_world_use": content["real_world_use"],
        "practice_prompt": f"Try one short task using {content['concept_name']}.",
        "summary": f"{content['concept_name']} is important in {content['subject']}: {content['key_points'][0]}",
    }
    return {
        **content,
        "selected_view": selected,
        "selectedView": selected,
        "available_views": TEACHING_VIEWS,
        "fallback_views": TEACHING_VIEWS,
        "fallbackViewNames": TEACHING_VIEWS,
        "content_by_view": content_by_view,
        "teaching_content": selected_content,
        "adaptiveExplanation": content_by_view[selected]["explanation"],
        "adaptive_explanation": content_by_view[selected]["explanation"],
        "keyPoints": content_by_view[selected]["key_points"],
        "commonMistakes": content_by_view[selected]["common_mistakes"],
        "workedExample": content_by_view[selected]["code"],
        "baseContent": content["base_content"],
        "realWorldUse": content["real_world_use"],
        "nextConceptLink": content["next_concept_link"],
        "guide_message": f"Let's learn {content['concept_name']} with the {selected.replace('_', ' ')} view.",
        "voice_script": build_voice_scripts(content, "teaching_voice_script")["teaching_voice_script"],
        "llm_generation": llm_status("teaching_view_generation"),
    }


def _q(base: dict[str, Any], qtype: str, difficulty: str, prompt: str, **extra: Any) -> dict[str, Any]:
    order_value = extra.get("order", extra.get("idx", 1))
    task_type = extra.pop("task_type", qtype)
    title = extra.pop("title", qtype.replace("_", " ").title())
    instructions = extra.pop("instructions", "")
    constraints = extra.pop("constraints", [])
    expected_answer = extra.get("expected_answer", extra.get("correct_answer", extra.get("correctAnswer", "")))
    evaluation_mode = extra.pop("evaluation_mode", _evaluation_mode(task_type))
    return {
        "question_id": f"{base['concept_id']}-{difficulty}-{qtype}-{order_value}",
        "questionId": f"{base['concept_id']}-{difficulty}-{qtype}-{order_value}",
        "question_type": qtype,
        "questionType": qtype,
        "task_type": task_type,
        "taskType": task_type,
        "title": title,
        "difficulty": difficulty,
        "prompt": prompt,
        "instructions": instructions,
        "instruction": instructions or prompt,
        "subject": base["subject"],
        "concept_id": base["concept_id"],
        "conceptId": base["concept_id"],
        "concept_name": base["concept_name"],
        "conceptName": base["concept_name"],
        "sourceConcept": base["concept_id"],
        "teaching_view": extra.pop("teaching_view", None),
        "hidden_hint": base["key_points"][0],
        "hint": base["key_points"][0],
        "explanation": base["base_content"],
        "expected_answer": expected_answer,
        "expected_idea": expected_answer,
        "rubric": extra.pop("rubric", None),
        "constraints": constraints,
        "evaluation_mode": evaluation_mode,
        "generated_source": extra.pop("generated_source", "concept_resource_validated_fallback"),
        "grounding_source_label": extra.pop("grounding_source_label", f"{base.get('db_name', 'concept_resources')}:{base['concept_id']}"),
        "frontend_component": extra.pop("frontend_component", _frontend_component(task_type)),
        "frontend_render_type": task_type,
        "source": extra.pop("source", "concept_resource_fallback"),
        **extra,
    }


def _evaluation_mode(task_type: str) -> str:
    task_type = str(task_type or "").lower()
    if task_type in {"mcq", "true_or_false", "flashcard_recall"}:
        return "exact_match"
    if task_type in {"coding_question", "coding_prompt", "debug_task", "output_prediction", "syntax_completion"}:
        return "structured_or_code_evaluation"
    if task_type == "puzzle":
        return "interactive_structured"
    return "rubric"


def _frontend_component(task_type: str) -> str:
    return {
        "mcq": "MCQQuestionCard",
        "output_prediction": "OutputPredictionCard",
        "debug_task": "DebugQuestionCard",
        "syntax_completion": "SyntaxCompletionCard",
        "coding_question": "CodeWritingCard",
        "coding_prompt": "CodeWritingCard",
        "transfer_question": "TransferQuestionCard",
        "challenge_question": "ChallengeQuestionCard",
        "explanation": "ShortExplanationCard",
        "explanation_check": "ShortExplanationCard",
        "flashcard_recall": "FlashcardRecallCard",
        "puzzle": "PuzzleQuestionCard",
        "fill_in_the_blank": "FillBlankCard",
        "true_or_false": "MCQQuestionCard",
    }.get(str(task_type or ""), "GenericQuestionCard")


def _line_limit(difficulty: str) -> str:
    if difficulty == "hard":
        return "Keep your answer around 10-18 lines."
    if difficulty == "medium":
        return "Keep your answer around 6-12 lines."
    return "Keep your answer around 4-8 lines."


def _subject_patterns(c: dict[str, Any], difficulty: str) -> dict[str, Any]:
    subj = c["subject"]
    name = c["concept_name"]
    base = c["base_content"]
    example = c["examples"]
    key = c["key_points"][0]
    real = c["real_world_use"]
    lowered = f"{subj} {name}".lower()

    if "sql" in lowered or "database" in lowered:
        return {
            "snippet": "SELECT name, score\nFROM students\nWHERE score >= 80;",
            "expected_output": "Rows containing student names and scores where score is at least 80.",
            "buggy": "SELECT name score FROM students WHERE score >= 80;",
            "fix": "SELECT name, score FROM students WHERE score >= 80;",
            "bug_type": "missing_comma",
            "incomplete": "SELECT name FROM students _____ score >= 80;",
            "missing": "WHERE",
            "coding": "Write one SQL query for a `students` table that selects student names and scores for rows that meet a condition related to the current concept.",
            "requirements": ["Use a valid SELECT statement.", "Reference a table name.", "Include one filter, join, or ordering step when relevant.", "Return only the needed columns."],
            "expected": "A valid SQL query grounded in the concept.",
            "transfer": f"A school dashboard needs a query for {real}. Explain which columns/table/filter you would use and why.",
        }
    if "html" in lowered or "web" in lowered:
        return {
            "snippet": "<ul>\n  <li>Variables</li>\n  <li>Loops</li>\n</ul>",
            "expected_output": "A bulleted list with two items.",
            "buggy": "<ul>\n  <li>Variables\n  <li>Loops</li>\n</ul>",
            "fix": "<ul>\n  <li>Variables</li>\n  <li>Loops</li>\n</ul>",
            "bug_type": "unclosed_tag",
            "incomplete": "<a _____=\"https://example.com\">Open example</a>",
            "missing": "href",
            "coding": f"Write a small HTML snippet that demonstrates {name} in a realistic page section.",
            "requirements": ["Use semantic HTML where possible.", "Include at least two nested or related elements.", "Close every tag correctly.", "Keep the snippet readable."],
            "expected": "A valid HTML snippet that demonstrates the concept.",
            "transfer": f"A learning page needs a section for {real}. Describe or write the HTML structure you would use.",
        }
    if "git" in lowered:
        return {
            "snippet": "Repository state: app.py is modified but not staged.\nCommand: git status",
            "expected_output": "git status shows app.py under changes not staged for commit.",
            "buggy": "git add .\ngit commit -m \"Update app\"\ngit push origin wrong-branch",
            "fix": "git add .\ngit commit -m \"Update app\"\ngit push origin main",
            "bug_type": "wrong_target_branch",
            "incomplete": "git commit _____ \"Update app\"",
            "missing": "-m",
            "coding": f"Write a short Git command sequence that uses {name} during a normal project change.",
            "requirements": ["Use commands in a sensible order.", "Include the target file or branch when needed.", "Include a short explanation of each command.", "Avoid destructive commands."],
            "expected": "A safe Git command sequence with the correct command effect.",
            "transfer": f"A teammate asks how to use {name} while saving work before a review. State the command sequence and explain the effect.",
        }
    if "data structures" in lowered or "array" in lowered or "stack" in lowered or "queue" in lowered:
        return {
            "snippet": "items = [3, 5]\nitems.append(7)\nprint(items[-1])",
            "expected_output": "7",
            "buggy": "items = [3, 5]\nitems.add(7)\nprint(items[-1])",
            "fix": "items = [3, 5]\nitems.append(7)\nprint(items[-1])",
            "bug_type": "wrong_operation",
            "incomplete": "items = [3, 5]\nitems._____(7)",
            "missing": "append",
            "coding": f"Write a small operation or trace that demonstrates {name} on a short collection.",
            "requirements": ["Create a small collection.", "Perform one concept-specific operation.", "Print or state the final state/output.", "Use clear variable names."],
            "expected": "A small trace or implementation that shows the operation and result.",
            "transfer": f"A queue of tasks must be updated using {name}. Explain the operation you would perform and the final state.",
        }
    return {
        "snippet": "score = 10\nbonus = 5\nscore = score + bonus\nprint(score)",
        "expected_output": "15",
        "buggy": "score = 10\nbonus = \"5\"\nscore = score + bonus\nprint(score)",
        "fix": "score = 10\nbonus = 5\nscore = score + bonus\nprint(score)",
        "bug_type": "type_or_assignment_mismatch",
        "incomplete": "score = 10\nscore _____ 5\nprint(score)",
        "missing": "= score +",
        "coding": f"Write a short Python program that applies {name} to update and print a final result.",
        "requirements": ["Create at least two meaningful variables.", "Update one value using the concept.", "Print the final result.", "Use names that make the purpose clear."],
        "expected": "A runnable Python answer that creates values, updates one of them, and prints the final result.",
        "transfer": f"A learner app needs to track a score update using {name}. Write or explain the variables you would use and how the final score is produced.",
    }


def _make_task_set(c: dict[str, Any], difficulty: str) -> list[dict[str, Any]]:
    name = c["concept_name"]
    p = _subject_patterns(c, difficulty)
    requirements = p["requirements"]
    concept_label = _clean_concept_title(name)
    correct_mcq = _short_definition(c)
    mcq_explanation = _sentence_limit(correct_mcq, 2, 240)
    if "git" in str(c["subject"]).lower():
        real_world_points = _expected_points(c["key_points"][0], c["real_world_use"], "restore or check earlier work", "collaborate safely")
        real_world_prompt = f"Scenario: A team is working on the same project and needs to track changes.\n\nQuestion: How does {concept_label.lower()} help the team avoid losing work?"
    else:
        real_world_points = _expected_points(c["key_points"][0], c["real_world_use"], "clear application to the scenario", "short explanation of the result")
        real_world_prompt = f"Scenario: Someone is using {concept_label} in a practical {c['subject']} task.\n\nQuestion: How does {concept_label.lower()} help them get the right result?"
    puzzle_items = (
        [
            {"id": "edit", "text": "Edit the file"},
            {"id": "add", "text": "Stage the change with git add"},
            {"id": "commit", "text": "Commit with a clear message"},
            {"id": "push", "text": "Push to the correct remote branch"},
        ]
        if "git" in str(c["subject"]).lower()
        else [
            {"id": "s1", "text": "Identify the concept rule"},
            {"id": "s2", "text": "Apply it to the example or scenario"},
            {"id": "s3", "text": "Check the final output/result"},
        ]
    )
    puzzle_order = [str(item["id"]) for item in puzzle_items]
    return [
        _q(c, "mcq", "easy", f"Which statement best explains {concept_label} in {c['subject']}?", title=f"{concept_label}: core idea", options=[correct_mcq, f"It is unrelated to {c['subject']}.", "It should be memorized without examples.", "It only matters after all work is finished."], correct_answer=correct_mcq, correctAnswer=correct_mcq, expected_answer=correct_mcq, instructions="Choose the option that best matches the concept.", explanation=mcq_explanation, order=1),
        _q(c, "output_prediction", "medium", f"What is the output of this {c['subject']} snippet?", title=f"Predict the output for {name}", instructions="Read the snippet line by line, then write only the exact final output or visible result.", code=p["snippet"], code_snippet=p["snippet"], starter_code=p["snippet"], starterCode=p["snippet"], expected_output=p["expected_output"], expectedOutput=p["expected_output"], correct_answer=p["expected_output"], correctAnswer=p["expected_output"], expected_answer=p["expected_output"], explanation=f"The snippet demonstrates {name}; trace each line to reach the result.", order=2),
        _q(c, "debug_task", "medium", f"Find and fix the one clear bug in this {name} example.", title=f"Debug {name}", instructions="Identify the broken rule, rewrite the corrected snippet/command/query, and briefly name the bug.", buggy_code=p["buggy"], buggyCode=p["buggy"], starter_code=p["buggy"], starterCode=p["buggy"], bug_type=p["bug_type"], expected_fix=p["fix"], expected_answer={"expected_fix": p["fix"], "bug_type": p["bug_type"]}, correct_answer=p["fix"], correctAnswer=p["fix"], explanation=f"The bug is `{p['bug_type']}`. Correct version: {p['fix']}", order=3),
        _q(c, "syntax_completion", "medium", f"Fill the blank so the {name} example is valid.", title=f"Complete the syntax for {name}", instructions="Replace the blank marker `_____` with the missing syntax only.", code=p["incomplete"], starter_code=p["incomplete"], starterCode=p["incomplete"], expected_answer=p["missing"], correct_answer=p["missing"], correctAnswer=p["missing"], explanation=f"The missing syntax is `{p['missing']}` because it completes the concept pattern.", order=4),
        _q(c, "coding_prompt", "hard", p["coding"], task_type="coding_question", title=f"Build with {name}", instructions="Complete the task in the editor. " + _line_limit(difficulty), constraints=requirements + [_line_limit(difficulty)], starter_code="", starterCode="", expected_output=p["expected_output"], expectedOutput=p["expected_output"], expected_answer={"expected_behavior": p["expected"], "requirements": requirements}, rubric={"must_include": requirements, "expected_behavior": p["expected"]}, correct_answer=p["expected"], correctAnswer=p["expected"], explanation=f"A strong answer uses {name}, satisfies the requirements, and produces the stated behavior.", order=5),
        _q(c, "transfer_question", "medium", p["transfer"], title=f"Apply {name} in a new situation", instructions="Answer the concrete scenario in 2-3 sentences.", expected_answer={"expected_points": _expected_points(c["key_points"][0], c["real_world_use"], "clear application to scenario", "short explanation of usefulness")}, rubric={"keywords": [name, c["key_points"][0], c["real_world_use"]], "partial_credit": "Valid application/code with weak explanation should be partial, not weak."}, explanation=f"This applies {name} beyond the worked example.", order=6),
        _q(c, "real_world_application_question", "medium", real_world_prompt, title="Real-world application", instructions="Answer in 2-3 sentences.", expected_answer={"expected_points": real_world_points[:4]}, rubric={"keywords": real_world_points}, explanation=f"A strong answer connects {concept_label} to the scenario and the expected result.", order=7),
        _q(c, "challenge_question", "hard", f"Combine {name} with one related idea from the lesson. Produce a small solution and explain the reasoning that proves it works.", title=f"{name} reasoning challenge", instructions="Give the solution first, then 2-3 sentences explaining why it works. This is harder than transfer because it combines a rule, an example, and reasoning.", constraints=["Use the current concept explicitly.", "Mention one related key point or common mistake.", "Show the final output/result/decision."], expected_answer={"success_criteria": ["uses current concept", "combines another idea", "explains why the result is correct"]}, rubric={"success_criteria": ["uses current concept", "combines another idea", "explains why the result is correct"]}, explanation=f"The answer should reason from {name} and avoid the common mistake: {c['misconceptions'][0]}", order=7),
        _q(c, "explanation_check", "easy", f"Explain {name} in 2-3 sentences. Include what it does and one common mistake to avoid.", task_type="explanation", title=f"Explain {name}", instructions="Use your own words, but include the concept purpose and a mistake to avoid.", expected_answer={"rubric_keywords": [name, c["key_points"][0], c["misconceptions"][0]]}, rubric={"keywords": [name, c["key_points"][0], c["misconceptions"][0]]}, explanation=f"A good explanation names the concept, its purpose, and a common mistake.", order=8),
        _q(c, "flashcard_recall", "easy", f"Quick recall: what is the main idea of {name}?", title=f"{name} flashcard recall", instructions="Answer with one concise definition or rule.", expected_answer=correct_mcq, correct_answer=correct_mcq, correctAnswer=correct_mcq, explanation=f"Recall answer: {correct_mcq}", order=9),
        _q(c, "puzzle", "medium", f"Puzzle: arrange the steps for using {name} correctly.", title=f"{name} step puzzle", instructions="Order the steps from first to last.", puzzle_type="order", items=puzzle_items, correct_order=puzzle_order, expected_answer={"correct_order": puzzle_order}, explanation=f"Correct order: {', '.join(puzzle_order)}.", frontend_component="PuzzleQuestionCard", order=10),
    ]


def build_assessment_questions(subject: str | None, concept_id: str | None, difficulty: str = "easy") -> list[dict[str, Any]]:
    c = resolve_concept_content(subject, concept_id)
    questions = _make_task_set(c, difficulty if difficulty in {"easy", "medium", "hard"} else "easy")
    order = {"easy": 0, "medium": 1, "hard": 2}
    max_rank = order.get(difficulty, 0)
    filtered = [q for q in questions if order.get(q["difficulty"], 0) <= max_rank]
    return (filtered or questions)[:10]


def fallback_questions(subject: str | None, concept_id: str | None, difficulty: str = "easy") -> list[dict[str, Any]]:
    return build_assessment_questions(subject, concept_id, difficulty)


def assessment_payload(subject: str | None, concept_id: str | None, difficulty: str = "easy") -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    questions = build_assessment_questions(c["subject"], c["concept_id"], difficulty)
    coverage: dict[str, int] = {}
    for question in questions:
        coverage[question["question_type"]] = coverage.get(question["question_type"], 0) + 1
    return {**c, "difficulty": difficulty, "question_count": len(questions), "questions": questions, "assessment": questions, "coverage": coverage, "llm_generation": llm_status("assessment_generation")}


def build_hints(subject: str | None, concept_id: str | None, question_type: str | None = None, hint_count: int = 0) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    name = c["concept_name"]
    hints = {
        "hint": f"Focus on the meaning of {name}: {c['base_content']}",
        "small_hint": c["key_points"][0],
        "guided_hint": f"Step 1: read the prompt. Step 2: connect it to {name}. Step 3: use the example: {c['examples']}",
        "worked_example_hint": f"Worked example for {name}: {c['examples']}",
        "debug_hint": f"Check for this mistake: {c['misconceptions'][0]}",
        "syntax_hint": f"Use the valid pattern shown here: {c['examples']}",
        "output_prediction_hint": "Trace each line and keep only the final printed output.",
        "misconception_hint": f"Avoid this misconception: {c['misconceptions'][0]}",
        "next_step_hint": f"Try applying this key point: {c['key_points'][0]}",
        "analogy_hint": f"Think of {name} as a labeled container or organized slot for the needed information.",
    }
    qtype = str(question_type or "").lower()
    selected = "guided_hint"
    if "debug" in qtype:
        selected = "debug_hint"
    elif "syntax" in qtype:
        selected = "syntax_hint"
    elif "output" in qtype:
        selected = "output_prediction_hint"
    elif hint_count == 0:
        selected = "small_hint"
    return {**c, "available_hints": hints, "hint_type": selected, "hint_level": hint_count + 1, "hint_text": hints[selected], "worked_example": hints["worked_example_hint"], "llm_generation": llm_status("hint_generation")}


def build_feedback(subject: str | None, concept_id: str | None, is_correct: bool, score: float, question_type: str | None = None) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    label = "correct_answer_feedback" if is_correct else "partial_answer_feedback" if score >= 0.45 else "wrong_answer_feedback"
    typed = "debug_feedback" if "debug" in str(question_type or "") else "output_prediction_feedback" if "output" in str(question_type or "") else label
    feedback = {
        "feedback": f"Use {c['concept_name']} evidence from the lesson to judge the answer.",
        "correct_answer_feedback": f"Correct. Your answer matches the key idea: {c['key_points'][0]}",
        "wrong_answer_feedback": f"Review {c['concept_name']}. Anchor on this idea: {_short_definition(c)}",
        "partial_answer_feedback": f"You are close. Add the missing detail from: {c['key_points'][0]}",
        "debug_feedback": f"For debug tasks, find the broken rule first. Common issue: {c['misconceptions'][0]}",
        "output_prediction_feedback": "For output prediction, trace line by line and write only what is printed.",
        "next_step_feedback": "Next, use a different teaching view or a targeted flashcard before retrying.",
        "encouragement_feedback": "Keep the same concept in focus and use the hint trail before the next attempt.",
        "mistake_feedback": f"Mistake pattern to watch: {c['misconceptions'][0]}",
    }
    return {**c, "feedback_type": typed, "feedback_by_type": feedback, "feedback": feedback[typed], "voice_script": build_voice_scripts(c, "mistake_feedback_voice_script" if not is_correct else "encouragement_script").get("mistake_feedback_voice_script") or build_voice_scripts(c, "encouragement_script")["encouragement_script"], "source": "concept_resource_fallback"}


def build_flashcards(subject: str | None, concept_id: str | None) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    title = _clean_concept_title(c["concept_name"])
    question_title = title[:1].lower() + title[1:] if title else str(c["concept_name"]).lower()
    definition = _short_definition(c)
    cards = [
        {"id": f"fc-{c['concept_id']}-{kind}", "conceptId": c["concept_id"], "card_type": kind, "cardType": kind, "front": front, "back": back, "explanation": f"This card is grounded in {c['subject']} / {c['concept_name']}: {c['key_points'][0]}", "difficulty": diff, "due": True}
        for kind, front, back, diff in [
            ("concept_recall_flashcard", f"What is {question_title}?", definition, "easy"),
            ("misconception_flashcard", "What mistake should you avoid?", c["misconceptions"][0], "medium"),
            ("example_flashcard", f"Give an example of {title}.", _sentence_limit(c["examples"], 2, 220), "easy"),
            ("debug_flashcard", f"How do you debug a {title} mistake?", f"Find the broken rule, compare with {c['key_points'][0]}, then correct it.", "medium"),
            ("syntax_flashcard", f"What syntax or pattern represents {title}?", _sentence_limit(c["examples"], 2, 220), "easy"),
            ("personal_flashcards", f"What should I personally remember about {title}?", c["key_points"][0], "medium"),
            ("spaced_repetition_card", f"Spaced review: summarize {title}.", definition, "easy"),
        ]
    ]
    return {**c, "flashcards": cards, "available_flashcard_types": FLASHCARD_TYPES, "llm_generation": llm_status("flashcard_generation")}


def build_mindmap(subject: str | None, concept_id: str | None) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    practice_prompt = c.get("practice_prompt") or c.get("practice") or f"Try one short question about {c['concept_name']}."
    base_nodes = [
        {"id": "definition", "title": "Definition", "body": c["base_content"], "color": "#2563eb", "x": 50, "y": 16},
        {"id": "examples", "title": "Examples", "body": c["examples"], "color": "#16a34a", "x": 82, "y": 32},
        {"id": "key_points", "title": "Key Points", "body": "; ".join(c["key_points"]), "color": "#7c3aed", "x": 78, "y": 72},
        {"id": "misconceptions", "title": "Misconceptions", "body": "; ".join(c["misconceptions"]), "color": "#e11d48", "x": 22, "y": 72},
        {"id": "real_world", "title": "Real-world Use", "body": c["real_world_use"], "color": "#0891b2", "x": 18, "y": 32},
        {"id": "related", "title": "Related Concept", "body": c["next_concept_link"], "color": "#ca8a04", "x": 50, "y": 90},
    ]
    comparison = [
        {"id": "center", "title": c["concept_name"], "body": "Current selected concept", "color": "#2563eb", "x": 50, "y": 50},
        {"id": "compare_a", "title": "Concept vs Example", "body": f"{c['base_content']} vs {c['examples']}", "color": "#16a34a", "x": 25, "y": 35},
        {"id": "compare_b", "title": "Correct vs Mistake", "body": f"{c['key_points'][0]} vs {c['misconceptions'][0]}", "color": "#e11d48", "x": 75, "y": 35},
    ]
    misconception = [
        {"id": "center", "title": c["concept_name"], "body": "Misconception review", "color": "#2563eb", "x": 50, "y": 50},
        {"id": "mistake", "title": "Common Mistake", "body": "; ".join(c["misconceptions"]), "color": "#e11d48", "x": 24, "y": 45},
        {"id": "correction", "title": "Correction", "body": "; ".join(c["key_points"]), "color": "#16a34a", "x": 76, "y": 45},
        {"id": "practice", "title": "Practice", "body": practice_prompt, "color": "#ca8a04", "x": 50, "y": 78},
    ]
    variants = {
        "mindmap": base_nodes,
        "concept_mindmap": base_nodes,
        "comparison_mindmap": comparison,
        "revision_mindmap": base_nodes[:4],
        "misconception_mindmap": misconception,
    }
    return {**c, "title": c["concept_name"], "center": c["concept_name"], "nodes": base_nodes, "mindmap_variants": variants, "available_mindmap_types": list(variants.keys()), "llm_generation": llm_status("mindmap_generation")}


def build_notebook(subject: str | None, concept_id: str | None, learner_id: str) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    short_base = str(c["base_content"]).split(".")[0].strip()
    if len(short_base.split()) > 32:
        short_base = " ".join(short_base.split()[:32]).rstrip(",;:")
    return {
        **c,
        "learnerId": learner_id,
        "conceptId": c["concept_id"],
        "summary": f"Quick summary for {c['concept_name']}: {short_base}.",
        "weakPoints": c["misconceptions"],
        "mistakeSummary": [f"Common mistake: {item}" for item in c["misconceptions"]],
        "mistakes": [f"Watch for: {item}" for item in c["misconceptions"]],
        "pastDoubts": [],
        "savedFlashcards": [f"What is {c['concept_name']}?", "What mistake should I avoid?"],
        "revisionPlan": ["Review definition", "Try output/debug if relevant", "Answer a mixed assessment"],
        "comebackSummary": f"Return to {c['concept_name']} with a quick revision and one mixed question.",
        "returningLearnerSummary": f"Start with a short {c['concept_name']} recap before the next assessment.",
        "progressInsight": f"Progress should stay tied to {c['subject']} / {c['concept_name']}.",
        "notebook_task_types": ["notebook_summary", "mistake_summary", "revision_plan", "comeback_summary", "returning_learner_summary", "progress_insight"],
    }


def build_doubt_answer(subject: str | None, concept_id: str | None, doubt_text: str | None) -> dict[str, Any]:
    c = resolve_concept_content(subject, concept_id)
    text = str(doubt_text or "").lower()
    dtype = "debug_doubt_answer" if "debug" in text or "error" in text else "syntax_doubt_answer" if "syntax" in text else "output_doubt_answer" if "output" in text else "example_request_answer" if "example" in text else "concept_doubt_answer"
    return {
        **c,
        "intent": dtype,
        "doubt_type": dtype,
        "answer": f"For {c['concept_name']}: {c['base_content']} Example: {c['examples']} Key point: {c['key_points'][0]}",
        "example": {"title": f"{c['concept_name']} example", "code": c["examples"], "explanation": c["base_content"]},
        "follow_up_check": {"questionType": "explanation_check", "question": f"Explain {c['concept_name']} in one sentence.", "correctAnswer": c["base_content"]},
        "available_doubt_types": DOUBT_TYPES,
        "voice_script": build_voice_scripts(c, "doubt_explanation_voice_script")["doubt_explanation_voice_script"],
        "llm_generation": llm_status("doubt_answer_generation"),
    }


def build_voice_scripts(content: dict[str, Any], preferred: str | None = None) -> dict[str, str]:
    c = content
    scripts = {
        "voice_script": f"Let's stay with {c['concept_name']} in {c['subject']}.",
        "teaching_voice_script": f"We are learning {c['concept_name']}. First understand the idea, then connect it to the example.",
        "revision_voice_script": f"Quick revision: {c['concept_name']} means {c['base_content']}",
        "mistake_feedback_voice_script": f"That answer needs one fix. Look again at {c['concept_name']} and the common mistake.",
        "doubt_explanation_voice_script": f"Your doubt is about {c['concept_name']}. I will answer using this concept only.",
        "encouragement_script": f"Good. Keep using the same {c['concept_name']} idea for the next step.",
        "next_step_guidance_script": f"Next, try a mixed question on {c['concept_name']}.",
        "concept_intro_voice_script": f"Welcome to {c['concept_name']} in {c['subject']}.",
    }
    if preferred:
        scripts["selected_script"] = scripts.get(preferred, scripts["voice_script"])
    return scripts


def llm_status(task_type: str, service: str = "fallback") -> dict[str, Any]:
    source = "cognitutor_lm_guarded" if service == "cognitutor" else "concept_resource_fallback"
    return {
        "service": "CogniTutorLM" if service == "cognitutor" else "RAG|fallback",
        "source": source,
        "generation_source": source,
        "task_type": task_type,
        "model_generated": service == "cognitutor",
        "fallback_used": service != "cognitutor",
        "format_valid": True,
    }
