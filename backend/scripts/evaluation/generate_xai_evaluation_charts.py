from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


FINAL_REPORT = Path("evaluation_outputs/json/xai_final_explanation_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/xai_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/xai_visualization_report.md")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_final_report() -> dict:
    if not FINAL_REPORT.exists():
        from scripts.evaluation.check_xai_final_explanation_report import build_report, write_reports

        report = build_report()
        write_reports(report)
        return report
    return _load_json(FINAL_REPORT)


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    report = _ensure_final_report()
    dashboard = report.get("dashboard", {})
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    charts = {}

    top_factors = dashboard.get("top_factors", [])
    factor_names = [item.get("factor") for item in top_factors]
    factor_values = [float(item.get("contribution", 0.0)) for item in top_factors]

    path = CHART_DIR / "xai_top_factor_distribution.png"
    plt.figure(figsize=(9, 4.5))
    plt.bar(factor_names, factor_values)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Normalized contribution")
    plt.title("XAI Top Factor Distribution")
    _save(path)
    charts["xai_top_factor_distribution"] = str(path)

    contributions = dashboard.get("factor_contributions", {})
    path = CHART_DIR / "xai_feature_contribution_example.png"
    plt.figure(figsize=(10, 4.5))
    plt.bar(list(contributions.keys()), list(contributions.values()))
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("Normalized contribution")
    plt.title("XAI Feature Contribution Example")
    _save(path)
    charts["xai_feature_contribution_example"] = str(path)

    pressure_keys = ["evaluation_need", "mastery_need", "behaviour_pressure", "revision_pressure", "promotion_block", "mistake_pressure"]
    path = CHART_DIR / "xai_decision_pressure_distribution.png"
    plt.figure(figsize=(9, 4.5))
    plt.bar(pressure_keys, [float(contributions.get(key, 0.0)) for key in pressure_keys])
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Pressure contribution")
    plt.title("XAI Decision Pressure Distribution")
    _save(path)
    charts["xai_decision_pressure_distribution"] = str(path)

    counterfactuals = dashboard.get("counterfactuals", [])
    path = CHART_DIR / "xai_counterfactual_summary.png"
    plt.figure(figsize=(8, 4.5))
    plt.bar(
        [f"CF{i + 1}" for i in range(len(counterfactuals))],
        [1 for _ in counterfactuals],
    )
    plt.ylim(0, 1.2)
    plt.ylabel("Available")
    plt.title("XAI Counterfactual Summary")
    _save(path)
    charts["xai_counterfactual_summary"] = str(path)

    coverage = dashboard.get("evidence_coverage", {}).get("module_coverage", {})
    path = CHART_DIR / "xai_module_evidence_coverage.png"
    plt.figure(figsize=(9, 4.5))
    plt.bar(list(coverage.keys()), [1 if value else 0 for value in coverage.values()])
    plt.xticks(rotation=35, ha="right")
    plt.ylim(0, 1.2)
    plt.ylabel("Evidence present")
    plt.title("XAI Module Evidence Coverage")
    _save(path)
    charts["xai_module_evidence_coverage"] = str(path)

    availability = report.get("dashboard_card_availability", {})
    path = CHART_DIR / "xai_dashboard_card_availability.png"
    plt.figure(figsize=(10, 4.5))
    plt.bar(list(availability.keys()), [1 if value else 0 for value in availability.values()])
    plt.xticks(rotation=35, ha="right")
    plt.ylim(0, 1.2)
    plt.ylabel("Available")
    plt.title("XAI Dashboard Card Availability")
    _save(path)
    charts["xai_dashboard_card_availability"] = str(path)

    visualization = {
        "status": "success" if charts else "warning",
        "module": "xai_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
        "source_report": str(FINAL_REPORT),
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# XAI Visualization Report",
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
    print("MODULE: xai_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
