from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from scripts.inspect_pretrained_finetune import (
    ROOT,
    has_adapter_artifacts,
    is_full_model_folder,
    relative,
)


CONFIG_PATH = ROOT / "pretrained_inference_config.json"
SERVICE = "pretrained_pretrained_finetuned_llm"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resolve_config_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def base_response(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "warning",
        "service": SERVICE,
        "available": False,
        "model_loaded": False,
        "adapter_loaded": False,
        "base_model_path": config.get("base_model_path", ""),
        "adapter_path": config.get("adapter_path", ""),
        "merged_model_path": config.get("merged_model_path", ""),
        "output": "",
        "latency_ms": 0.0,
        "reason": None,
        "limitations": [],
    }


def unavailable_response(
    config: dict[str, Any],
    reason: str,
    message: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    response = base_response(config)
    response.update(
        {
            "status": "warning",
            "available": False,
            "reason": reason,
            "message": message,
            "limitations": limitations or [],
        }
    )
    return response


def build_prompt(task: str, concept: str, prompt: str) -> str:
    if prompt:
        return prompt
    return (
        "You are an adaptive AI tutor. "
        f"Task: {task}. Concept: {concept}. "
        "Generate concise beginner-friendly tutor content."
    )


def load_transformers_model(model_path: Path, config: dict[str, Any]):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kwargs: dict[str, Any] = {
        "local_files_only": bool(config.get("local_files_only", True)),
    }
    device = config.get("device", "auto")
    if device == "auto":
        kwargs["device_map"] = "auto"

    tokenizer = AutoTokenizer.from_pretrained(model_path, **kwargs)
    model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)
    model.eval()
    return tokenizer, model


def generate(
    tokenizer: Any,
    model: Any,
    prompt: str,
    config: dict[str, Any],
) -> str:
    import torch

    inputs = tokenizer(prompt, return_tensors="pt")
    model_device = getattr(model, "device", None)
    if model_device is not None:
        inputs = {
            key: value.to(model_device)
            for key, value in inputs.items()
        }

    generate_kwargs = {
        "max_new_tokens": int(config.get("max_new_tokens", 160)),
        "do_sample": bool(config.get("do_sample", False)),
        "pad_token_id": tokenizer.eos_token_id,
    }
    if generate_kwargs["do_sample"]:
        generate_kwargs["temperature"] = float(config.get("temperature", 0.2))

    with torch.no_grad():
        outputs = model.generate(**inputs, **generate_kwargs)

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if decoded.startswith(prompt):
        decoded = decoded[len(prompt):]
    return decoded.strip()


def run_inference(task: str, concept: str, prompt: str) -> dict[str, Any]:
    start = time.perf_counter()
    config = load_config()
    if not config:
        return unavailable_response(
            config,
            "config_missing",
            "pretrained_inference_config.json is required for local inference.",
        )

    merged_path = resolve_config_path(config.get("merged_model_path"))
    base_model_path = resolve_config_path(config.get("base_model_path"))
    adapter_path = resolve_config_path(config.get("adapter_path"))

    use_merged = bool(merged_path and is_full_model_folder(merged_path))
    use_adapter = bool(
        base_model_path
        and is_full_model_folder(base_model_path)
        and adapter_path
        and has_adapter_artifacts(adapter_path)
    )

    if not use_merged and not use_adapter:
        if not base_model_path or not is_full_model_folder(base_model_path):
            return unavailable_response(
                config,
                "base_model_path_missing_or_invalid",
                "LoRA adapter exists but matching local base model folder is required for inference.",
                [
                    "External downloads are disabled.",
                    "Required base model files: config.json, tokenizer.json or tokenizer.model, tokenizer_config.json, model.safetensors or pytorch_model.bin.",
                ],
            )
        return unavailable_response(
            config,
            "adapter_path_missing_or_invalid",
            "A valid LoRA adapter folder with adapter_config.json and adapter_model weights is required.",
        )

    try:
        if use_merged and merged_path is not None:
            tokenizer, model = load_transformers_model(merged_path, config)
            adapter_loaded = False
            active_model_path = relative(merged_path)
        else:
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            assert base_model_path is not None
            assert adapter_path is not None

            kwargs: dict[str, Any] = {
                "local_files_only": bool(config.get("local_files_only", True)),
            }
            if config.get("device", "auto") == "auto":
                kwargs["device_map"] = "auto"

            tokenizer = AutoTokenizer.from_pretrained(base_model_path, **kwargs)
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_path,
                **kwargs,
            )
            model = PeftModel.from_pretrained(
                base_model,
                adapter_path,
                local_files_only=bool(config.get("local_files_only", True)),
            )
            model.eval()
            adapter_loaded = True
            active_model_path = relative(base_model_path)

        output = generate(
            tokenizer,
            model,
            build_prompt(task, concept, prompt),
            config,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response = base_response(config)
        response.update(
            {
                "status": "success",
                "available": True,
                "model_loaded": True,
                "adapter_loaded": adapter_loaded,
                "output": output,
                "latency_ms": latency_ms,
                "reason": None,
                "limitations": [],
                "active_model_path": active_model_path,
            }
        )
        return response
    except Exception as exc:
        response = base_response(config)
        response.update(
            {
                "status": "error",
                "reason": "inference_failed",
                "message": str(exc),
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "limitations": ["No fallback or fake generation output was used."],
            }
        )
        return response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="explanation")
    parser.add_argument("--concept", default="Python Variables")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()

    result = run_inference(
        task=args.task,
        concept=args.concept,
        prompt=args.prompt,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
