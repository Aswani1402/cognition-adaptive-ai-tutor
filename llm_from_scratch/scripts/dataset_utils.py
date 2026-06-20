"""
CogniTutorLM Dataset Builder — Utility Functions
Project: Cognition-Adaptive AI Tutor (From-Scratch LLM)
Author Reference: Aswini Ayappan

Usage: Import into your main dataset_builder.py
All functions are standalone and dependency-light (stdlib only).
"""
import sys
import json
import re
import subprocess
from collections import Counter
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

TASK_TOKENS = {
    # Teaching content
    "explanation":                  "<task_explanation>",
    "definition_view":              "<task_definition>",
    "simple_example_view":          "<task_simple_example>",
    "step_by_step_view":            "<task_step_by_step>",
    "analogy_view":                 "<task_analogy>",
    "code_view":                    "<task_code_view>",
    "misconception_view":           "<task_misconception>",
    "debug_view":                   "<task_debug_view>",
    "output_prediction_view":       "<task_output_prediction_view>",
    "transfer_view":                "<task_transfer_view>",
    "challenge_view":               "<task_challenge_view>",
    "revision_summary_view":        "<task_revision_summary_view>",
    "comparison_view":              "<task_comparison>",
    "real_world_connection_view":   "<task_real_world>",
    # Assessment
    "mcq":                          "<task_mcq>",
    "debug_task":                   "<task_debug>",
    "output_prediction":            "<task_output_prediction>",
    "transfer_question":            "<task_transfer>",
    "challenge_question":           "<task_challenge>",
    "explanation_check":            "<task_explanation_check>",
    "syntax_completion":            "<task_syntax_completion>",
    "coding_prompt":                "<task_coding_prompt>",
    "code_reasoning_task":          "<task_code_reasoning>",
    "fill_in_the_blank":            "<task_fill_blank>",
    "true_or_false":                "<task_true_false>",
    # Revision
    "revision_note":                "<task_revision_note>",
    "revision_summary":             "<task_revision>",
    "weakness_review":              "<task_weakness_review>",
    "daily_review":                 "<task_daily_review>",
    "personal_revision_plan":       "<task_revision_plan>",
    "recommended_revision_views":   "<task_recommended_views>",
    "spaced_repetition_card":       "<task_spaced_repetition>",
    # Flashcards
    "flashcard":                    "<task_flashcard>",
    "concept_recall_flashcard":     "<task_concept_recall>",
    "misconception_flashcard":      "<task_misconception_flashcard>",
    "example_flashcard":            "<task_example_flashcard>",
    "debug_flashcard":              "<task_debug_flashcard>",
    "personal_flashcards":          "<task_personal_flashcards>",
    "syntax_flashcard":             "<task_syntax_flashcard>",
    # Mindmaps
    "mindmap":                      "<task_mindmap>",
    "concept_mindmap":              "<task_concept_mindmap>",
    "comparison_mindmap":           "<task_comparison_mindmap>",
    # Feedback
    "feedback":                     "<task_feedback>",
    "correct_answer_feedback":      "<task_correct_feedback>",
    "wrong_answer_feedback":        "<task_wrong_feedback>",
    "partial_answer_feedback":      "<task_partial_feedback>",
    "debug_feedback":               "<task_debug_feedback>",
    "output_prediction_feedback":   "<task_output_feedback>",
    "next_step_feedback":           "<task_next_step_feedback>",
    "encouragement_feedback":       "<task_encouragement>",
    # Hints
    "hint":                         "<task_hint>",
    "small_hint":                   "<task_small_hint>",
    "guided_hint":                  "<task_guided_hint>",
    "worked_example_hint":          "<task_worked_hint>",
    "debug_hint":                   "<task_debug_hint>",
    "syntax_hint":                  "<task_syntax_hint>",
    "output_prediction_hint":       "<task_output_hint>",
    "misconception_hint":           "<task_misconception_hint>",
    "next_step_hint":               "<task_next_step_hint>",
    "analogy_hint":                 "<task_analogy_hint>",
    # Doubt answers
    "doubt_answer":                 "<task_doubt>",
    "concept_doubt_answer":         "<task_concept_doubt>",
    "syntax_doubt_answer":          "<task_syntax_doubt>",
    "debug_doubt_answer":           "<task_debug_doubt>",
    "output_doubt_answer":          "<task_output_doubt>",
    "example_request_answer":       "<task_example_request>",
    "revision_doubt_answer":        "<task_revision_doubt>",
    "next_step_doubt_answer":       "<task_next_step_doubt>",
    "comparison_doubt_answer":      "<task_comparison_doubt>",
    # NotebookLM memory
    "notebook_summary":             "<task_notebook_summary>",
    "mistake_summary":              "<task_mistake_summary>",
    "revision_plan":                "<task_revision_plan>",
    "comeback_summary":             "<task_comeback_summary>",
    "returning_learner_summary":    "<task_returning_learner>",
    "progress_insight":             "<task_progress_insight>",
    # Practice/challenge
    "practice_question":            "<task_practice>",
    "challenge_question":           "<task_challenge>",
    "transfer_task":                "<task_transfer_task>",
    "real_world_application_question": "<task_real_world_q>",
    "debug_challenge":              "<task_debug_challenge>",
    "output_prediction_challenge":  "<task_output_challenge>",
    "code_reasoning_task":          "<task_code_reasoning>",
    "multi_step_challenge":         "<task_multi_step>",
    # Voice
    "voice_script":                 "<task_voice>",
    "teaching_voice_script":        "<task_teaching_voice>",
    "revision_voice_script":        "<task_revision_voice>",
    "mistake_feedback_voice_script":"<task_mistake_voice>",
    "doubt_explanation_voice_script":"<task_doubt_voice>",
    "encouragement_script":         "<task_encouragement_voice>",
    "next_step_guidance_script":    "<task_next_step_voice>",
    "concept_intro_voice_script":   "<task_intro_voice>",
}

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

