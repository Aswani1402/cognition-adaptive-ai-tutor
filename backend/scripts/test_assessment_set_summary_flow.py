from __future__ import annotations

from scripts.production_readiness_checks import assert_assessment_coverage, submit_answer


def main() -> None:
    assert_assessment_coverage()
    payload = submit_answer("practice_question")["answer_response"]
    assert payload.get("difficulty_progress"), payload
    assert payload.get("next_recommended_activity"), payload
    print("assessment set summary flow test success")


if __name__ == "__main__":
    main()
