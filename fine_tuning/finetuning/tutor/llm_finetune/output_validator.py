from __future__ import annotations

import re
from typing import Dict, List


BAD_PATTERNS = [

    "PUT_HREF",
    "Task_instance",
    "Diff_diff",
    "Diff_message",
    "Hook Hook",
    "HREF_HREF",
    "application/x-www-form-urlencoded",
    "base_url",
    "https://",
    "http://",
]


def has_repetition(text: str) -> bool:

    tokens = re.findall(
        r"\b\w+\b",
        text.lower()
    )

    if len(tokens) < 8:
        return False

    joined_tokens = " ".join(tokens)

    for i in range(len(tokens) - 3):

        chunk = tokens[i:i + 3]

        phrase = " ".join(chunk)

        count = joined_tokens.count(phrase)

        if count >= 4:
            return True

    return False


def infer_debug_domain(concept: str) -> str:
    c = (concept or "").lower()
    if "sql" in c or "select" in c or "join" in c or "where" in c:
        return "sql"
    if "html" in c or "semantic" in c or "tags" in c or "forms" in c:
        return "html"
    if "git" in c or "branch" in c or "merge" in c or "commit" in c:
        return "git"
    if (
        "stack" in c
        or "queue" in c
        or "tree" in c
        or "graph" in c
        or "linked list" in c
        or "hash" in c
        or "array" in c
        or "data structure" in c
        or "binary search" in c
    ):
        return "data_structures"
    if "python" in c:
        return "python"
    return "python"


def wrong_domain_debug(concept: str, text: str) -> bool:
    if not text.strip():
        return False
    low = text.lower()
    domain = infer_debug_domain(concept)

    if domain == "html":
        if "```python" in text[:2000]:
            return True
        if ("for i in range" in low or "def " in low) and "<" not in text:
            return True

    elif domain == "sql":
        if "for i in range" in low or ("print(" in low and "select" not in low):
            return True

    elif domain == "git":
        py_strong = "for i in range" in low or ("def " in low and "git" not in low)
        git_weak = not any(k in low for k in ("git", "merge", "commit", "branch", "push", "pull"))
        if py_strong and git_weak:
            return True

    elif domain == "python":
        if "```html" in low or "<!doctype" in low:
            return True

    return False


def validate_output(
    text: str,
    concept: str = "",
    task_type: str = "",
) -> Dict[str, object]:

    issues: List[str] = []

    blocking_issues: List[str] = []

    clean = (text or "").strip()

    lower = clean.lower()

    # ==================================================
    # BASIC CHECKS
    # ==================================================

    if not clean:
        issues.append("empty_output")

    if len(clean.split()) < 5:
        issues.append("too_short")

    # ==================================================
    # BAD PATTERN DETECTION
    # ==================================================

    for bad in BAD_PATTERNS:

        if bad.lower() in lower:

            issues.append(f"bad_pattern:{bad}")

    # ==================================================
    # REPETITION DETECTION
    # ==================================================

    if has_repetition(clean):

        issues.append("repetition")

    # ==================================================
    # CONCEPT RELEVANCE
    # ==================================================

    if concept:

        concept_tokens = concept.lower().split()

        if concept_tokens:

            if concept_tokens[0] not in lower:

                issues.append("concept_name_missing")

    # ==================================================
    # TASK FORMAT VALIDATION
    # ==================================================

    if task_type == "flashcard":

        if (
            "front:" not in lower
            or "back:" not in lower
        ):
            issues.append(
                "flashcard_format_missing"
            )

    elif task_type == "debug_task":

        if (
            "buggy code:" not in lower
            or "expected fix:" not in lower
        ):
            issues.append(
                "debug_format_missing"
            )

        if wrong_domain_debug(concept, clean):
            issues.append("wrong_domain_debug")

    elif task_type == "output_prediction":

        if (
            "code:" not in lower
            or "answer:" not in lower
        ):
            issues.append(
                "output_prediction_format_missing"
            )

    elif task_type == "transfer_question":

        if (
            "question:" not in lower
            or "answer:" not in lower
        ):
            issues.append(
                "transfer_question_format_missing"
            )

    elif task_type == "challenge_question":

        if (
            "challenge:" not in lower
            or "solution outline:" not in lower
        ):
            issues.append(
                "challenge_question_format_missing"
            )

    elif task_type == "explanation":

        if "```json" in lower and '"front"' in lower:
            issues.append("explanation_wrong_structure")

        prose = re.sub(
            r"```[\s\S]*?```",
            " ",
            clean,
        )
        prose_words = len(prose.split())
        if prose_words < 18:
            issues.append("explanation_prose_too_short")
        if prose_words < 8 and "```" in clean:
            issues.append("explanation_code_only")

    # ==================================================
    # BLOCKING ISSUES (task format / domain)
    # ==================================================

    blocking_keys = {

        "flashcard_format_missing",
        "debug_format_missing",
        "wrong_domain_debug",
        "output_prediction_format_missing",
        "transfer_question_format_missing",
        "challenge_question_format_missing",
        "explanation_prose_too_short",
        "explanation_code_only",
        "explanation_wrong_structure",
    }

    for i in issues:
        if i in blocking_keys or i.startswith("bad_pattern:"):
            if i not in blocking_issues:
                blocking_issues.append(i)

    # ==================================================
    # TASK SUCCESS
    # ==================================================

    task_blocking = {

        "flashcard_format_missing",
        "debug_format_missing",
        "wrong_domain_debug",
        "output_prediction_format_missing",
        "transfer_question_format_missing",
        "challenge_question_format_missing",
        "explanation_prose_too_short",
        "explanation_code_only",
        "explanation_wrong_structure",
    }

    task_success = not any(
        issue in task_blocking
        for issue in issues
    )

    if any(i.startswith("bad_pattern:") for i in issues):
        task_success = False

    # ==================================================
    # VALIDITY DECISION
    # ==================================================

    hard_failures = {

        "empty_output",
        "repetition",
    }

    valid = True

    for item in issues:

        if item in hard_failures or item.startswith("bad_pattern:"):
            valid = False

    if not task_success:

        valid = False

    retry_recommended = (
        ("repetition" in issues or "empty_output" in issues)
        or (not task_success and "wrong_domain_debug" not in issues)
    )

    return {

        "valid": valid,

        "task_success": task_success,

        "issues": issues,

        "blocking_issues": blocking_issues,

        "cleaned_output": clean,

        "retry_recommended": retry_recommended,
    }
