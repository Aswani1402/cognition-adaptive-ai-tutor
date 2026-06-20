from __future__ import annotations

from scripts.final_demo_contract_checks import component, options, correct_answer, passed, fail, write_result
from tutor.api.concept_content_resolver import assessment_payload


def main() -> None:
    packet = assessment_payload("Python", "P1", "easy")
    mcqs = [q for q in packet["questions"] if str(q.get("task_type") or q.get("question_type")).lower() == "mcq"]
    if not mcqs:
        result = fail("No MCQ returned", packet)
    else:
        q = mcqs[0]
        errors = []
        if component(q) != "MCQQuestionCard":
            errors.append(f"frontend_component={component(q)}")
        if len(options(q)) != 4:
            errors.append(f"options_count={len(options(q))}")
        if correct_answer(q) is None:
            errors.append("missing_correct_answer")
        if str(q.get("evaluation_mode")) != "exact_match":
            errors.append(f"evaluation_mode={q.get('evaluation_mode')}")
        result = fail("MCQ contract failed", {"errors": errors, "question": q}) if errors else passed("MCQ contract valid", q)
    write_result("final_demo_backend_contract_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
