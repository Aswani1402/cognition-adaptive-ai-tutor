from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "pretrained_runtime_report.json"
REPORT_MD = ROOT / "pretrained_runtime_report.md"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
}

TOKENIZER_FILES = {
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
}

MODEL_WEIGHT_FILES = {
    "model.safetensors",
    "pytorch_model.bin",
}

MODEL_INDEX_FILES = {
    "model.safetensors.index.json",
    "pytorch_model.bin.index.json",
}

ADAPTER_WEIGHT_FILES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
}

DATASET_SUFFIXES = {
    ".json",
    ".jsonl",
    ".csv",
    ".parquet",
    ".txt",
}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def iter_dirs(root: Path = ROOT):
    for current, dirs, _files in root.walk():
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS
        ]
        yield current


def iter_files(root: Path = ROOT):
    for current, dirs, files in root.walk():
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS
        ]
        for filename in files:
            yield current / filename


def directory_files(path: Path) -> set[str]:
    if not path.exists() or not path.is_dir():
        return set()
    return {
        child.name
        for child in path.iterdir()
        if child.is_file()
    }


def has_adapter_artifacts(path: Path) -> bool:
    files = directory_files(path)
    return "adapter_config.json" in files and bool(files & ADAPTER_WEIGHT_FILES)


def has_tokenizer_artifacts(path: Path) -> bool:
    files = directory_files(path)
    return "tokenizer_config.json" in files and bool(
        files & {"tokenizer.json", "tokenizer.model", "vocab.json"}
    )


def has_model_weight_artifacts(path: Path) -> bool:
    files = directory_files(path)
    if files & MODEL_WEIGHT_FILES or files & MODEL_INDEX_FILES:
        return True
    return any(
        name.startswith("model-") and name.endswith(".safetensors")
        for name in files
    ) or any(
        name.startswith("pytorch_model-") and name.endswith(".bin")
        for name in files
    )


def is_full_model_folder(path: Path) -> bool:
    files = directory_files(path)
    return (
        "config.json" in files
        and has_tokenizer_artifacts(path)
        and has_model_weight_artifacts(path)
    )


def load_adapter_base_name(path: Path) -> str | None:
    config_path = path / "adapter_config.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    value = data.get("base_model_name_or_path")
    return str(value) if value else None


def describe_dir(path: Path) -> dict[str, Any]:
    files = sorted(directory_files(path))
    return {
        "path": relative(path),
        "files": files,
    }


def inspect_project(write_report: bool = True) -> dict[str, Any]:
    adapter_folders: list[dict[str, Any]] = []
    checkpoint_folders: list[dict[str, Any]] = []
    full_model_folders: list[dict[str, Any]] = []
    merged_model_folders: list[dict[str, Any]] = []

    for directory in iter_dirs():
        name = directory.name.lower()
        if has_adapter_artifacts(directory):
            adapter_folders.append(
                {
                    **describe_dir(directory),
                    "base_model_name_or_path": load_adapter_base_name(directory),
                }
            )
        if name.startswith("checkpoint"):
            checkpoint_folders.append(describe_dir(directory))
        if is_full_model_folder(directory):
            item = describe_dir(directory)
            full_model_folders.append(item)
            if "merged" in relative(directory).lower():
                merged_model_folders.append(item)

    inference_scripts = []
    requirements_files = []
    loader_files = []
    dataset_files = []

    for file_path in iter_files():
        rel = relative(file_path)
        lowered = rel.lower()
        if file_path.suffix == ".py" and any(
            token in lowered
            for token in ("generate", "inference", "model_loader", "pretrained")
        ):
            inference_scripts.append(rel)
        if file_path.name.lower().startswith("requirements") or file_path.name in {
            "pyproject.toml",
            "setup.py",
        }:
            requirements_files.append(rel)
        if file_path.name in {"model_loader.py", "pretrained_generator.py"}:
            loader_files.append(rel)
        if "training_data/" in lowered and file_path.suffix.lower() in DATASET_SUFFIXES:
            dataset_files.append(rel)

    runnable = bool(full_model_folders)
    reason = None if runnable else "no_complete_local_base_or_merged_model_detected"

    report = {
        "status": "success" if runnable else "warning",
        "module": "inspect_pretrained_finetune",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "folder_exists": ROOT.exists(),
        "lora_adapter_folders": sorted(adapter_folders, key=lambda item: item["path"]),
        "checkpoint_folders": sorted(checkpoint_folders, key=lambda item: item["path"]),
        "full_local_base_model_folders": sorted(
            full_model_folders,
            key=lambda item: item["path"],
        ),
        "merged_model_folders": sorted(
            merged_model_folders,
            key=lambda item: item["path"],
        ),
        "inference_scripts": sorted(inference_scripts),
        "requirements_files": sorted(requirements_files),
        "model_loader_files": sorted(loader_files),
        "dataset_files": sorted(dataset_files),
        "inference_runnable": runnable,
        "reason": reason,
        "required_files_for_base_model": [
            "config.json",
            "tokenizer.json or tokenizer.model",
            "tokenizer_config.json",
            "model.safetensors or pytorch_model.bin",
        ],
        "next_step": (
            "Place the matching base model folder locally and set "
            "base_model_path in pretrained_inference_config.json, or create a "
            "merged full model folder at merged_model_path."
            if not runnable
            else "Use scripts/run_pretrained_local_inference.py for local comparison."
        ),
    }

    if write_report:
        write_reports(report)

    return report


