from __future__ import annotations

import csv
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from tutor.generation.adaptive_content_generator import AdaptiveContentGenerator
from tutor.generation.cognitutor_lm_connector import (
    ask_cognitutor_doubt,
    generate_cognitutor_session_packet,
)
from tutor.rag.rag_context_builder import build_rag_concept_resource
from tutor.rag.rag_grounding_checker import check_rag_grounding


JSON_REPORT = Path("evaluation_outputs/json/generation_service_comparison_report.json")
MD_REPORT = Path("evaluation_outputs/reports/generation_service_comparison_report.md")
CSV_OUTPUT = Path("evaluation_outputs/csv/generation_service_comparison_cases.csv")

STOPWORDS = {
    "and", "are", "can", "for", "from", "how", "into", "the", "this", "that",
    "what", "when", "where", "will", "with", "your", "about", "after", "before",
}

CASES = [
    {"case_id": "py_var_explain", "domain": "Python", "concept_id": "1", "concept_name": "Variables", "task_type": "explanation", "prompt": "Explain Python variables with a simple example."},
    {"case_id": "py_loop_revision", "domain": "Python", "concept_id": "4", "concept_name": "Loops", "task_type": "revision", "prompt": "Revise Python loops quickly with key reminders."},
    {"case_id": "sql_select_flashcard", "domain": "SQL", "concept_id": "S2", "concept_name": "SQL SELECT", "task_type": "flashcard", "prompt": "Create flashcards for SQL SELECT."},
    {"case_id": "html_tags_debug", "domain": "HTML", "concept_id": "H1", "concept_name": "HTML Tags", "task_type": "debug_task", "prompt": "Create a debug task for incorrect HTML tag syntax."},
    {"case_id": "py_var_output", "domain": "Python", "concept_id": "1", "concept_name": "Variables", "task_type": "output_prediction", "prompt": "What will this code print: x = 10; x = 20; print(x)?"},
    {"case_id": "git_commit_transfer", "domain": "Git", "concept_id": "G1", "concept_name": "Git Commits", "task_type": "transfer_question", "prompt": "Ask a transfer question about using Git commits in a team project."},
    {"case_id": "arrays_challenge", "domain": "Data Structures", "concept_id": "DS1", "concept_name": "Arrays", "task_type": "challenge_question", "prompt": "Create a challenge question about array indexing."},
    {"case_id": "sql_select_doubt", "domain": "SQL", "concept_id": "S2", "concept_name": "SQL SELECT", "task_type": "doubt_answer", "prompt": "I do not understand what SELECT returns."},
    {"case_id": "html_tags_explain", "domain": "HTML", "concept_id": "H1", "concept_name": "HTML Tags", "task_type": "explanation", "prompt": "Explain HTML tags and elements."},
    {"case_id": "git_commit_revision", "domain": "Git", "concept_id": "G1", "concept_name": "Git Commits", "task_type": "revision", "prompt": "Give a quick recap of Git commits."},
]

FIELDS = [
    "service_name", "case_id", "task_type", "domain", "concept_name",
    "service_available", "output_generated", "format_valid", "concept_relevance",
    "grounding_score", "unsupported_terms_count", "repetition_rate", "latency_ms",
    "fallback_used", "task_supported", "quality_score", "status",
]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def _token_set(text: str) -> set[str]:
    return set(_tokens(text))


def _concept_relevance(text: str, case: dict[str, Any]) -> float:
    text_tokens = _token_set(text)
    query_tokens = _token_set(" ".join([case["domain"], case["concept_name"], case["prompt"]]))
    if not text_tokens or not query_tokens:
        return 0.0
    overlap = len(text_tokens & query_tokens) / max(1, len(query_tokens))
    direct_bonus = 0.15 if case["concept_name"].split()[0].lower() in text.lower() else 0.0
    return round(min(1.0, overlap + direct_bonus), 4)


