from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from tutor.rag.option_c_tfidf_retriever import OptionCTFIDFRetriever


SECTION_MAP = {
    "definition": "definition",
    "examples": "examples",
    "key_points": "key_points",
    "misconceptions": "misconceptions",
    "real_world_use": "real_world_use",
    "next_concept": "next_concept_link",
}


class RAGContextBuilder:
    """
    Final project RAG builder.

    Uses Option C++:
    - no API
    - no pretrained retrieval model
    - TF-IDF + query expansion + custom reranking
    """

    def __init__(self) -> None:
        self.retriever = OptionCTFIDFRetriever()

    def build_context(
        self,
        query: str,
        top_k: int = 8,
        preferred_domain: Optional[str] = None,
    ) -> Dict[str, Any]:

        retrieved_chunks = self.retriever.search(
            query=query,
            top_k=top_k,
            candidate_k=30,
        )

        if preferred_domain:
            preferred = [
                c for c in retrieved_chunks
                if str(c.get("domain", "")).lower() == preferred_domain.lower()
            ]

            others = [
                c for c in retrieved_chunks
                if str(c.get("domain", "")).lower() != preferred_domain.lower()
            ]

            retrieved_chunks = preferred + others

        if not retrieved_chunks:
            return {
                "status": "error",
                "reason": "No RAG chunks found",
                "query": query,
                "retrieved_chunks": [],
            }

        best = retrieved_chunks[0]
        best_concept_id = best.get("content_concept_id", "")
        best_domain = best.get("domain", "")

        retrieved_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk.get("content_concept_id") == best_concept_id
               and chunk.get("domain") == best_domain
        ]

        concept_id = best.get("content_concept_id", "")
        topic = best.get("topic", "")
        domain = best.get("domain", "")
        all_retrieved_chunks = list(retrieved_chunks)
        retrieved_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk.get("content_concept_id") == concept_id
            and chunk.get("domain") == domain
        ]

        grouped_sections: Dict[str, List[str]] = defaultdict(list)

        for chunk in retrieved_chunks:
            section = chunk.get("section", "")
            content = str(chunk.get("content", "")).strip()

            if content:
                grouped_sections[section].append(content)

        concept_resource = {
            "status": "success",
            "source": "option_c_plus_rag",
            "query": query,
            "content_concept_id": concept_id,
            "system_concept_id": None,
            "domain": domain,
            "topic": topic,
            "definition": self._first(grouped_sections.get("definition")),
            "content": self._first(grouped_sections.get("definition")),
            "examples": self._split_lines(
                self._first(grouped_sections.get("examples"))
            ),
            "key_points": self._split_bullets(
                self._first(grouped_sections.get("key_points"))
            ),
            "misconceptions": self._split_bullets(
                self._first(grouped_sections.get("misconceptions"))
            ),
            "real_world_use": self._first(grouped_sections.get("real_world_use")),
            "next_concept_link": self._first(grouped_sections.get("next_concept")),
            "retrieved_chunks": retrieved_chunks,
            "all_retrieved_chunks": all_retrieved_chunks,
            "chunk_count": len(retrieved_chunks),
            "rag_method": "from_scratch_tfidf_query_expansion_custom_rerank",
        }

        return concept_resource

    def _first(self, values: Optional[List[str]]) -> str:
        if not values:
            return ""
        return values[0]

    def _split_bullets(self, text: str) -> List[str]:
        if not text:
            return []

        lines = []
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith("-"):
                clean = clean[1:].strip()
            lines.append(clean)

        return lines

    def _split_lines(self, text: str) -> List[str]:
        if not text:
            return []

        blocks = []
        current = []

        for line in text.splitlines():
            if line.strip().lower().startswith("example") and current:
                blocks.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)

        if current:
            blocks.append("\n".join(current).strip())

        return [b for b in blocks if b]

def build_rag_concept_resource(
    *,
    query: str,
    domain: Optional[str] = None,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    top_k: int = 8,
) -> Dict[str, Any]:
    builder = RAGContextBuilder()

    final_query = query

    if concept_name:
        final_query = f"{domain or ''} {concept_name}".strip()
    elif concept_id:
        final_query = f"{domain or ''} {concept_id} {query}".strip()

    return builder.build_context(
        query=final_query,
        top_k=top_k,
        preferred_domain=domain,
    )


if __name__ == "__main__":
    builder = RAGContextBuilder()

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

        resource = builder.build_context(query=query, top_k=8)

        print("status:", resource.get("status"))
        print("source:", resource.get("source"))
        print("domain:", resource.get("domain"))
        print("concept_id:", resource.get("content_concept_id"))
        print("topic:", resource.get("topic"))
        print("definition_preview:", resource.get("definition", "")[:200])
        print("examples_count:", len(resource.get("examples", [])))
        print("key_points_count:", len(resource.get("key_points", [])))
        print("misconceptions_count:", len(resource.get("misconceptions", [])))
        print("chunk_count:", resource.get("chunk_count"))
