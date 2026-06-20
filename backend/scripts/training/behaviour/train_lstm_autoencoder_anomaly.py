from __future__ import annotations

import json
import pickle
import random
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.behaviour.lstm_autoencoder_anomaly import (
    DB_PATH,
    FEATURE_NAMES,
    META_PATH,
    MODEL_PATH,
    _TorchAutoencoderFactory,
    build_learner_sequences,
    load_quiz_rows,
)


JSON_REPORT = Path("evaluation_outputs/json/lstm_autoencoder_anomaly_report.json")
MD_REPORT = Path("evaluation_outputs/reports/lstm_autoencoder_anomaly_report.md")


def _flatten_feature_mean(sequences: list[list[list[float]]]) -> list[float]:
    if not sequences:
        return [0.0] * len(FEATURE_NAMES)
    totals = [0.0] * len(FEATURE_NAMES)
    count = 0
    for seq in sequences:
        for row in seq:
            for idx, value in enumerate(row):
                totals[idx] += float(value)
            count += 1
    return [value / max(1, count) for value in totals]


def _statistical_errors(sequences: list[list[list[float]]], feature_mean: list[float]) -> list[float]:
    errors = []
    for seq in sequences:
        total = 0.0
        count = 0
        for row in seq:
            for value, avg in zip(row, feature_mean):
                total += (float(value) - float(avg)) ** 2
                count += 1
        errors.append(total / max(1, count))
    return errors


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.05
    values = sorted(values)
    idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * percentile))))
    return float(values[idx])


def _save_meta(meta: dict[str, Any]) -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _save_fallback_model(feature_mean: list[float]) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as handle:
        pickle.dump({"model_type": "statistical_fallback", "feature_mean": feature_mean}, handle)


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# LSTM Autoencoder Anomaly Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Sequence count: {report['sequence_count']}",
        f"- Learner count: {report['learner_count']}",
        f"- Feature count: {report['feature_count']}",
        f"- Model type: {report['model_type']}",
        f"- Final train loss: {report['train_loss_final']}",
        f"- Test reconstruction error mean: {report['test_reconstruction_error_mean']}",
        f"- Anomaly threshold: {report['anomaly_threshold']}",
        f"- Anomaly rate: {report['anomaly_rate']}",
        "",
        "## Top Anomalous Learners",
        "",
    ]
    for item in report["top_anomalous_learners"]:
        lines.append(f"- {item['learner_id']}: {item['anomaly_score']} ({item['risk_label']})")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fallback_training(
    sequences: list[list[list[float]]],
    learner_ids: list[str],
    reason: str,
    sequence_meta: dict[str, Any],
) -> dict[str, Any]:
    feature_mean = _flatten_feature_mean(sequences)
    errors = _statistical_errors(sequences, feature_mean)
    threshold = _percentile(errors, 0.95) if errors else 0.05
    _save_fallback_model(feature_mean)
    meta = {
        "status": "warning",
        "model_type": "statistical_fallback",
        "reason": reason,
        "model_path": str(MODEL_PATH),
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "max_seq_len": sequence_meta.get("max_seq_len", 20),
        "anomaly_threshold": threshold,
        "feature_mean": feature_mean,
        **sequence_meta,
    }
    _save_meta(meta)
    report = _build_report(
        status="warning",
        model_type="statistical_fallback",
        sequences=sequences,
        learner_ids=learner_ids,
        train_losses=[],
        train_errors=errors,
        test_errors=errors,
        threshold=threshold,
        reason=reason,
    )
    return report


