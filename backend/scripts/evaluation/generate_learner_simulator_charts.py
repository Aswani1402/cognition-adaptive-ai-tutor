from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/learner_simulator_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/learner_simulator_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/learner_simulator_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.evaluation.check_learner_simulator_report import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _bar_chart(values: dict, title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.bar(list(values.keys()), list(values.values()))
    plt.xticks(rotation=25, ha="right")
    plt.title(title)
    plt.ylabel(ylabel)
    _save(path)


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    score_path = CHART_DIR / "learner_simulator_score_by_profile.png"
    confidence_path = CHART_DIR / "learner_simulator_confidence_by_profile.png"
    time_path = CHART_DIR / "learner_simulator_time_by_profile.png"
    hint_path = CHART_DIR / "learner_simulator_hint_usage_by_profile.png"
    mistake_path = CHART_DIR / "learner_simulator_mistake_distribution.png"

    _bar_chart(report["average_score_by_profile"], "Learner Simulator Score by Profile", "Average score", score_path)
    _bar_chart(report["average_confidence_by_profile"], "Learner Simulator Confidence by Profile", "Average confidence", confidence_path)
    _bar_chart(report["average_time_by_profile"], "Learner Simulator Time by Profile", "Average seconds", time_path)
    _bar_chart(report["hint_usage_rate_by_profile"], "Learner Simulator Hint Usage by Profile", "Hint usage rate", hint_path)
    _bar_chart(report["mistake_type_distribution"], "Learner Simulator Mistake Distribution", "Count", mistake_path)

    return {
        "status": "success",
        "module": "learner_simulator_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "learner_simulator_score_by_profile": str(score_path),
            "learner_simulator_confidence_by_profile": str(confidence_path),
            "learner_simulator_time_by_profile": str(time_path),
            "learner_simulator_hint_usage_by_profile": str(hint_path),
            "learner_simulator_mistake_distribution": str(mistake_path),
        },
        "source_report": str(REPORT_PATH),
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Learner Simulator Visualization Report",
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
    print("MODULE: learner_simulator_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
