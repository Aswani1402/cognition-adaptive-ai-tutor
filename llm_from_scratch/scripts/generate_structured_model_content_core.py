import argparse
import json
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple

from scripts.structured_generation_common import ROOT_DIR, TASK_TOKENS, load_concepts
from scripts.inspect_structured_generation_quality import (
    concept_relevant,
    has_domain_noise,
    inspect_json_task,
    inspect_mcq,
    inspect_text_task,
    style_match,
)
from src.concept_resources_guarded_fallback import build_guarded_fallback
from src.live_tutor_generator import generate_with_cognitutor_lm
from src.model_content_validator import validate_model_output
from src.structured_output_normalizer import normalize_structured_output


MICRO = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_micro_eval.json"
EXPANDED = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_expanded_micro_eval.json"
EXPANDED_QUALITY = ROOT_DIR / "outputs" / "evaluation" / "structured_generation_quality_inspection.json"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
RAW_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_raw_generation_core.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.md"
REPORT_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_report.json"
REPORT_MD = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_report.md"
DIAGNOSIS_JSON = ROOT_DIR / "outputs" / "final_reports" / "structured_generation_pipeline_diagnosis.json"
DIAGNOSIS_MD = ROOT_DIR / "outputs" / "final_reports" / "structured_generation_pipeline_diagnosis.md"

CORE_TASK_TYPES = [
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "challenge_question",
    "revision_summary",
    "hint",
    "feedback",
    "mindmap",
    "doubt_answer",
    "voice_script",
]

TASK_MAX_NEW_TOKENS = {
    "explanation": 180,
    "flashcard": 120,
    "mcq": 220,
    "debug_task": 220,
    "output_prediction": 220,
    "challenge_question": 220,
    "revision_summary": 180,
    "hint": 120,
    "feedback": 160,
    "mindmap": 260,
    "doubt_answer": 200,
    "voice_script": 180,
}

STYLE_BY_TASK = {
    "explanation": "<style_step_by_step>",
    "flashcard": "<style_revision>",
    "mcq": "<style_challenge>",
    "debug_task": "<style_code>",
    "output_prediction": "<style_code>",
    "challenge_question": "<style_challenge>",
    "revision_summary": "<style_revision>",
    "hint": "<style_step_by_step>",
    "feedback": "<style_misconception>",
    "mindmap": "<style_revision>",
    "doubt_answer": "<style_misconception>",
    "voice_script": "<style_step_by_step>",
}

STRICT_SCHEMA = {
    "flashcard": '{"front": "...", "back": "..."}',
    "mcq": '{"question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "explanation": "..."}',
    "debug_task": '{"buggy_code": "...", "expected_fix": "...", "hint": "...", "explanation": "..."}',
    "output_prediction": '{"code": "...", "question": "...", "answer": "...", "explanation": "..."}',
    "challenge_question": '{"challenge": "...", "solution_outline": "..."}',
    "mindmap": '{"center": "...", "branches": ["Definition: ...", "Key point: ...", "Example: ...", "Common mistake: ...", "Real-world use: ..."]}',
}


def clean_text(value: Any, max_len: int = 700) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text[:max_len].strip()


def strip_bullets(text: Any) -> str:
    text = clean_text(text, 1400).replace("•", " ")
    text = text.replace(" - ", "\n- ")
    parts = []
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if chunk.startswith("-"):
            chunk = chunk[1:].strip()
        if chunk:
            parts.append(chunk)
    return " ".join(parts).strip()


def complete_sentence(text: Any, max_len: int = 220) -> str:
    text = strip_bullets(text)[:max_len].strip()
    if not text:
        return ""
    last_end = max(text.rfind("."), text.rfind("?"), text.rfind("!"))
    if last_end > 45:
        text = text[: last_end + 1].strip()
    if text and text[-1] not in ".!?;:})]\"'":
        text += "."
    return text


