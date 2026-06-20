import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from scripts.structured_generation_common import load_concepts
from src.cognitutor_lm_config import ALL_TASK_OUTPUT, PACKET_OUTPUT, REPORTS_DIR, TEACHING_VIEWS


OUT_JSON = REPORTS_DIR / "full_generation_level_coverage_report.json"
OUT_MD = REPORTS_DIR / "full_generation_level_coverage_report.md"

EXPECTED_CONCEPTS = 38
EXPECTED_TASK_COUNT = 89
EXPECTED_TOTAL_TASK_OUTPUTS = EXPECTED_CONCEPTS * EXPECTED_TASK_COUNT
DIFFICULTIES = ["easy", "medium", "hard", "revision"]
FLASHCARD_VARIANTS = {
    "flashcard",
    "concept_recall_flashcard",
    "misconception_flashcard",
    "example_flashcard",
    "debug_flashcard",
    "personal_flashcards",
    "syntax_flashcard",
}
ASSESSMENT_TYPES = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "fill_in_the_blank",
    "true_or_false",
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
}
MINDMAP_TYPES = {"mindmap", "concept_mindmap", "comparison_mindmap"}
VOICE_TYPES = {
    "voice_script",
    "teaching_voice_script",
    "revision_voice_script",
    "mistake_feedback_voice_script",
    "doubt_explanation_voice_script",
    "encouragement_script",
    "next_step_guidance_script",
    "concept_intro_voice_script",
}
EASY_ASSESSMENTS = {"mcq", "explanation_check", "fill_in_the_blank", "true_or_false"}
MEDIUM_ASSESSMENTS = {
    "debug_task",
    "output_prediction",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "debug_challenge",
    "output_prediction_challenge",
}
HARD_ASSESSMENTS = {
    "transfer_question",
    "challenge_question",
    "practice_question",
    "transfer_task",
    "real_world_application_question",
    "multi_step_challenge",
}
HARD_ONLY_TERMS = ["challenge", "advanced", "edge case", "transfer", "multi-step", "multi step"]


