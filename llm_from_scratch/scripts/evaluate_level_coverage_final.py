from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.cognitutor_lm_config import ALL_89_TASK_TYPES, DIFFICULTIES, TEACHING_VIEWS


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "final_evaluation"
JSON_OUT = OUT / "json" / "level_coverage_final_evaluation.json"
MD_OUT = OUT / "md" / "level_coverage_final_evaluation.md"
CSV_OUT = OUT / "csv" / "level_coverage_by_concept.csv"
ALL_TASKS = ROOT / "outputs" / "model_generated" / "structured_model_generated_all_tasks.json"

ASSESSMENT_TYPES = {
    "mcq", "debug_task", "output_prediction", "transfer_question", "challenge_question",
    "explanation_check", "syntax_completion", "coding_prompt", "code_reasoning_task",
    "fill_in_the_blank", "true_or_false", "practice_question", "transfer_task",
    "real_world_application_question", "debug_challenge", "output_prediction_challenge",
    "multi_step_challenge",
}
FLASHCARD_VARIANTS = {
    "flashcard", "concept_recall_flashcard", "misconception_flashcard", "example_flashcard",
    "debug_flashcard", "personal_flashcards", "syntax_flashcard",
}
MINDMAP_VARIANTS = {"mindmap", "concept_mindmap", "comparison_mindmap"}
VOICE_VARIANTS = {
    "voice_script", "teaching_voice_script", "revision_voice_script",
    "mistake_feedback_voice_script", "doubt_explanation_voice_script",
    "encouragement_script", "next_step_guidance_script", "concept_intro_voice_script",
}


def load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def main() -> None:
    for directory in [OUT / "json", OUT / "md", OUT / "csv"]:
        directory.mkdir(parents=True, exist_ok=True)
    rows = load_json(ALL_TASKS)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("domain"), row.get("concept_id"), row.get("concept_name"))].append(row)

    concept_reports = []
    for (domain, concept_id, concept_name), items in sorted(grouped.items()):
        task_types = {r.get("task_type") for r in items}
        difficulties = {r.get("difficulty") for r in items}
        teaching_views = {r.get("teaching_view") for r in items if r.get("teaching_view")}
        assessment = task_types & ASSESSMENT_TYPES
        flashcards = task_types & FLASHCARD_VARIANTS
        mindmaps = task_types & MINDMAP_VARIANTS
        voices = task_types & VOICE_VARIANTS
        flashcards_by_difficulty = {
            diff: sorted({r.get("task_type") for r in items if r.get("difficulty") == diff and r.get("task_type") in FLASHCARD_VARIANTS})
            for diff in DIFFICULTIES
        }
        missing = {
            "difficulty": [d for d in DIFFICULTIES if d not in difficulties],
            "teaching_views": [v for v in TEACHING_VIEWS if v not in teaching_views],
            "assessment_types": sorted(ASSESSMENT_TYPES - assessment),
            "flashcard_variants": sorted(FLASHCARD_VARIANTS - flashcards),
            "mindmap_variants": sorted(MINDMAP_VARIANTS - mindmaps),
            "voice_variants": sorted(VOICE_VARIANTS - voices),
            "all_89_task_types": [t for t in ALL_89_TASK_TYPES if t not in task_types],
        }
        core_pass = all(not values for values in missing.values()) and len(items) == 89
        flashcard_diff_pass = all(len(flashcards_by_difficulty[d]) >= 7 for d in DIFFICULTIES)
        status = "PASS" if core_pass and flashcard_diff_pass else ("WARN" if core_pass else "FAIL")
        concept_reports.append({
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "status": status,
            "task_count": len(items),
            "difficulty_coverage": {d: d in difficulties for d in DIFFICULTIES},
            "teaching_view_count": len(teaching_views),
            "assessment_type_count": len(assessment),
            "flashcard_variant_count": len(flashcards),
            "flashcard_variants_by_difficulty": flashcards_by_difficulty,
            "mindmap_variant_count": len(mindmaps),
            "voice_variant_count": len(voices),
            "missing": missing,
        })

    failed = [r for r in concept_reports if r["status"] == "FAIL"]
    warned = [r for r in concept_reports if r["status"] == "WARN"]
    concepts_checked = len(concept_reports)
    final_status = "FAIL" if failed else ("WARN" if warned else "PASS")
    coverage_percent = round(((concepts_checked - len(failed)) / concepts_checked) * 100, 2) if concepts_checked else 0
    concept_level_flashcards_ok = all(
        report["flashcard_variant_count"] >= 7 and not report["missing"]["flashcard_variants"]
        for report in concept_reports
    )
    flashcard_difficulty_coverage = "PASS" if concept_level_flashcards_ok and not warned and not failed else ("WARN" if concept_level_flashcards_ok else "FAIL")
    flash_reason = None
    if flashcard_difficulty_coverage == "WARN":
        flash_reason = "7 variants exist at concept level but not per easy/medium/hard/revision level for all concepts"
    elif flashcard_difficulty_coverage == "FAIL":
        flash_reason = "7 concept-level flashcard variants are missing for one or more concepts"

    report = {
        "evaluation_name": "level_coverage_final_evaluation",
        "concepts_checked": concepts_checked,
        "concepts_passed": sum(1 for r in concept_reports if r["status"] == "PASS"),
        "concepts_failed": len(failed),
        "concepts_warned": len(warned),
        "failed_concepts": [f"{r['domain']} / {r['concept_id']} / {r['concept_name']}" for r in failed],
        "coverage_percent": coverage_percent,
        "missing_by_concept": {f"{r['domain']} / {r['concept_id']} / {r['concept_name']}": r["missing"] for r in concept_reports if any(r["missing"].values())},
        "flashcard_difficulty_coverage": flashcard_difficulty_coverage,
        "flashcard_difficulty_coverage_reason": flash_reason,
        "concept_reports": concept_reports,
        "final_status": final_status,
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["domain", "concept_id", "concept_name", "status", "task_count", "teaching_view_count", "assessment_type_count", "flashcard_variant_count", "mindmap_variant_count", "voice_variant_count"])
        writer.writeheader()
        for row in concept_reports:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    lines = [
        "# Level Coverage Final Evaluation",
        "",
        f"- final_status: {final_status}",
        f"- concepts_checked: {concepts_checked}",
        f"- concepts_passed: {report['concepts_passed']}",
        f"- concepts_warned: {len(warned)}",
        f"- concepts_failed: {len(failed)}",
        f"- coverage_percent: {coverage_percent}",
        f"- flashcard_difficulty_coverage: {flashcard_difficulty_coverage}",
        f"- reason: {flash_reason or 'none'}",
    ]
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"final_status": final_status, "json": str(JSON_OUT)}, indent=2))


if __name__ == "__main__":
    main()
