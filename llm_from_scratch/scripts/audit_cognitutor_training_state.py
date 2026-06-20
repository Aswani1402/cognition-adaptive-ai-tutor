import json
from collections import Counter
from pathlib import Path

import torch
import yaml

from scripts.structured_generation_common import ROOT_DIR, TASK_TOKENS, load_jsonl
from src.generate import load_checkpoint
from src.model import CogniTutorLM, CogniTutorLMConfig
from src.tokenizer_wrapper import CogniTutorTokenizer


OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_training_state_audit.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "cognitutor_training_state_audit.md"


def exists(path: Path) -> bool:
    return path.exists()


def main() -> None:
    tokenizer_files = {
        "model": ROOT_DIR / "data" / "tokenizer" / "cognitutor.model",
        "vocab": ROOT_DIR / "data" / "tokenizer" / "cognitutor.vocab",
    }
    checkpoints = sorted((ROOT_DIR / "outputs" / "checkpoints").glob("*.pt"))
    config_path = ROOT_DIR / "configs" / "cognitutor_s.yaml"
    split_paths = {
        "processed": ROOT_DIR / "data" / "processed" / "tutor_instruction_dataset.jsonl",
        "train": ROOT_DIR / "data" / "splits" / "train.jsonl",
        "val": ROOT_DIR / "data" / "splits" / "val.jsonl",
        "test": ROOT_DIR / "data" / "splits" / "test.jsonl",
    }
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    tokenizer_status = "PASS" if all(path.exists() for path in tokenizer_files.values()) else "FAIL"
    training_rows = {name: len(load_jsonl(path)) for name, path in split_paths.items()}
    training_data_status = "PASS" if training_rows.get("train", 0) and training_rows.get("val", 0) else "FAIL"
    current_checkpoint = ROOT_DIR / "outputs" / "checkpoints" / "cognitutor_s_best.pt"
    checkpoint_status = "FAIL"
    param_count = None
    checkpoint_error = None
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, _, _ = load_checkpoint(current_checkpoint, device)
        param_count = model.count_parameters()
        checkpoint_status = "PASS"
    except Exception as exc:
        checkpoint_error = str(exc)

    try:
        tokenizer = CogniTutorTokenizer()
        vocab_size = tokenizer.vocab_size()
    except Exception:
        vocab_size = None

    quality_path = ROOT_DIR / "outputs" / "rag_grounded_generation" / "rag_grounded_generation_test.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    quality_summary = quality.get("summary", {})
    recommendation = (
        "Build structured task dataset and fine-tune the from-scratch checkpoint; current direct structured generation is WARN."
        if quality_summary.get("status") != "PASS"
        else "Current micro generation is passing; verify core before full generation."
    )
    report = {
        "checkpoint_status": checkpoint_status,
        "tokenizer_status": tokenizer_status,
        "training_data_status": training_data_status,
        "task_tokens_found": sorted(TASK_TOKENS.values()),
        "task_token_count": len(TASK_TOKENS),
        "current_checkpoint_path": str(current_checkpoint),
        "checkpoint_files": [str(path) for path in checkpoints],
        "checkpoint_error": checkpoint_error,
        "tokenizer_files": {key: str(path) for key, path in tokenizer_files.items()},
        "vocab_size": vocab_size,
        "training_config": config,
        "training_rows": training_rows,
        "dataset_builder_file": str(ROOT_DIR / "src" / "dataset_builder.py"),
        "model_parameter_count": param_count,
        "current_generation_quality_summary": quality_summary,
        "recommendation": recommendation,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# CogniTutor Training State Audit\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"training_config"})
        + "\n",
        encoding="utf-8",
    )
    print(f"checkpoint_status: {checkpoint_status}")
    print(f"tokenizer_status: {tokenizer_status}")
    print(f"training_data_status: {training_data_status}")
    print(f"task_tokens_found: {len(TASK_TOKENS)}")
    print(f"current_checkpoint_path: {current_checkpoint}")
    print(f"recommendation: {recommendation}")


if __name__ == "__main__":
    main()
