from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/rag_semantic_support_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/rag_semantic_support_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/rag_semantic_support_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.evaluation.check_rag_semantic_support_report import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _bar(values: dict, title: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(7, 4.5))
    plt.bar(list(values.keys()), list(values.values()))
    plt.xticks(rotation=25, ha="right")
    plt.title(title)
    plt.ylabel(ylabel)
    _save(path)


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    cases = report.get("case_outputs", [])

    support_path = CHART_DIR / "rag_semantic_support_score_distribution.png"
    verdict_path = CHART_DIR / "rag_semantic_verdict_distribution.png"
    unsupported_path = CHART_DIR / "rag_semantic_unsupported_terms.png"
    similarity_path = CHART_DIR / "rag_semantic_context_similarity.png"
    reranker_path = CHART_DIR / "rag_reranker_section_distribution.png"

    labels = [case.get("case_name", f"case_{idx + 1}") for idx, case in enumerate(cases)]
    support_scores = [float(case.get("support_score", 0.0)) for case in cases]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, support_scores)
    plt.xticks(rotation=25, ha="right")
    plt.ylim(0, 1)
    plt.title("RAG Semantic Support Score Distribution")
    plt.ylabel("Support score")
    _save(support_path)

    verdict_counts = Counter(case.get("verdict", "unknown") for case in cases)
    _bar(dict(verdict_counts), "RAG Semantic Verdict Distribution", "Case count", verdict_path)

    unsupported_counts = {case.get("case_name", f"case_{idx + 1}"): case.get("unsupported_terms_count", 0) for idx, case in enumerate(cases)}
    _bar(unsupported_counts, "RAG Semantic Unsupported Terms", "Unsupported term count", unsupported_path)

    similarity_values = {case.get("case_name", f"case_{idx + 1}"): case.get("context_similarity", 0.0) for idx, case in enumerate(cases)}
    _bar(similarity_values, "RAG Semantic Context Similarity", "Similarity", similarity_path)

    _bar(
        report.get("reranker_top_section_distribution", {}),
        "RAG Reranker Section Distribution",
        "Top chunk count",
        reranker_path,
    )

    visualization = {
        "status": "success",
        "module": "rag_semantic_support_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "rag_semantic_support_score_distribution": str(support_path),
            "rag_semantic_verdict_distribution": str(verdict_path),
            "rag_semantic_unsupported_terms": str(unsupported_path),
            "rag_semantic_context_similarity": str(similarity_path),
            "rag_reranker_section_distribution": str(reranker_path),
        },
        "source_report": str(REPORT_PATH),
    }
    return visualization


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# RAG Semantic Support Visualization Report",
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
    print("MODULE: rag_semantic_support_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
