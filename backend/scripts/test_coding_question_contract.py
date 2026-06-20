from __future__ import annotations

from scripts.final_demo_contract_checks import fail, passed, write_result
from tutor.api.concept_content_resolver import assessment_payload


def main() -> None:
    packet = assessment_payload("Python", "P1", "hard")
    coding = [q for q in packet["questions"] if str(q.get("task_type")).lower() in {"coding_question", "coding_prompt"}]
    errors = []
    if not coding:
        errors.append("no coding question")
    else:
        q = coding[0]
        if q.get("frontend_component") != "CodeWritingCard":
            errors.append("coding question not mapped to CodeWritingCard")
        if len(str(q.get("prompt") or "").split()) < 8:
            errors.append("coding prompt lacks clear goal")
        if "tiny example" in str(q.get("prompt") or "").lower():
            errors.append("coding prompt contains tiny example placeholder")
        if not q.get("constraints"):
            errors.append("missing requirements/constraints")
        if not (q.get("expected_output") or q.get("expectedOutput") or q.get("expected_answer")):
            errors.append("missing expected behavior/output")
    result = fail("Coding question contract failed", {"errors": errors, "question": coding[0] if coding else None}) if errors else passed("Coding question contract valid", coding[0])
    write_result("final_coding_question_contract_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
