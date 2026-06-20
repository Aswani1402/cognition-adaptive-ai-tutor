from __future__ import annotations

import json

from tutor.behaviour.behaviour_state_store import persist_behaviour_state
from tutor.behaviour.lstm_behaviour_model import BehaviourLSTMRuntime, find_lstm_artifact
from tutor.api.evaluation_routes import submit_answer
from tutor.api.schemas import SubmitAnswerRequest


def main() -> None:
    learner_id = "14"
    interaction = {
        "learner_id": learner_id,
        "concept_id": "smoke_concept",
        "domain": "python",
        "question_type": "practice_question",
        "difficulty": "medium",
        "time_taken_sec": 42,
        "confidence": 0.65,
        "hint_count": 1,
        "hint_used": True,
        "option_change_count": 1,
        "answer_change_count": 0,
        "run_code_count": 1,
        "attempt_count": 1,
        "wrong_attempt_count": 0,
        "score": 0.9,
    }

    artifact = find_lstm_artifact()
    result = BehaviourLSTMRuntime().predict(learner_id, interaction=interaction)
    persistence = persist_behaviour_state(result)
    submit_response = submit_answer(
        SubmitAnswerRequest(
            learner_id=learner_id,
            concept_id="smoke_concept",
            concept_name="Variables",
            domain="python",
            subject="python",
            difficulty="easy",
            question_type="mcq",
            answer="A variable stores a value.",
            question={
                "concept_id": "smoke_concept",
                "concept_name": "Variables",
                "domain": "python",
                "task_type": "mcq",
                "prompt": "What does a variable do?",
                "correct_answer": "A variable stores a value.",
            },
            confidence=0.8,
            time_taken_sec=18,
            hint_used=False,
            hint_count=0,
            option_change_count=0,
            answer_change_count=0,
            run_code_count=0,
            attempt_count=1,
            wrong_attempt_count=0,
        )
    )
    submit_data = submit_response.get("data", submit_response)
    submit_behaviour = submit_data.get("behaviour_update", {})

    assert result["status"] == "success"
    assert result["model_source"] in {
        "lstm_runtime",
        "fallback_proxy_signal_scoring",
        "lstm_load_failed_fallback",
    }
    assert result["behaviour_state"] in {"stable", "confused", "guessing", "struggling"}
    assert 0.0 <= float(result["behaviour_risk"]) <= 1.0
    assert "evidence_inputs" in result
    assert persistence["status"] in {"success", "error"}
    assert submit_behaviour.get("model_source") in {
        "lstm_runtime",
        "fallback_proxy_signal_scoring",
        "lstm_load_failed_fallback",
    }

    print(
        json.dumps(
            {
                "status": "success",
                "artifact_path": str(artifact) if artifact else None,
                "model_source": result["model_source"],
                "behaviour_state": result["behaviour_state"],
                "behaviour_risk": result["behaviour_risk"],
                "persistence_status": persistence["status"],
                "answer_submit_model_source": submit_behaviour.get("model_source"),
                "answer_submit_behaviour_state": submit_behaviour.get("behaviour_state"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