def train_autoencoder() -> dict[str, Any]:
    rows = load_quiz_rows(DB_PATH)
    sequences, learner_ids, sequence_meta = build_learner_sequences(rows, max_seq_len=20, min_seq_len=3)
    if len(sequences) < 4:
        report = _fallback_training(
            sequences=sequences,
            learner_ids=learner_ids,
            reason="Insufficient learner sequences for neural autoencoder training.",
            sequence_meta=sequence_meta,
        )
        _write_reports(report)
        return report
    if not _TorchAutoencoderFactory.available():
        report = _fallback_training(
            sequences=sequences,
            learner_ids=learner_ids,
            reason="PyTorch unavailable, using statistical reconstruction fallback.",
            sequence_meta=sequence_meta,
        )
        _write_reports(report)
        return report

    import torch
    import torch.nn as nn

    random.seed(42)
    torch.manual_seed(42)
    pairs = list(zip(sequences, learner_ids))
    random.shuffle(pairs)
    split_idx = max(1, int(len(pairs) * 0.75))
    train_pairs = pairs[:split_idx]
    test_pairs = pairs[split_idx:] or pairs[:1]
    x_train = torch.tensor([item[0] for item in train_pairs], dtype=torch.float32)
    x_test = torch.tensor([item[0] for item in test_pairs], dtype=torch.float32)

    hidden_size = 16
    latent_size = 8
    model = _TorchAutoencoderFactory.build(len(FEATURE_NAMES), hidden_size, latent_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()
    train_losses = []
    epochs = 35
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        reconstructed = model(x_train)
        loss = criterion(reconstructed, x_train)
        loss.backward()
        optimizer.step()
        train_losses.append(float(loss.item()))

    model.eval()
    with torch.no_grad():
        train_recon = model(x_train)
        test_recon = model(x_test)
        train_errors = torch.mean((train_recon - x_train) ** 2, dim=(1, 2)).tolist()
        test_errors = torch.mean((test_recon - x_test) ** 2, dim=(1, 2)).tolist()
    threshold = _percentile([float(value) for value in train_errors], 0.95)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict()}, MODEL_PATH)
    meta = {
        "status": "success",
        "model_type": "pytorch_lstm_autoencoder",
        "model_path": str(MODEL_PATH),
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "max_seq_len": sequence_meta.get("max_seq_len", 20),
        "hidden_size": hidden_size,
        "latent_size": latent_size,
        "epochs": epochs,
        "anomaly_threshold": threshold,
        "feature_mean": _flatten_feature_mean(sequences),
        **sequence_meta,
    }
    _save_meta(meta)
    report = _build_report(
        status="success",
        model_type="pytorch_lstm_autoencoder",
        sequences=sequences,
        learner_ids=learner_ids,
        train_losses=train_losses,
        train_errors=[float(value) for value in train_errors],
        test_errors=[float(value) for value in test_errors],
        threshold=threshold,
        reason=None,
    )
    _write_reports(report)
    return report


def _build_report(
    status: str,
    model_type: str,
    sequences: list[list[list[float]]],
    learner_ids: list[str],
    train_losses: list[float],
    train_errors: list[float],
    test_errors: list[float],
    threshold: float,
    reason: str | None,
) -> dict[str, Any]:
    all_errors = train_errors or test_errors or []
    learner_scores = [
        {
            "learner_id": learner_id,
            "anomaly_score": round(float(error), 6),
            "risk_label": "high_anomaly" if error > threshold * 1.5 else "unusual" if error > threshold else "normal",
        }
        for learner_id, error in zip(learner_ids, all_errors + [0.0] * max(0, len(learner_ids) - len(all_errors)))
    ]
    learner_scores = sorted(learner_scores, key=lambda item: item["anomaly_score"], reverse=True)
    anomaly_count = sum(1 for item in learner_scores if item["anomaly_score"] > threshold)
    return {
        "status": status,
        "module": "lstm_autoencoder_anomaly_training",
        "model_type": model_type,
        "model_path": str(MODEL_PATH),
        "meta_path": str(META_PATH),
        "sequence_count": len(sequences),
        "learner_count": len(learner_ids),
        "feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "train_loss_curve": [round(float(value), 8) for value in train_losses],
        "train_loss_final": round(float(train_losses[-1]), 8) if train_losses else None,
        "train_reconstruction_errors": [round(float(value), 8) for value in train_errors],
        "test_reconstruction_errors": [round(float(value), 8) for value in test_errors],
        "test_reconstruction_error_mean": round(mean(test_errors), 8) if test_errors else None,
        "anomaly_threshold": round(float(threshold), 8),
        "anomaly_rate": round(anomaly_count / max(1, len(learner_scores)), 6),
        "top_anomalous_learners": learner_scores[:10],
        "limitation_notes": [
            "Unsupervised anomaly scores indicate unusual sequences, not confirmed misconduct or failure.",
            "Threshold uses the 95th percentile of training reconstruction errors.",
            "This detector is comparison/evidence support and does not replace the main behaviour runtime.",
        ],
        "limitations": [
            "Requires enough chronological learner interaction sequences for stable neural training.",
            "Falls back to statistical reconstruction if PyTorch or data volume is insufficient.",
            "Feature availability depends on quiz_results columns in tutor.db.",
        ],
        "reason": reason,
    }


def main() -> None:
    report = train_autoencoder()
    print(f"STATUS: {report['status']}")
    print("MODULE: train_lstm_autoencoder_anomaly")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")
    print(f"MODEL_PATH: {MODEL_PATH}")
    print(f"META_PATH: {META_PATH}")


if __name__ == "__main__":
    main()
