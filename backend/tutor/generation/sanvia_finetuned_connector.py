from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


SERVICE_NAME = "sanvia_pretrained_finetuned_llm"


class SanviaFinetunedConnector:
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or self.locate_project()
        self._artifacts: Optional[Dict[str, Any]] = None

    def locate_project(self) -> Optional[Path]:
        current = Path(__file__).resolve()
        shared_parent = current.parents[3]
        candidate = shared_parent / "fine_tuing_llm" / "sanvia_finetuning"
        return candidate if candidate.exists() else None

    def inspect_artifacts(self) -> Dict[str, Any]:
        if self._artifacts is not None:
            return self._artifacts

        if self.project_path is None or not self.project_path.exists():
            self._artifacts = {
                "folder_exists": False,
                "project_path": None,
                "detected_files": [],
                "inference_scripts": [],
                "hf_model_dirs": [],
                "lora_adapter_dirs": [],
                "runnable_strategy": None,
                "reason": "sanvia_folder_not_found",
            }
            return self._artifacts

        ignored_parts = {".git", ".venv", "__pycache__"}
        detected: List[str] = []
        inference_scripts: List[str] = []
        hf_model_dirs: List[str] = []
        lora_dirs: List[str] = []
        configs: List[str] = []

        names_of_interest = {
            "README.md",
            "requirements.txt",
            "inference.py",
            "generate.py",
            "predict.py",
            "test_model.py",
            "app.py",
            "train.py",
            "finetune.py",
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "adapter_config.json",
            "adapter_model.safetensors",
            "model.safetensors",
            "pytorch_model.bin",
        }

        for path in self.project_path.rglob("*"):
            if any(part in ignored_parts for part in path.parts):
                continue
            if path.is_file() and (path.name in names_of_interest or path.suffix in {".json", ".yaml", ".yml", ".toml"}):
                rel = path.relative_to(self.project_path).as_posix()
                detected.append(rel)
                if path.name in {"inference.py", "generate.py", "predict.py", "test_model.py", "app.py"}:
                    inference_scripts.append(rel)
                if path.name in {"config.json", "adapter_config.json"}:
                    configs.append(rel)

        for directory in [p for p in self.project_path.rglob("*") if p.is_dir()]:
            if any(part in ignored_parts for part in directory.parts):
                continue
            files = {p.name for p in directory.iterdir() if p.is_file()}
            rel = directory.relative_to(self.project_path).as_posix()
            has_tokenizer = bool({"tokenizer.json", "tokenizer_config.json"} & files)
            has_full_weights = bool({"model.safetensors", "pytorch_model.bin"} & files)
            has_config = "config.json" in files
            has_adapter = bool({"adapter_model.safetensors", "adapter_config.json"} <= files)
            if has_config and has_tokenizer and has_full_weights:
                hf_model_dirs.append(rel)
            if has_adapter:
                lora_dirs.append(rel)

        runnable_strategy = None
        reason = "base_model_path_missing_or_invalid"
        if hf_model_dirs:
            runnable_strategy = "huggingface_local_model"
            reason = None
        elif lora_dirs:
            runnable_strategy = "lora_adapter_requires_local_base_model"
            reason = "base_model_path_missing_or_invalid"
        elif inference_scripts:
            runnable_strategy = "script_probe_only"

        self._artifacts = {
            "folder_exists": True,
            "project_path": str(self.project_path),
            "detected_files": sorted(detected),
            "inference_scripts": sorted(inference_scripts),
            "config_files": sorted(configs),
            "hf_model_dirs": sorted(hf_model_dirs),
            "lora_adapter_dirs": sorted(lora_dirs),
            "runnable_strategy": runnable_strategy,
            "reason": reason,
        }
        return self._artifacts

    def is_available(self) -> Dict[str, Any]:
        artifacts = self.inspect_artifacts()
        if not artifacts.get("folder_exists"):
            return {"available": False, "status": "warning", "reason": artifacts.get("reason"), **artifacts}
        if artifacts.get("hf_model_dirs"):
            return {"available": True, "status": "success", "reason": None, **artifacts}
        if artifacts.get("lora_adapter_dirs"):
            local_base = os.getenv("SANVIA_LOCAL_BASE_MODEL") or os.getenv("TUTOR_BASE_MODEL")
            if local_base and Path(local_base).exists():
                return {"available": True, "status": "success", "reason": None, **artifacts}
            return {
                **artifacts,
                "available": False,
                "status": "warning",
                "reason": "base_model_path_missing_or_invalid",
                "detail": "lora_adapter_base_model_not_available_locally",
            }
        return {"available": False, "status": "warning", "reason": "base_model_path_missing_or_invalid", **artifacts}

    def _response(
        self,
        status: str,
        available: bool,
        task_type: str,
        output: str = "",
        latency_ms: float = 0.0,
        fallback_used: bool = False,
        reason: Optional[str] = None,
        detected_model_path: Optional[str] = None,
        limitations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "service": SERVICE_NAME,
            "available": available,
            "runtime_role": "comparison_only",
            "task_type": task_type,
            "output": output,
            "latency_ms": round(float(latency_ms), 3),
            "fallback_used": fallback_used,
            "reason": reason,
            "detected_model_path": detected_model_path,
            "detected_files": self.inspect_artifacts().get("detected_files", []),
            "limitations": limitations or [],
        }

    def generate(self, prompt: str, task_type: str, concept: Optional[dict] = None, timeout_sec: int = 60) -> Dict[str, Any]:
        started = time.time()
        availability = self.is_available()
        artifacts = self.inspect_artifacts()
        detected_path = None
        if artifacts.get("hf_model_dirs"):
            detected_path = str(self.project_path / artifacts["hf_model_dirs"][0])
        elif artifacts.get("lora_adapter_dirs"):
            detected_path = str(self.project_path / artifacts["lora_adapter_dirs"][0])

        if not availability.get("available"):
            return self._response(
                status="warning",
                available=False,
                task_type=task_type,
                latency_ms=(time.time() - started) * 1000,
                reason="base_model_path_missing_or_invalid",
                detected_model_path=detected_path,
                limitations=[
                    "No external downloads or API calls are allowed.",
                    "LoRA adapters require a base model that is already available locally.",
                    str(availability.get("detail") or availability.get("reason") or ""),
                ],
            )

        if artifacts.get("hf_model_dirs"):
            return self._generate_hf_local(prompt, task_type, Path(detected_path), started)

        return self._generate_via_sanvia_loader(prompt, task_type, concept or {}, timeout_sec, started, detected_path)

    def _generate_hf_local(self, prompt: str, task_type: str, model_path: Path, started: float) -> Dict[str, Any]:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:
            return self._response(
                "warning",
                False,
                task_type,
                latency_ms=(time.time() - started) * 1000,
                reason="transformers_or_torch_missing",
                detected_model_path=str(model_path),
                limitations=[f"{type(exc).__name__}: {exc}"],
            )
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
            model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True)
            model.eval()
            inputs = tokenizer(prompt, return_tensors="pt")
            with torch.no_grad():
                generated = model.generate(**inputs, max_new_tokens=160, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            text = tokenizer.decode(generated[0], skip_special_tokens=True)
            output = text.split(prompt, 1)[-1].strip() if prompt in text else text.strip()
            return self._response("success", True, task_type, output, (time.time() - started) * 1000, False, None, str(model_path))
        except Exception as exc:
            return self._response(
                "error",
                False,
                task_type,
                latency_ms=(time.time() - started) * 1000,
                reason="local_huggingface_generation_failed",
                detected_model_path=str(model_path),
                limitations=[f"{type(exc).__name__}: {exc}"],
            )

    def _generate_via_sanvia_loader(
        self,
        prompt: str,
        task_type: str,
        concept: dict,
        timeout_sec: int,
        started: float,
        detected_model_path: Optional[str],
    ) -> Dict[str, Any]:
        script = (
            "import json, os\n"
            "os.environ['SANVIA_OFFLINE_MODE']='1'\n"
            "from tutor.llm_finetune.pretrained_generator import generate_tutor_output\n"
            f"concept={json.dumps({'concept_name': concept.get('concept_name') or concept.get('name') or 'Unknown Concept'})}\n"
            f"result=generate_tutor_output(concept, 'easy', 'comparison', 'simple', {json.dumps(task_type)})\n"
            "print(json.dumps(result, ensure_ascii=False))\n"
        )
        env = os.environ.copy()
        env["SANVIA_OFFLINE_MODE"] = "1"
        if os.getenv("SANVIA_LOCAL_BASE_MODEL"):
            env["TUTOR_BASE_MODEL"] = os.getenv("SANVIA_LOCAL_BASE_MODEL", "")
        try:
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=str(self.project_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            payload = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "{}"
            data = json.loads(payload)
            output = data.get("output") or ""
            return self._response(
                "success" if output and not data.get("fallback_used") else "warning",
                bool(output),
                task_type,
                output,
                (time.time() - started) * 1000,
                bool(data.get("fallback_used")),
                data.get("generation_status") if not output else None,
                detected_model_path,
                [data.get("error_message")] if data.get("error_message") else [],
            )
        except subprocess.TimeoutExpired:
            return self._response("error", False, task_type, latency_ms=(time.time() - started) * 1000, reason="sanvia_inference_timeout", detected_model_path=detected_model_path)
        except Exception as exc:
            return self._response("error", False, task_type, latency_ms=(time.time() - started) * 1000, reason="sanvia_inference_failed", detected_model_path=detected_model_path, limitations=[f"{type(exc).__name__}: {exc}"])

    def generate_task(self, task_type, concept_name, domain, difficulty, style, context):
        prompt = (
            f"Generate {task_type} tutor content.\n"
            f"Concept: {concept_name}\nDomain: {domain}\nDifficulty: {difficulty}\n"
            f"Teaching style: {style}\nContext: {context}\nOutput:"
        )
        return self.generate(prompt, task_type, {"concept_name": concept_name, "domain": domain}, timeout_sec=60)

    def self_test(self) -> Dict[str, Any]:
        return {
            "inspection": self.inspect_artifacts(),
            "availability": self.is_available(),
            "generation_probe": self.generate_task("explanation", "Python Variables", "Python", "easy", "simple", "Variables store values."),
        }
