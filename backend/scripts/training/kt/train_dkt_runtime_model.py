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

from tutor.knowledge_state.dkt.dkt_model import DKTModel


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
MODEL_DIR = Path("models/dkt")
MODEL_PATH = MODEL_DIR / "model.pt"
ID_MAP_PATH = MODEL_DIR / "id_map.json"
META_PATH = MODEL_DIR / "dkt_meta.json"
JSON_REPORT = Path("evaluation_outputs/json/dkt_runtime_training_report.json")
MD_REPORT = Path("evaluation_outputs/reports/dkt_runtime_training_report.md")

EPOCHS = 5
MIN_NEXT_STEP_LENGTH = 2
HYPERPARAMETER_CANDIDATES = [
    {"name": "DKT_small", "embedding_dim": 32, "hidden_dim": 64, "learning_rate": 0.001, "batch_size": 64, "max_seq_len": 50},
    {"name": "DKT_medium", "embedding_dim": 64, "hidden_dim": 128, "learning_rate": 0.0005, "batch_size": 64, "max_seq_len": 100},
]


class KTSequenceDataset(Dataset):
    def __init__(self, sequences: list[dict[str, list[int]]]):
        self.sequences = sequences

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        seq = self.sequences[index]
        return {
            "skills": torch.tensor(seq["skills"], dtype=torch.long),
            "correct": torch.tensor(seq["correct"], dtype=torch.long),
        }


def _ensure_training_data() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()


def _load_rows() -> list[dict[str, Any]]:
    _ensure_training_data()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _load_or_build_id_map() -> dict[str, Any]:
    from scripts.training.kt.build_skill_item_map import build_skill_item_map

    if not ID_MAP_PATH.exists():
        build_skill_item_map()
    data = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != "current_tutor_kt_v1" or not data.get("concept_to_idx"):
        build_skill_item_map()
        data = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
    return data


def _build_sequences(rows: list[dict[str, Any]], id_map: dict[str, Any], max_seq_len: int) -> list[dict[str, Any]]:
    concept_to_idx = id_map.get("concept_to_idx") or id_map.get("skill2idx") or {}
    learner_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        learner_rows[str(row["learner_id"])].append(row)

    sequences: list[dict[str, Any]] = []
    for learner_id, learner_seq in learner_rows.items():
        learner_seq.sort(key=lambda item: (_safe_int(item.get("sequence_index")), _safe_int(item.get("quiz_id"))))
        chunks = [
            learner_seq[start : start + max_seq_len]
            for start in range(0, len(learner_seq), max_seq_len)
        ]
        for chunk in chunks:
            skills = [int(concept_to_idx[str(row["concept_id"])]) for row in chunk if str(row.get("concept_id")) in concept_to_idx]
            correct = [1 if _safe_int(row.get("is_correct")) else 0 for row in chunk if str(row.get("concept_id")) in concept_to_idx]
            if len(skills) >= MIN_NEXT_STEP_LENGTH:
                split_counts = Counter(str(row.get("split", "train")) for row in chunk)
                split = split_counts.most_common(1)[0][0]
                sequences.append(
                    {
                        "learner_id": learner_id,
                        "skills": skills,
                        "correct": correct,
                        "split": split,
                    }
                )
    return sequences


