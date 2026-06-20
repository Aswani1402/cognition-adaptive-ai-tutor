from __future__ import annotations

import json
from pathlib import Path


JSON_REPORT = Path("evaluation_outputs/json/lstm_autoencoder_anomaly_report.json")
MD_REPORT = Path("evaluation_outputs/reports/lstm_autoencoder_anomaly_report.md")


def _ensure_report() -> dict:
    if not JSON_REPORT.exists() or not MD_REPORT.exists():
        from scripts.training.behaviour.train_lstm_autoencoder_anomaly import train_autoencoder

        return train_autoencoder()
    return json.loads(JSON_REPORT.read_text(encoding="utf-8"))


def main() -> None:
    report = _ensure_report()
    assert report.get("status") in {"success", "warning"}
    assert report.get("module") == "lstm_autoencoder_anomaly_training"
    assert report.get("feature_count") == 8
    assert "anomaly_threshold" in report
    assert "anomaly_rate" in report
    assert "top_anomalous_learners" in report
    assert report.get("limitations")

    print(f"STATUS: {report['status']}")
    print("MODULE: lstm_autoencoder_anomaly_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
