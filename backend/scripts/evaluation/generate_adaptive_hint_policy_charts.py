from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/adaptive_hint_policy_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/adaptive_hint_policy_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/adaptive_hint_policy_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.test_adaptive_hint_policy import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    report = _ensure_report()
    outputs = report.get("test_outputs", [])
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    type_path = CHART_DIR / "adaptive_hint_type_distribution.png"
    distribution = report.get("hint_type_distribution") or {}
    plt.figure(figsize=(9, 4.5))
    plt.bar(list(distribution.keys()), list(distribution.values()))
    plt.xticks(rotation=30, ha="right")
    plt.title("Adaptive Hint Type Distribution")
    plt.ylabel("Count")
    _save(type_path)

    support_path = CHART_DIR / "adaptive_hint_support_need_distribution.png"
    support_values = [float(item.get("support_need", 0.0)) for item in outputs]
    plt.figure(figsize=(7, 4.5))
    plt.hist(support_values, bins=8, range=(0, 1))
    plt.title("Adaptive Hint Support Need Distribution")
    plt.xlabel("Support need")
    plt.ylabel("Test case count")
    _save(support_path)

    fallback_path = CHART_DIR / "adaptive_hint_fallback_rate.png"
    fallback_count = sum(1 for item in outputs if item.get("fallback_used"))
    non_fallback_count = len(outputs) - fallback_count
    plt.figure(figsize=(5.5, 4.5))
    plt.bar(["fallback", "evidence"], [fallback_count, non_fallback_count])
    plt.title("Adaptive Hint Fallback Rate")
    plt.ylabel("Test case count")
    _save(fallback_path)

    question_path = CHART_DIR / "adaptive_hint_question_type_coverage.png"
    question_counts = Counter(
        ((item.get("evidence") or {}).get("question_type") or "unknown")
        for item in outputs
    )
    plt.figure(figsize=(8, 4.5))
    plt.bar(list(question_counts.keys()), list(question_counts.values()))
    plt.xticks(rotation=30, ha="right")
    plt.title("Adaptive Hint Question Type Coverage")
    plt.ylabel("Test case count")
    _save(question_path)

    visualization = {
        "status": "success",
        "module": "adaptive_hint_policy_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "adaptive_hint_type_distribution": str(type_path),
            "adaptive_hint_support_need_distribution": str(support_path),
            "adaptive_hint_fallback_rate": str(fallback_path),
            "adaptive_hint_question_type_coverage": str(question_path),
        },
        "source_report": str(REPORT_PATH),
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Adaptive Hint Policy Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: adaptive_hint_policy_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
