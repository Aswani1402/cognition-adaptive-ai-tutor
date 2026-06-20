from __future__ import annotations

import json

from tutor.behaviour.lstm_autoencoder_anomaly import (
    META_PATH,
    MODEL_PATH,
    BehaviourAnomalyDetector,
    load_quiz_rows,
)


REPORT_PATH = "evaluation_outputs/json/lstm_autoencoder_anomaly_report.json"


def _ensure_training() -> dict:
    if not MODEL_PATH.exists() or not META_PATH.exists():
        from scripts.training.behaviour.train_lstm_autoencoder_anomaly import train_autoencoder

        return train_autoencoder()
    report_path = __import__("pathlib").Path(REPORT_PATH)
    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))
    from scripts.training.behaviour.train_lstm_autoencoder_anomaly import train_autoencoder

    return train_autoencoder()


def main() -> None:
    report = _ensure_training()
    assert MODEL_PATH.exists()
    assert META_PATH.exists()

    detector = BehaviourAnomalyDetector().load()
    assert detector.loaded is True

    rows = load_quiz_rows()
    learner_ids = sorted({str(row.get("learner_id")) for row in rows if row.get("learner_id")})
    learner_id = learner_ids[0] if learner_ids else "14"
    output = detector.detect_for_learner(learner_id)
    assert output["status"] == "success"
    assert output["module"] == "BehaviourAnomalyDetector"
    assert output["learner_id"] == learner_id
    assert isinstance(output["anomaly_score"], (int, float))
    assert isinstance(output["anomaly_threshold"], (int, float))
    assert output["risk_label"] in {"normal", "unusual", "high_anomaly"}
    assert "feature_summary" in output
    assert report.get("sequence_count") is not None

    print("STATUS: success")
    print("MODULE: lstm_autoencoder_anomaly_test")
    print(f"MODEL_PATH: {MODEL_PATH}")
    print(f"META_PATH: {META_PATH}")


if __name__ == "__main__":
    main()
