from __future__ import annotations

from scripts.audit_full_system_module_connections import GENERATION_TASKS


REQUIRED = {
    "mcq",
    "fill_in_the_blank",
    "true_or_false",
    "debug_task",
    "output_prediction",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "transfer_question",
    "challenge_question",
    "explanation_check",
}


def main() -> None:
    assessment = set(GENERATION_TASKS["Assessment"])
    missing = REQUIRED - assessment
    assert not missing, f"Missing assessment task coverage entries: {missing}"
    print("STATUS: success")
    print("MODULE: test_assessment_type_coverage")


if __name__ == "__main__":
    main()
