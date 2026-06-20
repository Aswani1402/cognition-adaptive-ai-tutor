from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"

CONCEPTS = [
    {"subject": "Python", "concept_id": "P1", "concept": "Variables", "terms": ["variable", "value"]},
    {"subject": "SQL / Database", "concept_id": "S1", "concept": "Database Basics", "terms": ["database", "data"]},
    {"subject": "HTML/Web Basics", "concept_id": "H2", "concept": "Tags and Elements", "terms": ["tag", "element"]},
    {"subject": "Git", "concept_id": "G2", "concept": "Git Repositories", "terms": ["git", "repository"]},
    {"subject": "Data Structures", "concept_id": "D1", "concept": "Arrays", "terms": ["array", "index"]},
]

TASK_TYPES = [
    "explanation",
    "mcq",
    "flashcard",
    "hint",
    "revision_summary",
    "output_prediction",
    "debug_task",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def stable_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def try_raw_cognitutor(concept: dict[str, Any]) -> dict[str, Any]:
    sys_path_snapshot = list(sys.path)
    scripts_module_snapshot = sys.modules.get("scripts")
    try:
        from tutor.generation.cognitutor_lm_connector import get_cognitutor_teaching_packet

        raw = get_cognitutor_teaching_packet(
            domain=concept["subject"],
            concept_name=concept["concept"],
            concept_id=concept["concept_id"],
            difficulty="easy",
            teaching_view="definition_view",
        )
        status = raw.get("status") if isinstance(raw, dict) else None
        return {
            "attempted": True,
            "available": status == "success",
            "valid": status == "success" and bool(raw),
            "status": status,
            "error": None if status == "success" else (raw.get("error") or raw.get("reason") if isinstance(raw, dict) else "Invalid raw response"),
            "raw": raw,
        }
    except Exception as exc:
        return {
            "attempted": True,
            "available": False,
            "valid": False,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "raw": None,
        }
    finally:
        # The external CogniTutorLM connector intentionally adjusts sys.path to
        # reach the sibling project. Restore it so this repo's local scripts
        # package remains importable for fallback/backend modules.
        sys.path[:] = sys_path_snapshot
        if scripts_module_snapshot is not None:
            sys.modules["scripts"] = scripts_module_snapshot
        else:
            sys.modules.pop("scripts", None)


def rag_grounding(subject: str, concept: str, terms: list[str], output: Any) -> dict[str, Any]:
    try:
        from tutor.rag.rag_context_builder import RAGContextBuilder

        resource = RAGContextBuilder().build_context(f"{subject} {concept}", top_k=8, preferred_domain=subject)
        chunks = resource.get("retrieved_chunks", []) if isinstance(resource, dict) else []
        domain = resource.get("domain") or (chunks[0].get("domain") if chunks else None)
        topic = resource.get("topic") or (chunks[0].get("topic") if chunks else None)
        evidence = " ".join(
            [str(domain or ""), str(topic or ""), json.dumps(output, ensure_ascii=True, default=str)]
            + [str(chunk.get("content") or "") for chunk in chunks]
        ).lower()
        covered = [term for term in terms if term in evidence or term.rstrip("s") in evidence]
        expected_domain = normalize(subject).split("/")[0].strip()
        domain_match = expected_domain in normalize(domain)
        success = bool(chunks) and domain_match and len(covered) >= max(1, min(2, len(terms)))
        return {
            "success": success,
            "domain": domain,
            "topic": topic,
            "retrieved_sections": sorted({str(chunk.get("section")) for chunk in chunks if chunk.get("section")}),
            "covered_terms": covered,
            "notes": "Local RAG domain and key concept terms matched." if success else "Local RAG check did not fully match domain/terms.",
        }
    except Exception as exc:
        return {
            "success": False,
            "domain": None,
            "topic": None,
            "retrieved_sections": [],
            "covered_terms": [],
            "notes": f"RAG unavailable: {type(exc).__name__}: {exc}",
        }


def fallback_output(concept: dict[str, Any], task_type: str) -> tuple[Any, str | None]:
    try:
        from tutor.api.concept_content_resolver import (
            assessment_payload,
            build_flashcards,
            build_hints,
            build_lesson_payload,
            resolve_concept_content,
        )

        subject = concept["subject"]
        concept_id = concept["concept_id"]
        if task_type == "explanation":
            lesson = build_lesson_payload(subject, concept_id, difficulty="easy", view="definition_view")
            return {
                "title": lesson.get("teaching_content", {}).get("title"),
                "explanation": lesson.get("adaptive_explanation"),
                "key_points": lesson.get("keyPoints"),
                "source": lesson.get("llm_generation"),
            }, None
        if task_type == "revision_summary":
            lesson = build_lesson_payload(subject, concept_id, difficulty="easy", view="revision_summary_view")
            return {
                "title": lesson.get("teaching_content", {}).get("title"),
                "summary": lesson.get("adaptive_explanation"),
                "practice_prompt": lesson.get("teaching_content", {}).get("practice_prompt"),
                "source": lesson.get("llm_generation"),
            }, None
        if task_type == "flashcard":
            cards = build_flashcards(subject, concept_id).get("flashcards") or []
            return {"cards": cards[:2], "source": "concept_resource_fallback"}, None
        if task_type == "hint":
            hint = build_hints(subject, concept_id, question_type="mcq", hint_count=0)
            return {
                "hint_type": hint.get("hint_type"),
                "hint_text": hint.get("hint_text"),
                "worked_example": hint.get("worked_example"),
                "source": hint.get("llm_generation"),
            }, None
        assessment = assessment_payload(subject, concept_id, difficulty="medium")
        questions = assessment.get("questions") or []
        if task_type == "mcq":
            selected = next((q for q in questions if q.get("question_type") == "mcq"), None)
        elif task_type == "output_prediction":
            selected = next((q for q in questions if q.get("question_type") == "output_prediction"), None)
        else:
            selected = next((q for q in questions if q.get("question_type") == "debug_task"), None)
        if selected:
            return {"question": selected, "source": "concept_resource_validated_fallback"}, None
        content = resolve_concept_content(subject, concept_id)
        return {
            "prompt": f"Explain {content['concept_name']} in {content['subject']}.",
            "expected_answer": content.get("base_content"),
            "source": "minimal_concept_resource_fallback",
        }, "Requested structured task was not found; returned minimal concept fallback."
    except Exception as exc:
        return None, f"Fallback generation failed: {type(exc).__name__}: {exc}"


def format_valid(task_type: str, output: Any) -> tuple[bool, str]:
    if not isinstance(output, dict):
        return False, "Output is not a dictionary."
    if task_type in {"explanation", "revision_summary"}:
        text = output.get("explanation") or output.get("summary")
        return bool(text), "Explanation/summary text present." if text else "Missing explanation/summary text."
    if task_type == "flashcard":
        cards = output.get("cards") or []
        ok = bool(cards) and all(card.get("front") and card.get("back") for card in cards if isinstance(card, dict))
        return ok, "Flashcard front/back present." if ok else "Missing flashcard front/back."
    if task_type == "hint":
        return bool(output.get("hint_text")), "Hint text present." if output.get("hint_text") else "Missing hint text."
    question = output.get("question") if isinstance(output.get("question"), dict) else output
    if task_type == "mcq":
        return bool(question.get("options") and question.get("expected_answer")), "MCQ options and answer present."
    if task_type == "output_prediction":
        return bool(question.get("code") or question.get("code_snippet")) and bool(question.get("expected_answer")), "Output-prediction code and answer present."
    if task_type == "debug_task":
        return bool(question.get("buggy_code") or question.get("starter_code")) and bool(question.get("expected_answer")), "Debug code and answer present."
    return bool(output), "Generic non-empty output."


def run_case(concept: dict[str, Any], task_type: str, raw_probe: dict[str, Any], seen_hashes: set[str]) -> dict[str, Any]:
    output, fallback_reason = fallback_output(concept, task_type)
    fmt_ok, fmt_notes = format_valid(task_type, output)
    grounding = rag_grounding(concept["subject"], concept["concept"], concept["terms"], output)
    h = stable_hash(output)
    repetition_ok = h not in seen_hashes
    seen_hashes.add(h)
    final_valid = bool(fmt_ok and grounding["success"] and repetition_ok and output is not None)
    return {
        "subject": concept["subject"],
        "concept_id": concept["concept_id"],
        "concept": concept["concept"],
        "task_type": task_type,
        "raw_model_attempted": raw_probe.get("attempted"),
        "raw_model_available": raw_probe.get("available"),
        "raw_model_valid": raw_probe.get("valid"),
        "fallback_used": True,
        "fallback_reason": fallback_reason or "Validated local concept/RAG fallback used for final learner-facing output.",
        "final_output": output,
        "format_valid": fmt_ok,
        "format_notes": fmt_notes,
        "grounding": grounding,
        "repetition_pass": repetition_ok,
        "final_safe_output": final_valid,
    }


def write_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Final CogniTutorLM Guarded Generation Evaluation",
        "",
        f"Generated at: `{payload['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Total cases: `{payload['total_cases']}`",
        f"- Model available: `{payload['model_available']}`",
        f"- Raw model attempts: `{payload['raw_model_attempts']}`",
        f"- Raw valid outputs: `{payload['raw_valid_outputs']}`",
        f"- Raw invalid outputs: `{payload['raw_invalid_outputs']}`",
        f"- Fallback used: `{payload['fallback_used']}`",
        f"- Final valid outputs: `{payload['final_valid_outputs']}`",
        f"- Format validity rate: `{payload['format_validity_rate']}`",
        f"- Grounding pass rate: `{payload['grounding_pass_rate']}`",
        f"- Repetition pass rate: `{payload['repetition_pass_rate']}`",
        f"- Final safe output rate: `{payload['final_safe_output_rate']}`",
        "",
        "## Task Success By Type",
        "",
        "| Task type | Passed | Total | Rate |",
        "|---|---:|---:|---:|",
    ]
    for task_type, stats in payload["task_success_by_type"].items():
        lines.append(f"| {task_type} | {stats['passed']} | {stats['total']} | {stats['rate']} |")
    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Subject | Concept | Task | Format | Grounded | Repetition | Final safe | Notes |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for case in payload["cases"]:
        lines.append(
            "| {subject} | {concept} | {task} | {format_ok} | {grounded} | {repeat} | {safe} | {notes} |".format(
                subject=case["subject"],
                concept=case["concept"],
                task=case["task_type"],
                format_ok=case["format_valid"],
                grounded=case["grounding"]["success"],
                repeat=case["repetition_pass"],
                safe=case["final_safe_output"],
                notes=case["fallback_reason"],
            )
        )
    lines.extend(
        [
            "",
            "## Honest Interpretation",
            "",
            "- CogniTutorLM is treated as an optional domain-specific tutor generation component.",
            "- Raw CogniTutorLM output is not required for the final demo.",
            "- Final learner-facing output in this check uses validated local concept resources, RAG grounding checks, format validation, and fallback.",
            "- This is not evidence that CogniTutorLM is a ChatGPT-level LLM or that generation quality was classroom-proven.",
        ]
    )
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in payload["errors"]:
            lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    raw_probes = {concept["concept_id"]: try_raw_cognitutor(concept) for concept in CONCEPTS}
    seen_hashes: set[str] = set()
    cases = [
        run_case(concept, task_type, raw_probes[concept["concept_id"]], seen_hashes)
        for concept in CONCEPTS
        for task_type in TASK_TYPES
    ]

    raw_model_attempts = len(raw_probes)
    raw_valid_outputs = sum(1 for probe in raw_probes.values() if probe.get("valid"))
    raw_invalid_outputs = raw_model_attempts - raw_valid_outputs
    total = len(cases)
    final_valid_outputs = sum(1 for case in cases if case["final_safe_output"])
    format_valid_count = sum(1 for case in cases if case["format_valid"])
    grounding_pass_count = sum(1 for case in cases if case["grounding"]["success"])
    repetition_pass_count = sum(1 for case in cases if case["repetition_pass"])
    fallback_used = sum(1 for case in cases if case["fallback_used"])
    task_success_by_type: dict[str, dict[str, Any]] = {}
    for task_type in TASK_TYPES:
        matching = [case for case in cases if case["task_type"] == task_type]
        passed = sum(1 for case in matching if case["final_safe_output"])
        task_success_by_type[task_type] = {
            "passed": passed,
            "total": len(matching),
            "rate": round(passed / len(matching), 4) if matching else 0.0,
        }
    errors = [
        f"{concept['subject']} / {concept['concept']}: {probe.get('error')}"
        for concept in CONCEPTS
        for probe in [raw_probes[concept["concept_id"]]]
        if probe.get("error")
    ]
    payload = {
        "status": "success" if final_valid_outputs == total else "warning",
        "generated_at": now_iso(),
        "total_cases": total,
        "model_available": any(probe.get("available") for probe in raw_probes.values()),
        "raw_model_attempts": raw_model_attempts,
        "raw_valid_outputs": raw_valid_outputs,
        "raw_invalid_outputs": raw_invalid_outputs,
        "fallback_used": fallback_used,
        "final_valid_outputs": final_valid_outputs,
        "format_validity_rate": round(format_valid_count / total, 4) if total else 0.0,
        "grounding_pass_rate": round(grounding_pass_count / total, 4) if total else 0.0,
        "repetition_pass_rate": round(repetition_pass_count / total, 4) if total else 0.0,
        "final_safe_output_rate": round(final_valid_outputs / total, 4) if total else 0.0,
        "task_success_by_type": task_success_by_type,
        "errors": errors,
        "raw_model_probe_summary": raw_probes,
        "cases": cases,
        "limitations": [
            "Raw CogniTutorLM may be unavailable in this checkout.",
            "Grounding validation is local retrieval plus key-term coverage, not formal semantic entailment.",
            "The final demo should use validated fallback output rather than uncontrolled raw generation.",
        ],
    }

    json_path = JSON_DIR / "final_cognitutorlm_guarded_generation_eval.json"
    report_path = REPORT_DIR / "final_cognitutorlm_guarded_generation_eval_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(write_report(payload), encoding="utf-8")
    print("FINAL COGNITUTORLM GUARDED GENERATION EVAL")
    print(f"status: {payload['status']}")
    print(f"model_available: {payload['model_available']}")
    print(f"final_safe_output_rate: {payload['final_safe_output_rate']}")
    print(f"json: {json_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
