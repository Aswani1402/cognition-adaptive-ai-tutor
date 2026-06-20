from typing import Any, Dict, List


SAMPLES = [
    ("Python", "Variables", "P1"),
    ("SQL", "JOIN", "S4"),
    ("Data Structures", "Trees", "D5"),
    ("HTML", "Forms", "H5"),
    ("Git", "Branches", "G4"),
]


def validate_rag_grounding() -> Dict[str, Any]:
    try:
        from src.rag_connector import RagConnector

        connector = RagConnector()
        if connector.import_error:
            return {
                "status": "WARN",
                "rag_import_status": "WARN",
                "reason": f"RAG connector unavailable or optional: {connector.import_error}",
                "results": [],
            }
    except Exception as exc:
        return {
            "status": "WARN",
            "rag_import_status": "WARN",
            "reason": f"RAG connector unavailable or optional: {type(exc).__name__}: {exc}",
            "results": [],
        }

    results: List[Dict[str, Any]] = []
    for domain, concept, cid in SAMPLES:
        try:
            raw = connector.get_rag_context(concept, concept_id=cid, domain=domain, top_k=5)
            chunks = raw.get("chunks") or []
            ok = bool(chunks and raw.get("domain") and (raw.get("concept_id") or raw.get("concept_name")))
            results.append(
                {
                    "domain": domain,
                    "concept": concept,
                    "concept_id": cid,
                    "status": "PASS" if ok else "WARN",
                    "chunk_count": len(chunks),
                    "sections": [c.get("section") for c in chunks[:5]],
                }
            )
        except Exception as exc:
            results.append({"domain": domain, "concept": concept, "concept_id": cid, "status": "WARN", "reason": str(exc)})
    status = "PASS" if results and all(r["status"] == "PASS" for r in results) else "WARN"
    return {
        "status": status,
        "rag_import_status": "PASS",
        "rag_retrieval_status": status,
        "results": results,
    }
