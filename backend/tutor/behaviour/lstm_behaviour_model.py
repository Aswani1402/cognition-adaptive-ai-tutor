from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from tutor.behaviour.behaviour_state_store import compute_behavior_risk, enrich_behaviour_output


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
MODEL_PATH = PROJECT_ROOT / "models" / "behaviour_lstm" / "model.pt"
META_PATH = PROJECT_ROOT / "models" / "behaviour_lstm" / "meta.json"
ARTIFACT_SEARCH_PATHS = [
    PROJECT_ROOT / "models" / "behaviour_lstm" / "model.pt",
    PROJECT_ROOT / "models" / "behaviour_lstm" / "behaviour_lstm.pt",
    PROJECT_ROOT / "models" / "behaviour" / "behaviour_lstm.pt",
    PROJECT_ROOT / "models" / "behaviour" / "lstm_behaviour_model.pt",
    PROJECT_ROOT / "tutor" / "behaviour" / "model.pt",
    PROJECT_ROOT / "evaluation_outputs" / "model.pt",
    PROJECT_ROOT / "evaluation_outputs" / "json" / "behaviour_lstm_model.pt",
    PROJECT_ROOT / "evaluation_outputs" / "reports" / "behaviour_lstm_model.pt",
    PROJECT_ROOT / "scripts" / "training" / "behaviour" / "model.pt",
    PROJECT_ROOT / "scripts" / "evaluation" / "behaviour_lstm_model.pt",
]


class BehaviourLSTM(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 32, num_layers: int = 1, num_classes: int = 4):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]
        logits = self.fc(last_hidden)
        return logits


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def load_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {}
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def find_lstm_artifact() -> Path | None:
    for path in ARTIFACT_SEARCH_PATHS:
        if path.exists() and path.is_file():
            return path
    return None


