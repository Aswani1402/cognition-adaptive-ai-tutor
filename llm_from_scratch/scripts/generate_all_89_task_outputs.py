import argparse
import json
from collections import defaultdict
from typing import Any, Dict, List

from scripts.generate_teaching_aligned_packets import build_difficulty_content_blocks, source_level_for_difficulty
from src.cognitutor_lm_config import (
    ALL_89_TASK_TYPES,
    ALL_TASK_OUTPUT,
    ASSESSMENT_TASKS,
    BY_CONCEPT_DIR,
    BY_SUBJECT_DIR,
    DOUBT_TASKS,
    FEEDBACK_TASKS,
    FLASHCARD_TASKS,
    HINT_TASKS,
    MINDMAP_TASKS,
    NOTEBOOK_TASKS,
    PACKET_OUTPUT,
    PRACTICE_CHALLENGE_TASKS,
    REVISION_TASKS,
    TEACHING_TASKS,
    VOICE_TASKS,
)
from src.content_versioning import attach_version_metadata
from src.concept_resource_loader import clean_text, find_concept, load_concept_resources, safe_name
from src.production_quality_gate import apply_quality_gate
from src.voice_script_generator import VOICE_TASK_TYPES, generate_voice_script


TASK_FAMILIES = {
    "teaching": set(TEACHING_TASKS),
    "assessment": set(ASSESSMENT_TASKS),
    "revision": set(REVISION_TASKS),
    "flashcard": set(FLASHCARD_TASKS),
    "mindmap": set(MINDMAP_TASKS),
    "feedback": set(FEEDBACK_TASKS),
    "hint": set(HINT_TASKS),
    "doubt": set(DOUBT_TASKS),
    "notebook": set(NOTEBOOK_TASKS),
    "practice_challenge": set(PRACTICE_CHALLENGE_TASKS),
    "voice": set(VOICE_TASKS),
}


def family(task: str) -> str:
    for name, tasks in TASK_FAMILIES.items():
        if task in tasks:
            return name
    return "teaching"


def difficulty(task: str) -> str:
    if task in {"voice_script", "concept_intro_voice_script", "encouragement_script"}:
        return "easy"
    if task in {"teaching_voice_script", "mistake_feedback_voice_script", "doubt_explanation_voice_script"}:
        return "medium"
    if task == "next_step_guidance_script":
        return "hard"
    if task == "revision_voice_script":
        return "revision"
    if task in {"transfer_view", "challenge_view", "transfer_question", "challenge_question", "transfer_task", "real_world_application_question", "multi_step_challenge", "practice_question"}:
        return "hard"
    if task in {"debug_view", "output_prediction_view", "code_view", "debug_task", "output_prediction", "syntax_completion", "coding_prompt", "code_reasoning_task", "debug_flashcard", "syntax_flashcard", "debug_feedback", "output_prediction_feedback", "debug_hint", "syntax_hint", "output_prediction_hint", "debug_doubt_answer", "output_doubt_answer", "debug_challenge", "output_prediction_challenge"}:
        return "medium"
    if family(task) in {"revision", "flashcard", "mindmap"} or "revision" in task or task == "voice_script":
        return "revision"
    return "easy"


def teaching_view(task: str, diff: str) -> str:
    voice_mapping = {
        "voice_script": "voice_script_view",
        "teaching_voice_script": "code_view" if diff == "medium" else "definition_view",
        "revision_voice_script": "revision_view",
        "mistake_feedback_voice_script": "misconception_view",
        "doubt_explanation_voice_script": "step_by_step_view",
        "encouragement_script": "voice_script_view",
        "next_step_guidance_script": "challenge_view",
        "concept_intro_voice_script": "definition_view",
    }
    if task in voice_mapping:
        return voice_mapping[task]
    mapping = {
        "definition": "definition_view",
        "simple_example": "simple_example_view",
        "step": "step_by_step_view",
        "analogy": "analogy_view",
        "code": "code_view",
        "debug": "debug_view",
        "output_prediction": "output_prediction_view",
        "misconception": "misconception_view",
        "transfer": "transfer_view",
        "challenge": "challenge_view",
        "comparison": "mindmap_view",
        "real_world": "transfer_view",
        "flashcard": "flashcard_view",
        "mindmap": "mindmap_view",
        "voice": "voice_script_view",
        "revision": "revision_view",
    }
    for needle, view in mapping.items():
        if needle in task:
            return view
    return {"easy": "definition_view", "medium": "code_view", "hard": "challenge_view", "revision": "revision_view"}[diff]


