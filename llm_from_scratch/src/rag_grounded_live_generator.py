import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.generate import (
    clean_generated_answer,
    extract_json_object,
    generate_text,
    get_device,
    load_checkpoint,
)
from src.model_content_validator import repair_model_output, validate_model_output
from src.rag_connector import RagConnector
from src.tokenizer_wrapper import CogniTutorTokenizer


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = ROOT_DIR / "outputs" / "checkpoints" / "cognitutor_s_best.pt"


TASK_TOKENS = {
    "explanation": "<task_explanation>",
    "flashcard": "<task_flashcard>",
    "mcq": "<task_mcq>",
    "debug_task": "<task_debug>",
    "output_prediction": "<task_output_prediction>",
    "challenge_question": "<task_challenge>",
    "revision_summary": "<task_revision>",
}

DIFFICULTY_TOKENS = {
    "easy": "<easy>",
    "medium": "<medium>",
    "hard": "<hard>",
}

STYLE_TOKENS = {
    "simple": "<style_simple>",
    "code_first": "<style_code>",
    "step_by_step": "<style_step_by_step>",
    "challenge_based": "<style_challenge_based>",
    "revision_summary": "<style_revision_summary>",
}

FORMAT_RULES = {
    "explanation": "Concept:\nDefinition:\nExample:\nWhy it matters:",
    "flashcard": '{"front": "...", "back": "..."}',
    "mcq": '{"question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "explanation": "..."}',
    "debug_task": '{"buggy_code": "...", "expected_fix": "...", "hint": "...", "explanation": "..."}',
    "output_prediction": '{"code": "...", "question": "What is the output?", "answer": "...", "explanation": "..."}',
    "challenge_question": '{"challenge": "...", "solution_outline": "..."}',
    "revision_summary": "Summary:\nRemember:\nAvoid this mistake:",
}

FORMAT_EXAMPLES = {
    "explanation": (
        "Concept: Variables\n"
        "Definition: A variable is a name linked to a value or object.\n"
        "Example: x = 10 stores a reference to the integer object 10.\n"
        "Why it matters: Variables help name and reuse data in programs."
    ),
    "flashcard": '{"front": "What is a variable?", "back": "A variable is a name linked to a value or object."}',
    "mcq": (
        '{"question": "Which SQL command retrieves data?", '
        '"options": ["SELECT", "INSERT", "DELETE", "DROP"], '
        '"answer": "SELECT", "explanation": "SELECT retrieves data from tables."}'
    ),
    "debug_task": (
        '{"buggy_code": "2score = 10", "expected_fix": "score2 = 10", '
        '"hint": "Variable names cannot start with a digit.", '
        '"explanation": "Python variable names must start with a letter or underscore."}'
    ),
    "output_prediction": (
        '{"code": "x = 10\\nprint(x)", "question": "What is the output?", '
        '"answer": "10", "explanation": "print displays the value stored in x."}'
    ),
    "challenge_question": (
        '{"challenge": "Use a stack to reverse a list.", '
        '"solution_outline": "Push each item, then pop items to get reverse order."}'
    ),
    "revision_summary": (
        "Summary: A commit records a snapshot of staged changes.\n"
        "Remember: Use git add before git commit.\n"
        "Avoid this mistake: Do not confuse Git commits with GitHub uploads."
    ),
}

STRUCTURED_TASKS = {
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
}


def _clean_line(value: Any, max_chars: int = 160) -> str:
    text = str(value or "").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.lstrip("-*•0123456789. )\t").strip()
    return text[:max_chars].strip()


def _split_items(value: Any, max_items: int, max_chars: int = 160) -> List[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value or "").replace("\r", "\n")
        raw_items = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                raw_items.extend(part.strip() for part in line.split("|"))
            else:
                raw_items.append(line)

        if len(raw_items) <= 1 and ". " in text:
            raw_items = [part.strip() + "." for part in text.split(". ") if part.strip()]

    cleaned = []
    for item in raw_items:
        line = _clean_line(item, max_chars=max_chars)
        if line and line not in cleaned:
            cleaned.append(line)

    return cleaned[:max_items]


