import json
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
CORE_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
OUT_JSON = ROOT_DIR / "outputs" / "service_tests" / "website_exact_content_fetch_report.json"
OUT_MD = ROOT_DIR / "outputs" / "service_tests" / "website_exact_content_fetch_report.md"

EXPECTED_SOURCE = "cognitutor_lm_from_scratch_structured_model"
EXPECTED_MODEL = "CogniTutorLM-from-scratch-structured"

TEST_CASES = [
    {"domain": "Python", "concept": "Loops", "task_type": "debug_task"},
    {"domain": "Python", "concept": "Variables", "task_type": "explanation"},
    {"domain": "SQL", "concept": "SELECT", "task_type": "mcq"},
    {"domain": "HTML", "concept": "Tags", "task_type": "flashcard"},
    {"domain": "Git", "concept": "Commits", "task_type": "revision_summary"},
    {"domain": "Data Structures", "concept": "Linked", "task_type": "challenge_question"},
    {"domain": "Data Structures", "concept": "Stack", "task_type": "mindmap"},
]


def normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def load_items() -> List[Dict[str, Any]]:
    if not CORE_JSON.exists():
        return []
    data = json.loads(CORE_JSON.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def fetch_item(items: List[Dict[str, Any]], domain: str, concept: str, task_type: str) -> Dict[str, Any]:
    domain_norm = normalize(domain)
    concept_norm = normalize(concept)
    task_norm = normalize(task_type)
    for item in items:
        if normalize(item.get("domain")) != domain_norm:
            continue
        if task_norm != normalize(item.get("task_type")):
            continue
        concept_id = normalize(item.get("concept_id"))
        concept_name = normalize(item.get("concept_name"))
        if concept_norm in concept_name or concept_norm == concept_id:
            return item
    return {}


def result_for_case(items: List[Dict[str, Any]], case: Dict[str, str]) -> Dict[str, Any]:
    started = time.perf_counter()
    item = fetch_item(items, case["domain"], case["concept"], case["task_type"])
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    output = str(item.get("output", "")).strip() if item else ""
    success = (
        bool(item)
        and item.get("generation_source") == EXPECTED_SOURCE
        and item.get("model_used") == EXPECTED_MODEL
        and item.get("valid") is True
        and bool(output)
    )
    return {
        "requested_domain": case["domain"],
        "requested_concept": case["concept"],
        "requested_task_type": case["task_type"],
        "status": "success" if success else "fail",
        "matched_concept_id": item.get("concept_id") if item else None,
        "matched_concept_name": item.get("concept_name") if item else None,
        "task_type": item.get("task_type") if item else None,
        "generation_source": item.get("generation_source") if item else None,
        "model_used": item.get("model_used") if item else None,
        "valid": item.get("valid") if item else False,
        "quality_score": item.get("quality_score") if item else 0.0,
        "fetch_latency_ms": latency_ms,
        "output_preview": output[:240],
    }


def main() -> None:
    items = load_items()
    results = [result_for_case(items, case) for case in TEST_CASES]
    test_cases = len(TEST_CASES)
    success_count = sum(1 for item in results if item["status"] == "success")
    fail_count = test_cases - success_count
    avg_fetch_latency_ms = round(sum(item["fetch_latency_ms"] for item in results) / test_cases, 3) if test_cases else 0.0
    template_fallback_used = any(item.get("generation_source") in {"template_baseline", "template_fallback"} for item in results)
    status = "PASS" if success_count == test_cases and not template_fallback_used and avg_fetch_latency_ms < 500 else "WARN"

    report = {
        "test_cases": test_cases,
        "success_count": success_count,
        "fail_count": fail_count,
        "avg_fetch_latency_ms": avg_fetch_latency_ms,
        "template_fallback_used": template_fallback_used,
        "status": status,
        "source_file": str(CORE_JSON),
        "results": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Website Exact Content Fetch Report", ""]
    for key in ["test_cases", "success_count", "fail_count", "avg_fetch_latency_ms", "template_fallback_used", "status"]:
        lines.append(f"- {key}: {report[key]}")
    lines.append("")
    lines.append("## Results")
    for item in results:
        lines.extend(
            [
                "",
                f"### {item['requested_domain']} - {item['requested_concept']} - {item['requested_task_type']}",
                f"- status: {item['status']}",
                f"- matched_concept_id: {item['matched_concept_id']}",
                f"- matched_concept_name: {item['matched_concept_name']}",
                f"- generation_source: {item['generation_source']}",
                f"- model_used: {item['model_used']}",
                f"- valid: {item['valid']}",
                f"- quality_score: {item['quality_score']}",
                f"- fetch_latency_ms: {item['fetch_latency_ms']}",
                "",
                "```text",
                str(item["output_preview"]),
                "```",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"test_cases: {test_cases}")
    print(f"success_count: {success_count}")
    print(f"fail_count: {fail_count}")
    print(f"avg_fetch_latency_ms: {avg_fetch_latency_ms}")
    print(f"template_fallback_used: {template_fallback_used}")
    print(f"status: {status}")


if __name__ == "__main__":
    main()
