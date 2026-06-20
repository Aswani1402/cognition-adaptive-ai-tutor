from __future__ import annotations

import re
from typing import Any


USEFUL_SECTIONS = {
    "definition",
    "examples",
    "key_points",
    "misconceptions",
    "real_world_use",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "later",
    "of",
    "on",
    "or",
    "that",
    "the",
    "then",
    "this",
    "to",
    "use",
    "used",
    "uses",
    "using",
    "with",
    "you",
    "your",
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return {token for token in raw if len(token) > 2 and token not in STOPWORDS}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _chunk_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if not isinstance(chunk, dict):
        return ""
    values = [
        chunk.get("content"),
        chunk.get("chunk_text"),
        chunk.get("text"),
        chunk.get("definition"),
        chunk.get("reference_text"),
    ]
    return "\n".join(_safe_str(value) for value in values if _safe_str(value))


def _chunk_section(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    return _safe_str(chunk.get("section") or chunk.get("chunk_type") or chunk.get("type")).lower()


def _chunk_concept(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    return _safe_str(
        chunk.get("content_concept_id")
        or chunk.get("system_concept_id")
        or chunk.get("concept_id")
    )


def _chunk_concept_name(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    return _safe_str(chunk.get("topic") or chunk.get("concept_name") or chunk.get("concept"))


def _chunk_domain(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    return _safe_str(chunk.get("domain"))


def _normalize_context(rag_context: Any = None, chunks: Any = None) -> dict[str, Any]:
    normalized_chunks: list[dict[str, Any]] = []
    context_meta: dict[str, str] = {}

    if isinstance(rag_context, dict):
        context_meta = {
            "concept_id": _safe_str(
                rag_context.get("content_concept_id")
                or rag_context.get("system_concept_id")
                or rag_context.get("concept_id")
            ),
            "concept_name": _safe_str(
                rag_context.get("topic")
                or rag_context.get("concept_name")
                or rag_context.get("concept")
            ),
            "domain": _safe_str(rag_context.get("domain")),
        }

        for section in USEFUL_SECTIONS:
            value = rag_context.get(section)
            for item in _as_list(value):
                text = _safe_str(item)
                if text:
                    normalized_chunks.append(
                        {
                            "section": section,
                            "text": text,
                            "concept_id": context_meta["concept_id"],
                            "concept_name": context_meta["concept_name"],
                            "domain": context_meta["domain"],
                        }
                    )

        for key in ["retrieved_chunks", "all_retrieved_chunks", "chunks"]:
            for chunk in _as_list(rag_context.get(key)):
                text = _chunk_text(chunk)
                if text:
                    normalized_chunks.append(
                        {
                            "section": _chunk_section(chunk),
                            "text": text,
                            "concept_id": _chunk_concept(chunk) or context_meta["concept_id"],
                            "concept_name": _chunk_concept_name(chunk) or context_meta["concept_name"],
                            "domain": _chunk_domain(chunk) or context_meta["domain"],
                        }
                    )
    elif isinstance(rag_context, str) and rag_context.strip():
        normalized_chunks.append({"section": "context", "text": rag_context, "concept_id": "", "concept_name": "", "domain": ""})
    elif rag_context:
        for chunk in _as_list(rag_context):
            text = _chunk_text(chunk)
            if text:
                normalized_chunks.append(
                    {
                        "section": _chunk_section(chunk),
                        "text": text,
                        "concept_id": _chunk_concept(chunk),
                        "concept_name": _chunk_concept_name(chunk),
                        "domain": _chunk_domain(chunk),
                    }
                )

    for chunk in _as_list(chunks):
        text = _chunk_text(chunk)
        if text:
            normalized_chunks.append(
                {
                    "section": _chunk_section(chunk),
                    "text": text,
                    "concept_id": _chunk_concept(chunk),
                    "concept_name": _chunk_concept_name(chunk),
                    "domain": _chunk_domain(chunk),
                }
            )

    return {
        "chunks": normalized_chunks,
        "context_text": "\n".join(chunk["text"] for chunk in normalized_chunks),
        "context_meta": context_meta,
    }


def _matches_concept(chunks: list[dict[str, Any]], concept_id: str, concept_name: str) -> bool:
    if not chunks:
        return False

    wanted_id = _safe_str(concept_id).lower()
    wanted_name = _safe_str(concept_name).lower()

    if not wanted_id and not wanted_name:
        return True

    for chunk in chunks:
        chunk_id = _safe_str(chunk.get("concept_id")).lower()
        chunk_name = _safe_str(chunk.get("concept_name")).lower()
        text = _safe_str(chunk.get("text")).lower()

        if wanted_id and chunk_id and wanted_id == chunk_id:
            return True
        if wanted_name and (wanted_name == chunk_name or wanted_name in text):
            return True

    return False


def _matches_domain(chunks: list[dict[str, Any]], domain: str) -> bool:
    wanted = _safe_str(domain).lower()
    if not chunks:
        return False
    if not wanted:
        return True

    for chunk in chunks:
        chunk_domain = _safe_str(chunk.get("domain")).lower()
        text = _safe_str(chunk.get("text")).lower()
        if chunk_domain and chunk_domain == wanted:
            return True
        if wanted in text:
            return True

    return False


def _evidence_sections(chunks: list[dict[str, Any]], generated_tokens: set[str]) -> list[str]:
    sections = []
    for chunk in chunks:
        section = _safe_str(chunk.get("section")).lower()
        if section not in USEFUL_SECTIONS:
            continue
        if generated_tokens & _tokens(_safe_str(chunk.get("text"))):
            sections.append(section)
    return sorted(set(sections))


def _unsupported_terms(generated_text: str, context_text: str) -> list[str]:
    generated_tokens = _tokens(generated_text)
    context_tokens = _tokens(context_text)
    unsupported = generated_tokens - context_tokens

    # Keep this transparent and conservative: surface likely claim-bearing
    # terms, not every ordinary word in a learner-facing explanation.
    likely_claim_terms = []
    for term in sorted(unsupported):
        if "_" in term or len(term) >= 8 or term.endswith(("tion", "ing", "ment", "able", "ence")):
            likely_claim_terms.append(term)
    return likely_claim_terms[:20]


def check_rag_grounding(
    *,
    generated_text: str,
    rag_context: Any = None,
    chunks: Any = None,
    concept_id: str | None = None,
    concept_name: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_context(rag_context=rag_context, chunks=chunks)
    normalized_chunks = normalized["chunks"]
    context_text = normalized["context_text"]

    context_found = bool(normalized_chunks and context_text.strip())
    generated_tokens = _tokens(generated_text)
    context_tokens = _tokens(context_text)

    if not context_found:
        return {
            "status": "success",
            "module": "RAGGroundingChecker",
            "context_found": False,
            "concept_match": False,
            "domain_match": False,
            "section_match": False,
            "keyword_overlap_score": 0.0,
            "grounding_score": 0.0,
            "safe_to_generate": False,
            "risk_level": "high",
            "unsupported_terms": sorted(generated_tokens)[:20],
            "evidence_sections": [],
            "fallback_recommended": True,
            "reason": "No RAG context or chunks were found, so generated content should use a fallback.",
        }

    overlap = generated_tokens & context_tokens
    keyword_overlap_score = _clamp(len(overlap) / max(1, len(generated_tokens)))
    concept_match = _matches_concept(normalized_chunks, _safe_str(concept_id), _safe_str(concept_name))
    domain_match = _matches_domain(normalized_chunks, _safe_str(domain))
    evidence_sections = _evidence_sections(normalized_chunks, generated_tokens)
    section_match = bool(evidence_sections)
    unsupported = _unsupported_terms(generated_text, context_text)

    grounding_score = (
        0.55 * keyword_overlap_score
        + (0.15 if concept_match else 0.0)
        + (0.10 if domain_match else 0.0)
        + (0.15 if section_match else 0.0)
        - min(0.25, 0.04 * len(unsupported))
    )
    if not concept_match:
        grounding_score -= 0.12
    if not domain_match:
        grounding_score -= 0.10
    grounding_score = round(_clamp(grounding_score), 4)

    fallback_recommended = (
        not concept_match
        or not domain_match
        or grounding_score < 0.45
        or len(unsupported) >= 3
    )
    safe_to_generate = grounding_score >= 0.55 and concept_match and domain_match and len(unsupported) <= 2

    if not safe_to_generate and (grounding_score < 0.35 or not concept_match or not domain_match):
        risk_level = "high"
    elif safe_to_generate and grounding_score >= 0.70:
        risk_level = "low"
    else:
        risk_level = "medium"

    reason_parts = [
        f"Keyword overlap score is {round(keyword_overlap_score, 4)}.",
        f"Concept match is {concept_match}.",
        f"Domain match is {domain_match}.",
        f"Evidence sections: {evidence_sections}.",
    ]
    if unsupported:
        reason_parts.append(f"Unsupported terms detected: {unsupported}.")
    if fallback_recommended:
        reason_parts.append("Fallback or safer grounded wording is recommended.")
    else:
        reason_parts.append("Generated content is sufficiently grounded in retrieved context.")

    return {
        "status": "success",
        "module": "RAGGroundingChecker",
        "context_found": context_found,
        "concept_match": concept_match,
        "domain_match": domain_match,
        "section_match": section_match,
        "keyword_overlap_score": round(keyword_overlap_score, 4),
        "grounding_score": grounding_score,
        "safe_to_generate": safe_to_generate,
        "risk_level": risk_level,
        "unsupported_terms": unsupported,
        "evidence_sections": evidence_sections,
        "fallback_recommended": fallback_recommended,
        "reason": " ".join(reason_parts),
    }


class RAGGroundingChecker:
    def check(
        self,
        *,
        generated_text: str,
        rag_context: Any = None,
        chunks: Any = None,
        concept_id: str | None = None,
        concept_name: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        return check_rag_grounding(
            generated_text=generated_text,
            rag_context=rag_context,
            chunks=chunks,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )
