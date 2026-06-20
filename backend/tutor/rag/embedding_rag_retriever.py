from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from tutor.rag.simple_rag_retriever import CORPUS_PATH, SimpleRAGRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models" / "rag"
INDEX_PATH = MODELS_DIR / "rag_embedding_index.json"
EMBEDDINGS_PATH = MODELS_DIR / "rag_embeddings.npy"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _safe_import_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer, None
    except Exception as exc:
        return None, str(exc)


class EmbeddingRAGRetriever:
    def __init__(
        self,
        corpus_path: Path = CORPUS_PATH,
        index_path: Path = INDEX_PATH,
        embeddings_path: Path = EMBEDDINGS_PATH,
    ) -> None:
        self.corpus_path = Path(corpus_path)
        self.index_path = Path(index_path)
        self.embeddings_path = Path(embeddings_path)
        self.fallback = SimpleRAGRetriever(corpus_path=self.corpus_path)
        self.index_metadata: Dict[str, Any] = {}
        self.corpus: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.encoder: Any = None
        self.encoder_error: Optional[str] = None
        self.embedding_ready = False
        self.load()

    def load(self) -> None:
        self.embedding_ready = False
        self.index_metadata = {}
        self.corpus = []
        self.embeddings = None
        self.encoder = None
        self.encoder_error = None

        if not self.index_path.exists():
            self.encoder_error = f"Embedding index not found at {self.index_path}"
            return

        try:
            with self.index_path.open("r", encoding="utf-8") as handle:
                self.index_metadata = json.load(handle)
        except Exception as exc:
            self.encoder_error = f"Failed to load embedding index metadata: {exc}"
            return

        if self.index_metadata.get("status") != "ready":
            self.encoder_error = self.index_metadata.get("reason") or "Embedding index is not ready"
            return

        if not self.embeddings_path.exists():
            self.encoder_error = f"Embedding matrix not found at {self.embeddings_path}"
            return

        try:
            self.embeddings = np.load(self.embeddings_path)
        except Exception as exc:
            self.encoder_error = f"Failed to load embedding matrix: {exc}"
            return

        if self.corpus_path.exists():
            try:
                with self.corpus_path.open("r", encoding="utf-8") as handle:
                    self.corpus = json.load(handle)
            except Exception as exc:
                self.encoder_error = f"Failed to load RAG corpus: {exc}"
                self.corpus = []
                return

        if not self.corpus or self.embeddings is None:
            self.encoder_error = "Embedding corpus or matrix is empty"
            return

        if len(self.corpus) != int(self.embeddings.shape[0]):
            self.encoder_error = (
                f"Corpus/index size mismatch: corpus={len(self.corpus)} "
                f"embeddings={int(self.embeddings.shape[0])}"
            )
            return

        SentenceTransformer, import_error = _safe_import_sentence_transformer()
        if SentenceTransformer is None:
            self.encoder_error = import_error or "sentence-transformers is unavailable"
            return

        model_name = self.index_metadata.get("model_name") or DEFAULT_MODEL_NAME
        try:
            self.encoder = SentenceTransformer(model_name)
        except Exception as exc:
            self.encoder_error = f"Failed to load embedding model '{model_name}': {exc}"
            return

        self.embedding_ready = True

    def is_embedding_available(self) -> bool:
        return self.embedding_ready

    def is_available(self) -> bool:
        return self.is_embedding_available() or self.fallback.is_available()

    def _filter_candidates(
        self,
        domain: Optional[str] = None,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
    ) -> List[int]:
        matches: List[int] = []
        for idx, chunk in enumerate(self.corpus):
            if domain and str(chunk.get("domain", "")).lower() != str(domain).lower():
                continue
            if concept_id and str(chunk.get("concept_id", "")) != str(concept_id):
                continue
            if concept_name and str(chunk.get("concept_name", "")).lower() != str(concept_name).lower():
                continue
            matches.append(idx)
        return matches

    def _encode_query(self, query: str) -> Optional[np.ndarray]:
        if not self.encoder:
            return None

        vector = self.encoder.encode(
            [str(query)],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        if vector is None or len(vector) == 0:
            return None
        return vector[0]

    def _fallback_search(
        self,
        query: str,
        domain: Optional[str] = None,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        result = self.fallback.search(
            query=query,
            domain=domain,
            concept_id=concept_id,
            concept_name=concept_name,
            top_k=top_k,
        )
        result["retrieval_mode"] = "simple_fallback"
        if self.encoder_error:
            result["fallback_reason"] = self.encoder_error
        return result

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        if not self.is_embedding_available():
            return self._fallback_search(
                query=query,
                domain=domain,
                concept_id=concept_id,
                concept_name=concept_name,
                top_k=top_k,
            )

        candidate_indexes = self._filter_candidates(
            domain=domain,
            concept_id=concept_id,
            concept_name=concept_name,
        )

        if not candidate_indexes:
            return {
                "status": "success",
                "query": query,
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                "top_k": top_k,
                "chunks": [],
                "chunk_count": 0,
                "retrieval_mode": "embedding",
            }

        try:
            query_vector = self._encode_query(query)
        except Exception as exc:
            self.encoder_error = f"Failed to encode query: {exc}"
            return self._fallback_search(
                query=query,
                domain=domain,
                concept_id=concept_id,
                concept_name=concept_name,
                top_k=top_k,
            )

        if query_vector is None or self.embeddings is None:
            self.encoder_error = "Query embedding could not be generated"
            return self._fallback_search(
                query=query,
                domain=domain,
                concept_id=concept_id,
                concept_name=concept_name,
                top_k=top_k,
            )

        candidate_matrix = self.embeddings[candidate_indexes]
        scores = candidate_matrix @ query_vector

        ranked_positions = np.argsort(scores)[::-1]
        results: List[Dict[str, Any]] = []

        for position in ranked_positions[:top_k]:
            idx = candidate_indexes[int(position)]
            score = float(scores[int(position)])
            item = dict(self.corpus[idx])
            item["score"] = round(score, 4)
            results.append(item)

        return {
            "status": "success",
            "query": query,
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "top_k": top_k,
            "chunks": results,
            "chunk_count": len(results),
            "retrieval_mode": "embedding",
            "model_name": self.index_metadata.get("model_name"),
        }


def retrieve_context(
    query: str,
    domain: Optional[str] = None,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    retriever = EmbeddingRAGRetriever()
    return retriever.search(
        query=query,
        domain=domain,
        concept_id=concept_id,
        concept_name=concept_name,
        top_k=top_k,
    )
