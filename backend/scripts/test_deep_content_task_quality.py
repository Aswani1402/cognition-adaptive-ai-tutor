from __future__ import annotations

from scripts.final_demo_contract_checks import EXPECTED_TEACHING_VIEWS, fail, passed, validate_question, write_result
from tutor.api.concept_content_resolver import assessment_payload, build_lesson_payload


def main() -> None:
    errors = {}
    for subject, concept, concept_name in [
        ("Python", "P1", "Variables"),
        ("SQL / Database", "S1", "Database"),
        ("HTML/Web Basics", "H1", "HTML"),
        ("Git", "G1", "Version"),
        ("Data Structures", "D1", "Arrays"),
    ]:
        lesson = build_lesson_payload(subject, concept, "easy", "explanation")
        view_errors = []
        texts = []
        for view in EXPECTED_TEACHING_VIEWS:
            block = (lesson.get("content_by_view") or {}).get(view) or {}
            text = str(block.get("explanation") or "")
            texts.append(text)
            if not text.strip():
                view_errors.append(f"{view}: empty")
            if concept_name.lower().split()[0] not in text.lower() and str(lesson.get("concept_name", "")).lower() not in text.lower():
                view_errors.append(f"{view}: concept mismatch")
        if len(set(texts)) != len(texts):
            view_errors.append("teaching views are duplicated")
        task_errors = {}
        packet = assessment_payload(subject, concept, "hard")
        prompts = {str(q.get("task_type")): str(q.get("prompt")) for q in packet["questions"]}
        if prompts.get("challenge_question") == prompts.get("puzzle"):
            task_errors["challenge_vs_puzzle"] = ["identical prompt"]
        for q in packet["questions"]:
            problems = validate_question(q)
            if problems:
                task_errors[str(q.get("question_id"))] = problems
        if view_errors or task_errors:
            errors[subject] = {"view_errors": view_errors, "task_errors": task_errors}
    result = fail("Deep content/task quality failed", errors) if errors else passed("Deep content/task quality valid", {"subjects_checked": 5, "views_checked": EXPECTED_TEACHING_VIEWS})
    write_result("final_deep_content_quality_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