STYLE_TOKENS = [
    "style_code", "style_analogy", "style_step_by_step",
    "style_revision", "style_misconception", "style_challenge",
    "style_voice", "style_compare",
]

# Valid operations per concept — never invent operations outside this list
CONCEPT_VALID_OPERATIONS = {
    "D3": ["push()", "pop()", "peek()", "is_empty()", "size()"],
    "D4": ["enqueue()", "dequeue()", "front()", "rear()", "is_empty()"],
    "D2": ["append()", "prepend()", "delete()", "traverse()", "search()", "node.next", "head"],
    "D5": ["insert()", "search()", "delete()", "inorder()", "preorder()", "postorder()"],
    "D7": ["add_vertex()", "add_edge()", "BFS()", "DFS()"],
    "D6": ["add()", "remove()", "union()", "intersection()", "difference()", "issubset()"],
    "P4": ["range()", "enumerate()", "zip()", "break", "continue", "for...in", "while"],
    "P5": ["def", "return", "*args", "**kwargs", "lambda"],
    "P6": ["class", "__init__", "self", "super()", "inheritance", "@classmethod", "@staticmethod"],
    "S4": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN", "ON", "CROSS JOIN"],
    "S6": ["OVER()", "PARTITION BY", "ORDER BY", "RANK()", "ROW_NUMBER()", "LEAD()", "LAG()"],
    "S7": ["WITH", "AS", "CTE", "WITH RECURSIVE"],
    "G3": ["git add", "git commit -m", "git log", "git log --oneline", "git show", "git diff"],
    "G4": ["git branch", "git checkout -b", "git switch", "git merge", "git branch -d"],
}

GENERIC_FEEDBACK_PHRASES = [
    "use the valid operation",
    "check your syntax",
    "refer to documentation",
    "fix the error",
    "try again",
    "that is wrong",
    "incorrect",
    "use the correct method",
    "see the documentation",
]