def load_packets() -> Dict[tuple, Dict[str, Any]]:
    rows = json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []
    return {(p["domain"], p["concept_id"], p["difficulty"], p["teaching_view"]): p for p in rows}


def level_parts(concept: Dict[str, Any], diff: str) -> Dict[str, Any]:
    block = build_difficulty_content_blocks(concept)[source_level_for_difficulty(diff)]
    if diff == "easy":
        points = block.get("key_points", [])
        example = block.get("example", "")
        mistake = block.get("common_mistake", "")
    elif diff == "medium":
        points = block.get("key_points", [])
        example = (block.get("examples") or [block.get("debug_or_output_example", "")])[0]
        mistake = (block.get("common_mistakes") or ["Review the practical rule."])[0]
    elif diff == "hard":
        points = block.get("advanced_points", [])
        example = (block.get("transfer_examples") or block.get("challenge_tasks") or [block.get("real_world_use", "")])[0]
        mistake = (block.get("edge_cases") or ["Check the deeper reasoning."])[0]
    else:
        points = block.get("key_points", [])
        example = block.get("example", "")
        mistake = block.get("weakness_review", "")
    return {
        "block": block,
        "goal": clean_text(block.get("learning_goal") or block.get("summary")),
        "definition": clean_text(block.get("definition") or block.get("summary")),
        "points": [clean_text(p) for p in points if clean_text(p)] or [concept["concept_name"]],
        "example": clean_text(example),
        "mistake": clean_text(mistake),
        "real": clean_text(block.get("real_world_use") or block.get("summary") or concept.get("real_world_use")),
    }


def packet_for(packet_index: Dict[tuple, Dict[str, Any]], concept: Dict[str, Any], diff: str, view: str) -> Dict[str, Any]:
    return packet_index.get((concept["domain"], concept["concept_id"], diff, view)) or {}


