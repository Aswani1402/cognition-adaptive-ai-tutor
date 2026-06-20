import json
from pathlib import Path

from scripts.structured_generation_common import ROOT_DIR


OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "cleanup_candidates_report.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "cleanup_candidates_report.md"
PROTECTED_PREFIXES = (
    "models",
    "training_data",
    "outputs/final_reports",
    "outputs/model_generated/structured_model_generated_core",
    "outputs/evaluation",
    "outputs/artifacts",
    "outputs/question_bank",
    "src",
    "data",
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def protected(path: Path) -> bool:
    value = rel(path)
    return any(value == prefix or value.startswith(prefix + "/") for prefix in PROTECTED_PREFIXES)


def main() -> None:
    categories = {
        "temporary_debug_files": [],
        "duplicate_reports": [],
        "obsolete_cursor_generated_files": [],
        "old_failed_experiment_outputs": [],
        "cache_files": [],
        "pycache_files": [],
        "accidental_large_temporary_outputs": [],
    }
    for path in ROOT_DIR.rglob("*"):
        if path.is_dir():
            if path.name == "__pycache__":
                categories["pycache_files"].append(rel(path))
            continue
        if protected(path):
            continue
        name = path.name.lower()
        if name.endswith((".tmp", ".bak", ".log")):
            categories["temporary_debug_files"].append(rel(path))
        if name.endswith(".pyc"):
            categories["cache_files"].append(rel(path))
        if "cursor" in name or "true_model" in name:
            categories["obsolete_cursor_generated_files"].append(rel(path))
        if "failed" in name or "experiment" in name:
            categories["old_failed_experiment_outputs"].append(rel(path))
        try:
            if path.stat().st_size > 50 * 1024 * 1024 and name.endswith((".txt", ".jsonl", ".log")):
                categories["accidental_large_temporary_outputs"].append(rel(path))
        except OSError:
            pass
    report = {"categories": categories, "total_candidates": sum(len(v) for v in categories.values()), "deletion_performed": False}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Cleanup Candidates Report", "", f"- total_candidates: {report['total_candidates']}", "- deletion_performed: False"]
    for category, paths in categories.items():
        lines.extend(["", f"## {category}"])
        lines.extend(f"- {path}" for path in paths) if paths else lines.append("- None")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cleanup_candidates: {report['total_candidates']}")
    print(f"report_path: {OUT_MD}")


if __name__ == "__main__":
    main()
