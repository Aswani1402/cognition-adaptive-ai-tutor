from __future__ import annotations

import json
from pathlib import Path

from tutor.api.concept_content_resolver import SUBJECT_DBS, assessment_payload


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "evaluation_outputs" / "reports" / "assessment_prompt_quality_fix_report.md"
REPORT_JSON = ROOT / "evaluation_outputs" / "json" / "assessment_prompt_quality_fix_report.json"

REQUIRED = {
    "question_id", "subject", "concept_id", "concept_name", "difficulty", "task_type",
    "title", "prompt", "instructions", "expected_answer", "hint", "explanation",
    "evaluation_mode", "generated_source", "grounding_source_label", "frontend_component",
}
BAD = ["tiny example", "this concept", "short reasoning challenge using the concept", "solve this challenge", "write your explanation"]


def main() -> None:
    failures: list[str] = []
    subjects = list(SUBJECT_DBS)
    seen_task_types: set[str] = set()
    samples = []
    for subject in subjects:
        packet = assessment_payload(subject, None, "hard")
        questions = packet.get("questions", [])
        if not questions:
            failures.append(f"{subject}: no questions")
            continue
        for q in questions:
            missing = sorted(field for field in REQUIRED if q.get(field) in (None, "", []))
            if missing:
                failures.append(f"{subject}/{q.get('task_type')}: missing {missing}")
            prompt = str(q.get("prompt") or "").lower()
            if any(bad in prompt for bad in BAD):
                failures.append(f"{subject}/{q.get('task_type')}: vague placeholder prompt")
            if q.get("task_type") == "challenge_question" and "puzzle" in prompt:
                failures.append(f"{subject}: challenge duplicates puzzle wording")
            seen_task_types.add(str(q.get("task_type")))
        samples.append({"subject": subject, "concept_id": packet.get("concept_id"), "task_types": [q.get("task_type") for q in questions]})
    expected_types = {"mcq", "output_prediction", "debug_task", "syntax_completion", "coding_question", "transfer_question", "challenge_question", "explanation", "flashcard_recall", "puzzle"}
    missing_types = sorted(expected_types - seen_task_types)
    if missing_types:
        failures.append(f"missing task types: {missing_types}")
    status = "pass" if not failures else "fail"
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({"status": status, "failures": failures, "samples": samples}, indent=2), encoding="utf-8")
    REPORT_MD.write_text("# Assessment Prompt Quality Fix Report\n\n" + f"Status: {status}\n\n" + "\n".join(f"- {item}" for item in (failures or ["All checked task prompts are structured and concept-grounded."])), encoding="utf-8")
    if failures:
        raise SystemExit(1)
    print(json.dumps({"status": status, "subjects": subjects, "task_types": sorted(seen_task_types)}, indent=2))


if __name__ == "__main__":
    main()