def load_json(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def concept_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (row.get("domain", ""), row.get("concept_id", ""), row.get("concept_name", ""))


def row_text(row: Dict[str, Any]) -> str:
    return json.dumps(row.get("output") or {}, ensure_ascii=False).lower()


def flashcard_levels(rows: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    found: Dict[str, Set[str]] = {level: set() for level in DIFFICULTIES}
    for row in rows:
        task_type = row.get("task_type")
        if task_type not in FLASHCARD_VARIANTS:
            continue
        output = row.get("output") or {}
        level_cards = output.get("cards_by_difficulty") or output.get("all_level_flashcards") or {}
        if isinstance(level_cards, dict):
            for level in DIFFICULTIES:
                card = level_cards.get(level)
                if isinstance(card, dict) and card.get("front") and card.get("back"):
                    found[level].add(task_type)
        else:
            found[row.get("difficulty", "")].add(task_type)
    return found


def quality_issues(rows: List[Dict[str, Any]]) -> List[str]:
    issues = []
    for row in rows:
        task_type = row.get("task_type")
        missing = []
        for field in ["source_level", "difficulty", "task_family"]:
            if not row.get(field):
                missing.append(field)
        if task_type in ASSESSMENT_TYPES | FLASHCARD_VARIANTS | MINDMAP_TYPES | VOICE_TYPES and not row.get("alignment_reason"):
            missing.append("alignment_reason")
        if row.get("valid") is not True:
            missing.append("valid true")
        if float(row.get("quality_score") or 0) < 0.85:
            missing.append("quality_score >= 0.85")
        if missing:
            issues.append(f"{task_type}: missing/invalid {', '.join(missing)}")
    return issues


def concept_report(concept: Dict[str, Any], rows: List[Dict[str, Any]], packets: List[Dict[str, Any]]) -> Dict[str, Any]:
    key = (concept["domain"], concept["concept_id"], concept["concept_name"])
    packet_rows = [p for p in packets if concept_key(p) == key]
    task_types = {r.get("task_type") for r in rows}
    packet_pairs = {(p.get("difficulty"), p.get("teaching_view")) for p in packet_rows}
    difficulties = {p.get("difficulty") for p in packet_rows} | {r.get("difficulty") for r in rows}
    teaching_views = {p.get("teaching_view") for p in packet_rows} | {r.get("teaching_view") for r in rows}
    flashcards = flashcard_levels(rows)
    assessment_rows = [r for r in rows if r.get("task_type") in ASSESSMENT_TYPES]
    assessment_types = {r.get("task_type") for r in assessment_rows}
    by_diff_assessments = defaultdict(set)
    for row in assessment_rows:
        by_diff_assessments[row.get("difficulty")].add(row.get("task_type"))
    easy_bad_terms = [
        row.get("task_type")
        for row in assessment_rows
        if row.get("difficulty") == "easy" and any(term in row_text(row) for term in HARD_ONLY_TERMS)
    ]
    level_packets = {
        level: {
            "exists": any(p.get("difficulty") == level for p in packet_rows),
            "teaching_views": sorted(p.get("teaching_view") for p in packet_rows if p.get("difficulty") == level),
        }
        for level in DIFFICULTIES
    }
    checks = {
        "identity": {"domain": concept["domain"], "concept_id": concept["concept_id"], "concept_name": concept["concept_name"]},
        "difficulty_coverage": level_packets,
        "teaching_views_found": sorted(teaching_views),
        "missing_teaching_views": sorted(set(TEACHING_VIEWS) - teaching_views),
        "flashcard_variants_by_difficulty": {level: sorted(values) for level, values in flashcards.items()},
        "flashcard_counts_by_difficulty": {level: len(values) for level, values in flashcards.items()},
        "assessment_types_found": sorted(assessment_types),
        "missing_assessment_types": sorted(ASSESSMENT_TYPES - assessment_types),
        "assessment_types_by_difficulty": {level: sorted(values) for level, values in by_diff_assessments.items()},
        "unexpected_easy_assessments": sorted(by_diff_assessments["easy"] - EASY_ASSESSMENTS),
        "unexpected_medium_assessments": sorted(by_diff_assessments["medium"] - MEDIUM_ASSESSMENTS),
        "unexpected_hard_assessments": sorted(by_diff_assessments["hard"] - HARD_ASSESSMENTS),
        "easy_tasks_with_hard_only_terms": sorted(set(easy_bad_terms)),
        "mindmap_variants_found": sorted(task_types & MINDMAP_TYPES),
        "missing_mindmap_variants": sorted(MINDMAP_TYPES - task_types),
        "voice_variants_found": sorted(task_types & VOICE_TYPES),
        "missing_voice_variants": sorted(VOICE_TYPES - task_types),
        "all_task_count": len(rows),
        "task_type_count": len(task_types),
        "quality_issues": quality_issues(rows),
    }
    required_flashcards_pass = all(len(flashcards[level]) == 7 for level in ["easy", "medium", "hard"])
    revision_flashcards_pass = not level_packets["revision"]["exists"] or len(flashcards["revision"]) == 7
    hard_pass = (
        len(rows) == EXPECTED_TASK_COUNT
        and len(task_types) == EXPECTED_TASK_COUNT
        and not checks["missing_teaching_views"]
        and required_flashcards_pass
        and not checks["missing_assessment_types"]
        and not checks["unexpected_easy_assessments"]
        and not checks["unexpected_medium_assessments"]
        and not checks["unexpected_hard_assessments"]
        and not checks["easy_tasks_with_hard_only_terms"]
        and not checks["missing_mindmap_variants"]
        and not checks["missing_voice_variants"]
        and not checks["quality_issues"]
        and all(level_packets[level]["exists"] for level in ["easy", "medium", "hard"])
    )
    status = "PASS" if hard_pass and revision_flashcards_pass else ("WARN" if hard_pass else "FAIL")
    if status == "WARN" and not revision_flashcards_pass:
        checks["warning"] = "revision flashcards missing; this is WARN unless revision flashcards are product-required"
    return {"concept": checks["identity"], "status": status, "checks": checks}


def markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Full Generation Level Coverage Report",
        "",
        f"- status: {report['status']}",
        f"- total_concepts: {report['total_concepts']}",
        f"- concepts_passed: {report['concepts_passed']}",
        f"- concepts_failed: {report['concepts_failed']}",
        f"- total_all_task_outputs: {report['total_all_task_outputs']}",
        f"- expected_all_task_outputs: {report['expected_all_task_outputs']}",
        f"- flashcard_level_coverage_pass: {report['flashcard_level_coverage_pass']}",
        f"- assessment_coverage_pass: {report['assessment_coverage_pass']}",
        f"- mindmap_coverage_pass: {report['mindmap_coverage_pass']}",
        f"- voice_coverage_pass: {report['voice_coverage_pass']}",
        f"- all_89_coverage_pass: {report['all_89_coverage_pass']}",
        "",
        "## Failed Or Warn Concepts",
    ]
    for item in report["concept_reports"]:
        if item["status"] != "PASS":
            c = item["concept"]
            checks = item["checks"]
            lines.extend(
                [
                    f"- {item['status']}: {c['domain']} / {c['concept_id']} / {c['concept_name']}",
                    f"  - missing_assessment_types: {checks['missing_assessment_types']}",
                    f"  - flashcard_counts_by_difficulty: {checks['flashcard_counts_by_difficulty']}",
                    f"  - missing_mindmap_variants: {checks['missing_mindmap_variants']}",
                    f"  - missing_voice_variants: {checks['missing_voice_variants']}",
                    f"  - quality_issues: {len(checks['quality_issues'])}",
                ]
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    concepts = load_concepts()
    tasks = load_json(ALL_TASK_OUTPUT)
    packets = load_json(PACKET_OUTPUT)
    rows_by_concept: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in tasks:
        rows_by_concept[concept_key(row)].append(row)
    concept_reports = [
        concept_report(concept, rows_by_concept[(concept["domain"], concept["concept_id"], concept["concept_name"])], packets)
        for concept in concepts
    ]
    failed = [r for r in concept_reports if r["status"] == "FAIL"]
    warned = [r for r in concept_reports if r["status"] == "WARN"]
    summary = {
        "total_concepts": len(concepts),
        "concepts_passed": sum(1 for r in concept_reports if r["status"] == "PASS"),
        "concepts_warned": len(warned),
        "concepts_failed": len(failed),
        "total_all_task_outputs": len(tasks),
        "expected_all_task_outputs": EXPECTED_TOTAL_TASK_OUTPUTS,
        "flashcard_level_coverage_pass": all(
            all(r["checks"]["flashcard_counts_by_difficulty"][level] == 7 for level in ["easy", "medium", "hard"])
            for r in concept_reports
        ),
        "assessment_coverage_pass": all(not r["checks"]["missing_assessment_types"] for r in concept_reports),
        "mindmap_coverage_pass": all(not r["checks"]["missing_mindmap_variants"] for r in concept_reports),
        "voice_coverage_pass": all(not r["checks"]["missing_voice_variants"] for r in concept_reports),
        "all_89_coverage_pass": all(r["checks"]["all_task_count"] == 89 and r["checks"]["task_type_count"] == 89 for r in concept_reports),
        "raw_generation_status": "WARN",
        "guarded_generation_status": "PASS",
        "concept_reports": concept_reports,
    }
    pass_ready = (
        summary["total_concepts"] == EXPECTED_CONCEPTS
        and summary["total_all_task_outputs"] == EXPECTED_TOTAL_TASK_OUTPUTS
        and summary["flashcard_level_coverage_pass"]
        and summary["assessment_coverage_pass"]
        and summary["mindmap_coverage_pass"]
        and summary["voice_coverage_pass"]
        and summary["all_89_coverage_pass"]
        and not failed
        and not warned
    )
    summary["status"] = "PASS" if pass_ready else ("FAIL" if failed else "WARN")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(markdown(summary), encoding="utf-8")
    for key in [
        "total_concepts",
        "concepts_passed",
        "concepts_failed",
        "total_all_task_outputs",
        "expected_all_task_outputs",
        "flashcard_level_coverage_pass",
        "assessment_coverage_pass",
        "mindmap_coverage_pass",
        "voice_coverage_pass",
        "all_89_coverage_pass",
        "status",
    ]:
        print(f"{key}: {summary[key]}")


if __name__ == "__main__":
    main()
