"""
Validate XAI surrogate model report JSON and refresh Markdown.

Run: python -m scripts.evaluation.check_xai_surrogate_report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "xai_surrogate_model_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "xai_surrogate_model_report.md"

from tutor.xai.xai_surrogate_trainer import (  # noqa: E402
    XAISurrogateTrainer,
    build_xai_surrogate_markdown,
    save_json,
)


def validate(report: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if report.get("dataset_size", 0) <= 0:
        issues.append("dataset_size must be > 0")
    if not report.get("feature_names"):
        issues.append("feature_names must be non-empty")
    if not report.get("targets_trained"):
        issues.append("at least one target must be trained")
    if not report.get("best_model_per_target"):
        issues.append("best_model_per_target missing")
    trained = report.get("targets_trained", [])
    for t in trained:
        tops = report.get("attribution_per_target", {}).get(t, {}).get("top_features")
        if not tops:
            issues.append(f"top features missing for {t}")
    st = report.get("status")
    if st not in ("success", "warning"):
        issues.append("status must be success or warning")
    lims = report.get("limitations")
    if lims is None:
        issues.append("limitations must be present (list)")
    elif not isinstance(lims, list):
        issues.append("limitations must be a list")
    return issues


def main() -> None:
    if not JSON_REPORT.exists():
        trainer = XAISurrogateTrainer()
        report = trainer.train_all_and_report()
        save_json(JSON_REPORT, report)
    else:
        report = json.loads(JSON_REPORT.read_text(encoding="utf-8"))

    issues = validate(report)
    if issues:
        report["status"] = "warning"
        report.setdefault("limitations", [])
        for msg in issues:
            if msg not in report["limitations"]:
                report["limitations"].append(f"Report validation: {msg}")
        save_json(JSON_REPORT, report)

    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.write_text(build_xai_surrogate_markdown(report), encoding="utf-8")

    status = "success" if not issues else "warning"
    print(f"STATUS: {status}")
    print("MODULE: xai_surrogate_model_report")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
