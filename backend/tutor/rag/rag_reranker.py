from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

from tutor.utils.sklearn_safe_loader import safe_joblib_load, safe_model_call


MODEL_PATH = Path("models/rag/rag_reranker_model.pkl")

SECTION_PRIORITY = {
    "definition": 1.0,
    "examples": 0.92,
    "key_points": 0.95,
    "misconceptions": 0.9,
    "real_world_use": 0.65,
    "next_concept": 0.35,
}

STOPWORDS = {"the", "and", "for", "with", "what", "how", "why", "does", "this", "that", "are", "use", "used", "using"}


def _text(chunk: dict[str, Any]) -> str:
    return str(chunk.get("text") or chunk.get("content") or chunk.get("chunk_text") or "").strip()


def _section(chunk: dict[str, Any]) -> str:
    return str(chunk.get("section") or chunk.get("chunk_type") or chunk.get("type") or "").strip().lower()


def _tokens(text: Any) -> set[str]:
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", str(text or "").lower())
    return {token for token in raw if len(token) > 2 and token not in STOPWORDS}


def _overlap(query: str, text: str) -> float:
    q = _tokens(query)
    t = _tokens(text)
    return len(q & t) / max(1, len(q))


class RAGReranker:
    def __init__(self):
        self.model = None
        self.available = False
        self.load()

    def load(self) -> None:
        if not MODEL_PATH.exists():
            return

        loaded = safe_joblib_load(MODEL_PATH)
        self.model = loaded["model"]
        self.metadata = loaded["metadata"]
        self.available = self.model is not None

    def is_available(self) -> bool:
        return self.available

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self.available or not chunks:
            return chunks[:top_k]

        pair_texts = [
            "Query: " + str(query) + "\nChunk: " + str(chunk.get("text", ""))
            for chunk in chunks
        ]

        result = safe_model_call(
            self.model,
            MODEL_PATH,
            lambda: self.model.predict_proba(pair_texts),
        )
        if not result["ok"]:
            self.available = False
            self.metadata = result["metadata"]
            return chunks[:top_k]
        probs = result["value"][:, 1]

        reranked = []
        for chunk, prob in zip(chunks, probs):
            item = dict(chunk)
            item["reranker_score"] = round(float(prob), 4)
            reranked.append(item)

        reranked.sort(key=lambda x: x["reranker_score"], reverse=True)

        return reranked[:top_k]

    def rerank_local(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
        concept_id: str | None = None,
        domain: str | None = None,
    ) -> Dict[str, Any]:
        if not chunks:
            return {
                "status": "success",
                "module": "RAGReranker",
                "method": "section_tfidf_overlap",
                "reranked_chunks": [],
                "top_sections": [],
                "fallback_used": True,
            }
        tfidf_scores = self._tfidf_scores(query, chunks)
        reranked = []
        for idx, chunk in enumerate(chunks):
            item = dict(chunk)
            text = _text(item)
            section_score = SECTION_PRIORITY.get(_section(item), 0.45)
            overlap_score = _overlap(query, text)
            tfidf_score = tfidf_scores[idx] if idx < len(tfidf_scores) else overlap_score
            concept_boost = 0.05 if concept_id and str(item.get("concept_id") or item.get("content_concept_id")) == str(concept_id) else 0.0
            domain_boost = 0.05 if domain and str(item.get("domain") or "").lower() == str(domain).lower() else 0.0
            score = 0.35 * section_score + 0.35 * tfidf_score + 0.20 * overlap_score + concept_boost + domain_boost
            item["rerank_score"] = round(max(0.0, min(1.0, score)), 6)
            item["reranker_score"] = item["rerank_score"]
            reranked.append(item)
        reranked.sort(key=lambda chunk: chunk["rerank_score"], reverse=True)
        top = reranked[:top_k]
        return {
            "status": "success",
            "module": "RAGReranker",
            "method": "section_tfidf_overlap",
            "reranked_chunks": top,
            "top_sections": [str(chunk.get("section") or chunk.get("chunk_type") or "") for chunk in top],
            "fallback_used": False,
        }

    def _tfidf_scores(self, query: str, chunks: List[Dict[str, Any]]) -> list[float]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            corpus = [_text(chunk) for chunk in chunks]
            matrix = TfidfVectorizer(stop_words="english").fit_transform([query, *corpus])
            return cosine_similarity(matrix[0], matrix[1:]).flatten().tolist()
        except Exception:
            return [_overlap(query, _text(chunk)) for chunk in chunks]


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    reranker = RAGReranker()
    return reranker.rerank(query=query, chunks=chunks, top_k=top_k)


def rerank_chunks_local(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    concept_id: str | None = None,
    domain: str | None = None,
) -> Dict[str, Any]:
    return RAGReranker().rerank_local(
        query=query,
        chunks=chunks,
        top_k=top_k,
        concept_id=concept_id,
        domain=domain,
    )
