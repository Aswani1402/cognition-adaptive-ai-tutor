import json
from pathlib import Path

from scripts.structured_generation_common import ROOT_DIR


OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "safe_cleanup_report.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "safe_cleanup_report.md"
PROTECTED_DIRS = {"models", "training_data", "outputs", "src", "data"}


def is_protected(path: Path) -> bool:
    rel = path.relative_to(ROOT_DIR).parts
    return bool(rel and rel[0] in PROTECTED_DIRS and path.suffix not in {".pyc", ".tmp"})


def main() -> None:
    delete_files = []
    delete_dirs = []
    for path in ROOT_DIR.rglob("*"):
        if path.is_file() and (path.suffix in {".pyc", ".tmp"}):
            delete_files.append(path)
        elif path.is_dir() and path.name == "__pycache__":
            delete_dirs.append(path)
    for path in sorted(ROOT_DIR.rglob("*"), reverse=True):
        if path.is_dir() and path not in delete_dirs:
            try:
                if not any(path.iterdir()) and not is_protected(path):
                    delete_dirs.append(path)
            except OSError:
                pass
    deletion_list = [str(path.relative_to(ROOT_DIR)) for path in delete_files + delete_dirs]
    print("deletion_list:")
    for item in deletion_list:
        print(item)
    deleted = []
    errors = []
    for path in delete_files:
        try:
            path.unlink()
            deleted.append(str(path.relative_to(ROOT_DIR)))
        except OSError as exc:
            errors.append({"path": str(path), "error": str(exc)})
    for path in sorted(delete_dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            if path.exists() and path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file() and child.suffix not in {".pyc", ".tmp"}:
                        raise OSError("directory contains protected non-junk file")
                for child in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                path.rmdir()
                deleted.append(str(path.relative_to(ROOT_DIR)))
        except OSError as exc:
            errors.append({"path": str(path), "error": str(exc)})
    report = {"files_deleted_count": len(deleted), "deleted": deleted, "errors": errors}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Safe Cleanup Report\n\n"
        f"- files_deleted_count: {len(deleted)}\n"
        f"- errors: {len(errors)}\n\n"
        + "\n".join(f"- {item}" for item in deleted)
        + "\n",
        encoding="utf-8",
    )
    print(f"files_deleted_count: {len(deleted)}")
    print(f"errors: {len(errors)}")


if __name__ == "__main__":
    main()
