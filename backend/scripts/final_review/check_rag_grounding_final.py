from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORT_DIR = ROOT / "evaluation_outputs" / "reports"

CASES = [
    ("Python variables store values", "Python", "Variables", ["variables", "store", "values"]),
    ("SQL primary key foreign key", "SQL", "Database keys", ["primary", "foreign", "key"]),
    ("HTML tags and elements", "HTML", "HTML Tags", ["tags", "elements"]),
    ("Git commit repository", "Git", "Git repository/commit", ["commit", "repository"]),
    ("arrays index access", "Data Structures", "Arrays", ["arrays", "index", "access"]),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def run_case(query: str, expected_domain: str, expected_concept: str, required_terms: list[str]) -> dict[str, Any]:
    try:
        from tutor.rag.rag_context_builder import RAGContextBuilder

        resource = RAGContextBuilder().build_context(query=query, top_k=8)
        chunks = resource.get("retrieved_chunks", []) if isinstance(resource, dict) else []
        first = chunks[0] if chunks else {}
        domain = resource.get("domain") or first.get("domain")
        topic = resource.get("topic") or first.get("topic")
        concept_id = resource.get("content_concept_id") or first.get("content_concept_id")
        sections = sorted({str(chunk.get("section")) for chunk in chunks if chunk.get("section")})
        source_db = first.get("source_db")
        evidence_text = " ".join(
            [str(topic or ""), str(domain or "")]
            + [str(chunk.get("content") or "") for chunk in chunks]
        ).lower()
        covered_terms = [term for term in required_terms if normalize(term) in evidence_text]
        success = normalize(expected_domain) in normalize(domain) and len(covered_terms) == len(required_terms)
        return {
            "query": query,
            "expected_subject_or_concept": f"{expected_domain} / {expected_concept}",
            "retrieved_subject/domain": domain,
            "retrieved_concept_id": concept_id,
            "retrieved_topic": topic,
            "retrieved_sections": sections,
            "source_db": source_db,
            "success": bool(success),
            "notes": (
                f"Matched expected domain and covered terms: {covered_terms}."
                if success
                else f"Domain/topic mismatch or missing terms. Covered terms: {covered_terms}."
            ),
        }
    except Exception as exc:
        return {
            "query": query,
            "expected_subject_or_concept": f"{expected_domain} / {expected_concept}",
            "retrieved_subject/domain": None,
            "retrieved_concept_id": None,
            "retrieved_topic": None,
            "retrieved_sections": [],
            "source_db": None,
            "success": False,
            "notes": f"RAG check failed: {type(exc).__name__}: {exc}",
        }


def write_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Final RAG Grounding Check Report",
        "",
        f"Generated at: `{payload['generated_at']}`",
        "",
        f"- Total cases: `{payload['total_cases']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Failed: `{payload['failed']}`",
        f"- Pass rate: `{payload['pass_rate']}`",
        "",
        "| Query | Expected | Retrieved domain | Retrieved topic | Sections | Success | Notes |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in payload["cases"]:
        lines.append(
            "| {query} | {expected_subject_or_concept} | {domain} | {topic} | {sections} | {success} | {notes} |".format(
                query=item["query"],
                expected_subject_or_concept=item["expected_subject_or_concept"],
                domain=item.get("retrieved_subject/domain"),
                topic=item.get("retrieved_topic"),
                sections=", ".join(item.get("retrieved_sections") or []),
                success=item.get("success"),
                notes=item.get("notes"),
            )
        )
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            "- This check validates local retrieval alignment by domain/topic/sections; it is not a semantic entailment proof.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = [run_case(*case) for case in CASES]
    passed = sum(1 for case in cases if case["success"])
    payload = {
        "status": "success" if passed == len(cases) else "warning",
        "generated_at": now_iso(),
        "total_cases": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "cases": cases,
    }
    json_path = JSON_DIR / "final_rag_grounding_check.json"
    report_path = REPORT_DIR / "final_rag_grounding_check_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(write_report(payload), encoding="utf-8")
    print("FINAL RAG GROUNDING CHECK")
    print(f"status: {payload['status']}")
    print(f"passed: {payload['passed']}/{payload['total_cases']}")
    print(f"json: {json_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
