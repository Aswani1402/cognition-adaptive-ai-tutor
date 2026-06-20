from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"

SECTION_ALIASES = {
    "definition": "definition",
    "example": "examples",
    "examples": "examples",
    "key_point": "key_points",
    "key_points": "key_points",
    "misconception": "misconceptions",
    "misconceptions": "misconceptions",
    "practice_idea": "practice_ideas",
    "practice_ideas": "practice_ideas",
}

STRATEGY_SECTION_WEIGHTS = {
    "remedial": {
        "definition": 8,
        "examples": 6,
        "key_points": 4,
        "misconceptions": 3,
        "practice_ideas": 1,
    },
    "practice": {
        "examples": 8,
        "practice_ideas": 6,
        "key_points": 4,
        "definition": 2,
    },
    "advanced": {
        "practice_ideas": 8,
        "key_points": 5,
        "examples": 3,
        "definition": 1,
    },
}

CONTENT_TYPE_SECTION_WEIGHTS = {
    "worked_example": {
        "examples": 5,
        "definition": 2,
    },
    "guided_practice": {
        "practice_ideas": 5,
        "examples": 2,
        "key_points": 1,
    },
    "challenge_problem": {
        "practice_ideas": 6,
        "key_points": 1,
    },
}


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_chunks_by_system_concept_id(
    system_concept_id: str,
    section: str | None = None,
) -> list[dict[str, Any]]:
    conn = get_db_connection()
    try:
        normalized_section = SECTION_ALIASES.get(str(section or "").strip().lower(), section)
        if section:
            rows = conn.execute(
                """
                SELECT chunk_id, system_concept_id, concept_name, domain, section, content
                FROM rag_chunks
                WHERE system_concept_id = ? AND section = ?
                ORDER BY chunk_id ASC
                """,
                (str(system_concept_id), normalized_section),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT chunk_id, system_concept_id, concept_name, domain, section, content
                FROM rag_chunks
                WHERE system_concept_id = ?
                ORDER BY chunk_id ASC
                """,
                (str(system_concept_id),),
            ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def _safe_json_loads(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []


def _normalize_section(section: Any) -> str:
    lowered = str(section or "").strip().lower()
    return SECTION_ALIASES.get(lowered, lowered)


def _keyword_bonus(
    content: str,
    strategy: str | None = None,
    content_type: str | None = None,
) -> int:
    lowered = str(content or "").lower()
    bonus = 0

    if strategy == "remedial":
        if "step-by-step" in lowered or "support" in lowered or "review" in lowered:
            bonus += 2
    elif strategy == "practice":
        if "guided practice" in lowered or "try" in lowered or "observe" in lowered:
            bonus += 2
    elif strategy == "advanced":
        if "challenge" in lowered or "independently" in lowered or "justify" in lowered:
            bonus += 2

    if content_type == "challenge_problem" and "challenge" in lowered:
        bonus += 2
    if content_type == "guided_practice" and "guided practice" in lowered:
        bonus += 2
    if content_type == "worked_example" and "example" in lowered:
        bonus += 1

    return bonus


def _score_chunk(
    chunk: dict[str, Any],
    strategy: str | None = None,
    content_type: str | None = None,
) -> int:
    section = _normalize_section(chunk.get("section"))
    content = str(chunk.get("content") or "")

    score = 0
    if strategy:
        score += STRATEGY_SECTION_WEIGHTS.get(strategy, {}).get(section, 0)
    if content_type:
        score += CONTENT_TYPE_SECTION_WEIGHTS.get(content_type, {}).get(section, 0)

    score += _keyword_bonus(
        content=content,
        strategy=strategy,
        content_type=content_type,
    )
    return score


def _rank_chunks(
    chunks: list[dict[str, Any]],
    strategy: str | None = None,
    content_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    ranked: list[tuple[int, int, dict[str, Any]]] = []

    for idx, chunk in enumerate(chunks):
        section = _normalize_section(chunk.get("section"))
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue

        dedupe_key = (section, content)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        normalized = dict(chunk)
        normalized["section"] = section
        ranked.append(
            (
                _score_chunk(
                    normalized,
                    strategy=strategy,
                    content_type=content_type,
                ),
                -idx,
                normalized,
            )
        )

    ranked.sort(key=lambda item: (-item[0], -item[1]))
    ordered = [item[2] for item in ranked]

    if limit is not None and limit > 0 and ordered:
        preferred_sections: list[str] = []
        if strategy:
            section_weights = STRATEGY_SECTION_WEIGHTS.get(strategy, {})
            preferred_sections.extend(
                section
                for section, _ in sorted(
                    section_weights.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            )
        if content_type:
            section_weights = CONTENT_TYPE_SECTION_WEIGHTS.get(content_type, {})
            for section, _ in sorted(
                section_weights.items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                if section not in preferred_sections:
                    preferred_sections.append(section)

        diversified: list[dict[str, Any]] = []
        used_indexes: set[int] = set()

        for section in preferred_sections:
            for idx, chunk in enumerate(ordered):
                if idx in used_indexes:
                    continue
                if chunk.get("section") == section:
                    diversified.append(chunk)
                    used_indexes.add(idx)
                    break
            if len(diversified) >= limit:
                return diversified[:limit]

        for idx, chunk in enumerate(ordered):
            if idx in used_indexes:
                continue
            diversified.append(chunk)
            if len(diversified) >= limit:
                return diversified[:limit]

        return diversified[:limit]

    return ordered


def get_bundle_by_system_concept_id(system_concept_id: str) -> dict[str, Any] | None:
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM rag_resource_bundle
            WHERE system_concept_id = ?
            LIMIT 1
            """,
            (str(system_concept_id),),
        ).fetchone()

        if not row:
            return None

        raw = dict(row)

        return {
            "status": "success",
            "system_concept_id": raw.get("system_concept_id"),
            "content_concept_id": raw.get("content_concept_id"),
            "domain": raw.get("domain"),
            "concept_name": raw.get("concept_name"),
            "source_db": raw.get("source_db"),
            "resource_bundle": {
                "definition": raw.get("definition") or "",
                "examples": _safe_json_loads(raw.get("examples")),
                "key_points": _safe_json_loads(raw.get("key_points")),
                "misconceptions": _safe_json_loads(raw.get("misconceptions")),
                "practice_ideas": _safe_json_loads(raw.get("practice_ideas")),
                "reference_text": raw.get("reference_text") or "",
            },
        }
    finally:
        conn.close()


def retrieve_rag_context(
    system_concept_id: str,
    strategy: str | None = None,
    difficulty: str | None = None,
    content_type: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    bundle = get_bundle_by_system_concept_id(system_concept_id)
    chunks = get_chunks_by_system_concept_id(system_concept_id)
    ranked_chunks = _rank_chunks(
        chunks,
        strategy=strategy,
        content_type=content_type,
        limit=limit,
    )

    return {
        "status": "success",
        "system_concept_id": str(system_concept_id),
        "bundle": bundle,
        "difficulty": difficulty,
        "chunks": ranked_chunks,
        "chunk_count": len(ranked_chunks),
        "available_chunk_count": len(chunks),
    }
