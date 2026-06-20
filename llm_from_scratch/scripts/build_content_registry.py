import json
from collections import defaultdict

from src.cognitutor_lm_config import ALL_TASK_OUTPUT, CORE_OUTPUT, PACKET_OUTPUT, REPORTS_DIR, ROOT
from src.content_versioning import CONTENT_VERSION, attach_version_metadata
from src.concept_resource_loader import load_concept_resources


OUT_DIR = ROOT / "outputs" / "content_registry"
OUT_JSON = OUT_DIR / "content_registry.json"
OUT_MD = OUT_DIR / "content_registry.md"


def load_json(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def status_from(path, key="status"):
    data = load_json(path, {})
    return data.get(key) or data.get("rag_connection_status") or data.get("frontend_contract_status") or "MISSING"


def main() -> None:
    concepts = load_concept_resources()
    packets = load_json(PACKET_OUTPUT, [])
    tasks = load_json(ALL_TASK_OUTPUT, [])
    core = load_json(CORE_OUTPUT, [])
    by_concept_packets = defaultdict(list)
    by_concept_tasks = defaultdict(list)
    for packet in packets:
        by_concept_packets[(packet.get("domain"), packet.get("concept_id"))].append(packet)
    for row in tasks:
        by_concept_tasks[(row.get("domain"), row.get("concept_id"))].append(row)

    concept_rows = []
    for concept in concepts:
        key = (concept["domain"], concept["concept_id"])
        rows = by_concept_packets.get(key, [])
        task_rows = by_concept_tasks.get(key, [])
        concept_rows.append(
            {
                "domain": concept["domain"],
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "learning_packet_count": len(rows),
                "all_task_count": len(task_rows),
                "easy_packets": sum(1 for p in rows if p.get("difficulty") == "easy"),
                "medium_packets": sum(1 for p in rows if p.get("difficulty") == "medium"),
                "hard_packets": sum(1 for p in rows if p.get("difficulty") == "hard"),
                "revision_packets": sum(1 for p in rows if p.get("difficulty") == "revision"),
                "website_ready": bool(rows) and bool(task_rows) and all(p.get("website_ready") for p in rows) and all(t.get("website_ready") for t in task_rows),
            }
        )

    report = {
        "status": "PASS" if len(core) == 456 and len(packets) >= 532 and len(tasks) == 3382 and all(c["website_ready"] for c in concept_rows) else "FAIL",
        "content_version": CONTENT_VERSION,
        "core_outputs_count": len(core),
        "learning_packet_count": len(packets),
        "all_89_output_count": len(tasks),
        "concepts_covered": len({(r.get("domain"), r.get("concept_id")) for r in tasks}),
        "subjects_covered": sorted({c["domain"] for c in concepts}),
        "task_types_covered": len({r.get("task_type") for r in tasks}),
        "quality_status": status_from(REPORTS_DIR / "all_89_task_generation_quality_scan.json"),
        "rag_status": status_from(ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json"),
        "backend_connection_status": status_from(ROOT / "outputs" / "service_tests" / "main_backend_cognitutor_connection_test.json"),
        "frontend_contract_status": status_from(ROOT / "outputs" / "service_tests" / "frontend_contract_validation.json", "frontend_contract_status"),
        "concepts": concept_rows,
    }
    attach_version_metadata(report, source=report, concept_resource={"concept_count": len(concepts)}, website_ready=report["status"] == "PASS")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Content Registry", "", f"- status: {report['status']}", f"- content_version: {report['content_version']}", f"- core_outputs_count: {len(core)}", f"- learning_packet_count: {len(packets)}", f"- all_89_output_count: {len(tasks)}", "", "## Concepts"]
    lines.extend(f"- {c['domain']} / {c['concept_id']} / {c['concept_name']}: packets={c['learning_packet_count']}, tasks={c['all_task_count']}, website_ready={c['website_ready']}" for c in concept_rows)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"content_registry_status: {report['status']}")
    print(f"output_json: {OUT_JSON}")


if __name__ == "__main__":
    main()