def fetch_recent_attempts(learner_id: str, seq_len: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT quiz_id,
                   learner_id,
                   is_correct,
                   confidence,
                   time_taken_sec,
                   attempt_no,
                   hint_used,
                   hint_count,
                   option_changes_count,
                   timestamp
            FROM quiz_results
            WHERE learner_id = ?
            ORDER BY
                CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                timestamp DESC,
                quiz_id DESC
            LIMIT ?
            """,
            (learner_id, seq_len),
        ).fetchall()

    rows = [dict(r) for r in rows]
    rows.reverse()
    return rows


def build_sequence(attempts: list[dict[str, Any]], seq_len: int) -> list[list[float]]:
    if not attempts:
        return [[0.0] * 7 for _ in range(seq_len)]

    times = [float(a.get("time_taken_sec") or 0.0) for a in attempts]
    positive_times = [t for t in times if t > 0]
    avg_time = sum(positive_times) / len(positive_times) if positive_times else 30.0
    max_time = max(positive_times) if positive_times else 60.0
    if max_time <= 0:
        max_time = 60.0

    seq: list[list[float]] = []
    for a in attempts[-seq_len:]:
        is_correct = float(int(a.get("is_correct") or 0))
        confidence = float(a.get("confidence") or 0.0)
        time_taken = float(a.get("time_taken_sec") or 0.0)
        attempt_no = float(a.get("attempt_no") or 1.0)
        hint_used = float(int(a.get("hint_used") or 0))
        hint_count = float(a.get("hint_count") or 0.0)
        option_changes = float(a.get("option_changes_count") or 0.0)

        time_norm = clamp(time_taken / max_time)
        conf_norm = clamp(confidence / 5.0)
        attempt_norm = clamp(attempt_no / 5.0)
        hint_count_norm = clamp(hint_count / 5.0)
        option_change_norm = clamp(option_changes / 5.0)
        slow_flag = 1.0 if time_taken > avg_time else 0.0

        seq.append(
            [
                is_correct,
                conf_norm,
                time_norm,
                attempt_norm,
                hint_used,
                hint_count_norm,
                max(option_change_norm, slow_flag),
            ]
        )

    while len(seq) < seq_len:
        seq.insert(0, [0.0] * 7)

    return seq


def normalize_interaction(interaction: dict[str, Any] | None) -> dict[str, Any]:
    item = dict(interaction or {})
    score = _safe_float(item.get("score", item.get("correctness", item.get("is_correct"))), 0.0)
    correctness = 1.0 if score >= 0.8 else 0.0
    confidence = _safe_float(item.get("confidence"), 0.5)
    if confidence <= 1.0:
        confidence *= 5.0
    return {
        "quiz_id": item.get("quiz_id", 0),
        "learner_id": item.get("learner_id"),
        "concept_id": item.get("concept_id"),
        "domain": item.get("domain") or item.get("subject"),
        "question_type": item.get("question_type") or item.get("task_type"),
        "difficulty": item.get("difficulty"),
        "is_correct": correctness,
        "confidence": confidence,
        "time_taken_sec": _safe_float(item.get("time_taken_sec"), 0.0),
        "attempt_no": _safe_int(item.get("attempt_count", item.get("attempt_no")), 1),
        "hint_used": 1 if item.get("hint_used") else 0,
        "hint_count": _safe_int(item.get("hint_count"), 0),
        "option_changes_count": _safe_int(
            item.get("option_change_count", item.get("option_changes_count")),
            0,
        ),
        "answer_change_count": _safe_int(item.get("answer_change_count"), 0),
        "run_code_count": _safe_int(item.get("run_code_count"), 0),
        "wrong_attempt_count": _safe_int(item.get("wrong_attempt_count"), 0),
    }


def compute_stats(attempts: list[dict[str, Any]]) -> dict[str, float]:
    n = len(attempts)
    if n == 0:
        return {
            "wrong_rate": 0.0,
            "slow_rate": 0.0,
            "low_confidence_rate": 0.0,
            "hint_rate": 0.0,
            "option_change_rate": 0.0,
        }

    times = [float(a.get("time_taken_sec") or 0.0) for a in attempts]
    positive_times = [t for t in times if t > 0]
    avg_time = sum(positive_times) / len(positive_times) if positive_times else 30.0

    wrong_rate = sum(1 for a in attempts if int(a.get("is_correct") or 0) == 0) / n
    slow_rate = sum(1 for a in attempts if float(a.get("time_taken_sec") or 0.0) > avg_time) / n
    low_confidence_rate = sum(1 for a in attempts if float(a.get("confidence") or 0.0) <= 2) / n
    hint_rate = sum(1 for a in attempts if int(a.get("hint_used") or 0) == 1) / n
    option_change_rate = sum(1 for a in attempts if int(a.get("option_changes_count") or 0) > 0) / n

    return {
        "wrong_rate": round(clamp(wrong_rate), 4),
        "slow_rate": round(clamp(slow_rate), 4),
        "low_confidence_rate": round(clamp(low_confidence_rate), 4),
        "hint_rate": round(clamp(hint_rate), 4),
        "option_change_rate": round(clamp(option_change_rate), 4),
    }


def infer_fallback_label(stats: dict[str, float]) -> str:
    wrong_rate = _safe_float(stats.get("wrong_rate"))
    slow_rate = _safe_float(stats.get("slow_rate"))
    low_confidence_rate = _safe_float(stats.get("low_confidence_rate"))
    hint_rate = _safe_float(stats.get("hint_rate"))
    option_change_rate = _safe_float(stats.get("option_change_rate"))
    answer_change_rate = _safe_float(stats.get("answer_change_rate"))
    retry_rate = _safe_float(stats.get("retry_rate"))
    run_code_rate = _safe_float(stats.get("run_code_rate"))

    if wrong_rate >= 0.6 and (slow_rate >= 0.4 or hint_rate >= 0.3 or retry_rate >= 0.3):
        return "struggling"
    if option_change_rate >= 0.35 and wrong_rate >= 0.35:
        return "guessing"
    if low_confidence_rate >= 0.5 or hint_rate >= 0.4 or answer_change_rate >= 0.5 or run_code_rate >= 0.5:
        return "confused"
    return "stable"


def fallback_proxy_signal_scoring(
    learner_id: str,
    attempts: list[dict[str, Any]] | None = None,
    interaction: dict[str, Any] | None = None,
    fallback_reason: str = "LSTM artifact not found.",
    model_source: str = "fallback_proxy_signal_scoring",
) -> dict[str, Any]:
    attempts = list(attempts or [])
    if interaction:
        attempts.append(normalize_interaction(interaction))

    stats = compute_stats(attempts)
    if interaction:
        normalized = normalize_interaction(interaction)
        stats.update(
            {
                "answer_change_rate": clamp(_safe_float(normalized.get("answer_change_count")) / 5.0),
                "run_code_rate": clamp(_safe_float(normalized.get("run_code_count")) / 5.0),
                "retry_rate": clamp(
                    max(
                        _safe_float(normalized.get("attempt_no"), 1.0) - 1.0,
                        _safe_float(normalized.get("wrong_attempt_count")),
                    )
                    / 3.0
                ),
            }
        )
    else:
        stats.update({"answer_change_rate": 0.0, "run_code_rate": 0.0, "retry_rate": 0.0})

    label = infer_fallback_label(stats)
    risk = compute_behavior_risk(
        behavior_label=label,
        wrong_rate=stats["wrong_rate"],
        slow_rate=stats["slow_rate"],
        low_confidence_rate=stats["low_confidence_rate"],
        hint_rate=stats["hint_rate"],
        option_change_rate=stats["option_change_rate"],
    )
    evidence_inputs = {
        "time_taken_sec": interaction.get("time_taken_sec") if interaction else None,
        "confidence": interaction.get("confidence") if interaction else None,
        "hint_count": interaction.get("hint_count") if interaction else None,
        "hint_used": interaction.get("hint_used") if interaction else None,
        "option_change_count": interaction.get("option_change_count") if interaction else None,
        "answer_change_count": interaction.get("answer_change_count") if interaction else None,
        "run_code_count": interaction.get("run_code_count") if interaction else None,
        "attempt_count": interaction.get("attempt_count") if interaction else None,
        "wrong_attempt_count": interaction.get("wrong_attempt_count") if interaction else None,
        "correctness": interaction.get("correctness", interaction.get("score")) if interaction else None,
        "question_type": interaction.get("question_type") if interaction else None,
        "difficulty": interaction.get("difficulty") if interaction else None,
        "learner_id": learner_id,
        "concept_id": interaction.get("concept_id") if interaction else None,
        "domain": interaction.get("domain") or interaction.get("subject") if interaction else None,
        "sequence_length": len(attempts),
    }
    output = {
        "status": "success",
        "module": "BehaviourLSTMRuntime",
        "learner_id": learner_id,
        "behaviour_state": label,
        "behavior_label": label,
        "behaviour_risk": risk["behavior_risk"],
        "behavior_risk": risk["behavior_risk"],
        "behavior_risk_label": risk["behavior_risk_label"],
        "behavior_score": risk["behavior_risk"],
        "confidence_score": round(clamp(1.0 - risk["behavior_risk"]), 4),
        "behavior_confidence": round(clamp(1.0 - risk["behavior_risk"]), 4),
        "wrong_rate": stats["wrong_rate"],
        "slow_rate": stats["slow_rate"],
        "low_confidence_rate": stats["low_confidence_rate"],
        "hint_rate": stats["hint_rate"],
        "option_change_rate": stats["option_change_rate"],
        "answer_change_rate": stats["answer_change_rate"],
        "run_code_rate": stats["run_code_rate"],
        "retry_rate": stats["retry_rate"],
        "sequence_length": len(attempts),
        "model_used": False,
        "model_source": model_source,
        "behavior_source": model_source,
        "evidence_inputs": evidence_inputs,
        "fallback_reason": fallback_reason,
        "artifact_search_paths": [str(path) for path in ARTIFACT_SEARCH_PATHS],
    }
    return enrich_behaviour_output(output)


class BehaviourLSTMRuntime:
    def __init__(self, artifact_path: Path | None = None, meta_path: Path = META_PATH):
        self.artifact_path = artifact_path
        self.meta_path = meta_path
        self.meta: dict[str, Any] = {}
        self.model: BehaviourLSTM | None = None
        self.load_error: str | None = None
        self.loaded_path: Path | None = None
        self.loaded = False

    def load(self) -> bool:
        if self.loaded and self.model is not None:
            return True
        path = self.artifact_path or find_lstm_artifact()
        if path is None or not path.exists():
            self.load_error = "LSTM artifact not found."
            return False
        try:
            self.meta = load_meta()
            checkpoint = torch.load(path, map_location="cpu")
            input_size = int(checkpoint.get("input_size", self.meta.get("input_size", 7)))
            hidden_size = int(checkpoint.get("hidden_size", self.meta.get("hidden_size", 32)))
            num_layers = int(checkpoint.get("num_layers", self.meta.get("num_layers", 1)))
            num_classes = int(checkpoint.get("num_classes", self.meta.get("num_classes", 4)))
            model = BehaviourLSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                num_classes=num_classes,
            )
            state_dict = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) else None
            if not state_dict:
                raise ValueError("Checkpoint missing model_state_dict.")
            model.load_state_dict(state_dict)
            model.eval()
            self.model = model
            self.loaded_path = path
            self.loaded = True
            self.load_error = None
            return True
        except Exception as exc:
            self.model = None
            self.loaded = False
            self.loaded_path = path
            self.load_error = f"{type(exc).__name__}: {exc}"
            return False

    def predict(
        self,
        learner_id: str,
        interaction: dict[str, Any] | None = None,
        recent_sequence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.load():
            model_source = (
                "fallback_proxy_signal_scoring"
                if self.load_error == "LSTM artifact not found."
                else "lstm_load_failed_fallback"
            )
            return fallback_proxy_signal_scoring(
                learner_id=learner_id,
                attempts=recent_sequence,
                interaction=interaction,
                fallback_reason=self.load_error or "LSTM artifact not available.",
                model_source=model_source,
            )

        try:
            seq_len = int(self.meta.get("seq_len", 20))
            id_to_label = self.meta.get(
                "id_to_label",
                {"0": "stable", "1": "confused", "2": "guessing", "3": "struggling"},
            )
            attempts = list(recent_sequence or fetch_recent_attempts(learner_id, seq_len))
            if interaction:
                attempts.append(normalize_interaction(interaction))
            stats = compute_stats(attempts)
            sequence = build_sequence(attempts, seq_len)
            x = torch.tensor([sequence], dtype=torch.float32)
            with torch.no_grad():
                logits = self.model(x)
                probs = torch.softmax(logits, dim=1)[0]
                pred_id = int(torch.argmax(probs).item())
                behavior_confidence = float(torch.max(probs).item())
            label = id_to_label.get(str(pred_id), "stable")
            risk = compute_behavior_risk(
                behavior_label=label,
                wrong_rate=stats["wrong_rate"],
                slow_rate=stats["slow_rate"],
                low_confidence_rate=stats["low_confidence_rate"],
                hint_rate=stats["hint_rate"],
                option_change_rate=stats["option_change_rate"],
            )
            evidence_inputs = dict(interaction or {})
            evidence_inputs.update({"learner_id": learner_id, "sequence_length": len(attempts)})
            return enrich_behaviour_output(
                {
                    "status": "success",
                    "module": "BehaviourLSTMRuntime",
                    "learner_id": learner_id,
                    "behaviour_state": label,
                    "behavior_label": label,
                    "behaviour_risk": risk["behavior_risk"],
                    "behavior_risk": risk["behavior_risk"],
                    "behavior_risk_label": risk["behavior_risk_label"],
                    "behavior_score": risk["behavior_risk"],
                    "confidence_score": round(behavior_confidence, 4),
                    "behavior_confidence": round(behavior_confidence, 4),
                    "wrong_rate": stats["wrong_rate"],
                    "slow_rate": stats["slow_rate"],
                    "low_confidence_rate": stats["low_confidence_rate"],
                    "hint_rate": stats["hint_rate"],
                    "option_change_rate": stats["option_change_rate"],
                    "sequence_length": len(attempts),
                    "model_used": True,
                    "model_source": "lstm_runtime",
                    "behavior_source": "lstm_runtime",
                    "artifact_path": str(self.loaded_path),
                    "evidence_inputs": evidence_inputs,
                }
            )
        except Exception as exc:
            return fallback_proxy_signal_scoring(
                learner_id=learner_id,
                attempts=recent_sequence,
                interaction=interaction,
                fallback_reason=f"LSTM inference failed: {type(exc).__name__}: {exc}",
                model_source="lstm_load_failed_fallback",
            )


def predict_behaviour(
    learner_id: str,
    interaction: dict[str, Any] | None = None,
    recent_sequence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return BehaviourLSTMRuntime().predict(
        learner_id=str(learner_id),
        interaction=interaction,
        recent_sequence=recent_sequence,
    )


def run_behaviour_model(
    learner_id: str,
    interaction: dict[str, Any] | None = None,
    recent_sequence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return predict_behaviour(learner_id, interaction=interaction, recent_sequence=recent_sequence)


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    args = parser.parse_args()

    result = run_behaviour_model(str(args.learner_id))
    pprint.pp(result)
