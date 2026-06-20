"""Generate final RAG evaluation charts from existing report JSON files."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


JSON_DIR = Path("evaluation_outputs/json")
REPORT_DIR = Path("evaluation_outputs/reports")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = JSON_DIR / "rag_visualization_report.json"
MD_REPORT = REPORT_DIR / "rag_visualization_report.md"


def load_json(name: str) -> dict[str, Any]:
    path = JSON_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path) -> bool:
    if not labels or not values:
        return False
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=25)
    ax.set_ylim(0, max(1.0, max(values) * 1.15))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def save_hist(values: list[float], title: str, xlabel: str, path: Path) -> bool:
    if not values:
        return False
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(values, bins=min(8, max(3, len(values))))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    retrieval = load_json("rag_retrieval_comparison_report.json")
    grounding = load_json("rag_grounding_report.json")
    created: list[str] = []
    warnings: list[str] = []

    method_summaries = retrieval.get("method_summaries") or []
    methods = [row.get("method", "unknown") for row in method_summaries]
    quality = [
        float(row.get("precision_at_1") or row.get("mean_reciprocal_rank") or row.get("average_grounding_score") or 0.0)
        for row in method_summaries
    ]
    if save_bar(methods, quality, "RAG Retrieval Quality Comparison", "Quality score", CHART_DIR / "rag_retrieval_quality_comparison.png"):
        created.append("rag_retrieval_quality_comparison.png")
    else:
        warnings.append("RAG retrieval method summaries were unavailable.")

    cases = ((grounding.get("case_status") or {}).get("cases")) or []
    grounding_scores = [float(case.get("grounding_score", 0.0) or 0.0) for case in cases]
    if save_hist(grounding_scores, "RAG Grounding Score Distribution", "Grounding score", CHART_DIR / "rag_grounding_score_distribution.png"):
        created.append("rag_grounding_score_distribution.png")
    else:
        warnings.append("RAG grounding case scores were unavailable.")

    unsupported_counts = [len(case.get("unsupported_terms") or []) for case in cases]
    labels = [case.get("case_id", f"case_{idx + 1}") for idx, case in enumerate(cases)]
    if save_bar(labels, [float(v) for v in unsupported_counts], "RAG Unsupported Terms by Case", "Unsupported term count", CHART_DIR / "rag_unsupported_terms_distribution.png"):
        created.append("rag_unsupported_terms_distribution.png")
    else:
        warnings.append("RAG unsupported-term evidence was unavailable.")

    section_counts: Counter[str] = Counter()
    for case in cases:
        section_counts.update(case.get("evidence_sections") or [])
    if not section_counts:
        sections = ((retrieval.get("availability") or {}).get("sections")) or []
        section_counts.update({section: 1 for section in sections})
    if save_bar(list(section_counts.keys()), [float(v) for v in section_counts.values()], "RAG Source Section Coverage", "Evidence count", CHART_DIR / "rag_source_coverage.png"):
        created.append("rag_source_coverage.png")
    else:
        warnings.append("RAG source coverage evidence was unavailable.")

    status = "success" if len(created) == 4 and not warnings else "warning"
    report = {
        "status": status,
        "module": "rag_visualization_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chart_dir": str(CHART_DIR),
        "charts": created,
        "warnings": warnings,
        "source_reports": [
            "evaluation_outputs/json/rag_retrieval_comparison_report.json",
            "evaluation_outputs/json/rag_grounding_report.json",
        ],
    }
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT.write_text(
        "# RAG Visualization Report\n\n"
        f"- Status: {status}\n"
        f"- Charts generated: {len(created)}\n"
        + "\n".join(f"- `{chart}`" for chart in created)
        + ("\n\n## Warnings\n" + "\n".join(f"- {w}" for w in warnings) if warnings else "\n"),
        encoding="utf-8",
    )

    print(f"STATUS: {status}")
    print("MODULE: rag_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
