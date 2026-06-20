from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.test_rag_semantic_support_checker import sample_chunks
from tutor.rag.rag_reranker import rerank_chunks_local
from tutor.rag.rag_semantic_support_checker import RAGSemanticSupportChecker


JSON_REPORT = Path("evaluation_outputs/json/rag_semantic_support_report.json")
MD_REPORT = Path("evaluation_outputs/reports/rag_semantic_support_report.md")


CASES = [
    (
        "supported_variable_definition",
        "What is a variable?",
        "A Python variable is a named reference used to store a value for later use.",
        sample_chunks(),
    ),
    (
        "partial_variable_usefulness",
        "Why are variables useful?",
        "Variables make values reusable and clear variable names improve code readability. They also organize data in a program.",
        sample_chunks()[:2],
    ),
    (
        "unsupported_hallucination",
        "What is a variable?",
        "A variable creates quantum encryption and blockchain synchronization automatically.",
        sample_chunks(),
    ),
    (
        "empty_context",
        "What is a variable?",
        "A variable stores a value.",
        [],
    ),
]


def build_report() -> dict:
    checker = RAGSemanticSupportChecker()
    outputs = []
    for name, query, answer, chunks in CASES:
        result = checker.check_support(query, answer, chunks)
        result["case_name"] = name
        outputs.append(result)
    verdict_counts = Counter(item["verdict"] for item in outputs)
    reranker = rerank_chunks_local("variable stores value", sample_chunks(), top_k=4, concept_id="variables", domain="Python")
    top_sections = Counter(reranker.get("top_sections", []))

    def avg(key: str) -> float:
        return round(sum(float(item.get(key, 0.0)) for item in outputs) / len(outputs), 6)

    report = {
        "status": "success",
        "module": "rag_semantic_support_report",
        "case_count": len(outputs),
        "supported_count": verdict_counts.get("supported", 0),
        "partially_supported_count": verdict_counts.get("partially_supported", 0),
        "unsupported_count": verdict_counts.get("unsupported", 0),
        "average_support_score": avg("support_score"),
        "average_context_similarity": avg("context_similarity"),
        "average_keypoint_coverage": avg("keypoint_coverage"),
        "average_unsupported_terms_count": avg("unsupported_terms_count"),
        "safe_to_generate_rate": round(sum(1 for item in outputs if item["safe_to_generate"]) / len(outputs), 6),
        "case_outputs": outputs,
        "reranker_status": reranker.get("status"),
        "reranker_top_section_distribution": dict(top_sections),
        "reranker_output": reranker,
        "final_report_wording": (
            "The RAG module was extended with a semantic support checker that estimates whether generated tutor "
            "responses are supported by retrieved concept context. It combines local TF-IDF similarity, key-point "
            "coverage, unsupported-term detection, and section-aware evidence scoring to classify responses as "
            "supported, partially supported, or unsupported. This improves grounding transparency without relying "
            "on external APIs."
        ),
        "limitations": [
            "Local TF-IDF and token overlap are transparent but not full natural language inference.",
            "Unsupported term detection is conservative and may flag valid synonyms.",
            "Sentence-transformer support is intentionally not required to avoid remote downloads.",
        ],
    }
    return report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# RAG Semantic Support Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Case count: {report['case_count']}",
        f"- Supported: {report['supported_count']}",
        f"- Partially supported: {report['partially_supported_count']}",
        f"- Unsupported: {report['unsupported_count']}",
        f"- Average support score: {report['average_support_score']}",
        f"- Safe-to-generate rate: {report['safe_to_generate_rate']}",
        f"- Reranker status: {report['reranker_status']}",
        "",
        "## Limitations",
        "",
    ]
    for item in report["limitations"]:
        lines.append(f"- {item}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    assert report["status"] in {"success", "warning"}
    assert report["case_count"] == len(CASES)
    assert report["supported_count"] >= 1
    assert report["unsupported_count"] >= 1
    assert report["reranker_status"] == "success"
    print(f"STATUS: {report['status']}")
    print("MODULE: rag_semantic_support_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
