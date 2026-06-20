from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


CSV_INPUT = Path("evaluation_outputs/csv/multi_user_integrated_evaluation.csv")
JSON_SOURCE = Path("evaluation_outputs/json/multi_user_integrated_evaluation_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/multi_user_evaluation_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/multi_user_evaluation_visualization_report.md")


def _ensure_source() -> None:
    if not CSV_INPUT.exists() or not JSON_SOURCE.exists():
        from scripts.evaluation.run_multi_user_integrated_evaluation import build_report, write_reports

        report = build_report()
        write_reports(report)


def _rows() -> list[dict[str, Any]]:
    _ensure_source()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _hist(values: list[float], title: str, xlabel: str, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.hist(values, bins=min(8, max(1, len(values))))
    plt.xlabel(xlabel)
    plt.ylabel("Learner count")
    plt.title(title)
    _save(path)


def _bar(counter: Counter, title: str, ylabel: str, path: Path) -> None:
    labels = [str(key) for key in counter.keys()]
    values = list(counter.values())
    plt.figure(figsize=(9, 4.5))
    plt.bar(labels, values)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    _save(path)


def generate_charts() -> dict[str, Any]:
    rows = _rows()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}
    successful = [row for row in rows if row.get("pipeline_status") == "success"]

    mastery = [value for row in successful if (value := _safe_float(row.get("KT_mastery"))) is not None]
    path = CHART_DIR / "multi_user_mastery_distribution.png"
    _hist(mastery, "Multi-User Mastery Distribution", "KT mastery", path)
    charts["multi_user_mastery_distribution"] = str(path)

    risks = [value for row in successful if (value := _safe_float(row.get("behaviour_risk"))) is not None]
    path = CHART_DIR / "multi_user_behaviour_risk_distribution.png"
    _hist(risks, "Multi-User Behaviour Risk Distribution", "Behaviour risk", path)
    charts["multi_user_behaviour_risk_distribution"] = str(path)

    path = CHART_DIR / "multi_user_teaching_view_distribution.png"
    _bar(Counter(row.get("selected_teaching_view") or "missing" for row in successful), "Multi-User Teaching View Distribution", "Learner count", path)
    charts["multi_user_teaching_view_distribution"] = str(path)

    path = CHART_DIR / "multi_user_strategy_distribution.png"
    _bar(Counter(row.get("final_strategy") or "missing" for row in successful), "Multi-User Strategy Distribution", "Learner count", path)
    charts["multi_user_strategy_distribution"] = str(path)

    path = CHART_DIR / "multi_user_mistake_type_distribution.png"
    _bar(Counter(row.get("dominant_mistake_type") or "missing" for row in successful), "Multi-User Mistake Type Distribution", "Learner count", path)
    charts["multi_user_mistake_type_distribution"] = str(path)

    rewards = [value for row in successful if (value := _safe_float(row.get("reward_xp_awarded"))) is not None]
    path = CHART_DIR / "multi_user_reward_xp_distribution.png"
    _hist(rewards, "Multi-User Reward XP Distribution", "XP awarded", path)
    charts["multi_user_reward_xp_distribution"] = str(path)

    return {
        "status": "success" if charts else "warning",
        "module": "multi_user_evaluation_charts",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_csv": str(CSV_INPUT),
        "learner_count": len(rows),
        "successful_learner_count": len(successful),
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Multi-User Evaluation Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        f"Learners: {report['learner_count']}",
        f"Successful learners: {report['successful_learner_count']}",
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
    print("MODULE: multi_user_evaluation_charts")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
