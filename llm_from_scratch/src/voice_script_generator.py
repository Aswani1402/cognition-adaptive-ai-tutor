import re
from typing import Any, Dict, List, Optional

from scripts.generate_teaching_aligned_packets import build_difficulty_content_blocks, source_level_for_difficulty
from src.concept_resource_loader import clean_text


VOICE_TASK_TYPES = {
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
}

VIEW_OPENERS = {
    "definition_view": "Let us first understand the meaning.",
    "simple_example_view": "Look closely at this example.",
    "step_by_step_view": "Follow these steps.",
    "analogy_view": "Think of it like this.",
    "code_view": "Read the code line by line.",
    "debug_view": "Let us find what went wrong.",
    "output_prediction_view": "Before running it, predict the result.",
    "misconception_view": "A common wrong idea is this.",
    "transfer_view": "Now use the same idea in a new situation.",
    "challenge_view": "This is a challenge because it asks you to reason beyond the first example.",
    "revision_view": "Here is the quick recap.",
    "flashcard_view": "Try to recall before flipping the card.",
    "mindmap_view": "Place the concept in the center and connect the branches.",
    "voice_script_view": "Here is the spoken explanation.",
}

TARGET_WORDS = {
    "concept_intro_voice_script": (45, 70),
    "teaching_voice_script": (90, 140),
    "revision_voice_script": (60, 100),
    "mistake_feedback_voice_script": (70, 120),
    "doubt_explanation_voice_script": (80, 130),
    "encouragement_script": (30, 60),
    "next_step_guidance_script": (50, 90),
    "voice_script": (80, 120),
}


def _words(text: str) -> List[str]:
    return re.findall(r"\b[\w']+\b", text)


def _clip(text: str, max_words: int) -> str:
    text = clean_text(text)
    words = _words(text)
    if len(words) <= max_words:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept: List[str] = []
    count = 0
    for part in parts:
        part_count = len(_words(part))
        if kept and count + part_count > max_words:
            remaining = max_words - count
            if remaining > 8:
                kept.append(" ".join(_words(part)[:remaining]) + ".")
            break
        kept.append(part)
        count += part_count
    if kept:
        return clean_text(" ".join(kept))
    return clean_text(" ".join(words[:max_words]) + ".")


def _clean_sentence(value: Any, fallback: str) -> str:
    text = clean_text(value).strip()
    return text if text else fallback


def _first(items: Any, fallback: str) -> str:
    if isinstance(items, list):
        for item in items:
            text = clean_text(item)
            if text:
                return text
    return _clean_sentence(items, fallback)


def _level_parts(concept: Dict[str, Any], difficulty: str, packet: Optional[Dict[str, Any]]) -> Dict[str, str]:
    source_level = source_level_for_difficulty(difficulty)
    block = build_difficulty_content_blocks(concept)[source_level]
    teaching_content = (packet or {}).get("teaching_content") or {}
    concept_name = concept["concept_name"]
    if difficulty == "easy":
        key = _first(block.get("key_points"), f"{concept_name} has one beginner rule.")
        example = _clean_sentence(teaching_content.get("example") or block.get("example"), f"A short example shows {concept_name}.")
        mistake = _clean_sentence(teaching_content.get("common_mistake") or block.get("common_mistake"), f"The likely mistake is using {concept_name} without checking the rule.")
    elif difficulty == "medium":
        key = _first(block.get("syntax_or_rules") or block.get("key_points"), f"Use the practical rule for {concept_name}.")
        example = _first(block.get("examples") or block.get("debug_or_output_example"), f"A code example shows {concept_name} in use.")
        mistake = _first(block.get("common_mistakes"), f"The likely mistake is skipping the syntax rule for {concept_name}.")
    elif difficulty == "hard":
        key = _first(block.get("advanced_points"), f"Transfer {concept_name} to a harder case.")
        example = _first(block.get("transfer_examples") or block.get("challenge_tasks"), f"A challenge asks you to apply {concept_name} in a new situation.")
        mistake = _first(block.get("edge_cases"), f"The likely mistake is missing the edge case for {concept_name}.")
    else:
        key = _first(block.get("key_points"), f"Remember the core rule for {concept_name}.")
        example = _clean_sentence(block.get("example"), f"Use one familiar example for {concept_name}.")
        mistake = _clean_sentence(block.get("weakness_review") or block.get("common_mistake"), f"Review the common weak spot for {concept_name}.")
    return {
        "goal": _clip(_clean_sentence(teaching_content.get("learning_goal") or block.get("learning_goal") or block.get("summary"), f"Learn {concept_name}."), 22),
        "definition": _clip(_clean_sentence(teaching_content.get("definition") or block.get("definition") or block.get("summary"), key), 34),
        "key": _clip(key, 18),
        "example": _clip(example, 24),
        "mistake": _clip(mistake, 22),
        "real_world": _clip(_clean_sentence(teaching_content.get("real_world_use") or block.get("real_world_use"), f"Use {concept_name} in real work when the same idea appears again."), 22),
        "next_step": _clip(_clean_sentence((packet or {}).get("next_step") or block.get("next_concept_link"), f"Practice one more aligned task for {concept_name}."), 24),
    }