def output_for(concept: Dict[str, Any], task: str, diff: str, view: str, packet: Dict[str, Any]) -> Dict[str, Any]:
    if task in VOICE_TASK_TYPES:
        return generate_voice_script(concept, task_type=task, difficulty=diff, teaching_view=view, packet=packet)
    p = level_parts(concept, diff)
    name = concept["concept_name"]
    key = p["points"][0]
    tc = packet.get("teaching_content") or {}
    shown_example = clean_text(tc.get("example") or p["example"])
    if task == "mcq":
        return {"question": f"Which statement matches the {diff} packet for {name}?", "options": [f"A) {key}", f"B) {p['mistake']}", f"C) This topic is unrelated to {concept['domain']}.", "D) The shown example should be ignored."], "answer": "A", "explanation": f"A is correct because the packet teaches: {key}"}
    if task == "fill_in_the_blank":
        return {"question": f"Fill in the blank: In this packet, {name} is remembered as ____.", "answer": key, "explanation": f"The answer is shown in the linked {view} packet."}
    if task == "true_or_false":
        return {"statement": f"{p['mistake']}", "answer": False, "explanation": f"False. The packet correction is: {key}"}
    if task == "explanation_check":
        return {"question": f"Explain the {diff} idea for {name} using the linked packet.", "answer": key, "explanation": f"A complete explanation should include: {key}"}
    if task in {"debug_task", "debug_challenge"}:
        return {"buggy_code": f"BUGGY:\n{shown_example}\n# Mistake: {p['mistake']}", "expected_fix": f"Apply the packet rule: {key}", "hint": f"Use only the {diff} packet content.", "explanation": f"The fix follows the linked {view} teaching content."}
    if task in {"output_prediction", "output_prediction_challenge"}:
        return {"code": shown_example or key, "question": "What is the output or result?", "expected_output": key, "explanation": f"The prediction follows the {diff} packet point: {key}"}
    if task == "syntax_completion":
        return {"question": f"Complete the syntax or rule for {name}: ____", "answer": shown_example or key, "explanation": f"The completion comes from the medium packet example and rule."}
    if task in {"coding_prompt", "code_reasoning_task"}:
        return {"question": f"Use the {diff} packet for {name} to reason about this example: {shown_example}", "answer": key, "explanation": f"The reasoning must cite the linked packet point: {key}"}
    if task in {"transfer_question", "challenge_question", "practice_question", "transfer_task", "real_world_application_question", "multi_step_challenge"}:
        return {"question": f"Apply {name} to this deeper scenario: {p['real']}", "answer": key, "explanation": f"A strong answer transfers the hard packet idea and checks: {p['mistake']}"}
    if family(task) == "teaching":
        return {"title": f"{name} - {task}", "content": clean_text(tc.get("beginner_explanation") or p["goal"]), "example": shown_example, "key_points": p["points"][:4], "quick_check": clean_text(tc.get("quick_check") or f"Explain {name} using only this {diff} content.")}
    if family(task) == "revision":
        return {"summary": clean_text(packet.get("revision_summary") or p["goal"]), "strengths": p["points"][:2], "weaknesses": [p["mistake"]], "next_revision": clean_text(packet.get("next_step") or f"Review another {view} packet.")}
    if family(task) == "flashcard":
        return flashcard_output_for(concept, task)
    if family(task) == "mindmap":
        return {"center": name, "branches": [{"label": "Level", "items": [diff, source_level_for_difficulty(diff)]}, {"label": "Points", "items": p["points"][:4]}, {"label": "Example", "items": [shown_example]}, {"label": "Mistake", "items": [p["mistake"]]}]}
    if family(task) == "hint":
        return {"hint_type": task, "hint": clean_text(packet.get("hint") or f"Look back at the {diff} example and identify: {key}")}
    if family(task) == "feedback":
        fb = packet.get("feedback_template") or {}
        return {"correct": clean_text(fb.get("correct") or f"Correct: you used {key}."), "partial": clean_text(fb.get("partial") or f"Partly correct: connect it to {shown_example}."), "wrong": clean_text(fb.get("wrong") or f"Review: {p['mistake']}"), "next_step": clean_text(packet.get("next_step") or f"Continue with {view}.")}
    if family(task) == "doubt":
        return {"answer": f"For {name}, this packet teaches: {key}", "reason": p["definition"], "example": shown_example, "try_this": f"Answer one {diff} quick check about {name}."}
    if family(task) == "notebook":
        return {"summary": f"{name}: {key}", "strengths": p["points"][:2], "weaknesses": [p["mistake"]], "next_revision": clean_text(packet.get("next_step") or f"Review {view}.")}
    return {"title": f"{name} - {task}", "content": p["goal"], "example": shown_example, "key_points": p["points"], "quick_check": f"Explain {name}."}


