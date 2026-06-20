import csv
import json
import math
import random
import shutil
import time
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset

from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT
from src.generate import generate_text, load_checkpoint
from src.model_first_parser import parse_model_output
from src.model_first_training_config import CONFIG
from src.model_first_validator import validate_model_output
from src.tokenizer_wrapper import CogniTutorTokenizer

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "training"
OUT_JSON = OUT_DIR / "full_retrain_training_report.json"
OUT_MD = OUT_DIR / "full_retrain_training_report.md"
HISTORY = OUT_DIR / "training_history.csv"


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


class ModelFirstDataset(Dataset):
    def __init__(self, path: Path, tokenizer: CogniTutorTokenizer, context_length: int):
        self.rows = load_jsonl(path)
        self.tokenizer = tokenizer
        self.context_length = context_length
        self.pad_id = tokenizer.pad_id

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        prompt = str(row.get("instruction") or "").strip()
        target = str(row.get("target") or row.get("output") or "").strip()
        prompt_ids = self.tokenizer.encode(prompt + " ", add_bos=False, add_eos=False)
        target_ids = self.tokenizer.encode(target + "\n<eos>", add_bos=False, add_eos=False)

        # Reserve target room. The earlier loop truncated long RAG prompts before
        # the answer, which created batches with no supervised target tokens.
        max_target = max(8, min(len(target_ids), self.context_length // 2))
        target_ids = target_ids[:max_target]
        prompt_budget = max(1, self.context_length + 1 - len(target_ids))
        prompt_ids = prompt_ids[-prompt_budget:]
        ids = (prompt_ids + target_ids)[: self.context_length + 1]
        ids += [self.pad_id] * max(0, self.context_length + 1 - len(ids))

        targets = ids[1:]
        supervised_start = max(0, len(prompt_ids) - 1)
        targets = [self.pad_id] * supervised_start + targets[supervised_start:]
        return {
            "input_ids": torch.tensor(ids[:-1], dtype=torch.long),
            "target_ids": torch.tensor(targets, dtype=torch.long),
            "supervised_tokens": torch.tensor(sum(1 for value in targets if value != self.pad_id), dtype=torch.long),
        }


@torch.no_grad()
def evaluate_loss(model, loader, device, max_batches):
    model.eval()
    losses = []
    for idx, batch in enumerate(loader):
        if idx >= max_batches:
            break
        if int(batch.get("supervised_tokens", torch.tensor([0])).sum().item()) <= 0:
            continue
        _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
        if torch.isfinite(loss):
            losses.append(float(loss.item()))
    model.train()
    avg = sum(losses) / len(losses) if losses else float("inf")
    return avg, math.exp(avg) if avg < 20 else float("inf")


def validate_one_batch(model, loader, device):
    for batch in loader:
        supervised = int(batch["supervised_tokens"].sum().item())
        if supervised <= 0:
            return {"ok": False, "reason": "batch_has_no_supervised_target_tokens", "supervised_tokens": supervised}
        with torch.no_grad():
            logits, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
        return {
            "ok": bool(torch.isfinite(loss)),
            "reason": None if torch.isfinite(loss) else "nonfinite_initial_loss",
            "supervised_tokens": supervised,
            "input_shape": list(batch["input_ids"].shape),
            "label_shape": list(batch["target_ids"].shape),
            "logit_shape": list(logits.shape),
            "initial_loss": float(loss.item()) if torch.isfinite(loss) else None,
        }
    return {"ok": False, "reason": "empty_loader", "supervised_tokens": 0}


@torch.no_grad()
def sample_format_validity(model, tokenizer, device, rows):
    model.eval()
    selected = []
    wanted = [
        ("Python", "Variables", "mcq"),
        ("SQL", "JOIN Operations", "explanation"),
        ("HTML", "Forms and Inputs", "flashcard"),
        ("Git", "Branches", "hint"),
        ("Data Structures", "Trees", "mindmap"),
    ]
    for domain, concept, task in wanted:
        row = next((r for r in rows if r.get("domain") == domain and r.get("concept_name") == concept and r.get("task_type") == task), None)
        if row:
            selected.append(row)
    results = []
    for row in selected:
        raw, _ = generate_text(model, tokenizer, row["instruction"], device, max_new_tokens=120, temperature=0.2, top_k=40)
        parsed = parse_model_output(raw, row["task_type"])
        val = validate_model_output(parsed.get("parsed_output"), row["task_type"], row["domain"], row["concept_name"], row.get("difficulty") or "easy", row.get("teaching_view"), parser_repair_applied=bool(parsed.get("repair_applied")))
        results.append({"task_type": row["task_type"], "domain": row["domain"], "concept_name": row["concept_name"], "valid": val.get("valid"), "quality_score": val.get("quality_score"), "issues": val.get("issues")})
    rate = sum(1 for r in results if r["valid"]) / len(results) if results else 0.0
    model.train()
    return rate, results


def main():
    started = time.time()
    random.seed(CONFIG.seed)
    torch.manual_seed(CONFIG.seed)
    train_rows = load_jsonl(CONFIG.train_path)
    val_rows = load_jsonl(CONFIG.val_path)
    status = "FAIL"
    error = None
    history = []
    best_score = float("-inf")
    best_path = None
    finite_update_count = 0
    skipped_batch_count = 0
    nonfinite_loss_count = 0
    best_val_loss = None
    one_batch_check = {}
    try:
        if not train_rows or not val_rows:
            raise RuntimeError("model_first_full dataset missing; run scripts.build_model_first_full_dataset first")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, _, checkpoint = load_checkpoint(MODEL_CHECKPOINT, device)
        cfg = checkpoint["config"]
        tokenizer = CogniTutorTokenizer()
        train_loader = DataLoader(ModelFirstDataset(CONFIG.train_path, tokenizer, model.config.context_length), batch_size=CONFIG.batch_size, shuffle=True)
        val_loader = DataLoader(ModelFirstDataset(CONFIG.val_path, tokenizer, model.config.context_length), batch_size=CONFIG.batch_size, shuffle=False)
        one_batch_check = validate_one_batch(model, train_loader, device)
        if not one_batch_check.get("ok"):
            raise RuntimeError(f"training batch validation failed: {one_batch_check}")
        optimizer = AdamW(model.parameters(), lr=CONFIG.learning_rate, weight_decay=CONFIG.weight_decay)
        CONFIG.output_dir.mkdir(parents=True, exist_ok=True)
        CONFIG.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        epochs = int(CONFIG.max_epochs)
        no_improve = 0
        for epoch in range(1, epochs + 1):
            model.train()
            losses = []
            for batch in train_loader:
                if int(batch["supervised_tokens"].sum().item()) <= 0:
                    skipped_batch_count += 1
                    continue
                optimizer.zero_grad(set_to_none=True)
                _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
                if not torch.isfinite(loss):
                    nonfinite_loss_count += 1
                    continue
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), CONFIG.grad_clip)
                optimizer.step()
                losses.append(float(loss.item()))
                finite_update_count += 1
            val_loss, val_ppl = evaluate_loss(model, val_loader, device, CONFIG.max_val_batches)
            if not math.isfinite(val_loss):
                val_loss = 999.0
                val_ppl = float("inf")
            sample_rate, sample_cases = sample_format_validity(model, tokenizer, device, val_rows)
            train_loss = sum(losses) / len(losses) if losses else None
            score = sample_rate - (val_loss / 100.0)
            epoch_path = CONFIG.checkpoints_dir / f"epoch_{epoch:03d}.pt"
            torch.save({"model_state_dict": model.state_dict(), "config": cfg, "epoch": epoch, "val_metrics": {"val_loss": val_loss, "perplexity": val_ppl, "sample_format_validity": sample_rate}, "training_source": "model_first_full_local_guarded_outputs"}, epoch_path)
            if math.isfinite(val_loss) and finite_update_count > 0 and score > best_score:
                best_score = score
                best_val_loss = val_loss
                best_path = CONFIG.best_model_path
                shutil.copy2(epoch_path, CONFIG.best_model_path)
                no_improve = 0
            else:
                no_improve += 1
            history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, "val_perplexity": val_ppl, "sample_format_validity": sample_rate, "checkpoint": str(epoch_path), "best": score == best_score})
            train_loss_text = f"{train_loss:.4f}" if train_loss is not None else "nan"
            print(f"epoch={epoch} train_loss={train_loss_text} val_loss={val_loss:.4f} sample_valid={sample_rate:.3f}")
            if no_improve >= CONFIG.early_stopping_patience:
                break
        shutil.copy2(ROOT / "data" / "tokenizer" / "cognitutor.model", CONFIG.output_dir / "cognitutor.model")
        shutil.copy2(ROOT / "data" / "tokenizer" / "cognitutor.vocab", CONFIG.output_dir / "cognitutor.vocab")
        (CONFIG.output_dir / "model_first_training_config.json").write_text(json.dumps(CONFIG.to_jsonable(), indent=2), encoding="utf-8")
        status = "PASS" if CONFIG.best_model_path.exists() and finite_update_count > 0 and best_val_loss is not None and math.isfinite(best_val_loss) else "FAIL"
    except Exception as exc:
        import traceback
        error = traceback.format_exc()
        print(error)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "val_loss", "val_perplexity", "sample_format_validity", "checkpoint", "best"])
        writer.writeheader()
        writer.writerows(history)
    report = {
        "training_status": status,
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "finite_update_count": finite_update_count,
        "skipped_batch_count": skipped_batch_count,
        "nonfinite_loss_count": nonfinite_loss_count,
        "best_val_loss": best_val_loss,
        "val_perplexity": history[-1].get("val_perplexity") if history else None,
        "checkpoint_path": str(best_path) if best_path else None,
        "best_checkpoint": str(best_path) if best_path else None,
        "one_batch_check": one_batch_check,
        "history": history,
        "duration_seconds": round(time.time() - started, 2),
        "error": error,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Full Model-First Retrain Training Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items() if k != "history"), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
