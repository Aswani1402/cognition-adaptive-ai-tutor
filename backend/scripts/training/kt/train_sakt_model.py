from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import torch
import torch.nn as nn
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset

from tutor.knowledge_state.sakt.sakt_model import SAKTModel


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
ID_MAP_PATH = Path("models/dkt/id_map.json")
MODEL_DIR = Path("models/kt")
MODEL_PATH = MODEL_DIR / "sakt_model.pt"
META_PATH = MODEL_DIR / "sakt_meta.json"
JSON_REPORT = Path("evaluation_outputs/json/sakt_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/sakt_training_report.md")

EMBED_DIM = 64
NUM_HEADS = 2
MAX_SEQ_LEN = 50
EPOCHS = 5
BATCH_SIZE = 64


class SeqDataset(Dataset):
    def __init__(self, sequences: list[dict[str, list[int]]]):
        self.sequences = sequences

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        seq = self.sequences[index]
        return {
            "concepts": torch.tensor(seq["concepts"], dtype=torch.long),
            "correct": torch.tensor(seq["correct"], dtype=torch.long),
        }


def _load_rows() -> list[dict[str, Any]]:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_map() -> dict[str, Any]:
    if not ID_MAP_PATH.exists():
        from scripts.training.kt.build_skill_item_map import build_skill_item_map

        build_skill_item_map()
    return json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _build_sequences(rows: list[dict[str, Any]], concept_to_idx: dict[str, int]) -> list[dict[str, Any]]:
    learner_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        learner_rows[str(row["learner_id"])].append(row)

    sequences = []
    for learner_id, learner_seq in learner_rows.items():
        learner_seq.sort(key=lambda item: (_safe_int(item.get("sequence_index")), _safe_int(item.get("quiz_id"))))
        for start in range(0, len(learner_seq), MAX_SEQ_LEN):
            chunk = learner_seq[start : start + MAX_SEQ_LEN]
            concepts = [int(concept_to_idx[str(row["concept_id"])]) for row in chunk if str(row.get("concept_id")) in concept_to_idx]
            correct = [1 if _safe_int(row.get("is_correct")) else 0 for row in chunk if str(row.get("concept_id")) in concept_to_idx]
            if len(concepts) >= 2:
                split = Counter(str(row.get("split", "train")) for row in chunk).most_common(1)[0][0]
                sequences.append({"learner_id": learner_id, "concepts": concepts, "correct": correct, "split": split})
    return sequences


def _split(sequences: list[dict[str, Any]], split: str) -> list[dict[str, list[int]]]:
    selected = [seq for seq in sequences if seq["split"] == split]
    return [{"concepts": seq["concepts"], "correct": seq["correct"]} for seq in selected]


