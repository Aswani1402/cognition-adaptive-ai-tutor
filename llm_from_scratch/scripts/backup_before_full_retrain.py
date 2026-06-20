import json
import shutil
from datetime import datetime, timezone

from src.cognitutor_lm_config import MODEL_CHECKPOINT, ROOT
from src.tokenizer_wrapper import TOKENIZER_MODEL_PATH

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "backup"
BACKUP_DIR = ROOT / "models" / "backups_before_full_retrain"
OUT_JSON = OUT_DIR / "backup_report.json"
OUT_MD = OUT_DIR / "backup_report.md"


def copy_if_exists(path):
    if not path.exists():
        return {"source": str(path), "copied": False, "reason": "missing"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    if dest.exists():
        dest = BACKUP_DIR / f"{path.stem}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{path.suffix}"
    shutil.copy2(path, dest)
    return {"source": str(path), "destination": str(dest), "copied": True}


def main():
    structured_dir = ROOT / "models" / "cognitutor_lm_structured_generation"
    candidates = [
        MODEL_CHECKPOINT,
        TOKENIZER_MODEL_PATH,
        ROOT / "data" / "tokenizer" / "cognitutor.vocab",
        structured_dir / "structured_generation_config.json",
        structured_dir / "cognitutor.model",
        structured_dir / "cognitutor.vocab",
    ]
    copies = [copy_if_exists(path) for path in candidates]
    report = {
        "backup_status": "PASS" if any(c["copied"] for c in copies) else "WARN",
        "backup_dir": str(BACKUP_DIR),
        "backed_up_files": copies,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Backup Before Full Retrain", "", f"- backup_status: {report['backup_status']}", f"- backup_dir: {BACKUP_DIR}", ""]
    lines.extend(f"- copied={c['copied']}: {c['source']} -> {c.get('destination', c.get('reason'))}" for c in copies)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
