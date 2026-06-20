from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.rag.rag_grounding_checker import check_rag_grounding


CHECKER_PATH = Path("tutor/rag/rag_grounding_checker.py")
OUTPUT_JSON = Path("evaluation_outputs/json/rag_grounding_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/rag_grounding_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _context() -> dict[str, Any]:
    return {
        "status": "success",
        "source": "option_c_plus_rag",
        "content_concept_id": "1",
        "topic": "Variables",
        "domain": "Python",
        "definition": "A variable in Python is a named reference used to store a value for later use.",
        "examples": [
            "Example: name = 'Alice' stores the text Alice in the variable name.",
            "Example: total = price * quantity stores a calculated value.",
        ],
        "key_points": [
            "Variables make values reusable.",
            "Clear variable names help code readability.",
        ],
        "misconceptions": [
            "A variable is not a fixed box; it is a name that can refer to a new value after reassignment.",
        ],
        "real_world_use": "Variables can store prices, names, quantities, and totals in real programs.",
        "retrieved_chunks": [
            {
                "content_concept_id": "1",
                "topic": "Variables",
                "domain": "Python",
                "section": "definition",
                "content": "Python variables store values using names such as count, total, or name.",
            }
        ],
    }


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "grounded_matching_context",
            "generated_text": "A Python variable is a named reference that stores a value for later use.",
            "rag_context": _context(),
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "safe",
        },
        {
            "case_id": "no_context",
            "generated_text": "A variable stores a value.",
            "rag_context": None,
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "blocked",
        },
        {
            "case_id": "wrong_concept_domain",
            "generated_text": "A Python variable stores a value for later use.",
            "rag_context": {
                "content_concept_id": "9",
                "topic": "Primary Keys",
                "domain": "SQL",
                "definition": "A primary key uniquely identifies a row in a relational database table.",
            },
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "fallback",
        },
        {
            "case_id": "unsupported_terms",
            "generated_text": (
                "A Python variable stores values and automatically creates quantum_encryption "
                "for distributed blockchain synchronization."
            ),
            "rag_context": _context(),
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "risk_not_low",
        },
        {
            "case_id": "misconception_section",
            "generated_text": "A variable is not a fixed box because it can refer to a new value after reassignment.",
            "rag_context": _context(),
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "section_match",
        },
        {
            "case_id": "examples_section",
            "generated_text": "For example, total = price * quantity stores a calculated value in a variable.",
            "rag_context": _context(),
            "concept_id": "1",
            "concept_name": "Variables",
            "domain": "Python",
            "expectation": "section_match",
        },
    ]


def _case_passed(case: dict[str, Any], output: dict[str, Any]) -> bool:
    expectation = case["expectation"]
    if expectation == "safe":
        return output.get("safe_to_generate") is True and output.get("risk_level") == "low"
    if expectation == "blocked":
        return (
            output.get("safe_to_generate") is False
            and output.get("risk_level") == "high"
            and output.get("fallback_recommended") is True
        )
    if expectation == "fallback":
        return output.get("fallback_recommended") is True and output.get("grounding_score", 1.0) < 0.55
    if expectation == "risk_not_low":
        return output.get("risk_level") != "low" and bool(output.get("unsupported_terms"))
    if expectation == "section_match":
        return output.get("section_match") is True and bool(output.get("evidence_sections"))
    return False


def _static_status() -> dict[str, Any]:
    required_terms = [
        "context_found",
        "concept_match",
        "domain_match",
        "section_match",
        "keyword_overlap_score",
        "grounding_score",
        "safe_to_generate",
        "unsupported_terms",
        "fallback_recommended",
    ]
    report = {
        "status": "warning",
        "checker_exists": CHECKER_PATH.exists(),
        "required_terms": required_terms,
        "missing_terms": [],
    }
    if not CHECKER_PATH.exists():
        report["status"] = "error"
        report["missing_terms"] = required_terms
        return report

    text = CHECKER_PATH.read_text(encoding="utf-8", errors="ignore")
    report["missing_terms"] = [term for term in required_terms if term not in text]
    report["status"] = "success" if not report["missing_terms"] else "warning"
    return report


def _run_cases() -> dict[str, Any]:
    results = []
    failures = []
    for case in _cases():
        output = check_rag_grounding(
            generated_text=case["generated_text"],
            rag_context=case.get("rag_context"),
            concept_id=case.get("concept_id"),
            concept_name=case.get("concept_name"),
            domain=case.get("domain"),
        )
        passed = _case_passed(case, output)
        summary = {
            "case_id": case["case_id"],
            "passed": passed,
            "expectation": case["expectation"],
            "context_found": output.get("context_found"),
            "concept_match": output.get("concept_match"),
            "domain_match": output.get("domain_match"),
            "section_match": output.get("section_match"),
            "keyword_overlap_score": output.get("keyword_overlap_score"),
            "grounding_score": output.get("grounding_score"),
            "safe_to_generate": output.get("safe_to_generate"),
            "risk_level": output.get("risk_level"),
            "unsupported_terms": output.get("unsupported_terms"),
            "evidence_sections": output.get("evidence_sections"),
            "fallback_recommended": output.get("fallback_recommended"),
            "reason": output.get("reason"),
        }
        results.append(summary)
        if not passed:
            failures.append(case["case_id"])

    return {
        "status": "success" if not failures else "warning",
        "case_count": len(results),
        "cases": results,
        "failures": failures,
        "safe_case_count": sum(1 for result in results if result["safe_to_generate"]),
        "fallback_case_count": sum(1 for result in results if result["fallback_recommended"]),
    }


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# RAG Grounding Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Static Check",
        "",
        f"- Checker exists: {report['static_status']['checker_exists']}",
        f"- Missing required terms: {report['static_status']['missing_terms']}",
        "",
        "## Sample Cases",
        "",
        "| Case | Passed | Risk | Safe | Fallback | Grounding | Sections | Unsupported terms |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for case in report["case_status"]["cases"]:
        lines.append(
            "| {case_id} | {passed} | {risk_level} | {safe_to_generate} | {fallback_recommended} | {grounding_score} | {evidence_sections} | {unsupported_terms} |".format(
                **case
            )
        )

    lines.extend(
        [
            "",
            "## Claim",
            "",
            "The system uses a local, no-API, section-aware RAG baseline with grounding validation. "
            "The grounding checker verifies context availability, concept/domain match, section evidence, "
            "keyword overlap, and unsupported terms before generated tutor content is trusted.",
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: rag_grounding_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    static_status = _static_status()
    case_status = _run_cases()
    return {
        "overall_status": _overall_status([static_status, case_status]),
        "module": "rag_grounding_report",
        "generated_at": _now_iso(),
        "static_status": static_status,
        "case_status": case_status,
        "limitations": [
            "This is a transparent baseline checker, not a semantic entailment model.",
            "Unsupported-term detection is conservative and keyword-based.",
            "Option C TF-IDF/query-expansion/custom-reranking remains the active local RAG baseline.",
            "BM25, dense retrieval, and reranker comparisons remain future evaluation work.",
        ],
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")

    print(f"STATUS: {report['overall_status']}")
    print("MODULE: rag_grounding_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
