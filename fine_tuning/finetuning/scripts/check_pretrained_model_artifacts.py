import json
import re
from pathlib import Path

from scripts.pretrained_track_utils import REPO_ROOT, iter_files, rel, write_json, write_md


ARTIFACT_NAMES = {
    "config.json",
    "pytorch_model.bin",
    "model.safetensors",
    "adapter_model.bin",
    "adapter_model.safetensors",
    "adapter_config.json",
    "tokenizer.model",
    "tokenizer.json",
    "special_tokens_map.json",
    "trainer_state.json",
    "training_args.bin",
    "generation_config.json",
}


def _references() -> list:
    refs = []
    pattern = re.compile(r"(from_pretrained|base_model_name_or_path|model_name|model_dir|checkpoint|PRETRAINED_FINETUNED_MODEL_DIR)", re.I)
    for path in iter_files(REPO_ROOT):
        if path.suffix.lower() not in {".py", ".json", ".md", ".txt", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pattern.search(text):
            refs.append({"file": rel(path), "matches": sorted(set(pattern.findall(text)))})
    return refs


def main() -> None:
    artifacts = sorted(rel(path) for path in iter_files(REPO_ROOT) if path.name in ARTIFACT_NAMES)
    adapters = [item for item in artifacts if "adapter_model" in item]
    full_models = [item for item in artifacts if Path(item).name in {"pytorch_model.bin", "model.safetensors"}]
    tokenizers = [item for item in artifacts if "tokenizer" in Path(item).name or Path(item).name in {"vocab.json", "merges.txt"}]
    configs = [item for item in artifacts if Path(item).name == "config.json"]
    adapter_configs = [REPO_ROOT / item for item in artifacts if Path(item).name == "adapter_config.json"]
    base_models = []
    for config in adapter_configs:
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            if data.get("base_model_name_or_path"):
                base_models.append({"adapter_config": rel(config), "base_model_name_or_path": data["base_model_name_or_path"]})
        except Exception:
            pass
    remote_dependency = bool(base_models and not full_models)
    if full_models and tokenizers and configs:
        status = "PASS"
        runtime_status = "PASS"
        reason = "local full model, tokenizer, and config artifacts found"
    elif remote_dependency:
        status = "WARN"
        runtime_status = "WARN/PENDING_LOCAL_MODEL"
        reason = "LoRA adapter/tokenizer artifacts exist, but local base model weights/config are missing and remote download is disabled"
    else:
        status = "FAIL"
        runtime_status = "FAIL"
        reason = "required local inference artifacts are missing"
    data = {
        "status": status,
        "runtime_status": runtime_status,
        "reason": reason,
        "remote_model_dependency": remote_dependency,
        "artifact_files": artifacts,
        "adapter_files": adapters,
        "full_model_files": full_models,
        "tokenizer_files": tokenizers,
        "config_files": configs,
        "base_model_references": base_models,
        "script_config_references": _references(),
    }
    write_json(REPO_ROOT / "outputs/inspection/pretrained_model_artifact_check.json", data)
    write_md(
        REPO_ROOT / "outputs/inspection/pretrained_model_artifact_check.md",
        "Pretrained Fine-Tuned Model Artifact Check",
        {
            "Status": status,
            "Runtime Status": runtime_status,
            "Reason": reason,
            "Remote Model Dependency": remote_dependency,
            "Base Model References": base_models,
            "Artifact Files": artifacts,
        },
    )
    print(status, runtime_status, "artifact check saved")


if __name__ == "__main__":
    main()
