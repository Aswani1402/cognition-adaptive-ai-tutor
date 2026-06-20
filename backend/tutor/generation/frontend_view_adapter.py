from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


DEFAULT_VIEW_ORDER = [
    "definition_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "debug_view",
    "misconception_view",
    "challenge_view",
    "transfer_view",
    "revision_view",
    "flashcard_view",
]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _normalize_whitespace(text: str) -> str:
    text = _safe_str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _restore_python_code_lines(text: str) -> str:
    """
    Fixes compressed code-like text such as:
    name = "Alice" age = 30 print(name)
    into cleaner display lines where possible.
    """
    text = _normalize_whitespace(text)

    if not text:
        return text

    # Already has line breaks
    if "\n" in text:
        return text

    replacements = [
        (" print(", "\nprint("),
        (" if ", "\nif "),
        (" for ", "\nfor "),
        (" while ", "\nwhile "),
        (" def ", "\ndef "),
        (" class ", "\nclass "),
        (" return ", "\nreturn "),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    # Add line breaks before Example markers
    text = re.sub(r"\s+(Example\s+\d+\s*[—:\-])", r"\n\n\1", text)

    # Add line breaks between simple assignments only when many assignments exist
    assignment_count = len(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*=", text))
    if assignment_count >= 2:
        text = re.sub(
            r"\s+(?=[A-Za-z_][A-Za-z0-9_]*\s*=)",
            "\n",
            text,
        )

    return _normalize_whitespace(text)


def _extract_code_blocks(text: str) -> List[str]:
    text = _safe_str(text)
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return [_normalize_whitespace(block) for block in blocks if _normalize_whitespace(block)]


def _make_code_display(content: str) -> Dict[str, Any]:
    content = _normalize_whitespace(content)

    code_blocks = _extract_code_blocks(content)

    if code_blocks:
        cleaned_blocks = [_restore_python_code_lines(block) for block in code_blocks]
        return {
            "kind": "code",
            "language": "python",
            "code_blocks": cleaned_blocks,
            "plain_text": content,
        }

    repaired = _restore_python_code_lines(content)

    likely_code = any(token in repaired for token in ["print(", "=", "if ", "for ", "while ", "def "])

    return {
        "kind": "code" if likely_code else "text",
        "language": "python" if likely_code else None,
        "code_blocks": [repaired] if likely_code else [],
        "plain_text": repaired,
    }


def _compact_points(points: Any, limit: int = 6) -> List[str]:
    output = []
    seen = set()

    for item in _safe_list(points):
        text = _normalize_whitespace(str(item))
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        output.append(text)
        seen.add(key)

        if len(output) >= limit:
            break

    return output


def _normalize_flashcards(raw_cards: Any, generated_flashcards: Any = None) -> List[Dict[str, str]]:
    cards = []

    if isinstance(raw_cards, list):
        for card in raw_cards:
            if not isinstance(card, dict):
                continue

            front = card.get("front") or card.get("question")
            back = card.get("back") or card.get("answer")

            if front and back:
                cards.append(
                    {
                        "front": _normalize_whitespace(front),
                        "back": _normalize_whitespace(back),
                    }
                )

    if not cards and isinstance(generated_flashcards, list):
        for card in generated_flashcards:
            if not isinstance(card, dict):
                continue

            question = card.get("question") or card.get("front")
            answer = card.get("answer") or card.get("back")

            if question and answer:
                cards.append(
                    {
                        "front": _normalize_whitespace(question),
                        "back": _normalize_whitespace(answer),
                    }
                )

    return cards[:10]


def _normalize_mindmap(raw_mindmap: Any) -> Dict[str, Any]:
    if not isinstance(raw_mindmap, dict):
        return {
            "center": "",
            "branches": [],
        }

    center = _safe_str(raw_mindmap.get("center", ""))

    branches = []
    for branch in _safe_list(raw_mindmap.get("branches", [])):
        if not isinstance(branch, dict):
            continue

        title = _safe_str(branch.get("title", ""))
        points = _compact_points(branch.get("points", []), limit=5)

        if title or points:
            branches.append(
                {
                    "title": title,
                    "points": points,
                }
            )

    return {
        "center": center,
        "branches": branches[:8],
    }


def _normalize_debug_task(view_data: Dict[str, Any], generated_debug_task: Any = None) -> Dict[str, Any]:
    generated_debug_task = generated_debug_task if isinstance(generated_debug_task, dict) else {}

    buggy_code = (
        generated_debug_task.get("buggy_code")
        or view_data.get("buggy_code")
        or view_data.get("buggy_case")
        or ""
    )

    expected_fix = (
        generated_debug_task.get("expected_fix")
        or view_data.get("expected_fix")
        or view_data.get("correction_hint")
        or ""
    )

    task = view_data.get("task") or "Find the mistake, explain why it is wrong, and correct it."

    return {
        "task": _normalize_whitespace(task),
        "buggy_code": _restore_python_code_lines(_safe_str(buggy_code)),
        "expected_fix": expected_fix,
        "bug_type": generated_debug_task.get("bug_type"),
    }


def _normalize_selected_view(
    selected_view_name: str,
    view_data: Dict[str, Any],
    teaching_content: Dict[str, Any],
) -> Dict[str, Any]:
    view_type = view_data.get("view_type") or selected_view_name
    title = view_data.get("title") or selected_view_name.replace("_", " ").title()

    content = (
        view_data.get("content")
        or view_data.get("prompt")
        or view_data.get("buggy_case")
        or teaching_content.get("adaptive_explanation")
        or teaching_content.get("generated_level_content")
        or ""
    )

    steps = view_data.get("steps", [])
    cards = view_data.get("cards", [])
    focus_points = view_data.get("focus_points", [])
    remember = view_data.get("remember", [])
    avoid = view_data.get("avoid", [])

    expanded_content = teaching_content.get("expanded_content", {})
    if not isinstance(expanded_content, dict):
        expanded_content = {}

    generated_debug_task = (
        teaching_content.get("generated_debug_task")
        or expanded_content.get("debug_task")
        or {}
    )

    display_payload: Dict[str, Any] = {
        "view_type": view_type,
        "title": _normalize_whitespace(title),
        "best_for": view_data.get("best_for"),
    }

    if view_type == "step_by_step_view":
        display_payload["display_type"] = "steps"
        display_payload["steps"] = _compact_points(steps, limit=8)

    elif view_type == "code_view":
        display_payload["display_type"] = "code"
        display_payload.update(_make_code_display(_safe_str(content)))

    elif view_type == "debug_view":
        display_payload["display_type"] = "debug"
        display_payload["debug_task"] = _normalize_debug_task(
            view_data=view_data,
            generated_debug_task=generated_debug_task,
        )
        display_payload["content"] = _normalize_whitespace(content)

    elif view_type == "challenge_view":
        display_payload["display_type"] = "challenge"
        display_payload["prompt"] = _normalize_whitespace(
            view_data.get("prompt")
            or teaching_content.get("generated_challenge")
            or expanded_content.get("challenge")
            or content
        )
        display_payload["focus_points"] = _compact_points(focus_points, limit=6)

    elif view_type == "transfer_view":
        display_payload["display_type"] = "transfer"
        display_payload["content"] = _normalize_whitespace(
            content
            or teaching_content.get("generated_transfer_task")
            or expanded_content.get("transfer_task")
        )

    elif view_type == "revision_view":
        display_payload["display_type"] = "revision"
        display_payload["remember"] = _compact_points(remember, limit=8)
        display_payload["avoid"] = _compact_points(avoid, limit=5)
        display_payload["content"] = _normalize_whitespace(content)

    elif view_type == "flashcard_view":
        display_payload["display_type"] = "flashcards"
        display_payload["cards"] = _normalize_flashcards(
            raw_cards=cards,
            generated_flashcards=teaching_content.get("generated_flashcards"),
        )

    elif view_type == "misconception_view":
        display_payload["display_type"] = "misconception"
        display_payload["content"] = _normalize_whitespace(content)
        display_payload["correction_hint"] = _compact_points(
            view_data.get("correction_hint", []),
            limit=8,
        )

    else:
        display_payload["display_type"] = "text"
        display_payload["content"] = _normalize_whitespace(content)

    return display_payload


def build_frontend_teaching_view(
    teaching_content: Dict[str, Any],
    selected_teaching_view: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Converts full backend teaching output into frontend-safe selected-view output.

    Frontend should show:
    - selected_view first
    - fallback_views as buttons/options
    - flashcards/mindmap as separate tabs
    - not all views dumped together
    """
    teaching_content = teaching_content if isinstance(teaching_content, dict) else {}

    views = teaching_content.get("views", {})
    if not isinstance(views, dict):
        views = {}

    expanded_content = teaching_content.get("expanded_content", {})
    if not isinstance(expanded_content, dict):
        expanded_content = {}

    selected = (
        selected_teaching_view
        or teaching_content.get("selected_teaching_view")
        or teaching_content.get("recommended_view")
        or "definition_view"
    )

    if selected not in views:
        selected = teaching_content.get("recommended_view") or selected

    if selected not in views and views:
        selected = next((view for view in DEFAULT_VIEW_ORDER if view in views), next(iter(views)))

    view_data = views.get(selected, {})
    if not isinstance(view_data, dict):
        view_data = {}

    selected_view = _normalize_selected_view(
        selected_view_name=selected,
        view_data=view_data,
        teaching_content=teaching_content,
    )

    generated_flashcards = (
        teaching_content.get("generated_flashcards")
        or expanded_content.get("flashcards")
        or []
    )

    generated_mindmap = (
        teaching_content.get("generated_mindmap")
        or expanded_content.get("mindmap")
        or {}
    )

    frontend_payload = {
        "status": "success",
        "module": "FrontendTeachingViewAdapter",
        "concept_id": teaching_content.get("concept_id"),
        "concept_name": teaching_content.get("concept_name") or teaching_content.get("topic"),
        "difficulty": teaching_content.get("difficulty"),
        "selected_teaching_view": selected,
        "selected_view": selected_view,
        "available_view_names": list(views.keys()),
        "fallback_view_names": [
            view for view in DEFAULT_VIEW_ORDER
            if view in views and view != selected
        ],
        "summary": _normalize_whitespace(teaching_content.get("generated_summary", "")),
        "flashcards": _normalize_flashcards(
            raw_cards=[],
            generated_flashcards=generated_flashcards,
        ),
        "mindmap": _normalize_mindmap(generated_mindmap),
        "debug_task": _normalize_debug_task(
            view_data=views.get("debug_view", {}) if isinstance(views.get("debug_view"), dict) else {},
            generated_debug_task=teaching_content.get("generated_debug_task") or expanded_content.get("debug_task"),
        ),
        "frontend_rule": (
            "Show selected_view first. Show flashcards and mindmap in separate tabs. "
            "Do not render every available view at once."
        ),
    }

    return frontend_payload