def _collate(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    concepts = pad_sequence([item["concepts"] for item in batch], batch_first=True, padding_value=0)
    correct = pad_sequence([item["correct"] for item in batch], batch_first=True, padding_value=0)
    lengths = torch.tensor([len(item["concepts"]) for item in batch], dtype=torch.long)
    mask = torch.arange(concepts.shape[1]).unsqueeze(0) < lengths.unsqueeze(1)
    return {"concepts": concepts, "correct": correct, "mask": mask}


def _auc(y_true: list[int], y_prob: list[float]) -> float | None:
    try:
        from sklearn.metrics import roc_auc_score

        if len(set(y_true)) < 2:
            return None
        return float(roc_auc_score(y_true, y_prob))
    except Exception:
        return None


def _metrics(y_true: list[int], y_prob: list[float]) -> dict[str, Any]:
    if not y_true:
        return {"accuracy": None, "auc": None, "log_loss": None, "brier_score": None, "rmse": None, "row_count": 0}
    eps = 1e-6
    clipped = [max(eps, min(1.0 - eps, float(value))) for value in y_prob]
    y_pred = [1 if value >= 0.5 else 0 for value in clipped]
    brier = mean([(prob - y) ** 2 for y, prob in zip(y_true, clipped)])
    log_loss = mean([-(y * math.log(prob) + (1 - y) * math.log(1 - prob)) for y, prob in zip(y_true, clipped)])
    auc = _auc(y_true, clipped)
    return {
        "accuracy": round(sum(1 for y, pred in zip(y_true, y_pred) if y == pred) / len(y_true), 6),
        "auc": None if auc is None else round(auc, 6),
        "log_loss": round(log_loss, 6),
        "brier_score": round(brier, 6),
        "rmse": round(math.sqrt(brier), 6),
        "row_count": len(y_true),
    }


def _loss(model: SAKTModel, batch: dict[str, torch.Tensor], criterion: nn.Module) -> tuple[torch.Tensor, int]:
    logits = model(batch["concepts"], batch["correct"])
    valid = batch["mask"][:, 1:] & (batch["concepts"][:, 1:] > 0)
    if not bool(valid.any()):
        return torch.tensor(0.0), 0
    return criterion(logits[:, :-1][valid], batch["correct"][:, 1:].float()[valid]), int(valid.sum().item())


def _evaluate(model: SAKTModel, sequences: list[dict[str, list[int]]]) -> dict[str, Any]:
    loader = DataLoader(SeqDataset(sequences), batch_size=BATCH_SIZE, shuffle=False, collate_fn=_collate)
    y_true: list[int] = []
    y_prob: list[float] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            logits = model(batch["concepts"], batch["correct"])
            valid = batch["mask"][:, 1:] & (batch["concepts"][:, 1:] > 0)
            if not bool(valid.any()):
                continue
            probs = torch.sigmoid(logits[:, :-1])
            y_true.extend(batch["correct"][:, 1:][valid].int().tolist())
            y_prob.extend(probs[valid].float().tolist())
    return _metrics(y_true, y_prob)


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# SAKT Training Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Model: `{report.get('artifacts', {}).get('model')}`",
        f"- Meta: `{report.get('artifacts', {}).get('meta')}`",
        "",
        "## Metrics",
        "",
    ]
    for split, metrics in (report.get("metrics") or {}).items():
        lines.append(
            f"- {split}: accuracy={metrics.get('accuracy')}, auc={metrics.get('auc')}, "
            f"log_loss={metrics.get('log_loss')}, brier={metrics.get('brier_score')}, rmse={metrics.get('rmse')}"
        )
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_sakt() -> dict[str, Any]:
    try:
        rows = _load_rows()
        id_map = _load_map()
        concept_to_idx = {str(k): int(v) for k, v in (id_map.get("concept_to_idx") or id_map.get("skill2idx") or {}).items()}
        sequences = _build_sequences(rows, concept_to_idx)
        train_sequences = _split(sequences, "train")
        val_sequences = _split(sequences, "val")
        test_sequences = _split(sequences, "test")
        if not val_sequences or not test_sequences:
            ordered = [{"concepts": seq["concepts"], "correct": seq["correct"]} for seq in sequences]
            train_cut = max(1, int(len(ordered) * 0.7))
            val_cut = max(train_cut + 1, int(len(ordered) * 0.85))
            train_sequences = ordered[:train_cut]
            val_sequences = ordered[train_cut:val_cut]
            test_sequences = ordered[val_cut:]

        model = SAKTModel(num_concepts=int(id_map.get("num_concepts") or id_map.get("num_skills")), embed_dim=EMBED_DIM, num_heads=NUM_HEADS, max_seq_len=MAX_SEQ_LEN)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.BCEWithLogitsLoss()
        loader = DataLoader(SeqDataset(train_sequences), batch_size=BATCH_SIZE, shuffle=True, collate_fn=_collate)
        history = []
        for epoch in range(1, EPOCHS + 1):
            model.train()
            total_loss = 0.0
            total_steps = 0
            for batch in loader:
                optimizer.zero_grad()
                loss, steps = _loss(model, batch, criterion)
                if steps == 0:
                    continue
                loss.backward()
                optimizer.step()
                total_loss += float(loss.item()) * steps
                total_steps += steps
            history.append({"epoch": epoch, "train_loss": round(total_loss / total_steps, 6) if total_steps else None})

        metrics = {"train": _evaluate(model, train_sequences), "val": _evaluate(model, val_sequences), "test": _evaluate(model, test_sequences)}
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), MODEL_PATH)
        meta = {
            "model_type": "SAKT",
            "embedding_dim": EMBED_DIM,
            "num_heads": NUM_HEADS,
            "max_seq_len": MAX_SEQ_LEN,
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "metrics": metrics,
            "id_map": str(ID_MAP_PATH),
        }
        META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        correct = sum(1 for row in rows if _safe_int(row.get("is_correct")) == 1)
        correct_rate = correct / len(rows) if rows else 0.0
        warnings = []
        if correct_rate > 0.8 or correct_rate < 0.2:
            warnings.append("Correctness is highly imbalanced; SAKT accuracy can overstate model quality.")
        report = {
            "status": "warning" if warnings else "success",
            "module": "sakt_training",
            "artifacts": {"model": str(MODEL_PATH), "meta": str(META_PATH)},
            "dataset": {"row_count": len(rows), "sequence_count": len(sequences), "concept_count": len(concept_to_idx), "correct_rate": round(correct_rate, 6)},
            "metrics": metrics,
            "training_history": history,
            "warnings": warnings,
        }
    except Exception as exc:
        report = {
            "status": "warning",
            "module": "sakt_training",
            "reason": f"SAKT pending_due_to_time_or_training_issue: {exc}",
            "warnings": [str(exc)],
            "metrics": {},
        }
    _write_reports(report)
    return report


def main() -> None:
    report = train_sakt()
    print(f"STATUS: {report['status']}")
    print("MODULE: sakt_training")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
