import csv
import json
import math
import random
import shutil
import time
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader

from scripts.train_model_first_full_retrain import ModelFirstDataset, evaluate_loss, load_jsonl, sample_format_validity, validate_one_batch
from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT
from src.generate import load_checkpoint
from src.generate import generate_text
from src.tokenizer_wrapper import CogniTutorTokenizer

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "training"
OUT_JSON = OUT_DIR / "full_fixed_training_report.json"
OUT_MD = OUT_DIR / "full_fixed_training_report.md"
HISTORY = OUT_DIR / "full_fixed_training_history.csv"
MODEL_DIR = ROOT / "models" / "cognitutor_lm_model_first_full_fixed"
CHECKPOINT_DIR = MODEL_DIR / "checkpoints"
BEST_MODEL = MODEL_DIR / "best_model.pt"
TRAIN_PATH = ROOT / "training_data" / "model_first_full" / "tutor_train.jsonl"
VAL_PATH = ROOT / "training_data" / "model_first_full" / "tutor_val.jsonl"


def main():
    started = time.time()
    random.seed(42)
    torch.manual_seed(42)
    train_rows = load_jsonl(TRAIN_PATH)
    val_rows = load_jsonl(VAL_PATH)
    overfit_report = ROOT / "outputs" / "model_first_full_retrain" / "diagnostics" / "training_overfit_sanity_test.json"
    status = "FAIL"
    error = None
    history = []
    finite_update_count = 0
    skipped_batch_count = 0
    nonfinite_loss_count = 0
    best_val_loss = None
    best_checkpoint = None
    one_batch_check = {}
    sample_cases = []
    sample_generation_preview = ""
    try:
        sanity = json.loads(overfit_report.read_text(encoding="utf-8")) if overfit_report.exists() else {}
        if sanity.get("status") != "PASS":
            raise RuntimeError("overfit sanity test must PASS before fixed full training")
        if not train_rows or not val_rows:
            raise RuntimeError("model_first_full train/val data is missing")

        previous = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
        if (
            BEST_MODEL.exists()
            and int(previous.get("finite_update_count") or 0) > 0
            and previous.get("best_val_loss") is not None
            and math.isfinite(float(previous.get("best_val_loss")))
        ):
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model, _, _checkpoint = load_checkpoint(BEST_MODEL, device)
            tokenizer = CogniTutorTokenizer()
            sample_generation_preview, _ = generate_text(model, tokenizer, train_rows[0]["instruction"], device, max_new_tokens=80, temperature=0.2, top_k=20)
            status = "PASS" if sample_generation_preview.strip() else "FAIL"
            finite_update_count = int(previous.get("finite_update_count") or 0)
            skipped_batch_count = int(previous.get("skipped_batch_count") or 0)
            nonfinite_loss_count = int(previous.get("nonfinite_loss_count") or 0)
            best_val_loss = float(previous.get("best_val_loss"))
            best_checkpoint = str(BEST_MODEL)
            one_batch_check = previous.get("one_batch_check") or {}
            history = previous.get("history") or []
            raise StopIteration("existing fixed checkpoint verified")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, _, checkpoint = load_checkpoint(MODEL_CHECKPOINT, device)
        cfg = checkpoint["config"]
        tokenizer = CogniTutorTokenizer()
        train_loader = DataLoader(ModelFirstDataset(TRAIN_PATH, tokenizer, model.config.context_length), batch_size=4, shuffle=True)
        val_loader = DataLoader(ModelFirstDataset(VAL_PATH, tokenizer, model.config.context_length), batch_size=4, shuffle=False)
        one_batch_check = validate_one_batch(model, train_loader, device)
        if not one_batch_check.get("ok"):
            raise RuntimeError(f"training batch validation failed: {one_batch_check}")

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        optimizer = AdamW(model.parameters(), lr=1e-5, weight_decay=0.01)
        no_improve = 0
        for epoch in range(1, 4):
            losses = []
            model.train()
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
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                finite_update_count += 1
                losses.append(float(loss.item()))

            val_loss, val_ppl = evaluate_loss(model, val_loader, device, 60)
            sample_rate, sample_cases = sample_format_validity(model, tokenizer, device, val_rows)
            train_loss = sum(losses) / len(losses) if losses else None
            epoch_path = CHECKPOINT_DIR / f"epoch_{epoch:03d}.pt"
            metrics = {"val_loss": val_loss, "perplexity": val_ppl, "sample_format_validity": sample_rate}
            if math.isfinite(val_loss):
                torch.save({"model_state_dict": model.state_dict(), "config": cfg, "epoch": epoch, "val_metrics": metrics, "training_source": "model_first_full_fixed_local_guarded_outputs"}, epoch_path)
                if best_val_loss is None or val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_checkpoint = str(BEST_MODEL)
                    shutil.copy2(epoch_path, BEST_MODEL)
                    no_improve = 0
                else:
                    no_improve += 1
            else:
                no_improve += 1
            history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, "val_perplexity": val_ppl, "sample_format_validity": sample_rate, "checkpoint": str(epoch_path) if epoch_path.exists() else None, "best": best_checkpoint == str(BEST_MODEL) and best_val_loss == val_loss})
            print(f"fixed epoch={epoch} train_loss={train_loss if train_loss is not None else 'nan'} val_loss={val_loss} sample_valid={sample_rate:.3f}")
            if no_improve >= 2:
                break
        if (ROOT / "data" / "tokenizer" / "cognitutor.model").exists():
            shutil.copy2(ROOT / "data" / "tokenizer" / "cognitutor.model", MODEL_DIR / "cognitutor.model")
        if (ROOT / "data" / "tokenizer" / "cognitutor.vocab").exists():
            shutil.copy2(ROOT / "data" / "tokenizer" / "cognitutor.vocab", MODEL_DIR / "cognitutor.vocab")
        status = "PASS" if finite_update_count > 0 and best_val_loss is not None and math.isfinite(best_val_loss) and BEST_MODEL.exists() and sample_cases else "FAIL"
        sample_generation_preview, _ = generate_text(model, tokenizer, train_rows[0]["instruction"], device, max_new_tokens=80, temperature=0.2, top_k=20)
        status = "PASS" if finite_update_count > 0 and best_val_loss is not None and math.isfinite(best_val_loss) and BEST_MODEL.exists() and sample_generation_preview.strip() else "FAIL"
    except StopIteration as exc:
        print(str(exc))
    except Exception:
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
        "checkpoint_path": best_checkpoint,
        "best_checkpoint": best_checkpoint,
        "one_batch_check": one_batch_check,
        "sample_generation_non_empty": bool(sample_cases),
        "sample_generation_preview": sample_generation_preview[:500],
        "sample_generation_non_empty": bool(sample_generation_preview.strip()),
        "sample_cases": sample_cases,
        "history": history,
        "duration_seconds": round(time.time() - started, 2),
        "error": error,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUT_MD.write_text("# Full Fixed Model-First Training Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"history", "sample_cases"}), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