def flashcard_output_for(concept: Dict[str, Any], task: str) -> Dict[str, Any]:
    name = concept["concept_name"]
    level_data = {level: level_parts(concept, level) for level in ["easy", "medium", "hard", "revision"]}
    variant_plans = {
        "flashcard": {
            "easy": ("definition", "What is the basic idea of {name}?", "{definition}"),
            "medium": ("practical rule", "What practical rule should guide {name}?", "{key}"),
            "hard": ("deeper idea", "What deeper idea matters when using {name}?", "{key}"),
            "revision": ("summary", "What should you remember about {name}?", "{goal}"),
        },
        "concept_recall_flashcard": {
            "easy": ("simple example", "What is a simple example of {name}?", "{example}"),
            "medium": ("syntax/code rule", "What syntax or code rule supports {name}?", "{example}"),
            "hard": ("edge case", "What edge case should you check for {name}?", "{mistake}"),
            "revision": ("weak point", "Which weak point should you review for {name}?", "{mistake}"),
        },
        "misconception_flashcard": {
            "easy": ("key point", "What key point prevents confusion about {name}?", "{key}"),
            "medium": ("output prediction", "What should you predict from the {name} example?", "{key}"),
            "hard": ("transfer use", "How can {name} transfer to another context?", "{real}"),
            "revision": ("mistake review", "What mistake should you avoid next time in {name}?", "{mistake}"),
        },
        "example_flashcard": {
            "easy": ("valid/invalid example", "What makes an example valid or invalid for {name}?", "{example}"),
            "medium": ("debug mistake", "What debug mistake should you spot in {name}?", "{mistake}"),
            "hard": ("challenge scenario", "What challenge scenario can test {name}?", "{real}"),
            "revision": ("retry card", "What should you retry for {name}?", "{example}"),
        },
        "debug_flashcard": {
            "easy": ("common beginner mistake", "What beginner mistake appears in {name}?", "{mistake}"),
            "medium": ("misconception correction", "How do you correct the misconception in {name}?", "{key}"),
            "hard": ("advanced misconception", "What advanced misconception can affect {name}?", "{mistake}"),
            "revision": ("memory cue", "What memory cue helps you recall {name}?", "{key}"),
        },
        "personal_flashcards": {
            "easy": ("quick check", "Quick check: what should you say about {name}?", "{key}"),
            "medium": ("code reasoning", "How should you reason about code using {name}?", "{example}"),
            "hard": ("real-world reasoning", "How does {name} support real-world reasoning?", "{real}"),
            "revision": ("next practice", "What should you practice next for {name}?", "{real}"),
        },
        "syntax_flashcard": {
            "easy": ("real-world use", "Where can you use {name} in the real world?", "{real}"),
            "medium": ("usage/naming rule", "What usage or naming rule helps with {name}?", "{key}"),
            "hard": ("compare/justify card", "How would you justify choosing {name}?", "{real}"),
            "revision": ("confidence check", "Confidence check: what proves you know {name}?", "{key}"),
        },
    }
    plan = variant_plans[task]
    cards_by_difficulty: Dict[str, Dict[str, Any]] = {}
    for level, (card_kind, front_template, back_template) in plan.items():
        data = level_data[level]
        values = {
            "name": name,
            "goal": data["goal"],
            "definition": data["definition"],
            "key": data["points"][0],
            "example": data["example"],
            "mistake": data["mistake"],
            "real": data["real"],
        }
        cards_by_difficulty[level] = {
            "card_kind": card_kind,
            "front": front_template.format(**values),
            "back": back_template.format(**values),
            "difficulty": level,
            "source_level": source_level_for_difficulty(level),
        }
    primary = cards_by_difficulty["revision" if task in {"flashcard", "concept_recall_flashcard", "misconception_flashcard", "example_flashcard", "personal_flashcards"} else "medium"]
    return {
        "front": primary["front"],
        "back": primary["back"],
        "card_kind": primary["card_kind"],
        "cards_by_difficulty": cards_by_difficulty,
        "all_level_flashcards": cards_by_difficulty,
    }


