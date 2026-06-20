import json
import math
import shutil
import time
from pathlib import Path

import torch
import yaml
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset

from scripts.structured_generation_common import ROOT_DIR, load_jsonl
from src.generate import load_checkpoint
from src.model import CogniTutorLM, CogniTutorLMConfig
from src.tokenizer_wrapper import CogniTutorTokenizer


TRAIN = ROOT_DIR / "training_data" / "structured_generation" / "tutor_train.jsonl"
VAL = ROOT_DIR / "training_data" / "structured_generation" / "tutor_val.jsonl"
OUT_DIR = ROOT_DIR / "models" / "cognitutor_lm_structured_generation"
BEST = OUT_DIR / "best_model.pt"
REPORT_JSON = ROOT_DIR / "outputs" / "final_reports" / "structured_cognitutor_training_report.json"
REPORT_MD = ROOT_DIR / "outputs" / "final_reports" / "structured_cognitutor_training_report.md"
BASE = ROOT_DIR / "outputs" / "checkpoints" / "cognitutor_s_best.pt"


class JsonlTextDataset(Dataset):
    def __init__(self, path: Path, tokenizer: CogniTutorTokenizer, context_length: int):
        self.rows = load_jsonl(path)
        self.tokenizer = tokenizer
        self.context_length = context_length
        self.pad_id = tokenizer.pad_id

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]

        # New all-task dataset format:
        # instruction = prompt text
        # output = target answer text
        # input can be a dict with metadata
        prompt_text = row.get("instruction", "")
        output_text = row.get("output", "")

        # Backward compatibility for older datasets
        if not prompt_text and isinstance(row.get("input"), str):
            prompt_text = row.get("input", "")

        training_text = row.get("training_text")
        if not training_text:
            training_text = f"{prompt_text}\n{output_text}<eos>"

        ids = self.tokenizer.encode(training_text, add_bos=False, add_eos=False)
        prompt_ids = self.tokenizer.encode(prompt_text, add_bos=False, add_eos=False)
        ids = ids[: self.context_length + 1]
        ids += [self.pad_id] * max(0, self.context_length + 1 - len(ids))
        targets = ids[1:]
        prompt_target_cutoff = max(0, min(len(prompt_ids) - 1, len(targets)))
        targets = [self.pad_id] * prompt_target_cutoff + targets[prompt_target_cutoff:]
        return {
            "input_ids": torch.tensor(ids[:-1], dtype=torch.long),
            "target_ids": torch.tensor(targets, dtype=torch.long),
        }


@torch.no_grad()
def evaluate(model, loader, device, max_batches=30):
    model.eval()
    losses = []
    for i, batch in enumerate(loader):
        if i >= max_batches:
            break
        _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
        losses.append(float(loss.item()))
    model.train()
    avg = sum(losses) / len(losses) if losses else float("inf")
    return avg, math.exp(avg) if avg < 20 else float("inf")


def main() -> None:
    started = time.time()
    train_rows = load_jsonl(TRAIN)
    val_rows = load_jsonl(VAL)
    status = "FAIL"
    error = None
    best_loss = float("inf")
    ppl = float("inf")
    epochs = 0
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        base_model, _, checkpoint = load_checkpoint(BASE, device)
        cfg = checkpoint["config"]
        model_cfg = cfg["model"]
        context_length = int(model_cfg["context_length"])
        tokenizer = CogniTutorTokenizer()
        train_loader = DataLoader(JsonlTextDataset(TRAIN, tokenizer, context_length), batch_size=8, shuffle=True)
        val_loader = DataLoader(JsonlTextDataset(VAL, tokenizer, context_length), batch_size=8, shuffle=False)
        model = base_model
        optimizer = AdamW(model.parameters(), lr=2e-4, weight_decay=0.01)
        epochs = 10 if device.type == "cuda" else 8
        for epoch in range(epochs):
            model.train()
            for batch in train_loader:
                optimizer.zero_grad(set_to_none=True)
                _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            val_loss, val_ppl = evaluate(model, val_loader, device)
            if val_loss < best_loss:
                best_loss, ppl = val_loss, val_ppl
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "config": cfg,
                        "epoch": epoch + 1,
                        "val_metrics": {"val_loss": best_loss, "perplexity": ppl},
                        "training_source": "cognitutor_structured_from_scratch_training",
                        "loss_focus": "answer_tokens_only",
                    },
                    BEST,
                )
        shutil.copy2(ROOT_DIR / "data" / "tokenizer" / "cognitutor.model", OUT_DIR / "cognitutor.model")
        shutil.copy2(ROOT_DIR / "data" / "tokenizer" / "cognitutor.vocab", OUT_DIR / "cognitutor.vocab")
        (OUT_DIR / "structured_generation_config.json").write_text(json.dumps({"base_checkpoint": str(BASE), "epochs": epochs}, indent=2), encoding="utf-8")
        status = "PASS" if BEST.exists() else "FAIL"
    except Exception as exc:
        import traceback
        error = traceback.format_exc()
        print(error)

        
    report = {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "epochs": epochs,
        "best_val_loss": best_loss if best_loss != float("inf") else None,
        "val_perplexity": ppl if ppl != float("inf") else None,
        "checkpoint_path": str(BEST),
        "training_status": status,
        "error_message": error,
        "loss_focus": "answer_tokens_only",
        "duration_seconds": round(time.time() - started, 2),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_MD.write_text("# Structured CogniTutor Training Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n", encoding="utf-8")
    print(f"train_rows: {report['train_rows']}")
    print(f"val_rows: {report['val_rows']}")
    print(f"epochs: {epochs}")
    print(f"best_val_loss: {report['best_val_loss']}")
    print(f"val_perplexity: {report['val_perplexity']}")
    print(f"checkpoint_path: {BEST}")
    print(f"training_status: {status}")


if __name__ == "__main__":
    main()
