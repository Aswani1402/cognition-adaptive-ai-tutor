import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIRS = [
    REPO_ROOT / "models" / "llm_finetuned" / "qwen_coder_05b_lora",
    REPO_ROOT / "models" / "llm_finetuned" / "smollm2_135m_lora",
]

_STATE: Dict[str, Any] = {"model": None, "tokenizer": None, "model_dir": None, "error": None}


def _result(status: str, prompt: str = "", raw_output: str = "", error: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    return {
        "status": status,
        "source": "pretrained_finetuning_track",
        "model_loaded": _STATE["model"] is not None,
        "model_dir": str(_STATE["model_dir"]) if _STATE["model_dir"] else None,
        "task_type": extra.get("task_type"),
        "domain": extra.get("domain"),
        "concept_name": extra.get("concept_name"),
        "difficulty": extra.get("difficulty"),
        "prompt": prompt,
        "raw_output": raw_output,
        "error": error,
    }


def _resolve_model_dir(model_dir: Optional[str]) -> Path:
    if model_dir:
        return Path(model_dir).expanduser().resolve()
    env_dir = os.environ.get("PRETRAINED_FINETUNED_MODEL_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    for candidate in DEFAULT_MODEL_DIRS:
        if candidate.exists():
            return candidate.resolve()
    return DEFAULT_MODEL_DIRS[0].resolve()


def _read_adapter_base_model(model_dir: Path) -> Optional[str]:
    adapter_config = model_dir / "adapter_config.json"
    if not adapter_config.exists():
        return None
    try:
        data = json.loads(adapter_config.read_text(encoding="utf-8"))
        return data.get("base_model_name_or_path")
    except Exception:
        return None


def _local_artifacts_complete(model_dir: Path) -> Optional[str]:
    if not model_dir.exists():
        return f"model directory does not exist: {model_dir}"
    has_tokenizer = any((model_dir / name).exists() for name in ("tokenizer.json", "tokenizer.model", "vocab.json"))
    has_full_model = any((model_dir / name).exists() for name in ("pytorch_model.bin", "model.safetensors"))
    has_adapter = any((model_dir / name).exists() for name in ("adapter_model.bin", "adapter_model.safetensors"))
    if not has_tokenizer:
        return f"tokenizer files missing in {model_dir}"
    if has_adapter and not has_full_model:
        base_model = _read_adapter_base_model(model_dir)
        return (
            "local directory contains LoRA adapter weights but no local base model weights; "
            f"base_model_name_or_path={base_model!r}. Remote download is disabled."
        )
    if not has_full_model:
        return f"full local model checkpoint missing in {model_dir}"
    if not (model_dir / "config.json").exists():
        return f"config.json missing in {model_dir}"
    return None


def load_model(model_dir: Optional[str] = None, device: Optional[str] = None) -> Dict[str, Any]:
    resolved = _resolve_model_dir(model_dir)
    _STATE.update({"model": None, "tokenizer": None, "model_dir": resolved, "error": None})
    artifact_error = _local_artifacts_complete(resolved)
    if artifact_error:
        _STATE["error"] = artifact_error
        return _result("warn", error=artifact_error)
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        target_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(str(resolved), local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(str(resolved), local_files_only=True)
        model.to(target_device)
        model.eval()
        _STATE.update({"model": model, "tokenizer": tokenizer, "model_dir": resolved, "error": None, "device": target_device})
        return _result("success")
    except Exception as exc:
        message = f"failed to load local pretrained fine-tuned model: {type(exc).__name__}: {exc}"
        _STATE["error"] = message
        return _result("fail", error=message)


def generate_text(prompt: str, max_new_tokens: int = 256) -> Dict[str, Any]:
    if _STATE["model"] is None or _STATE["tokenizer"] is None:
        load_state = load_model()
        if load_state["status"] != "success":
            return _result(load_state["status"], prompt=prompt, error=load_state["error"])
    try:
        import torch

        tokenizer = _STATE["tokenizer"]
        model = _STATE["model"]
        inputs = tokenizer(prompt, return_tensors="pt")
        device = getattr(model, "device", None) or _STATE.get("device", "cpu")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return _result("success", prompt=prompt, raw_output=raw)
    except Exception as exc:
        message = f"generation failed: {type(exc).__name__}: {exc}"
        return _result("fail", prompt=prompt, error=message)


def generate_tutor_task(
    task_type: str,
    domain: str,
    concept_name: str,
    difficulty: str = "easy",
    teaching_view: Optional[str] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = (
        f"Create a {difficulty} {task_type} for the domain {domain} about {concept_name}. "
        "Return a structured, frontend-renderable tutor response with labels."
    )
    if teaching_view:
        prompt += f" Teaching view: {teaching_view}."
    if context:
        prompt += f" Context: {context}"
    result = generate_text(prompt)
    result.update(
        {
            "task_type": task_type,
            "domain": domain,
            "concept_name": concept_name,
            "difficulty": difficulty,
        }
    )
    return result