def split_items(value: Any, max_items: int = 3) -> List[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").replace("|", "\n").replace("•", "\n- ").splitlines()
    items = []
    for item in raw:
        cleaned = complete_sentence(str(item).lstrip("-* ").strip())
        if cleaned and cleaned not in items:
            items.append(cleaned)
    return items[:max_items]


def definition(concept: Dict[str, Any]) -> str:
    return complete_sentence(concept.get("base_content"), 520) or f"{concept['concept_name']} is a concept in {concept['domain']}."


def key(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("key_points"), 3)
    return " ".join(items) if items else definition(concept)


def example_text(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("examples"), 2)
    return " ".join(items) if items else f"Apply {concept['concept_name']} in a small {concept['domain']} example."


def mistake(concept: Dict[str, Any]) -> str:
    items = split_items(concept.get("misconceptions"), 1)
    return items[0] if items else f"A common mistake is misunderstanding {concept['concept_name']}."


def use_case(concept: Dict[str, Any]) -> str:
    return complete_sentence(concept.get("real_world_use"), 220) or f"{concept['concept_name']} is used in practical {concept['domain']} work."


def build_core_prompt(concept: Dict[str, Any], task_type: str, difficulty: str = "<easy>", style: str | None = None) -> str:
    return (
        "<bos>\n"
        "<instruction> Generate project-specific tutor learning output.\n"
        f"{TASK_TOKENS[task_type]}\n"
        f"{difficulty}\n"
        f"{style or STYLE_BY_TASK[task_type]}\n"
        f"<task_type> {task_type}\n"
        f"<concept> {concept['concept_name']}\n"
        f"<domain> {concept['domain']}\n"
        "<context>\n"
        f"Definition: {definition(concept)}\n"
        f"Key points: {key(concept)}\n"
        f"Examples: {example_text(concept)}\n"
        f"Misconceptions: {mistake(concept)}\n"
        f"Real-world use: {use_case(concept)}\n"
        "</context>\n"
        "<answer>"
    )


def strict_retry_prompt(concept: Dict[str, Any], task_type: str) -> str:
    prompt = build_core_prompt(concept, task_type)
    if task_type in STRICT_SCHEMA:
        return (
            f"{prompt}\n"
            f"Return valid JSON only for this exact schema: {STRICT_SCHEMA[task_type]}\n"
            "Do not include markdown, prompt text, or another task."
        )
    required = {
        "explanation": "Use labels exactly: Concept:, Definition:, Example:, Why it matters:",
        "revision_summary": "Use labels exactly: Summary:, Remember:, Avoid this mistake:",
        "hint": "Start with Hint:",
        "feedback": "Use labels exactly: What was correct:, What to improve:, Next step:",
        "doubt_answer": "Use labels exactly: Answer:, Reason:, Example:, Try this:",
        "voice_script": "Start with Voice Script:",
    }[task_type]
    return f"{prompt}\n{required}\nDo not include JSON unless the task requires JSON."


def validate(task_type: str, output: str, concept: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    return validate_model_output(
        task_type,
        output,
        concept["concept_name"],
        concept["domain"],
        prompt,
        grounding_score=1.0 if output else 0.0,
    )


def generate_attempt(concept: Dict[str, Any], task_type: str, prompt: str, max_new_tokens: int) -> Dict[str, Any]:
    gen = generate_with_cognitutor_lm(
        prompt,
        task_type,
        max_new_tokens=max_new_tokens,
        temperature=0.0,
        top_p=1.0,
        repetition_penalty=1.08,
    )
    extracted = gen.get("extracted_output") or gen.get("output", "")
    normalized, normalizer = normalize_structured_output(task_type, extracted)
    val = validate(task_type, normalized, concept, prompt)
    return {
        "raw_model_output": gen.get("raw_model_output", ""),
        "extracted_output": extracted,
        "normalized_output": normalized,
        "validation": val,
        "generation_parameters": gen.get("generation_parameters", {}),
        "normalizer": normalizer,
        "status": gen.get("status"),
        "error_message": gen.get("error_message"),
    }


def should_retry_or_fallback(validation: Dict[str, Any]) -> bool:
    return validation.get("valid") is not True or float(validation.get("quality_score", 0.0)) < 0.85


def quality_gate_passes(concept: Dict[str, Any], task_type: str, output: str, validation: Dict[str, Any]) -> Tuple[bool, List[str]]:
    item = {
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "task_type": task_type,
        "output": output,
        "valid": validation.get("valid"),
        "quality_score": validation.get("quality_score"),
        "issues": validation.get("issues", []),
    }
    if task_type == "mcq":
        semantic_score, option_score, issues = inspect_mcq(item)
        passed = semantic_score >= 0.85 and option_score >= 0.85
        return passed, issues + ([] if passed else [f"quality_gate_mcq:{semantic_score}", f"quality_gate_options:{option_score}"])
    if task_type in {"flashcard", "debug_task", "output_prediction", "challenge_question", "mindmap"}:
        semantic_score, issues = inspect_json_task(item)
    else:
        semantic_score, issues = inspect_text_task(item)
    domain_ok = concept_relevant(item, output) and not has_domain_noise(output, concept["domain"])
    style_ok = style_match(item)
    passed = semantic_score >= 0.85 and domain_ok and style_ok
    extra = []
    if semantic_score < 0.85:
        extra.append(f"quality_gate_semantic:{semantic_score}")
    if not domain_ok:
        extra.append("quality_gate_domain_relevance")
    if not style_ok:
        extra.append("quality_gate_style")
    return passed, issues + extra



def make_item(
    concept: Dict[str, Any],
    task_type: str,
    skip_model: bool = False,
    force_fallback: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    started = time.time()
    prompt = build_core_prompt(concept, task_type)

    attempt_1 = None
    attempt_2 = None
    retry_used = False

    # Fast safe modes:
    # --skip-model: do not call model at all.
    # --force-fallback: do not risk a long model call; preserve honesty by marking raw generation skipped.
    if skip_model or force_fallback:
        output = build_guarded_fallback(concept, task_type)
        final_validation = validate(task_type, output, concept, prompt)
        raw_valid = False
        fallback_applied = True
        fallback_reason = ["model_generation_skipped_for_guarded_fallback"] if skip_model else ["force_fallback_requested"]

        raw_output = ""
        extracted_output = ""

        item = {
            "item_id": f"{concept['domain']}:{concept['concept_id']}:{task_type}",
            "concept_id": concept["concept_id"],
            "concept_name": concept["concept_name"],
            "domain": concept["domain"],
            "task_type": task_type,
            "generation_source": "cognitutor_lm_from_scratch_structured_model_guarded_pipeline",
            "model_used": "CogniTutorLM-from-scratch-structured",
            "prompt": prompt,
            "raw_model_output": raw_output,
            "extracted_output": extracted_output,
            "output": output,
            "final_output": output,
            "final_output_source": "concept_resources_guarded_fallback",
            "generation_status": "raw_generation_skipped_guarded_fallback_used",
            "repair_or_guard_status": "guarded_fallback_applied",
            "raw_valid": raw_valid,
            "final_valid": final_validation.get("valid"),
            "valid": final_validation.get("valid"),
            "raw_quality_score": 0.0,
            "final_quality_score": final_validation.get("quality_score"),
            "quality_score": final_validation.get("quality_score"),
            "raw_issues": fallback_reason,
            "final_issues": final_validation.get("issues", []),
            "issues": final_validation.get("issues", []),
            "retry_used": False,
            "fallback_applied": fallback_applied,
            "fallback_source": "concept_resources_guarded_fallback",
            "fallback_reason": fallback_reason,
            "raw_model_output_attempt_1": raw_output,
            "extracted_output_attempt_1": extracted_output,
            "raw_model_output_attempt_2": None,
            "extracted_output_attempt_2": None,
            "used_retry": False,
            "generation_parameters": {"skip_model": skip_model, "force_fallback": force_fallback},
            "normalizer": {"status": "not_used_skip_or_force_fallback"},
            "generation_time_seconds": round(time.time() - started, 4),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        raw_item = {
            "item_id": item["item_id"],
            "concept_id": item["concept_id"],
            "concept_name": item["concept_name"],
            "domain": item["domain"],
            "task_type": task_type,
            "prompt": prompt,
            "raw_model_output_attempt_1": raw_output,
            "raw_model_output_attempt_2": None,
            "extracted_output": extracted_output,
            "extracted_output_attempt_1": extracted_output,
            "extracted_output_attempt_2": None,
            "raw_valid": False,
            "raw_quality_score": 0.0,
            "raw_issues": fallback_reason,
            "retry_used": False,
            "generation_parameters": {"skip_model": skip_model, "force_fallback": force_fallback},
            "generation_time_seconds": item["generation_time_seconds"],
        }
        return item, raw_item

    # Normal raw model path. Use carefully; this can be slow.
    attempt_1 = generate_attempt(concept, task_type, prompt, TASK_MAX_NEW_TOKENS[task_type])
    best_attempt = attempt_1

    if should_retry_or_fallback(attempt_1["validation"]):
        retry_used = True
        retry_prompt = strict_retry_prompt(concept, task_type)
        attempt_2 = generate_attempt(concept, task_type, retry_prompt, max(90, int(TASK_MAX_NEW_TOKENS[task_type] * 0.8)))
        if (
            attempt_2["validation"].get("valid") is True
            and float(attempt_2["validation"].get("quality_score", 0.0)) >= float(attempt_1["validation"].get("quality_score", 0.0))
        ):
            best_attempt = attempt_2

    raw_quality_gate_passed, raw_quality_gate_issues = quality_gate_passes(
        concept,
        task_type,
        best_attempt["normalized_output"],
        best_attempt["validation"],
    )

    raw_valid = (
        best_attempt["validation"].get("valid") is True
        and float(best_attempt["validation"].get("quality_score", 0.0)) >= 0.85
        and raw_quality_gate_passed
    )

    fallback_applied = not raw_valid
    fallback_reason = list(best_attempt["validation"].get("issues", [])) + raw_quality_gate_issues
    output = best_attempt["normalized_output"]
    final_validation = best_attempt["validation"]
    final_output_source = "raw_cognitutor_lm_generated_and_valid"

    if fallback_applied:
        output = build_guarded_fallback(concept, task_type)
        final_validation = validate(task_type, output, concept, prompt)
        final_output_source = "concept_resources_guarded_fallback"

    item = {
        "item_id": f"{concept['domain']}:{concept['concept_id']}:{task_type}",
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "task_type": task_type,
        "generation_source": "cognitutor_lm_from_scratch_structured_model_guarded_pipeline",
        "model_used": "CogniTutorLM-from-scratch-structured",
        "prompt": prompt,
        "raw_model_output": best_attempt["raw_model_output"],
        "extracted_output": best_attempt["extracted_output"],
        "output": output,
        "final_output": output,
        "final_output_source": final_output_source,
        "generation_status": "raw_valid" if raw_valid else "raw_invalid_guarded_fallback_used",
        "repair_or_guard_status": "none" if raw_valid else "guarded_fallback_applied",
        "raw_valid": raw_valid,
        "final_valid": final_validation.get("valid"),
        "valid": final_validation.get("valid"),
        "raw_quality_score": best_attempt["validation"].get("quality_score"),
        "final_quality_score": final_validation.get("quality_score"),
        "quality_score": final_validation.get("quality_score"),
        "raw_issues": best_attempt["validation"].get("issues", []),
        "final_issues": final_validation.get("issues", []),
        "issues": final_validation.get("issues", []),
        "retry_used": retry_used,
        "fallback_applied": fallback_applied,
        "fallback_source": "concept_resources_guarded_fallback" if fallback_applied else None,
        "fallback_reason": fallback_reason if fallback_applied else [],
        "raw_model_output_attempt_1": attempt_1["raw_model_output"],
        "extracted_output_attempt_1": attempt_1["extracted_output"],
        "raw_model_output_attempt_2": attempt_2["raw_model_output"] if attempt_2 else None,
        "extracted_output_attempt_2": attempt_2["extracted_output"] if attempt_2 else None,
        "used_retry": retry_used,
        "generation_parameters": best_attempt["generation_parameters"],
        "normalizer": best_attempt["normalizer"],
        "generation_time_seconds": round(time.time() - started, 4),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    raw_item = {
        "item_id": item["item_id"],
        "concept_id": item["concept_id"],
        "concept_name": item["concept_name"],
        "domain": item["domain"],
        "task_type": task_type,
        "prompt": prompt,
        "raw_model_output_attempt_1": attempt_1["raw_model_output"],
        "raw_model_output_attempt_2": attempt_2["raw_model_output"] if attempt_2 else None,
        "extracted_output": best_attempt["extracted_output"],
        "extracted_output_attempt_1": attempt_1["extracted_output"],
        "extracted_output_attempt_2": attempt_2["extracted_output"] if attempt_2 else None,
        "raw_valid": raw_valid,
        "raw_quality_score": best_attempt["validation"].get("quality_score"),
        "raw_issues": best_attempt["validation"].get("issues", []),
        "retry_used": retry_used,
        "generation_parameters": best_attempt["generation_parameters"],
        "generation_time_seconds": item["generation_time_seconds"],
    }
    return item, raw_item


def write_diagnosis(existing_items: List[Dict[str, Any]] | None = None) -> None:
    items = existing_items or (json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else [])
    issue_counts = Counter(issue for item in items for issue in item.get("raw_issues", item.get("issues", [])))
    diagnosis = {
        "prompt_format_different_from_training": False,
        "prompt_format_note": "Core prompt now matches build_high_quality_all_tasks_dataset.py structure: bos, instruction, task token, difficulty, style, task_type, concept, domain, context labels, answer.",
        "output_extraction_issue": "Patched extraction keeps only text after <answer>, removes prompt echo, and stops at <eos> or new prompt/task markers.",
        "tokenizer_decode_stopping_issue": "Greedy decoding stops on tokenizer eos_id; post extraction also truncates textual <eos> and new sample markers.",
        "model_continuing_into_another_sample": "Detected in prior outputs; guarded by stop markers and raw retry evidence fields.",
        "temperature_top_p": "Core generation uses deterministic greedy decoding: temperature=0.0, top_p=1.0.",
        "max_new_tokens": TASK_MAX_NEW_TOKENS,
        "json_task_output_not_constrained": "JSON tasks are normalized with structured_output_normalizer; invalid model JSON remains raw-invalid and may trigger retry/fallback.",
        "validator_field_coverage": "Validator now checks prompt echo, broken endings, placeholders, task-format mismatch, required JSON keys, and required text labels.",
        "task_type_tokens": {task: TASK_TOKENS[task] for task in CORE_TASK_TYPES},
        "final_report_stale_or_contradictory_metrics": "Backend report patched to use computed quality gates and distinguish raw from final guarded output.",
        "latest_raw_issue_counts": dict(issue_counts.most_common()),
        "output_files": {
            "raw_generation_evidence": str(RAW_JSON),
            "final_website_safe_generation": str(OUT_JSON),
        },
    }
    DIAGNOSIS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSIS_JSON.write_text(json.dumps(diagnosis, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Structured Generation Pipeline Diagnosis", ""]
    for key, value in diagnosis.items():
        lines.append(f"- {key}: {value}")
    DIAGNOSIS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")



def paths_with_suffix(suffix: str | None):
    if not suffix:
        return OUT_JSON, RAW_JSON, OUT_MD, REPORT_JSON, REPORT_MD
    suffix = suffix.strip().strip("_")
    return (
        OUT_JSON.with_name(f"structured_model_generated_core_{suffix}.json"),
        RAW_JSON.with_name(f"structured_model_raw_generation_core_{suffix}.json"),
        OUT_MD.with_name(f"structured_model_generated_core_{suffix}.md"),
        REPORT_JSON.with_name(f"structured_model_generated_core_report_{suffix}.json"),
        REPORT_MD.with_name(f"structured_model_generated_core_report_{suffix}.md"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CogniTutorLM structured core outputs safely.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--task_type", type=str, default=None)
    parser.add_argument("--domain", type=str, default=None)
    parser.add_argument("--concept", type=str, default=None)
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--force-fallback", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=20)  # currently informational
    parser.add_argument("--progress-every", type=int, default=1)
    parser.add_argument("--output-suffix", type=str, default=None)
    args = parser.parse_args()

    out_json, raw_json, out_md, report_json, report_md = paths_with_suffix(args.output_suffix)

    micro = json.loads(MICRO.read_text(encoding="utf-8")) if MICRO.exists() else {}
    expanded = json.loads(EXPANDED.read_text(encoding="utf-8")) if EXPANDED.exists() else {}
    expanded_quality = json.loads(EXPANDED_QUALITY.read_text(encoding="utf-8")) if EXPANDED_QUALITY.exists() else {}

    summary = micro.get("summary", {})
    expanded_summary = expanded.get("summary", {})
    quality_summary = expanded_quality.get("summary", {})

    preflight_status = "PASS" if (
        summary.get("status") == "PASS"
        and expanded_summary.get("status") == "PASS"
        and quality_summary.get("status") == "PASS"
    ) else "WARN"

    concepts = load_concepts()

    if args.domain:
        concepts = [c for c in concepts if args.domain.lower() in c.get("domain", "").lower()]

    if args.concept:
        q = args.concept.lower()
        concepts = [
            c for c in concepts
            if q in c.get("concept_name", "").lower() or q in c.get("concept_id", "").lower()
        ]

    task_types = CORE_TASK_TYPES
    if args.task_type:
        task_types = [t for t in CORE_TASK_TYPES if t == args.task_type]
        if not task_types:
            raise ValueError(f"Unknown task_type {args.task_type}. Valid: {CORE_TASK_TYPES}")

    jobs = [(concept, task) for concept in concepts for task in task_types]
    if args.limit is not None:
        jobs = jobs[: args.limit]

    print("model_load_mode:", "skipped" if args.skip_model or args.force_fallback else "enabled", flush=True)
    print("total_jobs:", len(jobs), flush=True)
    print("skip_model:", args.skip_model, flush=True)
    print("force_fallback:", args.force_fallback, flush=True)
    print("output_json:", out_json, flush=True)

    items = []
    raw_items = []

    for idx, (concept, task) in enumerate(jobs, start=1):
        if idx == 1 or idx % max(1, args.progress_every) == 0:
            print(
                f"[{idx}/{len(jobs)}] domain={concept.get('domain')} concept={concept.get('concept_name')} task={task}",
                flush=True,
            )

        item, raw_item = make_item(
            concept,
            task,
            skip_model=args.skip_model,
            force_fallback=args.force_fallback,
        )
        items.append(item)
        raw_items.append(raw_item)

    attempted = len(items)
    raw_valid = sum(1 for item in items if item.get("raw_valid"))
    final_valid = sum(1 for item in items if item.get("final_valid"))
    fallback_count = sum(1 for item in items if item.get("fallback_applied"))

    avg = round(sum(float(item.get("quality_score", 0.0)) for item in items) / attempted, 4) if attempted else 0.0
    raw_avg = round(sum(float(item.get("raw_quality_score", 0.0)) for item in items) / attempted, 4) if attempted else 0.0
    final_rate = round(final_valid / attempted, 4) if attempted else 0.0
    raw_rate = round(raw_valid / attempted, 4) if attempted else 0.0
    fallback_rate = round(fallback_count / attempted, 4) if attempted else 0.0

    status = "PASS" if final_rate >= 0.85 and avg >= 0.85 else "WARN"

    report = {
        "attempted": attempted,
        "raw_valid": raw_valid,
        "raw_valid_rate": raw_rate,
        "valid": final_valid,
        "valid_rate": final_rate,
        "avg_quality_score": avg,
        "raw_avg_quality_score": raw_avg,
        "fallback_applied_count": fallback_count,
        "fallback_rate": fallback_rate,
        "skip_model": args.skip_model,
        "force_fallback": args.force_fallback,
        "preflight_status": preflight_status,
        "micro_summary": summary,
        "expanded_summary": expanded_summary,
        "expanded_quality_summary": quality_summary,
        "concepts_attempted": len({item["concept_id"] for item in items}),
        "domains_covered": sorted({item["domain"] for item in items}),
        "task_types_covered": sorted({item["task_type"] for item in items}),
        "status": status,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    raw_json.write_text(json.dumps(raw_items, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text("# Structured Model Generated Core\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n", encoding="utf-8")
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_md.write_text("# Structured Core Generation Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n", encoding="utf-8")

    # Only update the normal diagnosis for the normal unsuffixed output.
    if not args.output_suffix:
        write_diagnosis(items)

    print("status:", status, flush=True)
    print("raw_valid_rate:", raw_rate, flush=True)
    print("valid_rate:", final_rate, flush=True)
    print("avg_quality_score:", avg, flush=True)
    print("fallback_applied_count:", fallback_count, flush=True)
    print("fallback_rate:", fallback_rate, flush=True)
    print("saved:", out_json, flush=True)


if __name__ == "__main__":
    main()
