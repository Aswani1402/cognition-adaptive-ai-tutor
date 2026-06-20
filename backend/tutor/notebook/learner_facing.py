from __future__ import annotations

import re
from typing import Any


RAW_LABELS = {
    "weak_answer",
    "wrong_option",
    "wrong_output",
    "syntax_misunderstanding",
    "debug_error",
    "debug_misdiagnosis",
    "none",
    "fallback_cumulative",
    "exact_match",
    "rubric",
    "mock",
}

WEAKNESS_TEXT = {
    "weak_answer": "Your answer was too short or unclear. Practice explaining the concept rule with one example.",
    "wrong_option": "You selected an incorrect option. Review the key definition and try one MCQ again.",
    "wrong_output": "Practice tracing the code step by step before writing the output.",
    "syntax_misunderstanding": "Review the syntax rule and complete one syntax practice.",
    "debug_error": "Practice identifying the exact line that causes the error.",
    "debug_misdiagnosis": "Practice identifying the exact line that causes the error.",
    "needs_review": "Review the concept rule, then try one similar question.",
    "partial": "Your idea was partly right, but it needs one missing detail or explanation.",
}


def normalize_notebook_memory(
    *,
    packet: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
    mistakes: list[dict[str, Any]] | None = None,
    doubts: list[dict[str, Any]] | None = None,
    revisions: list[dict[str, Any]] | None = None,
    cards: list[dict[str, Any]] | None = None,
    summary_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    notes = notes or []
    mistakes = mistakes or []
    doubts = doubts or []
    revisions = revisions or []
    cards = cards or []
    summary_state = summary_state or {}

    concept = str(packet.get("concept_name") or packet.get("conceptName") or packet.get("conceptId") or "this concept")
    subject = str(packet.get("subject") or summary_state.get("active_subject") or summary_state.get("domain") or "Selected subject")
    base = _clean_sentence(packet.get("base_content") or packet.get("summary") or f"{concept} is a key idea in {subject}.")
    key_points = _dedupe(
        [_clean_sentence(item) for item in packet.get("key_points", [])]
        + [_clean_sentence(item) for item in packet.get("keyPoints", [])]
    )[:5]
    if not key_points:
        key_points = [
            f"Understand the definition of {concept}.",
            f"Connect {concept} to one small example.",
            "Check the final result before answering.",
        ]

    learner_mistakes = _format_mistakes(mistakes, concept)[:5]
    revision_plan = _format_revision_plan(revisions, learner_mistakes, concept)[:5]
    flashcards = _format_flashcards(cards, packet, concept)[:5]
    past_doubts = _format_doubts(doubts, concept, subject)[:5]
    practice_queue = _format_practice_queue(packet, learner_mistakes, concept)[:5]
    saved_notes = _format_notes(notes)[:20]

    learner_summary = _first_clean(
        packet.get("learner_facing_summary"),
        f"{concept}: {base}",
        f"{concept} is a key idea in {subject}.",
    )

    return {
        "learner_facing_summary": learner_summary,
        "learner_facing_key_points": key_points,
        "learner_facing_mistakes": learner_mistakes,
        "learner_facing_revision_plan": revision_plan,
        "learner_facing_flashcards": flashcards,
        "learner_facing_doubts": past_doubts,
        "learner_facing_practice_queue": practice_queue,
        "summary": learner_summary,
        "weakPoints": learner_mistakes,
        "mistakes": learner_mistakes,
        "revisionPlan": revision_plan,
        "savedFlashcards": [f"Q: {card['front']}\nA: {card['back']}" for card in flashcards],
        "pastDoubts": [f"Q: {item['question']}\nA: {item['answer_preview']}" for item in past_doubts],
        "practiceQueue": practice_queue,
        "savedNotes": saved_notes,
        "notes": saved_notes,
        "source": _source(packet),
        "raw_evidence": {
            "mistake_count": len(mistakes),
            "revision_count": len(revisions),
            "doubt_count": len(doubts),
            "card_count": len(cards),
            "note_count": len(notes),
        },
        "debug_evidence": {
            "summary_state_keys": sorted(summary_state.keys())[:30],
        },
    }


def format_mistake_for_learner(row: dict[str, Any], concept: str = "this concept") -> str | None:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("mistake_type", "feedback", "question_type", "task_type", "learner_answer")
    ).strip()
    lowered = text.lower()
    if not text or lowered in {"none", "correct"}:
        return None
    if "correct. your answer matches" in lowered or "correct answer matches" in lowered:
        return None
    mistake_type = str(row.get("mistake_type") or "").strip().lower()
    if mistake_type in {"", "none", "correct"}:
        return None
    mapped = WEAKNESS_TEXT.get(mistake_type)
    if mapped:
        return mapped
    if "option" in lowered:
        return WEAKNESS_TEXT["wrong_option"]
    if "output" in lowered:
        return WEAKNESS_TEXT["wrong_output"]
    if "syntax" in lowered:
        return WEAKNESS_TEXT["syntax_misunderstanding"]
    if "debug" in lowered or "bug" in lowered:
        return WEAKNESS_TEXT["debug_error"]
    if "does not fully match" in lowered or "too short" in lowered:
        return WEAKNESS_TEXT["weak_answer"]
    return f"Review {concept}: your previous answer missed one expected idea."


