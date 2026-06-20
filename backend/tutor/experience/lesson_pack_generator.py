from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from tutor.memory.variation_memory import VariationMemory

def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()



def _safe_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip("- ").strip() for line in value.splitlines() if line.strip()]
    return []


def _get_concept_name(concept_resource: Dict[str, Any]) -> str:
    return (
        concept_resource.get("concept_name")
        or concept_resource.get("topic")
        or concept_resource.get("title")
        or "Concept"
    )


def _get_definition(concept_resource: Dict[str, Any]) -> str:
    return (
        concept_resource.get("definition")
        or concept_resource.get("base_content")
        or concept_resource.get("content")
        or ""
    )


def _get_examples(concept_resource: Dict[str, Any]) -> List[str]:
    examples = concept_resource.get("examples")
    if isinstance(examples, list) and examples:
        return [str(x) for x in examples]

    examples_base = concept_resource.get("examples_base", "")
    if examples_base:
        chunks = [x.strip() for x in examples_base.split("\n\n") if x.strip()]
        return chunks[:3]

    return []


def _get_key_points(concept_resource: Dict[str, Any]) -> List[str]:
    key_points = concept_resource.get("key_points")
    if key_points:
        return _safe_list(key_points)

    key_points_base = concept_resource.get("key_points_base")
    if key_points_base:
        return _safe_list(key_points_base)

    return []


def _get_misconceptions(concept_resource: Dict[str, Any]) -> List[str]:
    misconceptions = concept_resource.get("misconceptions")
    if misconceptions:
        return _safe_list(misconceptions)

    misconceptions_base = concept_resource.get("misconceptions_base")
    if misconceptions_base:
        return _safe_list(misconceptions_base)

    return []

def _clean_for_voice(text: str) -> str:
    text = str(text or "")
    text = text.replace("Definition:", "")
    text = text.replace("Worked Example:", "For example:")
    text = text.replace("Concept:", "")
    text = text.replace("Practice:", "")
    return " ".join(text.split())


