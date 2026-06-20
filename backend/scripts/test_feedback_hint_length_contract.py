from __future__ import annotations

from scripts.final_demo_contract_checks import fail, passed, sentence_count, write_result
from tutor.api.concept_content_resolver import build_feedback, build_hints


def main() -> None:
    errors = []
    hints = build_hints("Python", "P1", "mcq", 0)
    feedback = build_feedback("Python", "P1", True, 1.0, "mcq")
    if sentence_count(str(hints.get("hint_text") or "")) > 2:
        errors.append("hint_text longer than two sentences")
    for key in ("feedback", "correct_answer_feedback", "wrong_answer_feedback", "partial_answer_feedback"):
        if sentence_count(str(feedback.get(key) or "")) > 4:
            errors.append(f"{key} longer than four sentences")
    result = fail("Feedback/hint length contract failed", {"errors": errors, "hints": hints, "feedback": feedback}) if errors else passed("Feedback/hint length contract valid", {"hint_text": hints.get("hint_text"), "feedback": feedback.get("feedback")})
    write_result("final_feedback_hint_length_contract_report", result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
