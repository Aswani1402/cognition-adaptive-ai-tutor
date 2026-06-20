from tutor.api.evaluation_routes import _behaviour_signals
from tutor.api.schemas import SubmitAnswerRequest


def main():
    payload = SubmitAnswerRequest(
        learner_id="demo",
        subject="Python",
        concept_id="P1",
        question_type="mcq",
        answer="Referring to a value",
        confidence=0.3,
        time_taken_sec=42,
        hint_used=True,
        hint_count=1,
        option_change_count=2,
        answer_change_count=3,
        run_code_count=1,
        attempt_count=1,
        wrong_attempt_count=0,
    )
    signals = _behaviour_signals(payload=payload, score=0.5)
    assert signals["hint_rate"] > 0
    assert signals["low_confidence_rate"] > 0
    assert signals["answer_change_rate"] > 0
    print("behaviour payload flow ok")


if __name__ == "__main__":
    main()