def _collate(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    skills = pad_sequence([item["skills"] for item in batch], batch_first=True, padding_value=0)
    correct = pad_sequence([item["correct"] for item in batch], batch_first=True, padding_value=0)
    lengths = torch.tensor([len(item["skills"]) for item in batch], dtype=torch.long)
    mask = torch.arange(skills.shape[1]).unsqueeze(0) < lengths.unsqueeze(1)
    return {"skills": skills, "correct": correct, "lengths": lengths, "mask": mask}


def _sequence_split(sequences: list[dict[str, Any]], split: str) -> list[dict[str, list[int]]]:
    selected = [seq for seq in sequences if seq["split"] == split]
    if selected:
        return [{"skills": seq["skills"], "correct": seq["correct"]} for seq in selected]
    if split == "train":
        return [{"skills": seq["skills"], "correct": seq["correct"]} for seq in sequences]
    return []


def _loss_for_batch(model: DKTModel, batch: dict[str, torch.Tensor], criterion: nn.Module) -> tuple[torch.Tensor, int]:
    skills = batch["skills"]
    correct = batch["correct"]
    mask = batch["mask"]
    logits = model(skills, correct)
    if skills.shape[1] < 2:
        return torch.tensor(0.0), 0

    next_skills = skills[:, 1:]
    next_correct = correct[:, 1:].float()
    valid = mask[:, 1:] & (next_skills > 0)
    if not bool(valid.any()):
        return torch.tensor(0.0), 0

    next_logits = logits[:, :-1, :].gather(2, next_skills.unsqueeze(-1)).squeeze(-1)
    loss = criterion(next_logits[valid], next_correct[valid])
    return loss, int(valid.sum().item())


def _train(
    model: DKTModel,
    train_sequences: list[dict[str, list[int]]],
    val_sequences: list[dict[str, list[int]]],
    learning_rate: float,
    batch_size: int,
) -> dict[str, Any]:
    train_loader = DataLoader(KTSequenceDataset(train_sequences), batch_size=batch_size, shuffle=True, collate_fn=_collate)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.BCEWithLogitsLoss()
    history: list[dict[str, Any]] = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        total_steps = 0
        for batch in train_loader:
            optimizer.zero_grad()
            loss, valid_count = _loss_for_batch(model, batch, criterion)
            if valid_count == 0:
                continue
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * valid_count
            total_steps += valid_count
        epoch_report = {
            "epoch": epoch,
            "train_loss": round(total_loss / total_steps, 6) if total_steps else None,
            "train_steps": total_steps,
        }
        if val_sequences:
            val_metrics = _evaluate(model, val_sequences)
            epoch_report["val_log_loss"] = val_metrics.get("log_loss")
            epoch_report["val_brier_score"] = val_metrics.get("brier_score")
        history.append(epoch_report)
    return {"epochs": history}


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
        return {
            "accuracy": None,
            "auc": None,
            "log_loss": None,
            "brier_score": None,
            "rmse": None,
            "row_count": 0,
        }
    eps = 1e-6
    clipped = [max(eps, min(1.0 - eps, float(value))) for value in y_prob]
    y_pred = [1 if value >= 0.5 else 0 for value in clipped]
    brier = mean([(prob - y) ** 2 for y, prob in zip(y_true, clipped)])
    log_loss = mean([-(y * math.log(prob) + (1 - y) * math.log(1 - prob)) for y, prob in zip(y_true, clipped)])
    return {
        "accuracy": round(sum(1 for y, pred in zip(y_true, y_pred) if y == pred) / len(y_true), 6),
        "auc": None if _auc(y_true, clipped) is None else round(float(_auc(y_true, clipped)), 6),
        "log_loss": round(log_loss, 6),
        "brier_score": round(brier, 6),
        "rmse": round(math.sqrt(brier), 6),
        "row_count": len(y_true),
    }


def _evaluate(model: DKTModel, sequences: list[dict[str, list[int]]], batch_size: int = 64) -> dict[str, Any]:
    loader = DataLoader(KTSequenceDataset(sequences), batch_size=batch_size, shuffle=False, collate_fn=_collate)
    y_true: list[int] = []
    y_prob: list[float] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            skills = batch["skills"]
            correct = batch["correct"]
            mask = batch["mask"]
            logits = model(skills, correct)
            if skills.shape[1] < 2:
                continue
            next_skills = skills[:, 1:]
            valid = mask[:, 1:] & (next_skills > 0)
            if not bool(valid.any()):
                continue
            next_logits = logits[:, :-1, :].gather(2, next_skills.unsqueeze(-1)).squeeze(-1)
            probs = torch.sigmoid(next_logits)
            y_true.extend(correct[:, 1:][valid].int().tolist())
            y_prob.extend(probs[valid].float().tolist())
    return _metrics(y_true, y_prob)


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# DKT Runtime Training Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Artifacts",
        "",
        f"- Model: `{report['artifacts']['model']}`",
        f"- ID map: `{report['artifacts']['id_map']}`",
        f"- Meta: `{report['artifacts']['meta']}`",
        "",
        "## Dataset",
        "",
        f"- Learners: {report['dataset']['learner_count']}",
        f"- Concepts: {report['dataset']['concept_count']}",
        f"- Sequences: {report['dataset']['sequence_count']}",
        f"- Correct rate: {report['dataset']['correct_rate']}",
        "",
        "## Metrics",
        "",
    ]
    for split in ["train", "val", "test"]:
        metrics = report["metrics"].get(split, {})
        lines.append(
            f"- {split}: accuracy={metrics.get('accuracy')}, auc={metrics.get('auc')}, "
            f"log_loss={metrics.get('log_loss')}, brier={metrics.get('brier_score')}, "
            f"rmse={metrics.get('rmse')}, rows={metrics.get('row_count')}"
        )
    lines.extend(["", "## Hyperparameter Candidates", ""])
    for result in report.get("hyperparameter_results", []):
        metrics = result.get("metrics", {}).get("val", {})
        lines.append(
            f"- {result.get('name')}: embedding={result.get('embedding_dim')}, hidden={result.get('hidden_dim')}, "
            f"lr={result.get('learning_rate')}, max_seq_len={result.get('max_seq_len')}, "
            f"val_log_loss={metrics.get('log_loss')}, val_brier={metrics.get('brier_score')}"
        )
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Phase-1 Artifact Note", "", report["phase1_artifact_note"]])
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_dkt() -> dict[str, Any]:
    rows = _load_rows()
    id_map = _load_or_build_id_map()

    correctness = Counter(_safe_int(row.get("is_correct")) for row in rows)
    correct_rate = correctness.get(1, 0) / len(rows) if rows else 0.0
    warnings = []
    if correct_rate < 0.2 or correct_rate > 0.8:
        warnings.append("Correctness is highly imbalanced; accuracy should be interpreted with Brier/log-loss.")

    best: dict[str, Any] | None = None
    best_state: dict[str, Any] | None = None
    hyperparameter_results = []
    best_split_counts = {"train": 0, "val": 0, "test": 0, "sequences": 0}

    for candidate in HYPERPARAMETER_CANDIDATES:
        sequences = _build_sequences(rows, id_map, int(candidate["max_seq_len"]))
        train_sequences = _sequence_split(sequences, "train")
        val_sequences = _sequence_split(sequences, "val")
        test_sequences = _sequence_split(sequences, "test")
        if not val_sequences or not test_sequences:
            ordered = [{"skills": seq["skills"], "correct": seq["correct"]} for seq in sequences]
            train_cut = max(1, int(len(ordered) * 0.7))
            val_cut = max(train_cut + 1, int(len(ordered) * 0.85))
            train_sequences = ordered[:train_cut]
            val_sequences = ordered[train_cut:val_cut]
            test_sequences = ordered[val_cut:]

        if len(train_sequences) < 10:
            warnings.append("Few learner sequences are available; DKT generalization is limited.")

        model = DKTModel(
            num_skills=int(id_map["num_concepts"]),
            embed_dim=int(candidate["embedding_dim"]),
            hidden_dim=int(candidate["hidden_dim"]),
        )
        training_history = _train(
            model,
            train_sequences,
            val_sequences,
            learning_rate=float(candidate["learning_rate"]),
            batch_size=int(candidate["batch_size"]),
        )
        metrics = {
            "train": _evaluate(model, train_sequences, int(candidate["batch_size"])),
            "val": _evaluate(model, val_sequences, int(candidate["batch_size"])),
            "test": _evaluate(model, test_sequences, int(candidate["batch_size"])),
        }
        result = {**candidate, "metrics": metrics, "training_history": training_history}
        hyperparameter_results.append(result)
        score = metrics["val"].get("log_loss")
        if best is None or (score is not None and score < best["metrics"]["val"].get("log_loss", float("inf"))):
            best = result
            best_state = model.state_dict()
            best_split_counts = {
                "train": len(train_sequences),
                "val": len(val_sequences),
                "test": len(test_sequences),
                "sequences": len(sequences),
            }

    if best is None or best_state is None:
        raise RuntimeError("No DKT candidate could be trained.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, MODEL_PATH)
    runtime_id_map = dict(id_map)
    runtime_id_map["embedding_dim"] = int(best["embedding_dim"])
    runtime_id_map["hidden_dim"] = int(best["hidden_dim"])
    runtime_id_map["num_skills"] = int(runtime_id_map["num_concepts"])
    ID_MAP_PATH.write_text(json.dumps(id_map, indent=2), encoding="utf-8")
    ID_MAP_PATH.write_text(json.dumps(runtime_id_map, indent=2), encoding="utf-8")

    learner_count = len({str(row["learner_id"]) for row in rows})
    meta = {
        "model_type": "LSTM_DKT",
        "selected_candidate": best["name"],
        "best_hyperparameters": {
            "embedding_dim": best["embedding_dim"],
            "hidden_dim": best["hidden_dim"],
            "learning_rate": best["learning_rate"],
            "epochs": EPOCHS,
            "batch_size": best["batch_size"],
            "max_seq_len": best["max_seq_len"],
        },
        "metrics": best["metrics"],
        "id_map": str(ID_MAP_PATH),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    report = {
        "status": "warning" if warnings else "success",
        "module": "dkt_runtime_training",
        "artifacts": {"model": str(MODEL_PATH), "id_map": str(ID_MAP_PATH), "meta": str(META_PATH)},
        "model": {
            "type": "LSTM_DKT",
            "embedding_dim": best["embedding_dim"],
            "hidden_dim": best["hidden_dim"],
            "epochs": EPOCHS,
            "batch_size": best["batch_size"],
            "learning_rate": best["learning_rate"],
            "max_seq_len": best["max_seq_len"],
            "objective": "next-step correctness prediction by target concept",
        },
        "dataset": {
            "source_csv": str(CSV_INPUT),
            "row_count": len(rows),
            "learner_count": learner_count,
            "concept_count": len(id_map["concept_to_idx"]),
            "sequence_count": best_split_counts["sequences"],
            "train_sequence_count": best_split_counts["train"],
            "val_sequence_count": best_split_counts["val"],
            "test_sequence_count": best_split_counts["test"],
            "correctness_distribution": dict(correctness),
            "correct_rate": round(correct_rate, 6),
        },
        "metrics": best["metrics"],
        "training_history": best["training_history"],
        "hyperparameter_results": hyperparameter_results,
        "best_hyperparameters": meta["best_hyperparameters"],
        "warnings": warnings,
        "phase1_artifact_note": (
            "Old EdNet/ASSISTments Phase-1 DKT artifacts were intentionally not used for this runtime model "
            "because their skill mappings do not match the current tutor concepts."
        ),
    }
    _write_reports(report)
    return report


def main() -> None:
    report = train_dkt()
    print(f"STATUS: {report['status']}")
    print("MODULE: dkt_runtime_training")
    print(f"MODEL: {MODEL_PATH}")
    print(f"ID_MAP: {ID_MAP_PATH}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
