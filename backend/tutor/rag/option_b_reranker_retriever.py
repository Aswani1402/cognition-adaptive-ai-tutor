from __future__ import annotations

from typing import Any, Dict, List

from sentence_transformers import CrossEncoder

from tutor.rag.option_a_hybrid_retriever import OptionAHybridRetriever


SECTION_PRIORITY = {
    "definition": 1.00,
    "examples": 0.95,
    "key_points": 0.90,
    "misconceptions": 0.85,
    "real_world_use": 0.80,
    "next_concept": 0.45,
}


class OptionBRerankerRetriever:
    """
    Option B:
    Option A hybrid retrieval + cross-encoder reranking.

    Local. No API.
    Best-quality RAG retriever.
    """

    def __init__(self) -> None:
        self.base_retriever = OptionAHybridRetriever()

        self.reranker_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.reranker = CrossEncoder(self.reranker_model_name)

    def _chunk_text(self, chunk: Dict[str, Any]) -> str:
        return " ".join([
            str(chunk.get("domain", "")),
            str(chunk.get("topic", "")),
            str(chunk.get("section", "")),
            str(chunk.get("content", "")),
        ])

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 15,
    ) -> List[Dict[str, Any]]:

        candidates = self.base_retriever.search(
            query=query,
            top_k=candidate_k,
        )

        pairs = [
            [query, self._chunk_text(candidate)]
            for candidate in candidates
        ]

        rerank_scores = self.reranker.predict(pairs)

        results = []

        for candidate, rerank_score in zip(candidates, rerank_scores):
            item = dict(candidate)

            section = item.get("section", "")
            priority = SECTION_PRIORITY.get(section, 0.70)

            final_score = float(rerank_score) * priority

            item["rerank_score"] = round(float(rerank_score), 4)
            item["section_priority"] = priority
            item["retrieval_score"] = round(final_score, 4)
            item["retriever"] = "option_b_hybrid_cross_encoder"
            item["reranker_model"] = self.reranker_model_name

            results.append(item)

        results.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return results[:top_k]


if __name__ == "__main__":
    retriever = OptionBRerankerRetriever()

    queries = [
        "Python variables store values",
        "SQL primary key foreign key",
        "HTML tags and elements",
        "Git commit repository",
        "arrays index access",
    ]

    for query in queries:
        print("\n" + "=" * 80)
        print("QUERY:", query)

        results = retriever.search(query, top_k=5, candidate_k=15)

        for r in results:
            print("-" * 60)
            print("score:", r["retrieval_score"])
            print("rerank:", r["rerank_score"])
            print("priority:", r["section_priority"])
            print("chunk_id:", r["chunk_id"])
            print("domain:", r["domain"])
            print("topic:", r["topic"])
            print("section:", r["section"])
            print("preview:", r["content"][:180])