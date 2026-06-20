"""
Validate adaptive_path_ranker_report.json and refresh Markdown.

Run: python -m scripts.evaluation.check_adaptive_path_ranker_report
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "adaptive_path_ranker_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "adaptive_path_ranker_report.md"

from scripts.training.path.train_adaptive_path_ranker import (  # noqa: E402
    build_markdown,
    save_json,
    train_and_report,
)


def validate(report: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if report.get("dataset_size", 0) <= 0:
        issues.append("dataset_size")
    if not report.get("feature_names"):
        issues.append("feature_names")
    if report.get("status") not in ("success", "warning"):
        issues.append("status")
    return issues


def main() -> None:
    if not JSON_REPORT.exists():
        save_json(JSON_REPORT, train_and_report())
    report = json.loads(JSON_REPORT.read_text(encoding="utf-8"))
    issues = validate(report)
    if issues:
        report["status"] = "warning"
        for msg in issues:
            tag = f"Report validation: {msg}"
            if tag not in (report.get("limitations") or []):
                report.setdefault("limitations", []).append(tag)
        save_json(JSON_REPORT, report)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.write_text(build_markdown(report), encoding="utf-8")
    status = "success" if not issues else "warning"
    print(f"STATUS: {status}")
    print("MODULE: adaptive_path_ranker_report")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
