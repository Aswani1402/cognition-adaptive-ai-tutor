from __future__ import annotations

import json
from pathlib import Path

from tutor.behaviour.lstm_behaviour_model import BehaviourLSTMRuntime


def main() -> None:
    interaction = {
        "learner_id": "fallback_smoke",
        "concept_id": "fallback_concept",
        "domain": "python",
        "question_type": "mcq",
        "difficulty": "easy",
        "time_taken_sec": 95,
        "confidence": 0.25,
        "hint_count": 2,
        "hint_used": True,
        "option_change_count": 3,
        "answer_change_count": 2,
        "run_code_count": 0,
        "attempt_count": 3,
        "wrong_attempt_count": 2,
        "score": 0.0,
    }
    runtime = BehaviourLSTMRuntime(artifact_path=Path("models/behaviour_lstm/missing_model_for_fallback_test.pt"))
    result = runtime.predict("fallback_smoke", interaction=interaction, recent_sequence=[])

    assert result["status"] == "success"
    assert result["model_source"] == "fallback_proxy_signal_scoring"
    assert result["fallback_reason"] == "LSTM artifact not found."
    assert result["behaviour_state"] in {"stable", "confused", "guessing", "struggling"}
    assert 0.0 <= float(result["behaviour_risk"]) <= 1.0
    assert result["evidence_inputs"]["time_taken_sec"] == 95

    sparse_result = runtime.predict("fallback_sparse", interaction={"learner_id": "fallback_sparse"})
    assert sparse_result["status"] == "success"
    assert sparse_result["model_source"] == "fallback_proxy_signal_scoring"
    assert 0.0 <= float(sparse_result["behaviour_risk"]) <= 1.0

    print(
        json.dumps(
            {
                "status": "success",
                "model_source": result["model_source"],
                "behaviour_state": result["behaviour_state"],
                "behaviour_risk": result["behaviour_risk"],
                "fallback_reason": result["fallback_reason"],
                "sparse_missing_feature_status": sparse_result["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