def _difficulty_line(difficulty: str, concept_name: str, parts: Dict[str, str]) -> str:
    if difficulty == "easy":
        return f"Keep it beginner friendly: {parts['key']} Use the example as a small analogy, not a big rule."
    if difficulty == "medium":
        return f"Focus on the practical rule, syntax, debugging, and output. Trace it step by step before you answer."
    if difficulty == "hard":
        return f"Use transfer thinking and check the edge case in the example. Justify your answer before moving on."
    return f"Use this as a recap only: remember {parts['key']} Then practice the recommended next step."


def _next_action(difficulty: str) -> str:
    return {
        "easy": "stay easy for one more quick check",
        "medium": "move through the medium code view and practice the weak rule",
        "hard": "try the hard challenge and justify each step",
        "revision": "revise the memory cue, then practice the weakness",
    }[difficulty]


def _sections(task_type: str, concept_name: str, difficulty: str, teaching_view: str, parts: Dict[str, str]) -> Dict[str, str]:
    opener = VIEW_OPENERS.get(teaching_view, VIEW_OPENERS["voice_script_view"])
    difficulty_note = _difficulty_line(difficulty, concept_name, parts)
    if task_type == "concept_intro_voice_script":
        return {
            "opening": f"Welcome to {concept_name}.",
            "explanation": f"In this lesson you will learn {parts['goal']}",
            "example": f"We will use a simple example: {parts['example']}",
            "check_prompt": "No check yet. First listen for the main idea.",
            "closing": "By the end, you should know what to look for when this concept appears.",
        }
    if task_type == "revision_voice_script":
        return {
            "opening": f"{opener} We are revising {concept_name}.",
            "explanation": f"Remember this: {parts['key']}",
            "example": f"Memory cue: connect the rule to {parts['example']}",
            "check_prompt": f"Next recommended practice: {_next_action('revision')}.",
            "closing": "Keep the recap short and reuse it when you answer.",
        }
    if task_type == "mistake_feedback_voice_script":
        return {
            "opening": "That answer is close enough to learn from.",
            "explanation": f"The likely mistake is this: {parts['mistake']}",
            "example": f"The correction is to use the packet rule: {parts['key']}",
            "check_prompt": f"Try again by checking the {teaching_view} example before answering.",
            "closing": "Small correction, then continue.",
        }
    if task_type == "doubt_explanation_voice_script":
        return {
            "opening": f"Good doubt about {concept_name}.",
            "explanation": f"Here is the simple way to think about it: {parts['definition']}",
            "example": f"Use this example to test the idea: {parts['example']}",
            "check_prompt": f"Ask what part of the example proves the rule: {parts['key']}",
            "closing": "Once that link is clear, the doubt becomes easier to answer.",
        }
    if task_type == "encouragement_script":
        return {
            "opening": "You are making progress.",
            "explanation": "Pause for a moment and notice that the idea is becoming more familiar.",
            "example": "No new content now. Keep your attention on the next small action.",
            "check_prompt": "Take one steady attempt.",
            "closing": "Consistency matters more than speed.",
        }
    if task_type == "next_step_guidance_script":
        return {
            "opening": f"Here is your next step for {concept_name}.",
            "explanation": f"Based on this {difficulty} packet, {_next_action(difficulty)}.",
            "example": f"Use the same teaching view again if {parts['mistake']} is still confusing.",
            "check_prompt": "Choose one aligned practice item and explain your reasoning.",
            "closing": "Move only after the rule feels clear.",
        }
    if task_type == "voice_script":
        return {
            "opening": f"{opener} We are learning {concept_name}.",
            "explanation": f"The main idea is: {parts['definition']}",
            "example": f"Example: {parts['example']}",
            "check_prompt": f"Before you continue, say the rule in your own words: {parts['key']}",
            "closing": f"Watch for this common issue: {parts['mistake']}",
        }
    return {
        "opening": f"{opener} We are studying {concept_name} at the {difficulty} level.",
        "explanation": f"{parts['definition']} {difficulty_note}",
        "example": f"Example: {parts['example']}",
        "check_prompt": f"Now check yourself: explain how the example shows {parts['key']}",
        "closing": f"Use this view to avoid the common mistake: {parts['mistake']}",
    }