def row_for(concept: Dict[str, Any], task: str, packet_index: Dict[tuple, Dict[str, Any]]) -> Dict[str, Any]:
    diff = difficulty(task)
    view = teaching_view(task, diff)
    packet = packet_for(packet_index, concept, diff, view)
    out = output_for(concept, task, diff, view, packet)
    answer = out.get("answer", out.get("expected_output", out.get("back", "")))
    explanation = out.get("explanation", out.get("reason", "Generated from guarded concept resources."))
    row = {
        "domain": concept["domain"],
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "task_type": task,
        "task_family": family(task),
        "difficulty": diff,
        "source_level": source_level_for_difficulty(diff),
        "teaching_view": view,
        "linked_packet_id": packet.get("packet_id") or f"{safe_name(concept['domain'])}_{safe_name(concept['concept_id'])}_{diff}_{view}",
        "output": out,
        "answer": answer,
        "explanation": explanation,
        "alignment_reason": f"This {task} uses only {source_level_for_difficulty(diff)} and the linked {view} packet for {concept['concept_name']}.",
        "valid": True,
        "quality_score": 1.0,
        "issues": [],
        "raw_valid": False,
        "fallback_applied": True,
        "fallback_source": "concept_resources_guarded",
        "generation_source": "cognitutor_lm_guarded_product_generator",
    }
    if family(task) == "voice":
        row.update(
            {
                "audio_ready": out.get("audio_ready") is True,
                "script": out.get("script", ""),
                "voice_sections": out.get("voice_sections", {}),
                "estimated_duration_sec": out.get("estimated_duration_sec"),
            }
        )
        row["alignment_reason"] = out.get("alignment_reason") or row["alignment_reason"]
    apply_quality_gate(row, item_type="task")
    attach_version_metadata(row, source=row, concept_resource=concept, website_ready=row.get("website_ready", False))
    return row


def select_concepts(args: argparse.Namespace) -> List[Dict[str, Any]]:
    if args.all_concepts:
        return load_concept_resources()
    found = find_concept(args.domain or "", args.concept or "")
    return [found] if found else []


def markdown(rows: List[Dict[str, Any]]) -> str:
    lines = ["# CogniTutorLM All-89 Task Outputs", ""]
    for row in rows:
        lines += [
            f"## {row['domain']} / {row['concept_id']} / {row['concept_name']} / {row['task_type']}",
            f"- family: {row['task_family']}",
            f"- difficulty: {row['difficulty']}",
            f"- source_level: {row['source_level']}",
            f"- teaching_view: {row['teaching_view']}",
            "",
            "```json",
            json.dumps(row["output"], indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    return "\n".join(lines)


def write_grouped(rows: List[Dict[str, Any]]) -> None:
    BY_SUBJECT_DIR.mkdir(parents=True, exist_ok=True)
    BY_CONCEPT_DIR.mkdir(parents=True, exist_ok=True)
    by_subject: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_concept: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_subject[row["domain"]].append(row)
        stem = f"{safe_name(row['domain'])}_{safe_name(row['concept_id'])}_{safe_name(row['concept_name'])}"
        by_concept[stem].append(row)
    for domain, items in by_subject.items():
        stem = safe_name(domain)
        (BY_SUBJECT_DIR / f"{stem}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        (BY_SUBJECT_DIR / f"{stem}.md").write_text(markdown(items), encoding="utf-8")
    for stem, items in by_concept.items():
        (BY_CONCEPT_DIR / f"{stem}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        (BY_CONCEPT_DIR / f"{stem}.md").write_text(markdown(items), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain")
    parser.add_argument("--concept")
    parser.add_argument("--all-concepts", action="store_true")
    args = parser.parse_args()
    concepts = select_concepts(args)
    packet_index = load_packets()
    rows = [row_for(concept, task, packet_index) for concept in concepts for task in ALL_89_TASK_TYPES]
    ALL_TASK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ALL_TASK_OUTPUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    write_grouped(rows)
    print(f"Concepts: {len(concepts)}")
    print(f"Task types: {len(ALL_89_TASK_TYPES)}")
    print(f"Task outputs: {len(rows)}")
    print(f"Output: {ALL_TASK_OUTPUT}")
    print("STATUS: PASS" if len(rows) == len(concepts) * len(ALL_89_TASK_TYPES) and rows else "STATUS: FAIL")


if __name__ == "__main__":
    main()
