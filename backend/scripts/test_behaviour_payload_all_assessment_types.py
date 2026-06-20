from __future__ import annotations

from scripts.production_readiness_checks import submit_answer


def main() -> None:
    for question_type in ["mcq", "fill_in_the_blank", "true_or_false", "output_prediction", "debug_task", "syntax_completion", "coding_prompt", "code_reasoning_task", "transfer_question", "challenge_question"]:
        payload = submit_answer(question_type)["answer_response"]
        behaviour = payload.get("behaviour_update") or {}
        assert behaviour.get("signals_used"), behaviour
        assert "time_taken_sec" in behaviour.get("signals_used", []), behaviour
    print("behaviour payload all assessment types test success")


if __name__ == "__main__":
    main()
