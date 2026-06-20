import csv
import importlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
COGNITUTOR_ROOT = Path(r"C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\CogniTutor_LM_from_scratch")
BACKEND_ROOT = Path(r"C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\cognition_adaptive_AI_tutor")


def rel(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_md(path: Path, title: str, sections: Dict[str, Any]) -> None:
    ensure_parent(path)
    lines = [f"# {title}", ""]
    for heading, body in sections.items():
        lines.extend([f"## {heading}", ""])
        if isinstance(body, list):
            if body:
                lines.extend(f"- {item}" for item in body)
            else:
                lines.append("- None found")
        elif isinstance(body, dict):
            for key, value in body.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(str(body))
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    ensure_parent(path)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def iter_files(root: Path, include_venv: bool = False) -> Iterable[Path]:
    skip = {".git", "__pycache__", ".pytest_cache"}
    if not include_venv:
        skip.update({".venv", "venv", "env", "site-packages"})
    for path in root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.is_file():
            yield path


def classify_files(root: Path) -> Dict[str, List[str]]:
    files = list(iter_files(root))
    def by_suffix(*suffixes: str) -> List[str]:
        return sorted(rel(p, root) for p in files if p.suffix.lower() in suffixes)

    names = {
        "python_files": by_suffix(".py"),
        "notebooks": by_suffix(".ipynb"),
        "config_files": sorted(rel(p, root) for p in files if p.suffix.lower() in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}),
        "dataset_files": sorted(rel(p, root) for p in files if p.suffix.lower() in {".jsonl", ".csv", ".db", ".sqlite", ".parquet"}),
        "tokenizer_files": sorted(rel(p, root) for p in files if p.name in {"tokenizer.json", "tokenizer.model", "tokenizer_config.json", "special_tokens_map.json", "vocab.json", "merges.txt", "added_tokens.json"}),
        "checkpoint_model_files": sorted(rel(p, root) for p in files if p.name in {"pytorch_model.bin", "model.safetensors", "adapter_model.bin", "adapter_model.safetensors", "model.pt", "training_args.bin", "trainer_state.json", "optimizer.pt", "scheduler.pt"}),
        "requirements_files": sorted(rel(p, root) for p in files if p.name.lower() in {"requirements.txt", "pyproject.toml", "environment.yml", "setup.py", "setup.cfg"}),
        "readme_report_files": sorted(rel(p, root) for p in files if p.suffix.lower() in {".md", ".rst", ".txt"}),
    }
    py_files = [Path(item) for item in names["python_files"]]
    names["train_scripts"] = sorted(str(p).replace("\\", "/") for p in py_files if re.search(r"train|finetune|lora", p.name, re.I))
    names["inference_generation_scripts"] = sorted(str(p).replace("\\", "/") for p in py_files if re.search(r"generate|infer|runtime|loader", p.name, re.I))
    names["evaluation_scripts"] = sorted(str(p).replace("\\", "/") for p in py_files if re.search(r"eval|valid|test|compare", p.name, re.I))
    return names


def import_available(module: str) -> Dict[str, Any]:
    spec = importlib.util.find_spec(module)
    if spec is None:
        return {"available": False, "error": "module spec not found"}
    try:
        imported = importlib.import_module(module)
        return {"available": True, "version": getattr(imported, "__version__", None), "error": None}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def status_from_bool(pass_condition: bool, warn_condition: bool = False) -> str:
    if pass_condition:
        return "PASS"
    if warn_condition:
        return "WARN"
    return "FAIL"