def _repetition_rate(text: str) -> float:
    tokens = _tokens(text)
    if not tokens:
        return 1.0
    unique = len(set(tokens))
    return round(max(0.0, 1.0 - unique / len(tokens)), 4)


def _format_valid(output: Any, text: str, task_type: str) -> bool:
    if not text:
        return False
    if isinstance(output, dict) and output.get("status") in {"success", "warning"}:
        return True
    markers = {
        "flashcard": ["q:", "a:", "front", "back"],
        "debug_task": ["debug", "bug", "fix", "mistake"],
        "output_prediction": ["print", "output", "trace"],
        "challenge_question": ["challenge", "solve", "problem"],
        "transfer_question": ["real", "project", "apply", "team"],
    }
    needed = markers.get(task_type)
    return bool(not needed or any(marker in text.lower() for marker in needed))


def _quality_score(metrics: dict[str, Any]) -> float:
    unsupported_penalty = min(0.25, 0.03 * int(metrics["unsupported_terms_count"]))
    score = (
        0.18 * float(metrics["format_valid"])
        + 0.22 * float(metrics["concept_relevance"])
        + 0.24 * float(metrics["grounding_score"])
        + 0.12 * (1.0 - float(metrics["repetition_rate"]))
        + 0.12 * float(metrics["task_supported"])
        + 0.12 * float(metrics["output_generated"])
        - 0.10 * float(metrics["fallback_used"])
        - unsupported_penalty
    )
    return round(max(0.0, min(1.0, score)), 4)


def _resource_for(case: dict[str, Any]) -> dict[str, Any]:
    return build_rag_concept_resource(
        query=case["prompt"],
        domain=case["domain"],
        concept_id=case["concept_id"],
        concept_name=case["concept_name"],
        top_k=8,
    )


def _template_service(case: dict[str, Any]) -> tuple[Any, str, dict[str, Any], bool, bool]:
    resource = _resource_for(case)
    content_type = {
        "revision": "revision",
        "flashcard": "flashcard",
    }.get(case["task_type"], "teaching")
    strategy = {
        "revision": "revision_summary",
        "flashcard": "revision_summary",
        "debug_task": "misconception_first",
        "challenge_question": "advanced_learner",
        "transfer_question": "real_world_first",
    }.get(case["task_type"], "definition_first")
    output = AdaptiveContentGenerator(random_seed=42).generate_content(
        concept_resource=resource,
        content_type=content_type,
        strategy=strategy,
        difficulty="medium",
        learner_id=None,
    )
    return output, _safe_text(output.get("body") or output), resource, True, bool(output.get("metadata", {}).get("fallback_used"))


def _rag_service(case: dict[str, Any]) -> tuple[Any, str, dict[str, Any], bool, bool]:
    resource = _resource_for(case)
    if resource.get("status") != "success":
        return resource, "", resource, True, True
    parts = [
        f"Task: {case['task_type']}",
        f"Concept: {resource.get('topic') or case['concept_name']}",
        resource.get("definition", ""),
        "Key points: " + "; ".join(resource.get("key_points", [])[:4]),
    ]
    if case["task_type"] in {"flashcard", "revision"}:
        parts.append("Flashcard/revision prompts: " + "; ".join(resource.get("key_points", [])[:3]))
    if case["task_type"] in {"debug_task", "output_prediction", "challenge_question", "transfer_question"}:
        parts.append("Practice context: " + "; ".join(resource.get("examples", [])[:2]))
    text = "\n\n".join(part for part in parts if part)
    output = {"status": "success", "service": "rag_grounded_service", "text": text, "source_sections": [c.get("section") for c in resource.get("retrieved_chunks", [])]}
    return output, text, resource, True, False