def format_revision_plan_for_learner(items: list[Any], mistakes: list[str], concept: str) -> list[str]:
    return _format_revision_plan([item if isinstance(item, dict) else {"reason": item} for item in items], mistakes, concept)


def format_flashcard_for_learner(item: Any, concept: str) -> dict[str, str] | None:
    if isinstance(item, dict):
        front = _clean_sentence(item.get("front") or item.get("prompt") or item.get("title") or "")
        back = _clean_sentence(item.get("back") or item.get("answer") or item.get("content") or "")
    else:
        text = _clean_sentence(item)
        if not _is_useful(text):
            return None
        if text.lower().startswith("q:"):
            parts = re.split(r"\bA:\s*", text, maxsplit=1, flags=re.I)
            front = re.sub(r"^Q:\s*", "", parts[0], flags=re.I).strip()
            back = parts[1].strip() if len(parts) > 1 else f"Review the core idea of {concept}."
        else:
            front = f"What should I remember about {concept}?"
            back = text
    if not _is_useful(front) or not _is_useful(back):
        return None
    return {"front": front, "back": back}


def _format_mistakes(mistakes: list[dict[str, Any]], concept: str) -> list[str]:
    return _dedupe([item for item in (format_mistake_for_learner(row, concept) for row in mistakes) if item])


def _format_revision_plan(revisions: list[dict[str, Any]], mistakes: list[str], concept: str) -> list[str]:
    actions = [
        f"Review the definition of {concept}.",
        f"Write one clear example using {concept}.",
    ]
    for row in revisions:
        raw_reason = str(row.get("revision_reason") or row.get("reason") or row.get("priority") or row.get("task_type") or "")
        lowered = raw_reason.lower()
        reason = _clean_sentence(raw_reason)
        if not _is_useful(reason):
            if "output" not in lowered and "syntax" not in lowered and "debug" not in lowered and "transfer" not in lowered:
                continue
        if "output" in lowered:
            actions.append(f"Predict the output of one short {concept} example.")
        elif "syntax" in lowered:
            actions.append(f"Complete one syntax practice for {concept}.")
        elif "debug" in lowered:
            actions.append(f"Fix one small {concept} debugging task.")
        elif "transfer" in lowered:
            actions.append(f"Try one transfer task using {concept} in a real situation.")
    if mistakes:
        actions.append(f"Retry one similar question after reviewing {concept}.")
    else:
        actions.append(f"Try one MCQ and one short explanation for {concept}.")
    return _dedupe(actions)[:5]


