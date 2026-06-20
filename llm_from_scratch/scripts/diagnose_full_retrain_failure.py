import json
import math
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from scripts.train_model_first_full_retrain import ModelFirstDataset, load_jsonl, validate_one_batch
from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT
from src.generate import load_checkpoint
from src.tokenizer_wrapper import CogniTutorTokenizer

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "diagnostics"
OUT_JSON = OUT_DIR / "full_retrain_failure_diagnosis.json"
OUT_MD = OUT_DIR / "full_retrain_failure_diagnosis.md"


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": str(exc)}


def _safe_loss_check(dataset_path: Path, tokenizer: CogniTutorTokenizer, model, device):
    dataset = ModelFirstDataset(dataset_path, tokenizer, model.config.context_length)
    loader = DataLoader(dataset, batch_size=2, shuffle=False)
    check = validate_one_batch(model, loader, device)
    optimizer_step_ran = False
    step_loss = None
    for batch in loader:
        if int(batch["supervised_tokens"].sum().item()) <= 0:
            continue
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-6)
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(batch["input_ids"].to(device), batch["target_ids"].to(device))
        if torch.isfinite(loss):
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer_step_ran = True
            step_loss = float(loss.item())
        break
    check["optimizer_step_ran"] = optimizer_step_ran
    check["step_loss"] = step_loss
    return check


def main():
    train_path = ROOT / "training_data" / "model_first_full" / "tutor_train.jsonl"
    val_path = ROOT / "training_data" / "model_first_full" / "tutor_val.jsonl"
    latest_report = ROOT / "outputs" / "model_first_full_retrain" / "training" / "full_retrain_training_report.json"
    checkpoint_dir = ROOT / "models" / "cognitutor_lm_model_first_full"

    train_rows = load_jsonl(train_path)
    val_rows = load_jsonl(val_path)
    sample = train_rows[0] if train_rows else {}
    tokenizer = CogniTutorTokenizer()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, checkpoint = load_checkpoint(MODEL_CHECKPOINT, device)

    prompt_ids = tokenizer.encode(str(sample.get("instruction") or ""), add_bos=False, add_eos=False)
    target_ids = tokenizer.encode(str(sample.get("target") or sample.get("output") or ""), add_bos=False, add_eos=False)
    old_combined = tokenizer.encode(str(sample.get("training_text") or ""), add_bos=False, add_eos=False)
    old_target_survived = len(old_combined[: model.config.context_length + 1]) > len(prompt_ids)
    fixed_check = _safe_loss_check(train_path, tokenizer, model, device)
    latest = _read_json(latest_report) or {}

    checkpoint_files = sorted(str(p) for p in checkpoint_dir.rglob("*.pt")) if checkpoint_dir.exists() else []
    root_cause = (
        "long_prompt_truncation_removed_targets_or_left_no_supervised_tokens"
        if not old_target_survived or latest.get("finite_update_count") == 0
        else "undetermined"
    )
    suggested_fix = "Reserve target-token budget, ignore only prompt/pad positions, validate one finite-loss batch before training, and save best checkpoint only for finite validation loss."
    status = "PASS" if fixed_check.get("ok") and fixed_check.get("optimizer_step_ran") else "FAIL"

    report = {
        "status": status,
        "root_cause": root_cause,
        "suggested_fix": suggested_fix,
        "train_rows_non_empty": bool(train_rows),
        "val_rows_non_empty": bool(val_rows),
        "sample_has_input_target": bool(sample.get("instruction") and (sample.get("target") or sample.get("output"))),
        "sample_target_is_string": isinstance(sample.get("target") or sample.get("output"), str),
        "prompt_token_count": len(prompt_ids),
        "target_token_count": len(target_ids),
        "model_context_length": model.config.context_length,
        "old_combined_token_count": len(old_combined),
        "old_target_survived_context_truncation": old_target_survived,
        "fixed_one_batch_check": fixed_check,
        "labels_have_supervised_tokens": fixed_check.get("supervised_tokens", 0) > 0,
        "loss_finite_on_one_batch": fixed_check.get("ok"),
        "optimizer_step_runs": fixed_check.get("optimizer_step_ran"),
        "latest_training_report": latest,
        "checkpoint_files": checkpoint_files,
        "checkpoint_real_or_dummy": "bad_previous_checkpoint_not_promoted" if latest.get("finite_update_count") == 0 else "unknown",
        "val_loss_999_reason": "sentinel value used after no finite validation loss was available",
        "base_checkpoint_config_present": bool(checkpoint.get("config")),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUT_MD.write_text(
        "# Full Retrain Failure Diagnosis\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"latest_training_report", "checkpoint_files"}),
        encoding="utf-8",
    )
    print(json.dumps({"root_cause": root_cause, "suggested_fix": suggested_fix, "status": status}, indent=2))


if __name__ == "__main__":
    main()