def _cognitutor_service(case: dict[str, Any]) -> tuple[Any, str, dict[str, Any], bool, bool]:
    if case["task_type"] == "doubt_answer":
        output = ask_cognitutor_doubt(
            learner_id="generation_compare_learner",
            learner_doubt=case["prompt"],
            concept_id=case["concept_id"],
            concept_name=case["concept_name"],
            domain=case["domain"],
        )
    else:
        question_types = [case["task_type"]] if case["task_type"] not in {"explanation", "revision", "flashcard"} else None
        output = generate_cognitutor_session_packet(
            learner_id="generation_compare_learner",
            concept_id=case["concept_id"],
            concept_name=case["concept_name"],
            domain=case["domain"],
            selected_view="revision_view" if case["task_type"] == "revision" else None,
            question_types=question_types,
            num_questions=3,
        )
    text = _safe_text(output)
    resource = _resource_for(case)
    available = output.get("status") == "success"
    fallback = bool(output.get("fallback_used") or output.get("details", {}).get("exception_type"))
    return output, text, resource, True, fallback


def _sanvia_service(case: dict[str, Any]) -> tuple[Any, str, dict[str, Any], bool, bool]:
    path = Path("..") / "fine_tuing_llm" / "sanvia_finetuning"
    output = {
        "status": "pending_external_model" if path.exists() else "unavailable",
        "service": "sanvia_pretrained_finetuned_llm",
        "path": str(path),
        "reason": "Sanvia project folder exists, but no safe in-process generation API/model artifact is wired into this tutor evaluation harness.",
    }
    return output, "", {}, False, True


SERVICES: dict[str, Callable[[dict[str, Any]], tuple[Any, str, dict[str, Any], bool, bool]]] = {
    "template_rule_generator": _template_service,
    "rag_grounded_service": _rag_service,
    "cognitutor_lm_from_scratch": _cognitutor_service,
    "sanvia_pretrained_finetuned_llm": _sanvia_service,
}


def _evaluate_case(service_name: str, case: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    output: Any = {}
    text = ""
    resource: dict[str, Any] = {}
    task_supported = False
    fallback_used = False
    status = "success"
    try:
        output, text, resource, task_supported, fallback_used = SERVICES[service_name](case)
        status = str(output.get("status", "success")) if isinstance(output, dict) else "success"
    except Exception as exc:
        output = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        status = "error"
    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
    service_available = status in {"success", "warning", "pending_external_model"} and service_name != "sanvia_pretrained_finetuned_llm"
    output_generated = bool(text.strip())
    grounding = check_rag_grounding(
        generated_text=text,
        rag_context=resource,
        concept_id=case["concept_id"],
        concept_name=case["concept_name"],
        domain=case["domain"],
    )
    metrics = {
        "service_name": service_name,
        "case_id": case["case_id"],
        "task_type": case["task_type"],
        "domain": case["domain"],
        "concept_name": case["concept_name"],
        "service_available": service_available,
        "output_generated": output_generated,
        "format_valid": _format_valid(output, text, case["task_type"]),
        "concept_relevance": _concept_relevance(text, case),
        "grounding_score": float(grounding.get("grounding_score", 0.0)),
        "unsupported_terms_count": len(grounding.get("unsupported_terms", [])),
        "repetition_rate": _repetition_rate(text),
        "latency_ms": latency_ms,
        "fallback_used": bool(fallback_used or grounding.get("fallback_recommended")),
        "task_supported": bool(task_supported),
        "status": status,
    }
    metrics["quality_score"] = _quality_score(metrics)
    return metrics


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_service[row["service_name"]].append(row)
        by_task[row["task_type"]].append(row)

    metric_table = {}
    for service, items in by_service.items():
        generated_items = [item for item in items if item["output_generated"]]
        denom = max(1, len(items))
        metric_table[service] = {
            "service_available": any(item["service_available"] for item in items),
            "case_count": len(items),
            "output_rate": round(sum(item["output_generated"] for item in items) / denom, 4),
            "format_valid_rate": round(sum(item["format_valid"] for item in items) / denom, 4),
            "avg_concept_relevance": round(sum(float(item["concept_relevance"]) for item in items) / denom, 4),
            "avg_grounding_score": round(sum(float(item["grounding_score"]) for item in items) / denom, 4),
            "avg_repetition_rate": round(sum(float(item["repetition_rate"]) for item in items) / denom, 4),
            "avg_latency_ms": round(sum(float(item["latency_ms"]) for item in items) / denom, 3),
            "fallback_rate": round(sum(item["fallback_used"] for item in items) / denom, 4),
            "task_coverage": round(sum(item["task_supported"] and item["output_generated"] for item in items) / denom, 4),
            "avg_quality_score": round(sum(float(item["quality_score"]) for item in items) / denom, 4),
            "generated_case_count": len(generated_items),
        }

    best_by_task = {}
    for task, items in by_task.items():
        candidates = [item for item in items if item["output_generated"] and item["service_available"]]
        best = max(candidates, key=lambda item: item["quality_score"], default=None)
        best_by_task[task] = {
            "best_service": best["service_name"] if best else None,
            "quality_score": best["quality_score"] if best else 0.0,
        }
    return {"metric_comparison_table": metric_table, "best_service_by_task_type": best_by_task}


def _write_csv(rows: list[dict[str, Any]]) -> None:
    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in FIELDS})


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Generation Service Comparison Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Service Availability",
        "",
        "| Service | Available | Output rate | Quality | Grounding | Latency ms | Fallback rate | Coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for service, metrics in report["metric_comparison_table"].items():
        lines.append(
            f"| {service} | {metrics['service_available']} | {metrics['output_rate']} | {metrics['avg_quality_score']} | "
            f"{metrics['avg_grounding_score']} | {metrics['avg_latency_ms']} | {metrics['fallback_rate']} | {metrics['task_coverage']} |"
        )
    lines.extend(["", "## Best Service By Task Type", ""])
    for task, item in report["best_service_by_task_type"].items():
        lines.append(f"- {task}: {item['best_service']} (quality={item['quality_score']})")
    lines.extend(
        [
            "",
            "## Final Recommended System Design",
            "",
            report["final_recommended_system_design"],
            "",
            "## Sanvia Status",
            "",
            report["sanvia_status"],
            "",
            "## Limitations",
            "",
        ]
    )
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Human-Eval Next Step", "", report["human_eval_readiness"]])
    return "\n".join(lines) + "\n"


