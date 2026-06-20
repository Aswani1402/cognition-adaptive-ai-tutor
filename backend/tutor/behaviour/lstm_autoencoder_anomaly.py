from __future__ import annotations

import json
import math
import pickle
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
MODEL_PATH = PROJECT_ROOT / "models" / "behaviour" / "lstm_autoencoder.pt"
META_PATH = PROJECT_ROOT / "models" / "behaviour" / "lstm_autoencoder_meta.json"

FEATURE_NAMES = [
    "correctness",
    "score",
    "normalized_time",
    "confidence",
    "hint_used",
    "option_change_rate",
    "wrong_streak",
    "attempt_index_norm",
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def load_quiz_rows(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with _connect(db_path) as conn:
        cols = _columns(conn, "quiz_results")
        if not cols or "learner_id" not in cols:
            return []
        select_cols = [
            "quiz_id",
            "learner_id",
            "concept_id",
            "is_correct" if "is_correct" in cols else "NULL AS is_correct",
            "score" if "score" in cols else "NULL AS score",
            "time_taken_sec" if "time_taken_sec" in cols else "NULL AS time_taken_sec",
            "confidence" if "confidence" in cols else "NULL AS confidence",
            "hint_used" if "hint_used" in cols else "NULL AS hint_used",
            "hint_count" if "hint_count" in cols else "NULL AS hint_count",
            "option_changes_count" if "option_changes_count" in cols else "NULL AS option_changes_count",
            "attempt_no" if "attempt_no" in cols else "NULL AS attempt_no",
            "timestamp" if "timestamp" in cols else "NULL AS timestamp",
        ]
        rows = conn.execute(f"SELECT {', '.join(select_cols)} FROM quiz_results").fetchall()
    return [dict(row) for row in rows]


def build_learner_sequences(
    rows: list[dict[str, Any]],
    max_seq_len: int = 20,
    min_seq_len: int = 3,
) -> tuple[list[list[list[float]]], list[str], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        learner_id = str(row.get("learner_id") or "").strip()
        if not learner_id:
            continue
        grouped.setdefault(learner_id, []).append(row)

    sequences: list[list[list[float]]] = []
    learner_ids: list[str] = []
    skipped = 0
    for learner_id, learner_rows in grouped.items():
        learner_rows = sorted(
            learner_rows,
            key=lambda item: (
                str(item.get("timestamp") or ""),
                int(_safe_float(item.get("quiz_id"), 0)),
            ),
        )
        if len(learner_rows) < min_seq_len:
            skipped += 1
            continue
        seq = _rows_to_sequence(learner_rows[-max_seq_len:], max_seq_len)
        sequences.append(seq)
        learner_ids.append(learner_id)
    meta = {
        "raw_learner_count": len(grouped),
        "skipped_short_sequence_learners": skipped,
        "max_seq_len": max_seq_len,
        "min_seq_len": min_seq_len,
        "feature_names": FEATURE_NAMES,
    }
    return sequences, learner_ids, meta


def sequence_for_learner(
    learner_id: str,
    db_path: Path = DB_PATH,
    max_seq_len: int = 20,
    min_seq_len: int = 1,
) -> tuple[list[list[float]], list[dict[str, Any]]]:
    rows = [row for row in load_quiz_rows(db_path) if str(row.get("learner_id")) == str(learner_id)]
    rows = sorted(rows, key=lambda item: (str(item.get("timestamp") or ""), int(_safe_float(item.get("quiz_id"), 0))))
    if len(rows) < min_seq_len:
        return [[0.0] * len(FEATURE_NAMES) for _ in range(max_seq_len)], rows
    return _rows_to_sequence(rows[-max_seq_len:], max_seq_len), rows


def _rows_to_sequence(rows: list[dict[str, Any]], max_seq_len: int) -> list[list[float]]:
    positive_times = [_safe_float(row.get("time_taken_sec"), 0.0) for row in rows if _safe_float(row.get("time_taken_sec"), 0.0) > 0]
    max_time = max(positive_times) if positive_times else 60.0
    wrong_streak = 0
    seq = []
    for index, row in enumerate(rows[-max_seq_len:], start=1):
        correctness = _derive_correctness(row)
        score = _derive_score(row, correctness)
        time_norm = clamp(_safe_float(row.get("time_taken_sec"), 0.0) / max_time if max_time else 0.0)
        confidence = _safe_float(row.get("confidence"), 0.5)
        if confidence > 1.0:
            confidence = confidence / 5.0
        confidence = clamp(confidence, 0.0, 1.0)
        hint_count = _safe_float(row.get("hint_count"), 0.0)
        hint_used = 1.0 if _safe_float(row.get("hint_used"), 0.0) > 0 or hint_count > 0 else 0.0
        option_change_rate = clamp(_safe_float(row.get("option_changes_count"), 0.0) / 5.0)
        wrong_streak = wrong_streak + 1 if correctness < 0.5 else 0
        attempt_no = _safe_float(row.get("attempt_no"), index)
        seq.append(
            [
                clamp(correctness),
                clamp(score),
                time_norm,
                confidence,
                hint_used,
                option_change_rate,
                clamp(wrong_streak / 5.0),
                clamp(attempt_no / 10.0),
            ]
        )
    while len(seq) < max_seq_len:
        seq.insert(0, [0.0] * len(FEATURE_NAMES))
    return seq


def _derive_correctness(row: dict[str, Any]) -> float:
    if row.get("is_correct") is not None:
        return 1.0 if int(_safe_float(row.get("is_correct"), 0)) else 0.0
    if row.get("correct") is not None:
        return 1.0 if int(_safe_float(row.get("correct"), 0)) else 0.0
    return 1.0 if _safe_float(row.get("score"), 0.0) >= 0.75 else 0.0


def _derive_score(row: dict[str, Any], correctness: float) -> float:
    if row.get("score") is not None:
        return clamp(_safe_float(row.get("score"), correctness))
    return correctness


class _TorchAutoencoderFactory:
    @staticmethod
    def available() -> bool:
        try:
            import torch  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def build(input_size: int, hidden_size: int, latent_size: int):
        import torch
        import torch.nn as nn

        class LSTMAutoencoder(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.encoder = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
                self.to_latent = nn.Linear(hidden_size, latent_size)
                self.from_latent = nn.Linear(latent_size, hidden_size)
                self.decoder = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
                self.output = nn.Linear(hidden_size, input_size)

            def forward(self, x):
                _, (h, _) = self.encoder(x)
                latent = self.to_latent(h[-1])
                hidden = self.from_latent(latent).unsqueeze(0)
                cell = torch.zeros_like(hidden)
                decoder_input = torch.zeros_like(x)
                decoded, _ = self.decoder(decoder_input, (hidden, cell))
                return self.output(decoded)

        return LSTMAutoencoder()


class BehaviourAnomalyDetector:
    MODULE = "BehaviourAnomalyDetector"

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        meta_path: Path = META_PATH,
        db_path: Path = DB_PATH,
    ) -> None:
        self.model_path = Path(model_path)
        self.meta_path = Path(meta_path)
        self.db_path = Path(db_path)
        self.meta: dict[str, Any] = {}
        self.model: Any = None
        self.loaded = False

    def load(self) -> "BehaviourAnomalyDetector":
        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        else:
            self.meta = self._fallback_meta("Meta file missing.")
        model_type = self.meta.get("model_type", "statistical_fallback")
        if model_type == "pytorch_lstm_autoencoder" and self.model_path.exists() and _TorchAutoencoderFactory.available():
            import torch

            self.model = _TorchAutoencoderFactory.build(
                input_size=int(self.meta.get("feature_count", len(FEATURE_NAMES))),
                hidden_size=int(self.meta.get("hidden_size", 16)),
                latent_size=int(self.meta.get("latent_size", 8)),
            )
            checkpoint = torch.load(self.model_path, map_location="cpu")
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.eval()
        elif self.model_path.exists():
            try:
                with self.model_path.open("rb") as handle:
                    self.model = pickle.load(handle)
            except Exception:
                self.model = None
        self.loaded = True
        return self

    def score_sequence(self, sequence: list[list[float]]) -> dict[str, Any]:
        if not self.loaded:
            self.load()
        max_seq_len = int(self.meta.get("max_seq_len", len(sequence) or 20))
        sequence = self._normalize_sequence(sequence, max_seq_len)
        model_type = self.meta.get("model_type", "statistical_fallback")
        if model_type == "pytorch_lstm_autoencoder" and self.model is not None and _TorchAutoencoderFactory.available():
            import torch

            x = torch.tensor([sequence], dtype=torch.float32)
            with torch.no_grad():
                reconstructed = self.model(x)
                error = torch.mean((reconstructed - x) ** 2).item()
            model_used = True
            fallback_used = False
        else:
            error = self._statistical_error(sequence)
            model_used = False
            fallback_used = True
        threshold = float(self.meta.get("anomaly_threshold", 0.05))
        return {
            "anomaly_score": round(float(error), 6),
            "anomaly_threshold": round(threshold, 6),
            "is_anomalous": float(error) > threshold,
            "risk_label": self._risk_label(float(error), threshold),
            "model_used": model_used,
            "fallback_used": fallback_used,
        }

    def detect_for_learner(self, learner_id: str) -> dict[str, Any]:
        if not self.loaded:
            self.load()
        seq, rows = sequence_for_learner(
            learner_id=str(learner_id),
            db_path=self.db_path,
            max_seq_len=int(self.meta.get("max_seq_len", 20)),
            min_seq_len=1,
        )
        scored = self.score_sequence(seq)
        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": str(learner_id),
            **scored,
            "feature_summary": self._feature_summary(seq, len(rows)),
        }

    def detect_batch(self, learner_ids: list[str]) -> dict[str, Any]:
        outputs = [self.detect_for_learner(str(learner_id)) for learner_id in learner_ids]
        return {
            "status": "success",
            "module": self.MODULE,
            "learner_count": len(outputs),
            "results": outputs,
        }

    def _normalize_sequence(self, sequence: list[list[float]], max_seq_len: int) -> list[list[float]]:
        cleaned = []
        for row in sequence[-max_seq_len:]:
            values = [clamp(_safe_float(value, 0.0)) for value in list(row)[: len(FEATURE_NAMES)]]
            while len(values) < len(FEATURE_NAMES):
                values.append(0.0)
            cleaned.append(values)
        while len(cleaned) < max_seq_len:
            cleaned.insert(0, [0.0] * len(FEATURE_NAMES))
        return cleaned

    def _statistical_error(self, sequence: list[list[float]]) -> float:
        mean_vector = self.meta.get("feature_mean")
        if not mean_vector:
            mean_vector = [0.0] * len(FEATURE_NAMES)
        total = 0.0
        count = 0
        for row in sequence:
            for value, mean in zip(row, mean_vector):
                total += (float(value) - float(mean)) ** 2
                count += 1
        return total / max(1, count)

    def _feature_summary(self, sequence: list[list[float]], raw_sequence_length: int) -> dict[str, Any]:
        active = [row for row in sequence if any(value != 0.0 for value in row)]
        rows = active or sequence
        summary = {}
        for idx, name in enumerate(FEATURE_NAMES):
            summary[f"avg_{name}"] = round(sum(row[idx] for row in rows) / max(1, len(rows)), 6)
        summary["raw_sequence_length"] = raw_sequence_length
        summary["padded_sequence_length"] = len(sequence)
        return summary

    def _risk_label(self, score: float, threshold: float) -> str:
        if score > threshold * 1.5:
            return "high_anomaly"
        if score > threshold:
            return "unusual"
        return "normal"

    def _fallback_meta(self, reason: str) -> dict[str, Any]:
        return {
            "status": "warning",
            "model_type": "statistical_fallback",
            "reason": reason,
            "feature_names": FEATURE_NAMES,
            "feature_count": len(FEATURE_NAMES),
            "max_seq_len": 20,
            "anomaly_threshold": 0.05,
            "feature_mean": [0.0] * len(FEATURE_NAMES),
        }


def detect_for_learner(learner_id: str) -> dict[str, Any]:
    return BehaviourAnomalyDetector().load().detect_for_learner(learner_id)
