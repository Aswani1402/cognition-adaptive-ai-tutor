from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "final_evaluation"
JSON_OUT = OUT / "json" / "cognitutor_generation_final_evaluation.json"
MD_OUT = OUT / "md" / "cognitutor_generation_final_evaluation.md"
CSV_OUT = OUT / "csv" / "cognitutor_generation_task_counts.csv"

ALL_TASKS = ROOT / "outputs" / "model_generated" / "structured_model_generated_all_tasks.json"
PACKETS = ROOT / "outputs" / "learning_packets" / "all_learning_packets.json"
SCAN_89 = ROOT / "outputs" / "final_reports" / "all_89_task_generation_quality_scan.json"
VALIDATION = ROOT / "outputs" / "final_reports" / "full_product_generator_validation.json"
SMOKE = ROOT / "outputs" / "final_reports" / "cognitutor_lm_product_smoke_test.json"
RAG = ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json"
VOICE = ROOT / "outputs" / "service_tests" / "voice_script_generation_test.json"
API = ROOT / "outputs" / "service_tests" / "cognitutor_lm_api_service_test.json"

EXPECTED_CONCEPTS = 38
EXPECTED_TASK_TYPES = 89
EXPECTED_ALL_TASKS = EXPECTED_CONCEPTS * EXPECTED_TASK_TYPES


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def status_from(data: Any, keys: list[str]) -> str:
    if not isinstance(data, dict):
        return "WARN"
    values = [str(data.get(key, "")).upper() for key in keys if data.get(key) is not None]
    if any(value == "FAIL" or value == "ERROR" for value in values):
        return "FAIL"
    if any(value == "PASS" or value == "SUCCESS" for value in values):
        return "PASS"
    return "WARN"


def task_family_count(rows: list[dict[str, Any]], family: str) -> int:
    return sum(1 for row in rows if row.get("task_family") == family)


def main() -> None:
    for directory in [OUT / "json", OUT / "md", OUT / "csv", OUT / "charts"]:
        directory.mkdir(parents=True, exist_ok=True)

    rows = load_json(ALL_TASKS, [])
    packets = load_json(PACKETS, [])
    scan = load_json(SCAN_89, {})
    validation = load_json(VALIDATION, {})
    smoke = load_json(SMOKE, {})
    rag = load_json(RAG, {})
    voice = load_json(VOICE, {})
    api = load_json(API, {})

    concepts = {(r.get("domain"), r.get("concept_id"), r.get("concept_name")) for r in rows}
    task_types = {r.get("task_type") for r in rows if r.get("task_type")}
    difficulties = Counter(p.get("difficulty") for p in packets)
    family_counts = Counter(r.get("task_family") for r in rows)
    type_counts = Counter(r.get("task_type") for r in rows)

    missing_task_count = int(scan.get("missing_task_count", max(EXPECTED_ALL_TASKS - len(rows), 0)))
    invalid_count = int(scan.get("invalid_count", sum(1 for r in rows if not r.get("valid", True))))
    bad_schema_count = int(scan.get("bad_schema_count", 0))
    low_quality_count = int(scan.get("low_quality_count", sum(1 for r in rows if float(r.get("quality_score") or 0) < 0.5)))
    rag_status = status_from(rag, ["rag_connection_status", "status"])
    voice_status = status_from(voice, ["voice_script_status", "status", "final_status"])
    api_status = status_from(api, ["api_service_status", "status", "final_status"])

    pass_criteria = {
        "concept_count": len(concepts) == EXPECTED_CONCEPTS,
        "task_type_count": len(task_types) == EXPECTED_TASK_TYPES,
        "all_task_output_count": len(rows) == EXPECTED_ALL_TASKS,
        "missing_task_count": missing_task_count == 0,
        "invalid_count": invalid_count == 0,
        "bad_schema_count": bad_schema_count == 0,
        "rag_status": rag_status == "PASS",
        "voice_status": voice_status == "PASS",
        "api_status": api_status == "PASS",
    }
    generation_status = "PASS" if all(pass_criteria.values()) else "FAIL"
    product_smoke_status = status_from(smoke, ["status", "product_smoke_status"])
    final_status = generation_status if generation_status == "FAIL" else ("WARN" if product_smoke_status == "WARN" else "PASS")

    report = {
        "evaluation_name": "cognitutor_generation_final_evaluation",
        "source_files": {
            "all_tasks": str(ALL_TASKS),
            "learning_packets": str(PACKETS),
            "all_89_scan": str(SCAN_89),
            "full_product_generator_validation": str(VALIDATION),
            "rag_connection": str(RAG),
            "voice_test": str(VOICE),
            "api_service_test": str(API),
        },
        "concept_count": len(concepts),
        "task_type_count": len(task_types),
        "all_task_output_count": len(rows),
        "expected_all_task_outputs": EXPECTED_ALL_TASKS,
        "missing_task_count": missing_task_count,
        "invalid_count": invalid_count,
        "bad_schema_count": bad_schema_count,
        "low_quality_count": low_quality_count,
        "learning_packet_count": len(packets),
        "easy_packet_count": difficulties.get("easy", 0),
        "medium_packet_count": difficulties.get("medium", 0),
        "hard_packet_count": difficulties.get("hard", 0),
        "revision_packet_count": difficulties.get("revision", 0),
        "assessment_task_count": family_counts.get("assessment", 0) + family_counts.get("practice_challenge", 0),
        "flashcard_task_count": family_counts.get("flashcard", 0),
        "mindmap_task_count": family_counts.get("mindmap", 0),
        "voice_task_count": family_counts.get("voice", 0),
        "rag_status": rag_status,
        "voice_status": voice_status,
        "api_status": api_status,
        "raw_generation_status": "WARN",
        "guarded_generation_status": "PASS" if generation_status == "PASS" else "FAIL",
        "generation_status": generation_status,
        "product_smoke_status": product_smoke_status,
        "product_smoke_reason": "optional backend/frontend/manual verification remains" if product_smoke_status == "WARN" else None,
        "full_product_generator_validation_status": status_from(validation, ["status", "final_status"]),
        "pass_criteria": pass_criteria,
        "final_status": final_status,
    }

    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["task_type", "count"])
        writer.writeheader()
        for task_type, count in sorted(type_counts.items()):
            writer.writerow({"task_type": task_type, "count": count})

    lines = [
        "# CogniTutorLM Generation Final Evaluation",
        "",
        f"- final_status: {final_status}",
        f"- generation_status: {generation_status}",
        f"- product_smoke_status: {product_smoke_status}",
        f"- concept_count: {len(concepts)}",
        f"- task_type_count: {len(task_types)}",
        f"- all_task_output_count: {len(rows)} / {EXPECTED_ALL_TASKS}",
        f"- missing_task_count: {missing_task_count}",
        f"- invalid_count: {invalid_count}",
        f"- bad_schema_count: {bad_schema_count}",
        f"- low_quality_count: {low_quality_count}",
        f"- rag_status: {rag_status}",
        f"- voice_status: {voice_status}",
        f"- api_status: {api_status}",
        "",
        "## Saved Files",
        f"- {JSON_OUT}",
        f"- {MD_OUT}",
        f"- {CSV_OUT}",
    ]
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"final_status": final_status, "generation_status": generation_status, "json": str(JSON_OUT)}, indent=2))


if __name__ == "__main__":
    main()