def _compose(task_type: str, sections: Dict[str, str], difficulty: str, concept_name: str, parts: Dict[str, str]) -> str:
    script = " ".join(sections[k] for k in ["opening", "explanation", "example", "check_prompt", "closing"])
    if task_type == "teaching_voice_script" and difficulty == "medium":
        script += " Mention the syntax or rule, then trace it step by step so the output is not guessed."
    if task_type == "teaching_voice_script" and difficulty == "hard":
        script += " Transfer the idea to a real-world use, consider the edge case, and justify your answer."
    if task_type == "revision_voice_script":
        script += f" Practice next by revisiting {concept_name} with one short weakness review."
    if task_type == "encouragement_script":
        script = " ".join([sections["opening"], sections["explanation"], sections["example"], sections["check_prompt"], sections["closing"]])
    min_words, max_words = TARGET_WORDS.get(task_type, TARGET_WORDS["voice_script"])
    if len(_words(script)) < min_words and task_type != "encouragement_script":
        script += f" The important link is between the selected packet and this view: {parts['key']}"
    if len(_words(script)) < min_words and task_type == "teaching_voice_script":
        script += f" Use the selected example, name the rule, and connect it back to {concept_name} before you answer."
    if len(_words(script)) < min_words and task_type == "revision_voice_script":
        script += f" Say the memory cue once, then do one short practice item for {concept_name}."
    if len(_words(script)) < min_words and task_type == "mistake_feedback_voice_script":
        script += " The answer improves when you identify the exact rule, correct that part, and retry calmly."
    return _clip(script, max_words)


def generate_voice_script(
    concept: Dict[str, Any],
    *,
    task_type: str = "teaching_voice_script",
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
    packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if task_type not in VOICE_TASK_TYPES:
        task_type = "voice_script"
    if difficulty not in {"easy", "medium", "hard", "revision"}:
        difficulty = "easy"
    parts = _level_parts(concept, difficulty, packet)
    sections = _sections(task_type, concept["concept_name"], difficulty, teaching_view, parts)
    script = _compose(task_type, sections, difficulty, concept["concept_name"], parts)
    duration = max(20, min(120, round(len(_words(script)) / 2.3)))
    return {
        "task_type": task_type,
        "domain": concept["domain"],
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "difficulty": difficulty,
        "source_level": source_level_for_difficulty(difficulty),
        "teaching_view": teaching_view,
        "script": script,
        "speaker": "Cogni",
        "tone": "friendly_tutor",
        "estimated_duration_sec": duration,
        "audio_ready": True,
        "voice_sections": sections,
        "alignment_reason": "This voice script explains the same difficulty-level content and teaching view as the selected packet.",
    }