def render_markdown(report: dict[str, Any]) -> str:
    adapter_lines = [
        f"- `{item['path']}`"
        + (
            f" (base: `{item['base_model_name_or_path']}`)"
            if item.get("base_model_name_or_path")
            else ""
        )
        for item in report["lora_adapter_folders"]
    ] or ["- None detected"]

    base_lines = [
        f"- `{item['path']}`"
        for item in report["full_local_base_model_folders"]
    ] or ["- None detected"]

    merged_lines = [
        f"- `{item['path']}`"
        for item in report["merged_model_folders"]
    ] or ["- None detected"]

    script_lines = [
        f"- `{item}`"
        for item in report["inference_scripts"]
    ] or ["- None detected"]

    dataset_lines = [
        f"- `{item}`"
        for item in report["dataset_files"]
    ] or ["- None detected"]

    required_lines = [
        f"- `{item}`"
        for item in report["required_files_for_base_model"]
    ]

    if report["inference_runnable"]:
        runnable_text = (
            "Runnable status: available. A complete local model folder was "
            "detected, so Pretrained can be tested without external downloads."
        )
        missing_text = "No required runtime artifact is currently missing."
        comparison_text = "Comparison readiness: ready for local subprocess comparison."
    else:
        runnable_text = (
            "Runnable status: unavailable. Pretrained's fine-tuned LLM folder "
            "contains LoRA adapter checkpoints and inference-related scripts, "
            "but no complete local base model or merged model folder was "
            "detected. Since external downloads are disabled, the model cannot "
            "be safely run for local comparison yet. To enable runtime "
            "comparison, the matching base model must be placed locally and "
            "configured in pretrained_inference_config.json, or the LoRA adapter "
            "must be merged into a full local model artifact."
        )
        missing_text = (
            "What is missing: a complete matching local base model folder or "
            "merged model folder containing the required files below."
        )
        comparison_text = (
            "Comparison readiness: pending. Backend comparison should mark "
            "Pretrained as unavailable until available=true is returned by the "
            "local inference script."
        )

    return "\n".join(
        [
            "# Pretrained Runtime Report",
            "",
            f"Generated UTC: `{report['generated_at_utc']}`",
            f"Project root: `{report['project_root']}`",
            f"Inspection status: `{report['status']}`",
            "",
            "## Pretrained folder structure summary",
            "",
            f"- Folder exists: `{report['folder_exists']}`",
            f"- LoRA adapter folders: `{len(report['lora_adapter_folders'])}`",
            f"- Checkpoint folders: `{len(report['checkpoint_folders'])}`",
            f"- Full local model folders: `{len(report['full_local_base_model_folders'])}`",
            f"- Merged model folders: `{len(report['merged_model_folders'])}`",
            "",
            "## Adapter artifacts found",
            "",
            *adapter_lines,
            "",
            "## Base model status",
            "",
            *base_lines,
            "",
            "## Merged model status",
            "",
            *merged_lines,
            "",
            "## Inference script status",
            "",
            *script_lines,
            "",
            "## Dataset files",
            "",
            *dataset_lines,
            "",
            "## Runnable status",
            "",
            runnable_text,
            "",
            "## What is missing",
            "",
            missing_text,
            "",
            "Required local model files:",
            "",
            *required_lines,
            "",
            "## Exact instructions for making it runnable",
            "",
            "1. Place the matching base model folder inside this project or another local path.",
            "2. Set `base_model_path` in `pretrained_inference_config.json` to that local folder.",
            "3. Keep `local_files_only` set to `true`.",
            "4. Run `python -m scripts.merge_lora_if_base_available` to create a merged model, or run `python -m scripts.run_pretrained_local_inference` to load base plus adapter directly.",
            "",
            "## Comparison readiness",
            "",
            comparison_text,
            "",
            "## For main backend comparison",
            "",
            "- If `available=true`, backend connector can call `scripts/run_pretrained_local_inference.py` through subprocess.",
            "- If `available=false`, backend comparison should mark Pretrained as unavailable/pending.",
            "",
        ]
    )


def write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    report = inspect_project(write_report=True)
    print(f"STATUS: {report['status']}")
    print("MODULE: inspect_pretrained_finetune")
    print(f"REPORT_MD: {REPORT_MD.name}")
    print(f"REPORT_JSON: {REPORT_JSON.name}")


if __name__ == "__main__":
    main()
