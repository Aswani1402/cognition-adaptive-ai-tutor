from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.inspect_pretrained_finetune import (
    has_adapter_artifacts,
    is_full_model_folder,
)
from scripts.run_pretrained_local_inference import (
    CONFIG_PATH,
    load_config,
    resolve_config_path,
)


REQUIRED_FILES = [
    "config.json",
    "tokenizer.json or tokenizer.model",
    "tokenizer_config.json",
    "model.safetensors or pytorch_model.bin",
]


def response_base(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "warning",
        "available": False,
        "merged": False,
        "base_model_path": config.get("base_model_path", ""),
        "adapter_path": config.get("adapter_path", ""),
        "merged_model_path": config.get("merged_model_path", ""),
        "reason": None,
        "required_files": REQUIRED_FILES,
    }


def run_merge() -> dict[str, Any]:
    config = load_config()
    if not config:
        result = response_base({})
        result.update(
            {
                "reason": "config_missing",
                "message": f"Missing config file: {CONFIG_PATH.name}",
            }
        )
        return result

    base_model_path = resolve_config_path(config.get("base_model_path"))
    adapter_path = resolve_config_path(config.get("adapter_path"))
    merged_model_path = resolve_config_path(config.get("merged_model_path"))

    if not base_model_path or not is_full_model_folder(base_model_path):
        result = response_base(config)
        result.update(
            {
                "reason": "base_model_path_missing_or_invalid",
                "message": "Cannot merge LoRA adapter until a complete matching local base model folder is configured.",
            }
        )
        return result

    if not adapter_path or not has_adapter_artifacts(adapter_path):
        result = response_base(config)
        result.update(
            {
                "reason": "adapter_path_missing_or_invalid",
                "message": "Adapter folder must contain adapter_config.json and adapter_model.safetensors or adapter_model.bin.",
            }
        )
        return result

    if not merged_model_path:
        result = response_base(config)
        result.update(
            {
                "reason": "merged_model_path_missing",
                "message": "merged_model_path must be configured before merging.",
            }
        )
        return result

    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        local_files_only = bool(config.get("local_files_only", True))
        tokenizer = AutoTokenizer.from_pretrained(
            base_model_path,
            local_files_only=local_files_only,
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            local_files_only=local_files_only,
        )
        peft_model = PeftModel.from_pretrained(
            base_model,
            adapter_path,
            local_files_only=local_files_only,
        )
        merged_model = peft_model.merge_and_unload()
        merged_model_path.mkdir(parents=True, exist_ok=True)
        merged_model.save_pretrained(merged_model_path)
        tokenizer.save_pretrained(merged_model_path)

        result = response_base(config)
        result.update(
            {
                "status": "success",
                "available": True,
                "merged": True,
                "reason": None,
                "message": "Merged model saved locally.",
            }
        )
        return result
    except Exception as exc:
        result = response_base(config)
        result.update(
            {
                "status": "error",
                "reason": "merge_failed",
                "message": str(exc),
            }
        )
        return result


def main() -> None:
    print(json.dumps(run_merge(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