def _definition_lines(rag_result: Dict[str, Any]) -> List[str]:
    raw_definition = (
        rag_result.get("definition")
        or rag_result.get("definition_preview")
        or ""
    )

    lines = _split_items(raw_definition, max_items=3, max_chars=260)
    if lines:
        return lines

    for chunk in rag_result.get("chunks", []) or []:
        if str(chunk.get("section", "")).lower() == "definition":
            lines = _split_items(chunk.get("text"), max_items=3, max_chars=260)
            if lines:
                return lines

    context = rag_result.get("context_text") or ""
    return _split_items(context, max_items=3, max_chars=260)


def _section_items(rag_result: Dict[str, Any], section_name: str, max_items: int) -> List[str]:
    direct = _split_items(rag_result.get(section_name), max_items=max_items)
    if direct:
        return direct

    items = []
    for chunk in rag_result.get("chunks", []) or []:
        if str(chunk.get("section", "")).lower() == section_name.lower():
            items.extend(_split_items(chunk.get("text"), max_items=max_items))
        if len(items) >= max_items:
            break
    return items[:max_items]


def build_short_rag_context(rag_result: dict, max_chars: int = 700) -> dict:
    rag_result = rag_result or {}
    chunks = rag_result.get("chunks", []) or []
    retrieved_sections = []
    source_chunks_preview = []

    for chunk in chunks:
        section = str(chunk.get("section") or "context").strip()
        if section and section not in retrieved_sections:
            retrieved_sections.append(section)

        preview = _clean_line(
            chunk.get("text") or chunk.get("content") or chunk.get("preview"),
            max_chars=220,
        )
        if preview and len(source_chunks_preview) < 5:
            source_chunks_preview.append(
                {
                    "section": section,
                    "preview": preview,
                    "concept_id": chunk.get("concept_id") or rag_result.get("concept_id"),
                    "concept_name": chunk.get("concept_name") or rag_result.get("concept_name"),
                    "domain": chunk.get("domain") or rag_result.get("domain"),
                }
            )

    sections = [
        ("Definition", _definition_lines(rag_result)[:2]),
        ("Key points", _section_items(rag_result, "key_points", 3)),
        ("Example", _section_items(rag_result, "examples", 1)),
        ("Misconception", _section_items(rag_result, "misconceptions", 1)),
        ("Real-world use", _section_items(rag_result, "real_world_use", 1)),
    ]

    lines = []
    for title, items in sections:
        if not items:
            continue
        lines.append(f"{title}:")
        for item in items:
            lines.append(f"- {item}")

    context_text = "\n".join(lines).strip()
    if len(context_text) > max_chars:
        context_text = context_text[:max_chars].rsplit("\n", 1)[0].strip()

    return {
        "context_text": context_text,
        "retrieved_sections": retrieved_sections,
        "source_chunks_preview": source_chunks_preview,
    }


def build_compact_prompt(
    concept_name: str,
    domain: str,
    task_type: str,
    short_context: str,
    difficulty: str = "easy",
    teaching_style: str = "simple",
) -> str:
    task_token = TASK_TOKENS.get(task_type, f"<task_{task_type}>")
    difficulty_token = DIFFICULTY_TOKENS.get(difficulty, f"<{difficulty}>")
    style_token = STYLE_TOKENS.get(teaching_style, f"<style_{teaching_style}>")
    format_rule = FORMAT_RULES[task_type]
    format_example = FORMAT_EXAMPLES[task_type]

    return f"""<bos>
<instruction> Generate tutor output.
{task_token}
{difficulty_token}
{style_token}
<concept> {concept_name}
<domain> {domain}
<context>
{short_context}
</context>
<format_rule>
{format_rule}
</format_rule>
<format_example>
{format_example}
</format_example>
<answer>"""


