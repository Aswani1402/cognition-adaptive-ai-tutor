from __future__ import annotations

from scripts.final_demo_contract_checks import fail, passed, validate_question, write_result
from tutor.api.concept_content_resolver import assessment_payload


def main() -> None:
    errors = []
    details = {}
    for subject, concept in [
        ("Python", "P1"),
        ("SQL / Database", "S1"),
        ("HTML/Web Basics", "H1"),
        ("Git", "G1"),
        ("Data Structures", "D1"),
    ]:
        packet = assessment_payload(subject, concept, "hard")
        q_errors = {}
        for question in packet["questions"]:
            problems = validate_question(question)
            if problems:
                q_errors[question.get("question_id", "unknown")] = problems
        if q_errors:
            errors.append(subject)
            details[subject] = q_errors
    result = fail("Task rendering contract failed", details) if errors else passed("All task contracts valid", {"subjects_checked": 5})
    write_result("final_task_contract_fix_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
