from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.test_semantic_notebook_search import TEST_LEARNER_ID, seed_notebook_search_data
from tutor.memory.semantic_notebook_search import SemanticNotebookSearch


JSON_REPORT = Path("evaluation_outputs/json/semantic_notebook_search_report.json")
MD_REPORT = Path("evaluation_outputs/reports/semantic_notebook_search_report.md")

QUERIES = [
    "show my mistakes in variables",
    "what am I weak in?",
    "debug mistakes",
    "revision due",
    "why am I struggling with output prediction?",
    "past doubts about loops",
]


def build_report() -> dict:
    learner_id = seed_notebook_search_data(TEST_LEARNER_ID)
    service = SemanticNotebookSearch()
    index = service.build_search_index(learner_id)
    query_outputs = [service.search(learner_id, query, top_k=5) for query in QUERIES]
    forced_fallback = SemanticNotebookSearch(force_keyword=True).search(learner_id, "debug mistakes", top_k=5)
    summary = service.get_weakness_summary(learner_id)

    result_counts = [item["result_count"] for item in query_outputs]
    fallback_count = sum(1 for item in query_outputs if item["fallback_used"])
    top_sources = Counter()
    scores = []
    for output in query_outputs:
        for result in output["results"]:
            top_sources[result["source_table"]] += 1
            scores.append(result["score"])

    return {
        "status": "success" if index["record_count"] > 0 else "warning",
        "module": "semantic_notebook_search_report",
        "learner_id_tested": learner_id,
        "indexed_record_count": index["record_count"],
        "indexed_source_tables": index["source_tables"],
        "query_count": len(QUERIES),
        "average_result_count": round(sum(result_counts) / len(result_counts), 6),
        "fallback_rate": round(fallback_count / len(query_outputs), 6),
        "top_source_distribution": dict(top_sources),
        "score_values": scores,
        "query_outputs": query_outputs,
        "forced_fallback_method": forced_fallback["method"],
        "weakness_summary_available": summary["status"] == "success",
        "weakness_summary": summary,
        "final_report_wording": (
            "The semantic notebook search module allows the tutor to retrieve learner-specific memory such as "
            "past mistakes, doubts, weak concepts, and revision notes from SQLite. It uses local TF-IDF similarity "
            "with keyword fallback, enabling NotebookLM-style learner memory search without external APIs."
        ),
        "limitations": [
            "Search quality depends on the amount and quality of learner memory stored in SQLite.",
            "TF-IDF is lexical and transparent, not a neural semantic embedding model.",
            "Keyword fallback is used when sklearn is unavailable or explicitly forced.",
        ],
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Semantic Notebook Search Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Learner ID tested: {report['learner_id_tested']}",
        f"- Indexed records: {report['indexed_record_count']}",
        f"- Indexed source tables: {', '.join(report['indexed_source_tables'])}",
        f"- Query count: {report['query_count']}",
        f"- Average result count: {report['average_result_count']}",
        f"- Fallback rate: {report['fallback_rate']}",
        f"- Weakness summary available: {report['weakness_summary_available']}",
        "",
        "## Limitations",
        "",
    ]
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    assert report["status"] in {"success", "warning"}
    assert report["module"] == "semantic_notebook_search_report"
    assert report["indexed_record_count"] > 0
    assert report["query_count"] == len(QUERIES)
    assert report["weakness_summary_available"] is True
    print(f"STATUS: {report['status']}")
    print("MODULE: semantic_notebook_search_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