def calculate_grounding_score(output: str, concept_name: str, context_text: str) -> float:
    text = str(output or "").lower()
    concept_words = {
        word
        for word in re.findall(r"[a-z0-9]+", str(concept_name or "").lower())
        if len(word) >= 4
    }
    context_words = {
        word
        for word in re.findall(r"[a-z0-9]+", str(context_text or "").lower())
        if len(word) >= 5
    }

    concept_hits = sum(1 for word in concept_words if word in text)
    context_hits = sum(1 for word in context_words if word in text)
    concept_score = concept_hits / max(len(concept_words), 1)
    context_score = min(context_hits / 6.0, 1.0)
    return round((0.65 * concept_score) + (0.35 * context_score), 4)


def quality_score(validation: Dict[str, Any]) -> float:
    if not validation.get("valid"):
        errors = len(validation.get("errors") or [])
        return round(max(0.0, 0.55 - (errors * 0.12)), 4)
    warnings = len(validation.get("warnings") or [])
    return round(max(0.0, 1.0 - (warnings * 0.1)), 4)


class RagGroundedLiveGenerator:
    def __init__(self, checkpoint_path: Optional[Path] = None):
        self.checkpoint_path = checkpoint_path or DEFAULT_CHECKPOINT
        self.device = get_device()
        self.model, _, _ = load_checkpoint(self.checkpoint_path, self.device)
        self.tokenizer = CogniTutorTokenizer()
        self.rag = RagConnector()

    def retrieve_context(
        self,
        query: str,
        concept_id: str,
        concept_name: str,
        domain: str,
        top_k: int = 5,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        rag_result = self.rag.get_rag_context(
            query=query,
            concept_id=concept_id,
            domain=domain,
            top_k=top_k,
        )
        if not rag_result.get("concept_name"):
            rag_result["concept_name"] = concept_name
        short_context = build_short_rag_context(rag_result)
        return rag_result, short_context

    def generate_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        concept_name = item["concept_name"]
        domain = item["domain"]
        task_type = item["task_type"]
        query = item.get("query") or f"{concept_name} {task_type} in {domain}"

        rag_result, short_context = self.retrieve_context(
            query=query,
            concept_id=item["concept_id"],
            concept_name=concept_name,
            domain=domain,
        )

        prompt = build_compact_prompt(
            concept_name=concept_name,
            domain=domain,
            task_type=task_type,
            short_context=short_context["context_text"],
            difficulty=item.get("difficulty", "easy"),
            teaching_style=item.get("teaching_style", "simple"),
        )

        max_tokens = item.get("max_new_tokens") or {
            "flashcard": 90,
            "mcq": 150,
            "debug_task": 150,
            "challenge_question": 120,
            "revision_summary": 120,
        }.get(task_type, 140)

        raw_output, _ = generate_text(
            model=self.model,
            tokenizer=self.tokenizer,
            prompt=prompt,
            device=self.device,
            max_new_tokens=max_tokens,
            temperature=item.get("temperature", 0.45),
            top_k=item.get("top_k", 35),
        )
        raw_output = clean_generated_answer(raw_output)
        if task_type in STRUCTURED_TASKS:
            raw_output = extract_json_object(raw_output)

        repair = repair_model_output(
            output=raw_output,
            task_type=task_type,
            concept_name=concept_name,
            domain=domain,
            context_text=short_context["context_text"],
        )
        output = repair["output"]

        grounding_score = calculate_grounding_score(
            output=output,
            concept_name=concept_name,
            context_text=short_context["context_text"],
        )
        validation = validate_model_output(
            task_type=task_type,
            generated_text=output,
            concept_name=concept_name,
            domain=domain,
            context_text=short_context["context_text"],
            grounding_score=grounding_score,
        )

        return {
            **item,
            "success": bool(raw_output),
            "raw_output": raw_output,
            "output": output,
            "repair_applied": repair["repaired"],
            "repair_notes": repair["repair_notes"],
            "prompt": prompt,
            "rag_status": rag_result.get("status"),
            "grounding_score": grounding_score,
            "quality_score": quality_score(validation),
            "valid": validation["valid"],
            "issues": validation.get("errors", []) + validation.get("warnings", []),
            "validation": validation,
            "retrieved_sections": short_context["retrieved_sections"],
            "source_chunks_preview": short_context["source_chunks_preview"],
            "short_context": short_context["context_text"],
        }