def generate_voice_script(
    concept_resource: Dict[str, Any],
    difficulty: str = "easy",
) -> Dict[str, Any]:
    concept_name = _get_concept_name(concept_resource)
    definition = _clean_for_voice(_get_definition(concept_resource))
    examples = _get_examples(concept_resource)
    key_points = _get_key_points(concept_resource)

    example_text = _clean_for_voice(examples[0]) if examples else "Try a small example and observe the output."
    key_point = (
        _clean_for_voice(key_points[0])
        if key_points
        else "Focus on the main idea first."
    )

    script = (
        f"Today we are learning {concept_name}. "
        f"Think of it step by step. {definition} "
        f"The key idea is: {key_point}. "
        f"Here is a simple example: {example_text}. "
        f"Now pause and try to explain {concept_name} in your own words."
    )

    return {
        "type": "voice_script",
        "title": f"{concept_name} — Voice Teaching Script",
        "difficulty": difficulty,
        "script": script,
        "estimated_seconds": max(30, min(120, len(script.split()) // 2)),
        "content_hash": _hash_text(script),
    }


def generate_flashcards(
    concept_resource: Dict[str, Any],
    max_cards: int = 5,
) -> List[Dict[str, Any]]:
    concept_name = _get_concept_name(concept_resource)
    definition = _get_definition(concept_resource)
    key_points = _get_key_points(concept_resource)
    misconceptions = _get_misconceptions(concept_resource)

    cards = []

    if definition:
        cards.append({
            "type": "flashcard",
            "front": f"What is {concept_name}?",
            "back": definition,
        })

    for i, point in enumerate(key_points[:3]):
        prompts = [
            f"Key idea in {concept_name}",
            f"What should you remember about {concept_name}?",
            f"Explain this concept briefly:",
        ]

        cards.append({
            "type": "flashcard",
            "front": prompts[i % len(prompts)],
            "back": point,
        })

    if misconceptions:
        cards.append({
            "type": "flashcard",
            "front": f"Common mistake in {concept_name}",
            "back": misconceptions[0],
        })

    for card in cards:
        card["card_hash"] = _hash_text(card["front"] + card["back"])

    return cards[:max_cards]


def generate_quick_recap(concept_resource: Dict[str, Any]) -> Dict[str, Any]:
    concept_name = _get_concept_name(concept_resource)
    definition = _get_definition(concept_resource)
    key_points = _get_key_points(concept_resource)

    bullets = key_points[:5]
    if not bullets and definition:
        bullets = [definition]

    body = f"Quick recap for {concept_name}:\n" + "\n".join(
        f"- {point}" for point in bullets
    )

    return {
        "type": "quick_recap",
        "title": f"{concept_name} — Quick Recap",
        "body": body,
        "bullets": bullets,
        "content_hash": _hash_text(body),
    }


def generate_mini_challenge(
    concept_resource: Dict[str, Any],
    difficulty: str = "easy",
) -> Dict[str, Any]:
    concept_name = _get_concept_name(concept_resource)
    examples = _get_examples(concept_resource)

    if examples:
        base = random.choice(examples)
        prompt = (
            f"You are given this example in {concept_name}:\n\n{base}\n\n"
            f"👉 Change one part of the code.\n"
            f"👉 Predict the output.\n"
            f"👉 Explain why it changes."
        )
    else:
        prompt = f"Mini challenge for {concept_name}: Create your own example and explain the result."

    return {
        "type": "mini_challenge",
        "title": f"{concept_name} — Mini Challenge",
        "difficulty": difficulty,
        "prompt": prompt,
        "expected_skill": "apply_concept",
        "challenge_hash": _hash_text(prompt),
    }


def generate_mind_map_notes(concept_resource: Dict[str, Any]) -> Dict[str, Any]:
    concept_name = _get_concept_name(concept_resource)
    key_points = _get_key_points(concept_resource)
    examples = _get_examples(concept_resource)
    misconceptions = _get_misconceptions(concept_resource)

    nodes = {
        "center": concept_name,
        "branches": [
            {
                "label": "Meaning",
                "items": [_get_definition(concept_resource)[:250]],
            },
            {
                "label": "Key Points",
                "items": key_points[:4],
            },
            {
                "label": "Examples",
                "items": examples[:2],
            },
            {
                "label": "Common Mistakes",
                "items": misconceptions[:2],
            },
        ],
    }

    return {
        "type": "mind_map_notes",
        "title": f"{concept_name} — Mind Map Notes",
        "nodes": nodes,
        "content_hash": _hash_text(str(nodes)),
    }


def generate_lesson_pack(
    concept_resource: Dict[str, Any],
    generated_content: Optional[Dict[str, Any]] = None,
    assessment_output: Optional[Dict[str, Any]] = None,
    learner_id: Optional[str] = None,
    difficulty: str = "easy",
) -> Dict[str, Any]:
    concept_name = _get_concept_name(concept_resource)
    concept_id = str(
        concept_resource.get("system_concept_id")
        or concept_resource.get("concept_id")
        or concept_resource.get("content_concept_id")
        or ""
    )

    teaching_items = []
    if isinstance(generated_content, dict):
        teaching_items = generated_content.get("items", [])

    assessment_items = []
    if isinstance(assessment_output, dict):
        assessment_items = (
                assessment_output.get("questions")
                or assessment_output.get("assessment_items")
                or []
        )

    voice_script = generate_voice_script(concept_resource, difficulty=difficulty)
    flashcards = generate_flashcards(concept_resource)
    quick_recap = generate_quick_recap(concept_resource)
    mini_challenge = generate_mini_challenge(concept_resource, difficulty=difficulty)
    mind_map_notes = generate_mind_map_notes(concept_resource)

    memory_info = {
        "used": False,
        "filtered_teaching_items": 0,
        "filtered_flashcards": 0,
    }

    if learner_id and concept_id:
        memory = VariationMemory()

        original_teaching_count = len(teaching_items)
        original_flashcard_count = len(flashcards)

        teaching_items = memory.filter_new_content(
            learner_id=str(learner_id),
            concept_id=str(concept_id),
            items=teaching_items,
            field="content",
        )

        flashcards = memory.filter_new_content(
            learner_id=str(learner_id),
            concept_id=str(concept_id),
            items=flashcards,
            field="flashcards",
        )

        content_hashes = [
            item.get("content_hash")
            for item in teaching_items
            if item.get("content_hash")
        ]

        flashcard_hashes = [
            card.get("card_hash")
            for card in flashcards
            if card.get("card_hash")
        ]

        challenge_hash = mini_challenge.get("challenge_hash", "")

        memory.add_entry(
            learner_id=str(learner_id),
            concept_id=str(concept_id),
            content_hashes=content_hashes,
            flashcard_hashes=flashcard_hashes,
            challenge_hash=challenge_hash,
        )

        memory_info = {
            "used": True,
            "filtered_teaching_items": original_teaching_count - len(teaching_items),
            "filtered_flashcards": original_flashcard_count - len(flashcards),
        }


    pack = {
        "status": "success",
        "learner_id": learner_id,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "difficulty": difficulty,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lesson_flow": [
            "hook",
            "teaching",
            "voice_script",
            "flashcards",
            "quick_recap",
            "mini_challenge",
            "assessment",
            "feedback",
        ],
        "hook": {
            "type": "hook",
            "text": f"Let us master {concept_name} with a short lesson, examples, flashcards, and a challenge.",
        },
        "teaching_items": teaching_items,
        "progress": {
            "current_step": 1,
            "total_steps": 8,
            "completion_percent": 12,
        },
        "ui_flags": {
            "show_continue": True,
            "show_retry": False,
            "highlight_key_points": True,
        },
        "difficulty_label": difficulty.upper(),
        "voice_script": voice_script,
        "flashcards": flashcards,
        "quick_recap": quick_recap,
        "mind_map_notes": mind_map_notes,
        "mini_challenge": mini_challenge,
        "assessment_items": assessment_items,
        "engagement": {
            "xp_reward": 10 if difficulty == "easy" else 20 if difficulty == "medium" else 30,
            "estimated_minutes": 6 if difficulty == "easy" else 8 if difficulty == "medium" else 10,
            "streak_unit": "lesson_completed",
            "app_style": "duolingo_cake_inspired",
        },
        "gamification": {
            "xp": 10 if difficulty == "easy" else 20 if difficulty == "medium" else 30,
            "streak_increment": 1,
            "badge": "concept_master" if difficulty == "hard" else None,
        },
        "variation_memory": memory_info,
    }

    pack["lesson_pack_hash"] = _hash_text(str(pack))
    return pack


