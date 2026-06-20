from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


CORPUS_PATH = Path("models/rag/rag_corpus.json")


class SimpleRAGRetriever:
    def __init__(self, corpus_path: Path = CORPUS_PATH):
        self.corpus_path = corpus_path
        self.corpus: List[Dict[str, Any]] = []
        self.loaded = False
        self.load()

    def load(self) -> None:
        if not self.corpus_path.exists():
            self.loaded = False
            return

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            self.corpus = json.load(f)

        self.loaded = True

    def is_available(self) -> bool:
        return self.loaded and len(self.corpus) > 0

    def tokenize(self, text: str) -> List[str]:
        text = str(text).lower()
        return re.findall(r"[a-zA-Z0-9_]+", text)

    def score_text(self, query: str, text: str) -> float:
        query_tokens = self.tokenize(query)
        text_tokens = self.tokenize(text)

        if not query_tokens or not text_tokens:
            return 0.0

        q_counter = Counter(query_tokens)
        t_counter = Counter(text_tokens)

        common = set(q_counter.keys()) & set(t_counter.keys())

        score = 0.0
        for token in common:
            score += q_counter[token] * t_counter[token]

        # normalize by text length
        return score / math.sqrt(len(text_tokens))

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "status": "error",
                "reason": "RAG corpus not available",
                "chunks": [],
            }

        results = []

        for chunk in self.corpus:
            if domain and str(chunk.get("domain", "")).lower() != str(domain).lower():
                continue

            if concept_id and str(chunk.get("concept_id", "")) != str(concept_id):
                continue

            if concept_name:
                if str(chunk.get("concept_name", "")).lower() != str(concept_name).lower():
                    continue

            text = chunk.get("text", "")
            section = chunk.get("section", "")
            full_text = f"{chunk.get('concept_name', '')} {section} {text}"

            score = self.score_text(query, full_text)

            if score > 0:
                item = dict(chunk)
                item["score"] = round(score, 4)
                results.append(item)

        results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "status": "success",
            "query": query,
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "top_k": top_k,
            "chunks": results[:top_k],
            "chunk_count": len(results[:top_k]),
        }


def retrieve_context(
    query: str,
    domain: Optional[str] = None,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    retriever = SimpleRAGRetriever()
    return retriever.search(
        query=query,
        domain=domain,
        concept_id=concept_id,
        concept_name=concept_name,
        top_k=top_k,
    )