def _format_flashcards(cards: list[dict[str, Any]], packet: dict[str, Any], concept: str) -> list[dict[str, str]]:
    formatted = [card for card in (format_flashcard_for_learner(row, concept) for row in cards) if card]
    if not formatted:
        formatted = [
            {"front": f"What is {concept}?", "back": _clean_sentence(packet.get("base_content") or f"{concept} is a core concept.")},
            {"front": f"Give one example of {concept}.", "back": _clean_sentence(packet.get("examples") or f"Use one small {concept} example.")},
        ]
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for card in formatted:
        key = f"{card['front'].lower()}|{card['back'].lower()}"
        if key not in seen:
            output.append(card)
            seen.add(key)
    return output


def _format_doubts(doubts: list[dict[str, Any]], concept: str, subject: str) -> list[dict[str, str]]:
    output = []
    for row in doubts:
        question = _clean_sentence(row.get("doubt_text") or row.get("question") or "")
        answer = _clean_sentence(row.get("answer_summary") or row.get("answer") or row.get("response") or "")
        if not _is_useful(question):
            continue
        if question.lower() in {"what is this concept?", "what is this concept"}:
            question = f"What is {concept} in {subject}?"
        output.append({"question": question, "answer_preview": answer or f"Review the definition and one example of {concept}."})
    return _dedupe_dicts(output, "question")


def _format_practice_queue(packet: dict[str, Any], mistakes: list[str], concept: str) -> list[str]:
    queue = [
        f"Try one MCQ about {concept}.",
        f"Write a short example using {concept}.",
        f"Explain why {concept} is useful.",
    ]
    joined = " ".join(mistakes).lower()
    if "output" in joined:
        queue.append(f"Predict the output of one {concept} program or example.")
    if "debug" in joined or "syntax" in joined:
        queue.append(f"Fix one small {concept} mistake.")
    if "transfer" in joined or not mistakes:
        queue.append(f"Try one transfer question using a real situation.")
    return _dedupe(queue)


def _format_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in notes:
        title = _clean_sentence(row.get("title") or "Saved note")
        content = _clean_sentence(row.get("content") or "")
        if not _is_useful(content):
            continue
        output.append(
            {
                "id": row.get("id"),
                "title": title,
                "content": content,
                "note_type": row.get("note_type") or "saved_note",
                "source_page": row.get("source_page") or "notebook",
                "updated_at": row.get("updated_at") or row.get("created_at"),
            }
        )
    return output


def _clean_sentence(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\bC\d+\b", "the current concept", text)
    for raw in RAW_LABELS:
        text = re.sub(rf"\b{re.escape(raw)}\b", "", text, flags=re.I)
    text = text.replace("Apply  at easy level", "").strip(" -:;")
    if text.lower() in {"", "none", "null", "undefined"}:
        return ""
    return text[:360].rstrip()


def _first_clean(*values: Any) -> str:
    for value in values:
        text = _clean_sentence(value)
        if _is_useful(text):
            return text
    return ""


def _is_useful(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered or lowered in {"none", "null", "undefined"}:
        return False
    if any(raw in lowered for raw in ["weak_answer", "wrong_option", "fallback_cumulative", "apply c2", "exact_match"]):
        return False
    if lowered.startswith("correct. your answer matches"):
        return False
    return True


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        clean = _clean_sentence(item)
        key = clean.lower()
        if clean and key not in seen:
            output.append(clean)
            seen.add(key)
    return output


def _dedupe_dicts(items: list[dict[str, str]], key_name: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for item in items:
        key = item.get(key_name, "").lower()
        if key and key not in seen:
            output.append(item)
            seen.add(key)
    return output


def _source(packet: dict[str, Any]) -> str:
    llm = packet.get("llm_generation")
    if isinstance(llm, dict) and llm.get("model_generated"):
        return "cognitutor_lm_guarded"
    if packet.get("resource_source") == "concept_resources":
        return "rag_grounded_fallback"
    return "concept_resource_fallback"
