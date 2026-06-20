import json
import re
from typing import Any

from scripts.evaluate_generation_pedagogical_quality import no_full_db_dump_check, packet_rules, teaching_view_difference_failures
from scripts.generate_teaching_aligned_packets import build_difficulty_content_blocks
from src.cognitutor_lm_api_service import get_learning_packet, get_study_report_packet, get_website_session_packet
from src.cognitutor_lm_config import PACKET_OUTPUT, REPORTS_DIR, SUBJECT_DBS, TEACHING_VIEWS
from src.concept_resource_loader import find_concept, load_concept_resources


OUT_JSON = REPORTS_DIR / "learning_packet_smoke_test.json"
OUT_MD = REPORTS_DIR / "learning_packet_smoke_test.md"


def txt(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")


def has_bad(value: Any) -> bool:
    t = txt(value)
    return "..." in t or "N/A" in t or "placeholder" in t or "TODO" in t


def main() -> None:
    concepts = load_concept_resources()
    packets = json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []
    evaluator_report_path = REPORTS_DIR / "pedagogical_generation_quality_report.json"
    evaluator_report = json.loads(evaluator_report_path.read_text(encoding="utf-8")) if evaluator_report_path.exists() else {}
    by_concept = {}
    for p in packets:
        by_concept.setdefault((p["domain"], p["concept_id"]), []).append(p)
    checks = []

    def add(name: str, ok: bool, detail: Any = ""):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'}: {name} {detail}")

    add("All 5 subject DBs are readable", all(path.exists() for path in SUBJECT_DBS.values()))
    add("All 38 concepts loaded with full concept_resources", len(concepts) == 38 and all(c.get("definition") and c.get("examples") and c.get("key_points") for c in concepts), len(concepts))
    add("Packets generated for all 38 concepts", len(by_concept) == 38, len(by_concept))
    add("Every concept has all 14 teaching_view packets", all({p["teaching_view"] for p in rows} == set(TEACHING_VIEWS) for rows in by_concept.values()))
    blocks_by_concept = [build_difficulty_content_blocks(c) for c in concepts]
    add("easy_content exists for every concept", all(b.get("easy_content") for b in blocks_by_concept))
    add("medium_content exists for every concept", all(b.get("medium_content") for b in blocks_by_concept))
    add("hard_content exists for every concept", all(b.get("hard_content") for b in blocks_by_concept))
    add("revision_content exists for every concept", all(b.get("revision_content") for b in blocks_by_concept))
    add("Packets have source_level", all(p.get("source_level") for p in packets))
    add("Packets have difficulty", all(p.get("difficulty") for p in packets))
    add("easy, medium, hard content are different", all(len({b["easy_content"]["learning_goal"], b["medium_content"]["learning_goal"], b["hard_content"]["learning_goal"]}) == 3 for b in blocks_by_concept))
    add("No packet has empty teaching_content fields", all(all(v not in ("", None, []) for k, v in p["teaching_content"].items() if k != "resources_used") for p in packets))
    add("No teaching_content is one-line only", all(len([v for k, v in p["teaching_content"].items() if k not in {"title", "resources_used"} and v not in ("", None, [])]) >= 8 for p in packets))
    add("Every packet has aligned assessments", all(p.get("aligned_assessments") for p in packets))
    add("Definitions are focused and readable", all(25 <= len(p["teaching_content"]["definition"].split()) <= 110 for p in packets))
    add("No packet has beginner_explanation under 70 words", all(len(p["teaching_content"]["beginner_explanation"].split()) >= 70 for p in packets))
    add("No packet has placeholder markers", not any(has_bad(p) for p in packets))
    mcqs = [a for p in packets for a in p["aligned_assessments"] if a.get("options")]
    add("All MCQs have 4 options with valid answer key", all(len(a["options"]) == 4 and a.get("answer") in {"A", "B", "C", "D"} for a in mcqs))
    debug_packets = [p for p in packets if p["teaching_view"] == "debug_view"]
    add("All debug_tasks have buggy code and fix", all("BUGGY" in p["teaching_content"]["code_or_task_example"] and "FIXED" in p["teaching_content"]["code_or_task_example"] for p in debug_packets))
    output_packets = [p for p in packets if p["teaching_view"] == "output_prediction_view"]
    add("All output_prediction tasks ask for a predicted result", all("PREDICT THE RESULT" in p["teaching_content"]["code_or_task_example"] and "Question:" in p["teaching_content"]["code_or_task_example"] for p in output_packets))
    subjects_ok = all(get_website_session_packet(domain, next(c["concept_name"] for c in concepts if c["domain"] == domain)).get("status") == "success" for domain in SUBJECT_DBS)
    add("API service can return a session packet for each subject", subjects_ok)
    packet_rule_sets = [packet_rules(p) for p in packets]
    scores = [sum(1 for r in rules if r["pass"]) / len(rules) for rules in packet_rule_sets if rules]
    quality_ok_count = sum(1 for s in scores if s >= 0.85)
    add("Quality score >= 0.85 for at least 95% of packets", quality_ok_count >= int(len(packets) * 0.95), f"{quality_ok_count}/{len(packets)}")
    add("Pedagogical evaluator has no FAIL packets", evaluator_report.get("fail_count", evaluator_report.get("packet_fail_count", 1)) == 0)
    warn_count = evaluator_report.get("warn_count", evaluator_report.get("packet_warn_count", len(packets)))
    add("Pedagogical evaluator WARN rate <= 5%", warn_count <= int(len(packets) * 0.05), f"{warn_count}/{len(packets)}")
    add("Teaching view difference check passes", not teaching_view_difference_failures(packets))
    add("easy assessments only use easy_content", all(a.get("source_level") == "easy_content" for p in packets if p.get("source_level") == "easy_content" for a in p.get("aligned_assessments", [])))
    add("medium assessments only use medium_content", all(a.get("source_level") == "medium_content" for p in packets if p.get("source_level") == "medium_content" for a in p.get("aligned_assessments", [])))
    add("hard assessments only use hard_content", all(a.get("source_level") == "hard_content" for p in packets if p.get("source_level") == "hard_content" for a in p.get("aligned_assessments", [])))
    hard_terms = {"identity", "equality", "mutable", "reference", "references", "swap"}
    def has_hard_term(value):
        lowered = txt(value).lower()
        return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in hard_terms)
    add("No easy assessment includes hard-only terms", not any(has_hard_term(a) for p in packets if p.get("source_level") == "easy_content" for a in p.get("aligned_assessments", [])))
    add("Every assessment has alignment_reason", all(a.get("alignment_reason") for p in packets for a in p.get("aligned_assessments", [])))
    add("Every assessment has linked_content_points", all(a.get("linked_content_points") for p in packets for a in p.get("aligned_assessments", [])))
    api_exact = get_learning_packet("Python", concept_name="Variables", difficulty="easy", teaching_view="definition_view")
    add("API service can return exact difficulty + teaching_view packet", api_exact.get("status") == "success" and api_exact.get("difficulty") == "easy" and api_exact.get("teaching_view") == "definition_view")
    study_packet = get_study_report_packet("Python", concept_name="Variables", learner_id="demo_learner_001")
    add("Concept study report can be generated or retrieved", study_packet.get("status") == "success")
    dump_ok = True
    for packet in packets:
        concept = find_concept(packet.get("domain", ""), concept_id=packet.get("concept_id")) or {}
        if not no_full_db_dump_check(packet, concept):
            dump_ok = False
            break
    add("No packet has huge repeated DB dump", dump_ok)
    overall = all(c["status"] == "PASS" for c in checks)
    report = {"status": "PASS" if overall else "FAIL", "checks": checks, "packet_quality_pass_count": quality_ok_count, "packet_count": len(packets), "concept_count": len(concepts)}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Learning Packet Smoke Test\n\n" + "\n".join(f"- {c['status']}: {c['check']} {c['detail']}" for c in checks) + f"\n\nOverall: {report['status']}\n", encoding="utf-8")
    print("SMOKE TEST PASSED" if overall else "SMOKE TEST FAILED")


if __name__ == "__main__":
    main()
