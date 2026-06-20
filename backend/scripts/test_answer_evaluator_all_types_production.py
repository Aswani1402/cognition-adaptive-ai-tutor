from __future__ import annotations

from scripts.production_readiness_checks import submit_answer


def main() -> None:
    for question_type in ["mcq", "debug_task", "output_prediction", "transfer_question", "challenge_question", "syntax_completion", "coding_prompt", "code_reasoning_task"]:
        payload = submit_answer(question_type)["answer_response"]
        for key in ["score", "label", "correct_answer", "explanation", "feedback", "mistake_type", "weakest_skill", "recommended_next_activity"]:
            assert key in payload, f"Missing {key} for {question_type}: {payload}"
    print("answer evaluator all types production test success")


if __name__ == "__main__":
    main()