SQL_CONCEPT_QUERY_SCAFFOLDS = {
    "S2": "SELECT col1, col2 FROM table_name WHERE condition;",
    "S3": "SELECT * FROM table_name WHERE col > value AND col2 = 'x';",
    "S4": "SELECT a.col, b.col\nFROM table_a a\nJOIN table_b b ON a.id = b.a_id;",
    "S5": "-- Before index:\nEXPLAIN SELECT * FROM table_name WHERE col = value;\n\n-- Create index:\nCREATE INDEX idx_col ON table_name(col);",
    "S6": "SELECT col,\n       RANK() OVER (PARTITION BY group_col ORDER BY measure DESC) AS rnk\nFROM table_name;",
    "S7": "WITH cte_name AS (\n    SELECT col1, col2 FROM table_name WHERE condition\n)\nSELECT * FROM cte_name;",
}

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE LOADER
# ─────────────────────────────────────────────────────────────────────────────

TASK_TEMPLATES: dict[str, dict] = {
    "debug_task": {
        "bug_line": "",
        "bug_type": "",
        "bug_explanation": "",
        "fixed_code": "",
        "why_it_works": "",
        "distractor_fixes": [],
        "correct_output": "",
        "concept_reinforcement": ""
    },
    "output_prediction": {
        "code": "",
        "question": "",
        "options": {"A": "", "B": "", "C": "", "D": ""},
        "correct": "",
        "trace": [],
        "common_wrong_answer": "",
        "why_wrong": ""
    },
    "mindmap": {
        "root": "",
        "branches": [],
        "key_rule": "",
        "common_misconception": ""
    },
    "flashcard": {
        "front": "",
        "back": "",
        "tags": [],
        "difficulty": ""
    },
    "misconception_flashcard": {
        "misconception": "",
        "why_students_think_this": "",
        "correction": "",
        "reinforcement_code": ""
    },
    "feedback": {
        "task_ref": "",
        "learner_answer": "",
        "verdict": "",
        "wrong_answer_feedback": {
            "what_is_wrong": "",
            "correct_syntax": "",
            "rule": "",
            "next_step": ""
        },
        "partial_answer_feedback": {
            "what_is_right": "",
            "what_is_missing": "",
            "nudge": ""
        },
        "correct_answer_feedback": {
            "praise": "",
            "reinforcement": "",
            "next_step": ""
        }
    },
    "voice_script": {
        "script_type": "",
        "concept": "",
        "subject": "",
        "tone": "friendly, clear, conversational",
        "script": "",
        "pause_markers": [],
        "duration_estimate_seconds": 0,
        "forbidden_phrases": ["as mentioned earlier", "in conclusion", "obviously", "basically"]
    },
    "hint": {
        "task_ref": "",
        "hints": [
            {"level": "small_hint", "text": ""},
            {"level": "guided_hint", "text": ""},
            {"level": "analogy_hint", "text": ""},
            {"level": "worked_example_hint", "text": ""}
        ]
    },
    "syntax_completion": {
        "concept": "",
        "subject": "",
        "task_description": "",
        "incomplete_code": "",
        "blanks": [],
        "completed_code": "",
        "output": "",
        "key_rule": "",
        "common_mistake": ""
    },
    "mcq": {
        "question": "",
        "options": {"A": "", "B": "", "C": "", "D": ""},
        "correct": "",
        "explanation": {"A": "", "B": "", "C": "", "D": ""},
        "difficulty": "",
        "concept_tested": ""
    },
    "notebook_summary": {
        "learner_id": "",
        "session_date": "",
        "concepts_covered": [],
        "notebook_summary": "",
        "mistake_summary": {
            "repeated_mistake": "",
            "root_cause": "",
            "correction": ""
        },
        "weakness_review": [],
        "comeback_summary": "",
        "daily_review": "",
        "personal_revision_plan": {}
    },
}


def load_task_template(task_type: str) -> dict:
    """Returns a copy of the required output field schema for a task type."""
    import copy
    return copy.deepcopy(TASK_TEMPLATES.get(task_type, {}))


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE ID GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

_sample_counters: dict[str, int] = {}


