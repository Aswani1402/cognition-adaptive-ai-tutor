from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/lstm_autoencoder_anomaly_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/lstm_autoencoder_anomaly_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/lstm_autoencoder_anomaly_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.training.behaviour.train_lstm_autoencoder_anomaly import train_autoencoder

        return train_autoencoder()
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    loss_path = CHART_DIR / "lstm_autoencoder_loss_curve.png"
    score_path = CHART_DIR / "lstm_autoencoder_anomaly_score_distribution.png"
    rate_path = CHART_DIR / "lstm_autoencoder_anomaly_rate.png"
    top_path = CHART_DIR / "lstm_autoencoder_top_anomalies.png"

    losses = report.get("train_loss_curve") or [report.get("train_loss_final") or 0.0]
    plt.figure(figsize=(7, 4.5))
    plt.plot(list(range(1, len(losses) + 1)), losses)
    plt.title("LSTM Autoencoder Loss Curve")
    plt.xlabel("Epoch")
    plt.ylabel("MSE loss")
    _save(loss_path)

    scores = report.get("train_reconstruction_errors", []) + report.get("test_reconstruction_errors", [])
    if not scores:
        scores = [item.get("anomaly_score", 0.0) for item in report.get("top_anomalous_learners", [])] or [0.0]
    plt.figure(figsize=(7, 4.5))
    plt.hist(scores, bins=10)
    plt.title("LSTM Autoencoder Anomaly Score Distribution")
    plt.xlabel("Reconstruction error")
    plt.ylabel("Sequence count")
    _save(score_path)

    anomaly_rate = float(report.get("anomaly_rate", 0.0) or 0.0)
    plt.figure(figsize=(5.5, 4.5))
    plt.bar(["normal", "anomalous"], [1.0 - anomaly_rate, anomaly_rate])
    plt.title("LSTM Autoencoder Anomaly Rate")
    plt.ylabel("Rate")
    _save(rate_path)

    top = report.get("top_anomalous_learners", [])[:10]
    labels = [item.get("learner_id", "unknown") for item in top] or ["none"]
    values = [item.get("anomaly_score", 0.0) for item in top] or [0.0]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.xticks(rotation=30, ha="right")
    plt.title("Top LSTM Autoencoder Anomalies")
    plt.ylabel("Anomaly score")
    _save(top_path)

    visualization = {
        "status": "success",
        "module": "lstm_autoencoder_anomaly_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "lstm_autoencoder_loss_curve": str(loss_path),
            "lstm_autoencoder_anomaly_score_distribution": str(score_path),
            "lstm_autoencoder_anomaly_rate": str(rate_path),
            "lstm_autoencoder_top_anomalies": str(top_path),
        },
        "source_report": str(REPORT_PATH),
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# LSTM Autoencoder Anomaly Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: lstm_autoencoder_anomaly_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
