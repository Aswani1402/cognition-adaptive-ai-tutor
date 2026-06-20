from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from tutor.rag.rag_chunk_store import RAGChunkStore


SECTION_PRIORITY = {
    "definition": 1.00,
    "examples": 0.95,
    "key_points": 0.92,
    "misconceptions": 0.88,
    "real_world_use": 0.82,
    "next_concept": 0.35,
}

QUERY_EXPANSIONS = {
    "variable": ["variables", "value", "store", "assignment", "name"],
    "variables": ["variable", "value", "store", "assignment", "name"],
    "array": ["arrays", "index", "access", "element", "contiguous"],
    "arrays": ["array", "index", "access", "element", "contiguous"],
    "html": ["tag", "tags", "element", "elements", "webpage"],
    "tag": ["html", "tags", "element", "elements"],
    "tags": ["html", "tag", "element", "elements"],
    "git": ["repository", "commit", "branch", "version", "control"],
    "commit": ["git", "repository", "history", "snapshot"],
    "repository": ["git", "repo", "commit", "history"],
    "sql": ["database", "query", "table", "row", "column"],
    "database": ["sql", "table", "row", "column", "key"],
    "primary": ["key", "database", "table", "unique"],
    "foreign": ["key", "relationship", "table", "database"],
    "key": ["primary", "foreign", "unique", "database"],
    "index": ["indexes", "search", "access", "lookup"],
    "indexes": ["index", "search", "access", "lookup"],
}


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class OptionCTFIDFRetriever:
    """
    Option C++:
    Fully local, from-scratch RAG retriever.

    No API.
    No pretrained embedding.
    No downloaded model.

    Includes:
    - TF-IDF scoring
    - query expansion
    - section-aware ranking
    - concept/topic boosting
    - second-pass custom reranking
    """

    def __init__(self) -> None:
        self.store = RAGChunkStore()
        self.chunks = self.store.load_all_chunks()

        self.documents = [self._chunk_text(chunk) for chunk in self.chunks]
        self.doc_tokens = [tokenize(doc) for doc in self.documents]
        self.idf = self._build_idf()

    def _chunk_text(self, chunk: Dict[str, Any]) -> str:
        return " ".join(
            [
                str(chunk.get("domain", "")),
                str(chunk.get("topic", "")),
                str(chunk.get("section", "")),
                str(chunk.get("content", "")),
            ]
        )

    def _build_idf(self) -> Dict[str, float]:
        total_docs = len(self.doc_tokens)
        df = Counter()

        for tokens in self.doc_tokens:
            for token in set(tokens):
                df[token] += 1

        return {
            token: math.log((total_docs + 1) / (count + 1)) + 1
            for token, count in df.items()
        }

    def _expand_query(self, query_tokens: List[str]) -> List[str]:
        expanded = list(query_tokens)

        for token in query_tokens:
            expanded.extend(QUERY_EXPANSIONS.get(token, []))

        return expanded

    def _tfidf_score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
    ) -> float:
        query_counts = Counter(query_tokens)
        doc_counts = Counter(doc_tokens)

        score = 0.0

        for token, q_count in query_counts.items():
            tf = doc_counts.get(token, 0)
            if tf > 0:
                score += q_count * tf * self.idf.get(token, 0.0)

        return score

    def _topic_boost(
        self,
        original_query_tokens: List[str],
        chunk: Dict[str, Any],
    ) -> float:
        topic_tokens = set(tokenize(str(chunk.get("topic", ""))))
        domain_tokens = set(tokenize(str(chunk.get("domain", ""))))

        query_set = set(original_query_tokens)

        topic_overlap = len(query_set.intersection(topic_tokens))
        domain_overlap = len(query_set.intersection(domain_tokens))

        boost = 0.0

        if topic_overlap > 0:
            boost += 0.18 * topic_overlap

        if domain_overlap > 0:
            boost += 0.12 * domain_overlap

        return boost

    def _exact_phrase_boost(
        self,
        query: str,
        chunk: Dict[str, Any],
    ) -> float:
        query_lower = query.lower()
        topic_lower = str(chunk.get("topic", "")).lower()
        content_lower = str(chunk.get("content", "")).lower()

        boost = 0.0

        if topic_lower and topic_lower in query_lower:
            boost += 0.30

        if query_lower in content_lower:
            boost += 0.20

        return boost

    def _section_boost(self, chunk: Dict[str, Any]) -> float:
        section = str(chunk.get("section", ""))
        return SECTION_PRIORITY.get(section, 0.70)

    def _normalize(self, scores: List[float]) -> List[float]:
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

    def _initial_rank(self, query: str) -> List[Dict[str, Any]]:
        original_tokens = tokenize(query)
        expanded_tokens = self._expand_query(original_tokens)

        raw_tfidf_scores = []

        for doc_tokens in self.doc_tokens:
            raw_tfidf_scores.append(
                self._tfidf_score(expanded_tokens, doc_tokens)
            )

        normalized_tfidf = self._normalize(raw_tfidf_scores)

        results = []

        for index, chunk in enumerate(self.chunks):
            section_weight = self._section_boost(chunk)
            topic_bonus = self._topic_boost(original_tokens, chunk)
            phrase_bonus = self._exact_phrase_boost(query, chunk)

            score = (
                normalized_tfidf[index] * section_weight
                + topic_bonus
                + phrase_bonus
            )

            item = dict(chunk)
            item["tfidf_score"] = round(normalized_tfidf[index], 4)
            item["section_weight"] = section_weight
            item["topic_bonus"] = round(topic_bonus, 4)
            item["phrase_bonus"] = round(phrase_bonus, 4)
            item["initial_score"] = round(score, 4)
            item["retriever"] = "option_c_plus_from_scratch"

            results.append(item)

        results.sort(key=lambda x: x["initial_score"], reverse=True)
        return results

    def _custom_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        query_tokens = set(tokenize(query))

        reranked = []

        for item in candidates:
            content_tokens = set(tokenize(str(item.get("content", ""))))
            topic_tokens = set(tokenize(str(item.get("topic", ""))))

            content_overlap = len(query_tokens.intersection(content_tokens))
            topic_overlap = len(query_tokens.intersection(topic_tokens))

            coverage_bonus = 0.0
            if query_tokens:
                coverage_bonus = content_overlap / len(query_tokens)

            concept_bonus = 0.15 * topic_overlap

            final_score = (
                item["initial_score"]
                + 0.25 * coverage_bonus
                + concept_bonus
            )

            new_item = dict(item)
            new_item["coverage_bonus"] = round(coverage_bonus, 4)
            new_item["concept_bonus"] = round(concept_bonus, 4)
            new_item["retrieval_score"] = round(final_score, 4)

            reranked.append(new_item)

        reranked.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return reranked

    def _deduplicate_by_section(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Avoid one section dominating.
        Prefer diverse teaching sections.
        """
        selected = []
        seen_chunk_ids = set()
        section_counts = defaultdict(int)

        for item in results:
            chunk_id = item["chunk_id"]
            section = item.get("section", "")

            if chunk_id in seen_chunk_ids:
                continue

            if section_counts[section] >= 2:
                continue

            selected.append(item)
            seen_chunk_ids.add(chunk_id)
            section_counts[section] += 1

            if len(selected) >= top_k:
                break

        return selected

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> List[Dict[str, Any]]:
        initial_results = self._initial_rank(query)
        candidates = initial_results[:candidate_k]
        reranked = self._custom_rerank(query, candidates)
        return self._deduplicate_by_section(reranked, top_k=top_k)


if __name__ == "__main__":
    retriever = OptionCTFIDFRetriever()

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
            print("tfidf:", r["tfidf_score"])
            print("section_weight:", r["section_weight"])
            print("topic_bonus:", r["topic_bonus"])
            print("coverage_bonus:", r["coverage_bonus"])
            print("concept_bonus:", r["concept_bonus"])
            print("chunk_id:", r["chunk_id"])
            print("domain:", r["domain"])
            print("topic:", r["topic"])
            print("section:", r["section"])
            print("preview:", r["content"][:180])