def generate_sample_id(concept_id: str, task_type: str, difficulty: str) -> str:
    """
    Generates unique, sortable sample IDs.
    Format: {concept_id}_{task_type}_{difficulty}_{sequence:03d}
    Example: D3_debug_task_medium_001
    """
    key = f"{concept_id}_{task_type}_{difficulty}"
    _sample_counters[key] = _sample_counters.get(key, 0) + 1
    return f"{key}_{_sample_counters[key]:03d}"


# ─────────────────────────────────────────────────────────────────────────────
# INPUT PROMPT ASSEMBLER
# ─────────────────────────────────────────────────────────────────────────────

def build_input_prompt(
    task_type: str,
    difficulty: str,
    style: str,
    concept: str,
    subject: str,
    content_fields: dict[str, str],
    extra_context: str = ""
) -> str:
    """
    Assembles the structured input string for a training sample.
    Maps task + difficulty + style to control tokens + concept content.

    Args:
        task_type:      e.g. "debug_task"
        difficulty:     "easy" | "medium" | "hard"
        style:          e.g. "style_code"
        concept:        e.g. "Stack"
        subject:        e.g. "Data Structures"
        content_fields: dict of source fields used (base_content, examples, etc.)
        extra_context:  optional buggy code block or table to append

    Returns:
        Formatted input string with control tokens.
    """
    task_token = TASK_TOKENS.get(task_type, f"<task_{task_type}>")
    diff_token = f"<{difficulty}>"
    style_token = f"<{style}>"

    content_block = "\n".join(
        f"{k.replace('_', ' ').title()}: {v}"
        for k, v in content_fields.items() if v
    )

    parts = [
        f"{task_token} {diff_token} {style_token}",
        f"Concept: {concept}",
        f"Subject: {subject}",
        "",
        content_block,
    ]
    if extra_context:
        parts += ["", extra_context]

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# SQL SCAFFOLD SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

def get_sql_query_scaffold(concept_id: str) -> str:
    """
    Returns a concept-appropriate SQL scaffold string.
    Prevents the same SELECT pattern being reused across SQL concepts.
    Raises ValueError for unknown SQL concept IDs.
    """
    scaffold = SQL_CONCEPT_QUERY_SCAFFOLDS.get(concept_id)
    if scaffold is None:
        raise ValueError(
            f"No SQL scaffold defined for concept_id '{concept_id}'. "
            f"Valid SQL concept IDs: {list(SQL_CONCEPT_QUERY_SCAFFOLDS.keys())}"
        )
    return scaffold


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON OUTPUT VERIFIER
# ─────────────────────────────────────────────────────────────────────────────

