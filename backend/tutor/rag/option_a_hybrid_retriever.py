from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List

import numpy as np

from tutor.rag.rag_chunk_store import RAGChunkStore


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class OptionAHybridRetriever:
    """
    Option A:
    BM25-style keyword retrieval + MiniLM dense semantic retrieval.
    Local. No API.
    """

    def __init__(self) -> None:
        self.store = RAGChunkStore()
        self.chunks = self.store.load_all_chunks()
        self.documents = [self._chunk_text(c) for c in self.chunks]

        self.doc_tokens = [tokenize(doc) for doc in self.documents]
        self.avg_doc_len = sum(len(t) for t in self.doc_tokens) / max(len(self.doc_tokens), 1)
        self.idf = self._build_idf()

        from sentence_transformers import SentenceTransformer

        self.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        self.doc_embeddings = self.embedding_model.encode(
            self.documents,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def _chunk_text(self, chunk: Dict[str, Any]) -> str:
        return " ".join([
            str(chunk.get("domain", "")),
            str(chunk.get("topic", "")),
            str(chunk.get("section", "")),
            str(chunk.get("content", "")),
        ])

    def _build_idf(self) -> Dict[str, float]:
        total_docs = len(self.doc_tokens)
        df = Counter()

        for tokens in self.doc_tokens:
            for token in set(tokens):
                df[token] += 1

        return {
            token: math.log((total_docs - count + 0.5) / (count + 0.5) + 1)
            for token, count in df.items()
        }

    def _bm25_score(self, query: str) -> List[float]:
        query_tokens = tokenize(query)
        scores = []

        k1 = 1.5
        b = 0.75

        for tokens in self.doc_tokens:
            token_counts = Counter(tokens)
            doc_len = len(tokens)
            score = 0.0

            for token in query_tokens:
                if token not in token_counts:
                    continue

                tf = token_counts[token]
                idf = self.idf.get(token, 0.0)

                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / self.avg_doc_len)

                score += idf * (numerator / denominator)

            scores.append(score)

        return scores

    def _dense_score(self, query: str) -> List[float]:
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]

        scores = np.dot(self.doc_embeddings, query_embedding)
        return scores.tolist()

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [0.0 for _ in scores]

        return [
            (score - min_score) / (max_score - min_score)
            for score in scores
        ]

    def search(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.45,
        dense_weight: float = 0.55,
    ) -> List[Dict[str, Any]]:

        bm25_scores = self._bm25_score(query)
        dense_scores = self._dense_score(query)

        bm25_norm = self._normalize_scores(bm25_scores)
        dense_norm = self._normalize_scores(dense_scores)

        results = []

        for index, chunk in enumerate(self.chunks):
            final_score = (
                bm25_weight * bm25_norm[index]
                + dense_weight * dense_norm[index]
            )

            item = dict(chunk)
            item["bm25_score"] = round(bm25_norm[index], 4)
            item["dense_score"] = round(dense_norm[index], 4)
            item["retrieval_score"] = round(final_score, 4)
            item["retriever"] = "option_a_hybrid_minilm"
            item["embedding_model"] = self.embedding_model_name
            results.append(item)

        results.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return results[:top_k]


if __name__ == "__main__":
    retriever = OptionAHybridRetriever()

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

        results = retriever.search(query, top_k=5)

        for r in results:
            print("-" * 60)
            print("score:", r["retrieval_score"])
            print("bm25:", r["bm25_score"], "dense:", r["dense_score"])
            print("chunk_id:", r["chunk_id"])
            print("domain:", r["domain"])
            print("topic:", r["topic"])
            print("section:", r["section"])
            print("preview:", r["content"][:180])