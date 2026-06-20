import json
from typing import Any, Dict, List

from src.cognitutor_lm_api_service import ask_doubt_and_get_answer, get_website_session_packet
from src.cognitutor_lm_config import ROOT
from src.rag_grounding_validator import validate_rag_grounding


OUT_JSON = ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "rag_cognitutor_connection_test.md"


CASES = [
    ("Python", "Variables", "P1"),
    ("SQL", "JOIN", "S4"),
    ("Data Structures", "Trees", "D5"),
    ("HTML", "Forms", "H5"),
    ("Git", "Branches", "G4"),
]


def context_ok(result: Dict[str, Any]) -> bool:
    chunks = result.get("chunks") or []
    return bool(result.get("domain") and (result.get("concept_name") or result.get("concept_id")) and chunks and all(c.get("section") and c.get("text") for c in chunks[:1]))


def main() -> None:
    grounding_report = validate_rag_grounding()
    try:
        from src.rag_connector import RagConnector

        connector = RagConnector()
        rag_import_status = "PASS" if not connector.import_error else "WARN"
        import_reason = connector.import_error
    except Exception as exc:
        connector = None
        rag_import_status = "WARN"
        import_reason = f"RAG connector unavailable or optional: {exc}"

    retrievals: List[Dict[str, Any]] = []
    if connector:
        for domain, concept, cid in CASES:
            result = connector.get_rag_context(concept, concept_id=cid, domain=domain, top_k=5)
            retrievals.append({"domain": domain, "concept": concept, "status": "PASS" if context_ok(result) else "WARN", "result": result})

    packet = get_website_session_packet("Python", "Variables", difficulty="easy", teaching_view="definition_view", use_rag=True)
    doubt = ask_doubt_and_get_answer("Python", "Variables", "Why is 2score invalid?", use_rag=True)
    rag_retrieval_status = "PASS" if retrievals and all(r["status"] == "PASS" for r in retrievals) else "WARN"
    rag_api_packet_status = "PASS" if packet.get("status") == "success" else "FAIL"
    rag_grounding_status = packet.get("rag_grounding_status", "WARN")
    status = "PASS" if rag_import_status == rag_retrieval_status == rag_api_packet_status == rag_grounding_status == "PASS" else ("FAIL" if rag_api_packet_status == "FAIL" else "WARN")
    reason = None if status == "PASS" else (import_reason or "RAG connector unavailable or optional")
    report = {
        "rag_import_status": rag_import_status,
        "rag_retrieval_status": rag_retrieval_status,
        "rag_api_packet_status": rag_api_packet_status,
        "rag_grounding_status": rag_grounding_status,
        "rag_connection_status": status,
        "reason": reason,
        "retrievals": retrievals,
        "grounding_validator": grounding_report,
        "doubt_answer_status": "PASS" if doubt.get("status") == "success" else "WARN",
        "website_packet_metadata": {
            "rag_used": packet.get("rag_used"),
            "rag_context_count": packet.get("rag_context_count"),
            "rag_sections": packet.get("rag_sections"),
        },
        "status": status,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# RAG CogniTutor Connection Test\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items() if k not in {"retrievals", "website_packet_metadata"})
        + "\n",
        encoding="utf-8",
    )
    for key in ["rag_import_status", "rag_retrieval_status", "rag_api_packet_status", "rag_grounding_status", "status"]:
        print(f"{key}: {report[key]}")


if __name__ == "__main__":
    main()