def build_report() -> dict[str, Any]:
    rows = []
    for service_name in SERVICES:
        for case in CASES:
            rows.append(_evaluate_case(service_name, case))
    _write_csv(rows)
    aggregate = _aggregate(rows)
    sanvia_path = Path("..") / "fine_tuing_llm" / "sanvia_finetuning"
    report = {
        "status": "success",
        "module": "generation_service_comparison_report",
        "case_count": len(CASES),
        "services": list(SERVICES),
        "csv_output": str(CSV_OUTPUT),
        "service_availability_table": {
            service: aggregate["metric_comparison_table"][service]["service_available"]
            for service in SERVICES
        },
        **aggregate,
        "case_metrics": rows,
        "sanvia_status": (
            "pending_external_model: folder exists but no safe runnable generation API/model artifact is integrated."
            if sanvia_path.exists()
            else "unavailable: Sanvia folder not found."
        ),
        "final_recommended_system_design": (
            "Use RAG-grounded and CogniTutorLM paths behind validation checks, keep template generation as a deterministic fallback, "
            "and add Sanvia only after it exposes a safe local inference API and passes the same grounding/format/relevance checks."
        ),
        "human_eval_readiness": (
            "Ready for a small human-rated study: sample each task type, blind-rate correctness, helpfulness, grounding, and learner suitability."
        ),
        "limitations": [
            "Automatic metrics are proxy metrics and do not replace human judgement.",
            "CogniTutorLM is evaluated through its connector as a black-box service packet.",
            "Sanvia is marked pending because it is not safely wired as a local service in the main tutor.",
            "Latency is local runtime latency and may vary by hardware and cache state.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    MD_REPORT.write_text(_markdown(report), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: generation_service_comparison_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