def verify_python_output(code: str, expected_output: str, timeout: int = 5) -> dict:
    """
    Runs code in a subprocess and checks if actual output matches expected.

    WARNING: Only pass hand-written, reviewed code — never raw user input.

    Returns:
        dict with keys: verified (bool), actual_output (str), match (bool), error (str|None)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout
        )
        actual = result.stdout.strip()
        stderr = result.stderr.strip()
        return {
            "verified": True,
            "actual_output": actual,
            "match": actual == expected_output.strip(),
            "error": stderr if stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"verified": False, "actual_output": "TIMEOUT", "match": False, "error": "TimeoutExpired"}
    except FileNotFoundError:
        return {"verified": False, "actual_output": "", "match": False, "error": "python3 not found in PATH"}
    except Exception as e:
        return {"verified": False, "actual_output": "", "match": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# MINDMAP VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def validate_mindmap(mindmap_dict: dict, min_branches: int = 6, min_children: int = 4) -> dict:
    """
    Validates a mindmap output has sufficient depth and breadth.

    Args:
        mindmap_dict:  The mindmap output dict.
        min_branches:  Minimum number of top-level branches (default: 6).
        min_children:  Minimum children per branch (default: 4).

    Returns:
        dict with: valid (bool), errors (list[str])
    """
    errors = []
    branches = mindmap_dict.get("branches", [])

    if not mindmap_dict.get("root"):
        errors.append("Missing 'root' field.")

    if len(branches) < min_branches:
        errors.append(
            f"Only {len(branches)} branch(es) found. Minimum required: {min_branches}."
        )

    for branch in branches:
        name = branch.get("name", "<unnamed>")
        children = branch.get("children", [])
        if len(children) < min_children:
            errors.append(
                f"Branch '{name}' has {len(children)} child(ren). Minimum: {min_children}."
            )

    if not mindmap_dict.get("key_rule"):
        errors.append("Missing 'key_rule' field.")

    if not mindmap_dict.get("common_misconception"):
        errors.append("Missing 'common_misconception' field.")

    return {"valid": len(errors) == 0, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
# REPETITION DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_repetition(text: str, ngram_size: int = 3, threshold: int = 3) -> dict:
    """
    Detects repeated n-grams in an output string.
    A 3-gram appearing 3+ times in any output is a quality failure.

    Returns:
        dict with: repetition_detected (bool), flagged_phrases (dict phrase→count)
    """
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < ngram_size:
        return {"repetition_detected": False, "flagged_phrases": {}}

    ngrams = [' '.join(words[i:i + ngram_size]) for i in range(len(words) - ngram_size + 1)]
    counts = Counter(ngrams)
    flagged = {phrase: count for phrase, count in counts.items() if count >= threshold}
    return {
        "repetition_detected": bool(flagged),
        "flagged_phrases": flagged
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRUNCATION DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

SHORT_EXCEPTIONS = {'a', 'i', 'or', 'as', 'is', 'in', 'on', 'to', 'do', 'no', 'ok'}
VALID_END_CHARS = set('.!?:})]`"\';')


def detect_truncation(text: str) -> dict:
    """
    Detects outputs ending mid-word or without proper closing punctuation.

    Returns:
        dict with: truncated (bool), last_char (str), last_word (str), reason (str)
    """
    stripped = text.strip()
    if not stripped:
        return {"truncated": True, "last_char": "", "last_word": "", "reason": "Empty output"}

    last_char = stripped[-1]
    words = stripped.split()
    last_word = words[-1] if words else ""

    ends_badly = last_char not in VALID_END_CHARS
    suspicious_word = (
        len(last_word) < 3
        and last_word.lower() not in SHORT_EXCEPTIONS
        and not last_word.isdigit()
    )

    truncated = ends_badly or suspicious_word
    if suspicious_word:
        reason = f"Ends with suspicious short word: '{last_word}'"
    elif ends_badly:
        reason = f"Ends without closing punctuation (last char: '{last_char}')"
    else:
        reason = "OK"

    return {
        "truncated": truncated,
        "last_char": last_char,
        "last_word": last_word,
        "reason": reason
    }


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC FEEDBACK PHRASE CHECKER
# ─────────────────────────────────────────────────────────────────────────────

def check_generic_feedback(output_text: str) -> dict:
    """
    Detects vague, generic feedback phrases that reduce training quality.

    Returns:
        dict with: has_generic (bool), found_phrases (list[str])
    """
    lower = output_text.lower()
    found = [phrase for phrase in GENERIC_FEEDBACK_PHRASES if phrase in lower]
    return {
        "has_generic": bool(found),
        "found_phrases": found
    }


# ─────────────────────────────────────────────────────────────────────────────
# REQUIRED FIELDS CHECKER
# ─────────────────────────────────────────────────────────────────────────────

def check_required_fields(output: dict, task_type: str) -> dict:
    """
    Checks that a task output contains all required fields from its template.

    Returns:
        dict with: all_present (bool), missing_fields (list[str])
    """
    template = load_task_template(task_type)
    if not template:
        return {"all_present": True, "missing_fields": [], "note": f"No template defined for '{task_type}'"}

    missing = [field for field in template if field not in output]
    return {
        "all_present": len(missing) == 0,
        "missing_fields": missing
    }


# ─────────────────────────────────────────────────────────────────────────────
# FULL QUALITY GATE
# ─────────────────────────────────────────────────────────────────────────────

def quality_gate(sample: dict) -> dict:
    """
    Runs all validation checks on a single training sample dict.
    Returns a pass/fail result with detailed failure reasons.

    Args:
        sample: A complete training sample dict with keys:
                sample_id, subject, concept_id, topic, task_type,
                difficulty, style, input, output, source_fields_used

    Returns:
        dict with: sample_id (str), passed (bool), failures (list[str])
    """
    failures = []
    task_type = sample.get("task_type", "")
    output = sample.get("output", {})
    output_text = json.dumps(output, ensure_ascii=False)

    # 1. Truncation
    trunc = detect_truncation(output_text)
    if trunc["truncated"]:
        failures.append(f"TRUNCATION — {trunc['reason']}")

    # 2. Repetition
    rep = detect_repetition(output_text)
    if rep["repetition_detected"]:
        phrases = list(rep["flagged_phrases"].keys())[:3]
        failures.append(f"REPETITION — flagged: {phrases}")

    # 3. Mindmap depth
    if task_type in ("mindmap", "concept_mindmap", "comparison_mindmap"):
        mm_check = validate_mindmap(output)
        if not mm_check["valid"]:
            failures.extend([f"MINDMAP — {e}" for e in mm_check["errors"]])

    # 4. Generic feedback phrases
    if task_type in ("feedback", "wrong_answer_feedback", "debug_feedback",
                     "correct_answer_feedback", "partial_answer_feedback",
                     "encouragement_feedback"):
        gf = check_generic_feedback(output_text)
        if gf["has_generic"]:
            failures.append(f"GENERIC FEEDBACK — found: {gf['found_phrases']}")

    # 5. Required fields
    rf = check_required_fields(output, task_type)
    if not rf["all_present"]:
        failures.append(f"MISSING FIELDS — {rf['missing_fields']}")

    # 6. SQL concept diversity: warn if S2 scaffold detected for S4–S7
    if sample.get("concept_id") in ("S4", "S5", "S6", "S7"):
        if isinstance(output, dict):
            code_field = (
                output.get("query") or output.get("buggy_code") or
                output.get("code") or output.get("fixed_query") or ""
            )
            if code_field and not any(
                kw in code_field.upper()
                for kw in ["JOIN", "OVER", "WITH", "CREATE INDEX", "EXPLAIN"]
            ):
                failures.append(
                    f"SQL DIVERSITY — concept {sample.get('concept_id')} "
                    f"appears to use a generic SELECT without concept-specific keywords."
                )

    # 7. Voice script format check
    if task_type in ("voice_script", "teaching_voice_script", "revision_voice_script",
                     "mistake_feedback_voice_script", "encouragement_script"):
        script = output.get("script", "") if isinstance(output, dict) else ""
        forbidden_in_voice = ["```", "##", "- ", "* ", "**"]
        found_md = [f for f in forbidden_in_voice if f in script]
        if found_md:
            failures.append(f"VOICE FORMAT — script contains markdown: {found_md}")

    # 8. Flashcard front must be a question or fill-blank
    if task_type in ("flashcard", "concept_recall_flashcard", "syntax_flashcard"):
        front = output.get("front", "") if isinstance(output, dict) else ""
        if front and not (front.strip().endswith("?") or "_____" in front):
            failures.append(
                "FLASHCARD FORMAT — 'front' should be a question (end with ?) or fill-in-the-blank."
            )

    return {
        "sample_id": sample.get("sample_id", "unknown"),
        "passed": len(failures) == 0,
        "failures": failures
    }


# ─────────────────────────────────────────────────────────────────────────────
# BATCH QUALITY RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_quality_gate_on_file(filepath: str, output_report_path: str | None = None) -> dict:
    """
    Loads a JSONL dataset file and runs quality_gate on every sample.
    Writes a report JSON if output_report_path is provided.

    Args:
        filepath:           Path to .jsonl training file (one JSON object per line).
        output_report_path: Optional path to write the report JSON.

    Returns:
        dict with: total (int), passed (int), failed (int), failures (list[dict])
    """
    passed_samples = []
    failed_samples = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as e:
                failed_samples.append({
                    "line": line_number,
                    "sample_id": "parse_error",
                    "passed": False,
                    "failures": [f"JSON parse error: {e}"]
                })
                continue

            result = quality_gate(sample)
            result["line"] = line_number
            if result["passed"]:
                passed_samples.append(result)
            else:
                failed_samples.append(result)

    report = {
        "total": len(passed_samples) + len(failed_samples),
        "passed": len(passed_samples),
        "failed": len(failed_samples),
        "pass_rate": round(len(passed_samples) / max(1, len(passed_samples) + len(failed_samples)) * 100, 1),
        "failures": failed_samples
    }

    if output_report_path:
        with open(output_report_path, "w", encoding="utf-8") as out:
            json.dump(report, out, indent=2, ensure_ascii=False)
        print(f"Quality report written to: {output_report_path}")

    print(f"\nQuality Gate Summary")
    print(f"  Total samples : {report['total']}")
    print(f"  Passed        : {report['passed']} ({report['pass_rate']}%)")
    print(f"  Failed        : {report['failed']}")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# DATASET STATS PRINTER
# ─────────────────────────────────────────────────────────────────────────────

def print_dataset_coverage(filepath: str) -> None:
    """
    Reads a JSONL dataset file and prints coverage stats:
    - samples per concept_id
    - samples per task_type
    - samples per difficulty
    """
    concept_counts: dict[str, int] = Counter()
    task_counts: dict[str, int] = Counter()
    diff_counts: dict[str, int] = Counter()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
                concept_counts[s.get("concept_id", "unknown")] += 1
                task_counts[s.get("task_type", "unknown")] += 1
                diff_counts[s.get("difficulty", "unknown")] += 1
            except json.JSONDecodeError:
                continue

    print("\n── Concept Coverage ──")
    for cid, count in sorted(concept_counts.items()):
        print(f"  {cid}: {count} samples")

    print("\n── Task Type Coverage ──")
    for task, count in sorted(task_counts.items(), key=lambda x: -x[1]):
        print(f"  {task}: {count}")

    print("\n── Difficulty Distribution ──")
    total = sum(diff_counts.values())
    for diff in ["easy", "medium", "hard"]:
        count = diff_counts.get(diff, 0)
        pct = round(count / max(1, total) * 100, 1)
        print(f"  {diff}: {count} ({pct}%)")


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE USAGE (run directly for quick test)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test sample ID generation
    print(generate_sample_id("D3", "debug_task", "medium"))   # D3_debug_task_medium_001
    print(generate_sample_id("D3", "debug_task", "medium"))   # D3_debug_task_medium_002
    print(generate_sample_id("S4", "output_prediction", "hard"))  # S4_output_prediction_hard_001

    # Test truncation detector
    print(detect_truncation("The stack uses LIFO"))        # Ends without punctuation
    print(detect_truncation("The stack uses LIFO."))       # OK
    print(detect_truncation("LEFT JO"))                    # Short word flag

    # Test repetition detector
    print(detect_repetition("Stack. Stack. Stack. A Stack is a Stack and Stack."))

    # Test mindmap validator
    bad_mm = {
        "root": "HTML Tags",
        "branches": [
            {"name": "Structure", "children": ["html", "body"]},
            {"name": "Text", "children": ["p", "h1"]}
        ]
    }
    print(validate_mindmap(bad_mm))

    # Test quality gate
    test_sample = {
        "sample_id": "D3_debug_task_medium_001",
        "subject": "Data Structures",
        "concept_id": "D3",
        "topic": "Stack",
        "task_type": "debug_task",
        "difficulty": "medium",
        "style": "style_code",
        "input": "<task_debug> <medium> <style_code>\nConcept: Stack",
        "output": {
            "bug_line": "return self.items.pop(0)",
            "bug_type": "wrong_index_argument",
            "bug_explanation": "pop(0) removes the first element, not the top.",
            "fixed_code": "return self.items.pop()",
            "why_it_works": "pop() with no argument removes the last element — the stack top.",
            "distractor_fixes": [],
            "correct_output": "30",
            "concept_reinforcement": "Stack top = last index in Python list."
        },
        "source_fields_used": ["base_content", "examples", "misconceptions"],
    }
    print(quality_gate(test_sample))
