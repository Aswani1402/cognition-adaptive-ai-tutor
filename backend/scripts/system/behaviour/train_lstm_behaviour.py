from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
MODEL_DIR = PROJECT_ROOT / "models" / "behaviour_lstm"
MODEL_PATH = MODEL_DIR / "model.pt"
META_PATH = MODEL_DIR / "meta.json"

LABEL_TO_ID = {
    "stable": 0,
    "confused": 1,
    "guessing": 2,
    "struggling": 3,
}
ID_TO_LABEL = {v: k for k, v in LABEL_TO_ID.items()}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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


@dataclass
class LearnerSequenceExample:
    learner_id: str
    sequence: List[List[float]]
    label_id: int
    label_name: str
    stats: Dict[str, float]


class BehaviourSequenceDataset(Dataset):
    def __init__(self, examples: List[LearnerSequenceExample]):
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        ex = self.examples[idx]
        x = torch.tensor(ex.sequence, dtype=torch.float32)
        y = torch.tensor(ex.label_id, dtype=torch.long)
        return x, y


class BehaviourTrainer:
    def __init__(
        self,
        db_path: Path | str = DB_PATH,
        seq_len: int = 20,
        hidden_size: int = 32,
        batch_size: int = 32,
        epochs: int = 8,
        learning_rate: float = 1e-3,
        min_attempts: int = 5,
        seed: int = 42,
    ):
        self.db_path = str(db_path)
        self.seq_len = seq_len
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.min_attempts = min_attempts
        self.seed = seed
        self.device = torch.device("cpu")

        random.seed(seed)
        torch.manual_seed(seed)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_quiz_rows(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT quiz_id,
                       learner_id,
                       concept_id,
                       question_id,
                       is_correct,
                       confidence,
                       time_taken_sec,
                       attempt_no,
                       timestamp,
                       hint_used,
                       hint_count,
                       option_changes_count
                FROM quiz_results
                WHERE learner_id IS NOT NULL
                ORDER BY learner_id ASC,
                         CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                         timestamp ASC,
                         quiz_id ASC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def group_by_learner(self, rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            learner_id = str(row["learner_id"])
            grouped.setdefault(learner_id, []).append(row)
        return grouped

    def compute_proxy_stats(self, attempts: List[Dict[str, Any]]) -> Dict[str, float]:
        n = len(attempts)
        if n == 0:
            return {
                "wrong_rate": 0.0,
                "slow_rate": 0.0,
                "low_confidence_rate": 0.0,
                "hint_rate": 0.0,
                "option_change_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_time": 0.0,
            }

        times = [float(a.get("time_taken_sec") or 0.0) for a in attempts]
        positive_times = [t for t in times if t > 0]
        avg_time = sum(positive_times) / len(positive_times) if positive_times else 30.0

        confidences = [float(a.get("confidence") or 0.0) for a in attempts]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

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
            "avg_confidence": round(avg_confidence, 4),
            "avg_time": round(avg_time, 4),
        }

    def infer_proxy_label(self, stats: Dict[str, float]) -> str:
        wrong_rate = stats["wrong_rate"]
        slow_rate = stats["slow_rate"]
        low_confidence_rate = stats["low_confidence_rate"]
        hint_rate = stats["hint_rate"]
        option_change_rate = stats["option_change_rate"]

        if wrong_rate >= 0.6 and (slow_rate >= 0.4 or hint_rate >= 0.3):
            return "struggling"

        if option_change_rate >= 0.35 and wrong_rate >= 0.35:
            return "guessing"

        if low_confidence_rate >= 0.5 or (wrong_rate >= 0.4 and hint_rate >= 0.2):
            return "confused"

        return "stable"

    def build_sequence(self, attempts: List[Dict[str, Any]]) -> List[List[float]]:
        if not attempts:
            return [[0.0] * 7 for _ in range(self.seq_len)]

        times = [float(a.get("time_taken_sec") or 0.0) for a in attempts]
        positive_times = [t for t in times if t > 0]
        avg_time = sum(positive_times) / len(positive_times) if positive_times else 30.0
        max_time = max(positive_times) if positive_times else 60.0
        if max_time <= 0:
            max_time = 60.0

        seq: List[List[float]] = []
        for a in attempts[-self.seq_len:]:
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

        while len(seq) < self.seq_len:
            seq.insert(0, [0.0] * 7)

        return seq

    def create_examples(self, grouped: Dict[str, List[Dict[str, Any]]]) -> List[LearnerSequenceExample]:
        examples: List[LearnerSequenceExample] = []

        for learner_id, attempts in grouped.items():
            if len(attempts) < self.min_attempts:
                continue

            stats = self.compute_proxy_stats(attempts)
            label_name = self.infer_proxy_label(stats)
            label_id = LABEL_TO_ID[label_name]
            sequence = self.build_sequence(attempts)

            examples.append(
                LearnerSequenceExample(
                    learner_id=learner_id,
                    sequence=sequence,
                    label_id=label_id,
                    label_name=label_name,
                    stats=stats,
                )
            )

        return examples

    def split_examples(
        self,
        examples: List[LearnerSequenceExample],
        train_ratio: float = 0.8,
    ) -> Tuple[List[LearnerSequenceExample], List[LearnerSequenceExample]]:
        shuffled = examples[:]
        random.shuffle(shuffled)

        split_idx = int(len(shuffled) * train_ratio)
        train_examples = shuffled[:split_idx]
        val_examples = shuffled[split_idx:]

        if not train_examples and shuffled:
            train_examples = shuffled[:1]
            val_examples = shuffled[1:]

        if not val_examples and len(train_examples) > 1:
            val_examples = train_examples[-1:]
            train_examples = train_examples[:-1]

        return train_examples, val_examples

    def build_loaders(
        self,
        train_examples: List[LearnerSequenceExample],
        val_examples: List[LearnerSequenceExample],
    ) -> Tuple[DataLoader, DataLoader]:
        train_ds = BehaviourSequenceDataset(train_examples)
        val_ds = BehaviourSequenceDataset(val_examples)

        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        return train_loader, val_loader

    def evaluate(self, model: nn.Module, loader: DataLoader, criterion: nn.Module) -> Tuple[float, float]:
        model.eval()

        total_loss = 0.0
        total_count = 0
        total_correct = 0

        with torch.no_grad():
            for x, y in loader:
                x = x.to(self.device)
                y = y.to(self.device)

                logits = model(x)
                loss = criterion(logits, y)
                preds = torch.argmax(logits, dim=1)

                batch_size = x.size(0)
                total_loss += loss.item() * batch_size
                total_correct += (preds == y).sum().item()
                total_count += batch_size

        if total_count == 0:
            return 0.0, 0.0

        return total_loss / total_count, total_correct / total_count

    def train(self) -> Dict[str, Any]:
        rows = self.fetch_quiz_rows()
        grouped = self.group_by_learner(rows)
        examples = self.create_examples(grouped)

        if not examples:
            raise ValueError("No training examples created. Check quiz_results and min_attempts.")

        train_examples, val_examples = self.split_examples(examples)
        train_loader, val_loader = self.build_loaders(train_examples, val_examples)

        model = BehaviourLSTM(
            input_size=7,
            hidden_size=self.hidden_size,
            num_layers=1,
            num_classes=len(LABEL_TO_ID),
        ).to(self.device)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=self.learning_rate)

        history: List[Dict[str, float]] = []

        for epoch in range(1, self.epochs + 1):
            model.train()

            total_train_loss = 0.0
            total_train_count = 0
            total_train_correct = 0

            for x, y in train_loader:
                x = x.to(self.device)
                y = y.to(self.device)

                optimizer.zero_grad()
                logits = model(x)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()

                preds = torch.argmax(logits, dim=1)
                batch_size = x.size(0)

                total_train_loss += loss.item() * batch_size
                total_train_correct += (preds == y).sum().item()
                total_train_count += batch_size

            train_loss = total_train_loss / total_train_count if total_train_count else 0.0
            train_acc = total_train_correct / total_train_count if total_train_count else 0.0
            val_loss, val_acc = self.evaluate(model, val_loader, criterion)

            epoch_info = {
                "epoch": epoch,
                "train_loss": round(train_loss, 6),
                "train_acc": round(train_acc, 6),
                "val_loss": round(val_loss, 6),
                "val_acc": round(val_acc, 6),
            }
            history.append(epoch_info)
            print(epoch_info)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "input_size": 7,
                "hidden_size": self.hidden_size,
                "num_layers": 1,
                "num_classes": len(LABEL_TO_ID),
                "seq_len": self.seq_len,
            },
            MODEL_PATH,
        )

        meta = {
            "db_path": str(self.db_path),
            "num_rows": len(rows),
            "num_learners": len(grouped),
            "num_examples": len(examples),
            "num_train_examples": len(train_examples),
            "num_val_examples": len(val_examples),
            "seq_len": self.seq_len,
            "hidden_size": self.hidden_size,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "min_attempts": self.min_attempts,
            "seed": self.seed,
            "history": history,
            "label_to_id": LABEL_TO_ID,
            "id_to_label": ID_TO_LABEL,
            "label_definition": {
                "stable": "Low risk patterns overall",
                "confused": "Higher low-confidence/hint-based uncertainty",
                "guessing": "Higher option changes + wrong-rate pattern",
                "struggling": "High wrong-rate with slow/hint-heavy behavior",
            },
        }

        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return {
            "status": "ok",
            "model_path": str(MODEL_PATH),
            "meta_path": str(META_PATH),
            "num_rows": len(rows),
            "num_learners": len(grouped),
            "num_examples": len(examples),
            "num_train_examples": len(train_examples),
            "num_val_examples": len(val_examples),
            "last_epoch": history[-1] if history else None,
        }


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument("--seq_len", type=int, default=20)
    parser.add_argument("--hidden_size", type=int, default=32)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--min_attempts", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    trainer = BehaviourTrainer(
        db_path=DB_PATH,
        seq_len=args.seq_len,
        hidden_size=args.hidden_size,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.lr,
        min_attempts=args.min_attempts,
        seed=args.seed,
    )

    result = trainer.train()
    pprint.pp(result)