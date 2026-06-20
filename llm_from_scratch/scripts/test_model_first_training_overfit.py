import json
import math
import time

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader

from scripts.train_model_first_full_retrain import ModelFirstDataset, load_jsonl
from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT
from src.generate import generate_text, load_checkpoint
from src.tokenizer_wrapper import CogniTutorTokenizer

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "diagnostics"
OUT_JSON = OUT_DIR / "training_overfit_sanity_test.json"
OUT_MD = OUT_DIR / "training_overfit_sanity_test.md"


def main():
    started = time.time()
    train_path = ROOT / "training_data" / "model_first_full" / "tutor_train.jsonl"
    rows = load_jsonl(train_path)[:10]
    status = "FAIL"
    error = None
    losses = []
    finite_update_count = 0
    generated_output = ""
    try:
        if len(rows) < 10:
            raise RuntimeError("fewer than 10 training rows available")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, _, _checkpoint = load_checkpoint(MODEL_CHECKPOINT, device)
        tokenizer = CogniTutorTokenizer()
        dataset = ModelFirstDataset(train_path, tokenizer, model.config.context_length)
        dataset.rows = rows
        loader = DataLoader(dataset, batch_size=2, shuffle=True)
        optimizer = AdamW(model.parameters(), lr=1e-5, weight_decay=0.0)
        model.train()
        for step, batch in enumerate(loader):
            if step >= 8:
                break
            if int(batch["supervised_tokens"].sum().item()) <= 0:
                continue
            optimizer.zero_grad(set_to_none=True)
            _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
            if not torch.isfinite(loss):
                continue
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            finite_update_count += 1
            losses.append(float(loss.item()))
        model.eval()
        generated_output, _ = generate_text(model, tokenizer, rows[0]["instruction"], device, max_new_tokens=40, temperature=0.2, top_k=20)
        status = "PASS" if finite_update_count > 0 and losses and all(math.isfinite(x) for x in losses) and bool(generated_output.strip()) else "FAIL"
    except Exception as exc:
        import traceback
        error = traceback.format_exc()
        print(error)
    report = {
        "status": status,
        "finite_update_count": finite_update_count,
        "initial_loss": losses[0] if losses else None,
        "final_loss": losses[-1] if losses else None,
        "loss_decreased": bool(len(losses) >= 2 and losses[-1] <= losses[0]),
        "losses": losses,
        "generated_output_preview": generated_output[:500],
        "generated_output_non_empty": bool(generated_output.strip()),
        "duration_seconds": round(time.time() - started, 2),
        "error": error,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Training Overfit Sanity Test\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items() if k != "losses"), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
