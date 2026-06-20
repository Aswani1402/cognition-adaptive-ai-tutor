from __future__ import annotations

from tutor.rag.rag_reranker import rerank_chunks_local
from tutor.rag.rag_semantic_support_checker import RAGSemanticSupportChecker


def sample_chunks() -> list[dict]:
    return [
        {
            "section": "definition",
            "text": "A Python variable is a named reference used to store a value for later use.",
            "score": 0.8,
            "concept_id": "variables",
            "domain": "Python",
        },
        {
            "section": "key_points",
            "text": "Variables make values reusable. Clear variable names improve code readability.",
            "score": 0.75,
            "concept_id": "variables",
            "domain": "Python",
        },
        {
            "section": "examples",
            "text": "Example: score = 10 stores the value 10 using the variable name score.",
            "score": 0.7,
            "concept_id": "variables",
            "domain": "Python",
        },
        {
            "section": "next_concept",
            "text": "Loops repeat a block of code several times.",
            "score": 0.2,
            "concept_id": "loops",
            "domain": "Python",
        },
    ]


def main() -> None:
    checker = RAGSemanticSupportChecker()
    supported = checker.check_support(
        "What is a Python variable?",
        "A Python variable is a named reference that stores a value for later use.",
        sample_chunks(),
    )
    assert supported["status"] == "success"
    assert supported["verdict"] == "supported", supported
    assert supported["safe_to_generate"] is True

    partial = checker.check_support(
        "Why are variables useful?",
        "Variables make values reusable and clear variable names improve code readability, but they also organize program data.",
        sample_chunks()[:2],
    )
    assert partial["verdict"] in {"partially_supported", "supported"}, partial
    assert partial["support_score"] >= 0.45

    unsupported = checker.check_support(
        "What is a Python variable?",
        "A Python variable automatically creates quantum encryption for blockchain synchronization.",
        sample_chunks(),
    )
    assert unsupported["verdict"] in {"unsupported", "partially_supported"}
    assert unsupported["unsupported_terms_count"] > 0
    assert "blockchain" in unsupported["unsupported_terms"] or "synchronization" in unsupported["unsupported_terms"]

    terms = checker.detect_unsupported_terms(
        "Variables enable teleportation_buffer synchronization.",
        sample_chunks(),
    )
    assert terms

    reranked = rerank_chunks_local(
        "variable stores value",
        list(reversed(sample_chunks())),
        top_k=3,
        concept_id="variables",
        domain="Python",
    )
    assert reranked["status"] == "success"
    assert reranked["reranked_chunks"]
    assert reranked["reranked_chunks"][0]["section"] in {"definition", "examples", "key_points"}

    empty = checker.check_support("variables", "A variable stores a value.", [])
    assert empty["status"] == "success"
    assert empty["verdict"] == "unsupported"
    assert empty["safe_to_generate"] is False
    assert empty["fallback_used"] is True

    print("STATUS: success")
    print("MODULE: rag_semantic_support_checker_test")


if __name__ == "__main__":
    main()
