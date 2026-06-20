from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/semantic_notebook_search_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/semantic_notebook_search_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_notebook_search_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.evaluation.check_semantic_notebook_search_report import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _bar(values: dict, title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.bar(list(values.keys()), list(values.values()))
    plt.xticks(rotation=30, ha="right")
    plt.title(title)
    plt.ylabel(ylabel)
    _save(path)


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    source_path = CHART_DIR / "notebook_search_source_distribution.png"
    result_path = CHART_DIR / "notebook_search_result_count.png"
    score_path = CHART_DIR / "notebook_search_score_distribution.png"
    fallback_path = CHART_DIR / "notebook_search_fallback_rate.png"
    weakness_path = CHART_DIR / "notebook_weakness_summary_distribution.png"

    _bar(report.get("top_source_distribution", {}), "Notebook Search Source Distribution", "Result count", source_path)

    result_counts = {
        item.get("query", f"query_{idx + 1}")[:28]: item.get("result_count", 0)
        for idx, item in enumerate(report.get("query_outputs", []))
    }
    _bar(result_counts, "Notebook Search Result Count", "Result count", result_path)

    scores = report.get("score_values", [])
    plt.figure(figsize=(7, 4.5))
    plt.hist(scores, bins=8, range=(0, 1))
    plt.title("Notebook Search Score Distribution")
    plt.xlabel("Score")
    plt.ylabel("Result count")
    _save(score_path)

    fallback_rate = float(report.get("fallback_rate", 0.0))
    _bar(
        {"tfidf_or_primary": 1.0 - fallback_rate, "fallback": fallback_rate},
        "Notebook Search Fallback Rate",
        "Rate",
        fallback_path,
    )

    summary = report.get("weakness_summary", {})
    weakness_counts = {
        "weak_concepts": len(summary.get("weak_concepts", [])),
        "mistake_types": len(summary.get("dominant_mistake_types", [])),
        "question_types": len(summary.get("weak_question_types", [])),
        "recent_doubts": len(summary.get("recent_doubts", [])),
        "revision_focus": len(summary.get("recommended_revision_focus", [])),
    }
    _bar(weakness_counts, "Notebook Weakness Summary Distribution", "Item count", weakness_path)

    return {
        "status": "success",
        "module": "semantic_notebook_search_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "notebook_search_source_distribution": str(source_path),
            "notebook_search_result_count": str(result_path),
            "notebook_search_score_distribution": str(score_path),
            "notebook_search_fallback_rate": str(fallback_path),
            "notebook_weakness_summary_distribution": str(weakness_path),
        },
        "source_report": str(REPORT_PATH),
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Notebook Search Visualization Report",
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
    print("MODULE: semantic_notebook_search_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
