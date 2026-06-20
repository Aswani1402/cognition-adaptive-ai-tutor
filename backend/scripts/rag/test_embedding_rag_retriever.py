from __future__ import annotations

import json

from scripts.rag.build_embedding_index import build_embedding_index
from tutor.rag.embedding_rag_retriever import retrieve_context


def main() -> None:
    build_result = build_embedding_index()
    print("BUILD STATUS:", build_result.get("status"))
    if build_result.get("reason"):
        print("BUILD REASON:", build_result.get("reason"))

    tests = [
        {
            "query": "What is a variable in Python?",
            "domain": "Python",
            "concept_name": "Variables",
        },
        {
            "query": "How do select statements work in SQL tables?",
            "domain": "SQL",
        },
        {
            "query": "HTML tags and page elements",
            "domain": "HTML",
        },
        {
            "query": "How do I commit changes in Git?",
            "domain": "Git",
        },
        {
            "query": "What are arrays stacks and queues in data structures?",
            "domain": "Data Structures",
        },
    ]

    failures: list[str] = []

    for test in tests:
        print("\n---")
        output = retrieve_context(
            query=test["query"],
            domain=test.get("domain"),
            concept_name=test.get("concept_name"),
            top_k=3,
        )

        print("QUERY:", test["query"])
        print("DOMAIN:", test.get("domain"))
        print("STATUS:", output.get("status"))
        print("MODE:", output.get("retrieval_mode"))
        if output.get("fallback_reason"):
            print("FALLBACK REASON:", output["fallback_reason"])
        print("CHUNKS:", output.get("chunk_count", 0))

        chunks = output.get("chunks", [])
        if output.get("status") != "success" or not chunks:
            failures.append(test["domain"])
            continue

        for chunk in chunks:
            print(
                f"- score={chunk.get('score')} | "
                f"{chunk.get('domain')} | "
                f"{chunk.get('concept_id')} | "
                f"{chunk.get('concept_name')} | "
                f"{chunk.get('section')}"
            )
            print(" ", str(chunk.get("text", ""))[:180].replace("\n", " "), "...")

    if failures:
        raise SystemExit(f"Embedding RAG retrieval failed for domains: {', '.join(failures)}")

    print("\nAll 5 domain retrieval checks passed.")
    print(json.dumps({"status": "success", "tested_domains": len(tests)}, indent=2))


if __name__ == "__main__":
    main()
