"""
Train XAI surrogate models and write JSON + Markdown reports.

Run from project root:
  python -m scripts.training.xai.train_xai_surrogate_models
"""

from __future__ import annotations

from pathlib import Path
from tutor.xai.xai_surrogate_trainer import (
    XAISurrogateTrainer,
    build_xai_surrogate_markdown,
    save_json,
)

ROOT = Path(__file__).resolve().parents[3]
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "xai_surrogate_model_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "xai_surrogate_model_report.md"
MODEL_DIR = ROOT / "models" / "xai"


def main() -> None:
    trainer = XAISurrogateTrainer()
    report = trainer.train_all_and_report()
    save_json(JSON_REPORT, report)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.write_text(build_xai_surrogate_markdown(report), encoding="utf-8")

    status = report.get("status", "warning")
    print(f"STATUS: {status}")
    print("MODULE: train_xai_surrogate_models")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"MODEL_DIR: {MODEL_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
