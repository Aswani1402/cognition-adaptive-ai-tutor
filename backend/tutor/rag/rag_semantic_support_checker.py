from __future__ import annotations

import re
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "be", "by", "can", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "then", "this", "to", "use", "used", "uses", "using",
    "with", "you", "your", "what", "why", "how", "does", "do", "should", "will",
}

IMPORTANT_SECTIONS = {"definition", "examples", "key_points", "misconceptions"}
SECTION_WEIGHTS = {
    "definition": 1.0,
    "examples": 0.9,
    "key_points": 0.95,
    "misconceptions": 0.85,
    "real_world_use": 0.65,
    "next_concept": 0.35,
}


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _chunk_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if not isinstance(chunk, dict):
        return ""
    return _safe_str(
        chunk.get("text")
        or chunk.get("content")
        or chunk.get("chunk_text")
        or chunk.get("definition")
        or chunk.get("reference_text")
    )


def _section(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return "context"
    return _safe_str(chunk.get("section") or chunk.get("chunk_type") or chunk.get("type") or "context").lower()


def _tokens(text: Any) -> list[str]:
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", _safe_str(text).lower())
    return [token for token in raw if len(token) > 2 and token not in STOPWORDS]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class RAGSemanticSupportChecker:
    """Local semantic support estimate for RAG-generated answers."""

    MODULE = "RAGSemanticSupportChecker"

    def check_support(
        self,
        query: str,
        generated_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        chunks = self._normalize_chunks(retrieved_chunks or [])
        if not chunks or not _safe_str(generated_answer):
            return {
                "status": "success",
                "module": self.MODULE,
                "support_score": 0.0,
                "context_similarity": 0.0,
                "keypoint_coverage": 0.0,
                "unsupported_terms_count": len(_tokens(generated_answer)),
                "unsupported_terms": sorted(set(_tokens(generated_answer)))[:20],
                "safe_to_generate": False,
                "verdict": "unsupported",
                "evidence_sections_used": [],
                "fallback_used": True,
            }

        context_similarity = self.compute_context_similarity(generated_answer, chunks)
        keypoint_coverage = self.compute_keypoint_coverage(generated_answer, chunks)
        unsupported_terms = self.detect_unsupported_terms(generated_answer, chunks)
        unsupported_penalty_score = max(0.0, 1.0 - len(unsupported_terms) / 8.0)
        section_support = self._section_support(generated_answer, chunks)

        support_score = (
            0.45 * context_similarity
            + 0.35 * keypoint_coverage
            + 0.20 * unsupported_penalty_score
        )
        support_score = _clamp(0.85 * support_score + 0.15 * section_support)
        verdict = self.make_grounding_verdict(support_score, len(unsupported_terms))
        return {
            "status": "success",
            "module": self.MODULE,
            "support_score": round(support_score, 6),
            "context_similarity": round(context_similarity, 6),
            "keypoint_coverage": round(keypoint_coverage, 6),
            "unsupported_terms_count": len(unsupported_terms),
            "unsupported_terms": unsupported_terms,
            "safe_to_generate": verdict == "supported",
            "verdict": verdict,
            "evidence_sections_used": self._evidence_sections(generated_answer, chunks),
            "fallback_used": False,
        }

    def detect_unsupported_terms(
        self,
        generated_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None,
    ) -> list[str]:
        chunks = self._normalize_chunks(retrieved_chunks or [])
        answer_terms = set(_tokens(generated_answer))
        context_terms = set(_tokens(" ".join(chunk["text"] for chunk in chunks)))
        query_safe_terms = {"python", "code", "program", "value", "values", "learner", "example"}
        unsupported = []
        for term in sorted(answer_terms - context_terms - query_safe_terms):
            if "_" in term or len(term) >= 7 or term.endswith(("tion", "ing", "ment", "able", "ence", "ity")):
                unsupported.append(term)
        return unsupported[:20]

    def compute_keypoint_coverage(
        self,
        generated_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None,
    ) -> float:
        chunks = self._normalize_chunks(retrieved_chunks or [])
        answer_tokens = set(_tokens(generated_answer))
        keypoint_chunks = [
            chunk for chunk in chunks
            if chunk["section"] in {"key_points", "definition", "misconceptions"}
        ]
        if not keypoint_chunks:
            keypoint_chunks = chunks
        chunk_scores = []
        for chunk in keypoint_chunks:
            terms = set(_tokens(chunk["text"]))
            if terms:
                overlap = len(answer_tokens & terms)
                chunk_scores.append(
                    max(
                        overlap / max(1, len(terms)),
                        overlap / max(1, len(answer_tokens)),
                    )
                )
        return _clamp(max(chunk_scores) if chunk_scores else 0.0)

    def compute_context_similarity(
        self,
        generated_answer: str,
        retrieved_chunks: list[dict[str, Any]] | None,
    ) -> float:
        chunks = self._normalize_chunks(retrieved_chunks or [])
        context = " ".join(chunk["text"] for chunk in chunks)
        if not context or not generated_answer:
            return 0.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            matrix = TfidfVectorizer(stop_words="english").fit_transform([generated_answer, context])
            return _clamp(float(cosine_similarity(matrix[0], matrix[1])[0][0]))
        except Exception:
            answer_tokens = set(_tokens(generated_answer))
            context_tokens = set(_tokens(context))
            return _clamp(len(answer_tokens & context_tokens) / max(1, len(answer_tokens | context_tokens)))

    def make_grounding_verdict(self, support_score: float, unsupported_terms_count: int) -> str:
        if support_score >= 0.70 and unsupported_terms_count <= 3:
            return "supported"
        if support_score >= 0.45:
            return "partially_supported"
        return "unsupported"

    def _normalize_chunks(self, chunks: list[Any]) -> list[dict[str, Any]]:
        normalized = []
        for chunk in chunks:
            text = _chunk_text(chunk)
            if not text:
                continue
            item = dict(chunk) if isinstance(chunk, dict) else {}
            item["text"] = text
            item["section"] = _section(chunk)
            normalized.append(item)
        return normalized

    def _section_support(self, generated_answer: str, chunks: list[dict[str, Any]]) -> float:
        answer_tokens = set(_tokens(generated_answer))
        best = 0.0
        for chunk in chunks:
            terms = set(_tokens(chunk["text"]))
            if not terms:
                continue
            overlap = len(answer_tokens & terms) / max(1, len(answer_tokens))
            weighted = overlap * SECTION_WEIGHTS.get(chunk["section"], 0.5)
            best = max(best, weighted)
        return _clamp(best)

    def _evidence_sections(self, generated_answer: str, chunks: list[dict[str, Any]]) -> list[str]:
        answer_tokens = set(_tokens(generated_answer))
        sections = []
        for chunk in chunks:
            if answer_tokens & set(_tokens(chunk["text"])):
                sections.append(chunk["section"])
        return sorted(set(sections))


def check_semantic_support(
    query: str,
    generated_answer: str,
    retrieved_chunks: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    return RAGSemanticSupportChecker().check_support(query, generated_answer, retrieved_chunks)
