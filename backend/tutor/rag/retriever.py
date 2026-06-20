from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from tutor.rag.retrieve import retrieve_rag_context as retrieve_grounded_rag_context


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DATA = PROJECT_ROOT / "external" / "core_data"


SUBJECT_DB_MAP = {
    "Python": CORE_DATA / "python_learning.db",
    "HTML": CORE_DATA / "html_web_basics.db",
    "SQL": CORE_DATA / "database_sql.db",
    "Git": CORE_DATA / "git_version_control.db",
    "DataStructures": CORE_DATA / "data_structures.db",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def infer_domain_from_content_id(content_concept_id: str) -> str:
    cid = str(content_concept_id).strip().upper()

    if cid.startswith("P"):
        return "Python"
    if cid.startswith("H"):
        return "HTML"
    if cid.startswith("S") or cid.startswith("D"):
        return "SQL"
    if cid.startswith("G"):
        return "Git"
    return "DataStructures"


def get_concept_mapping(system_concept_id: str) -> Optional[Dict[str, str]]:
    tutor_db = CORE_DATA / "tutor.db"
    if not tutor_db.exists():
        return None

    conn = _connect(tutor_db)
    try:
        row = conn.execute(
            """
            SELECT system_concept_id, content_concept_id
            FROM concept_id_map
            WHERE system_concept_id = ?
            LIMIT 1
            """,
            (str(system_concept_id),),
        ).fetchone()

        if not row:
            return None

        content_concept_id = str(row["content_concept_id"])
        domain = infer_domain_from_content_id(content_concept_id)

        return {
            "system_concept_id": str(row["system_concept_id"]),
            "content_concept_id": content_concept_id,
            "domain": domain,
        }
    finally:
        conn.close()


def normalize_content_concept_id(content_concept_id: str, domain: str) -> str:
    cid = str(content_concept_id)

    if domain.lower() == "sql" and cid.startswith("D"):
        return "S" + cid[1:]

    return cid


def _legacy_fetch_teaching_content(
    system_concept_id: str,
    strategy: Optional[str] = None,
    difficulty: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    mapping = get_concept_mapping(system_concept_id)
    if not mapping:
        return []

    domain = mapping["domain"]
    db_path = SUBJECT_DB_MAP.get(domain)
    if not db_path or not db_path.exists():
        return []

    content_concept_id = normalize_content_concept_id(
        mapping["content_concept_id"], domain
    )

    conn = _connect(db_path)
    try:
        rows = []

        if strategy and difficulty and content_type:
            rows = conn.execute(
                """
                SELECT concept_id, strategy, difficulty, content_type, content
                FROM teaching_content
                WHERE concept_id = ?
                  AND strategy = ?
                  AND difficulty = ?
                  AND content_type = ?
                LIMIT ?
                """,
                (content_concept_id, strategy, difficulty, content_type, limit),
            ).fetchall()

        if not rows and strategy and difficulty:
            rows = conn.execute(
                """
                SELECT concept_id, strategy, difficulty, content_type, content
                FROM teaching_content
                WHERE concept_id = ?
                  AND strategy = ?
                  AND difficulty = ?
                LIMIT ?
                """,
                (content_concept_id, strategy, difficulty, limit),
            ).fetchall()

        if not rows and strategy:
            rows = conn.execute(
                """
                SELECT concept_id, strategy, difficulty, content_type, content
                FROM teaching_content
                WHERE concept_id = ?
                  AND strategy = ?
                LIMIT ?
                """,
                (content_concept_id, strategy, limit),
            ).fetchall()

        if not rows:
            rows = conn.execute(
                """
                SELECT concept_id, strategy, difficulty, content_type, content
                FROM teaching_content
                WHERE concept_id = ?
                LIMIT ?
                """,
                (content_concept_id, limit),
            ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()


def _infer_content_type(
    section: str,
    content: str,
    requested_content_type: Optional[str],
) -> str:
    if requested_content_type:
        return requested_content_type

    lowered = str(content).lower()
    if section == "practice_ideas":
        if "challenge" in lowered:
            return "challenge_problem"
        return "guided_practice"
    if section == "examples":
        return "worked_example"
    if section == "definition":
        return "worked_example"
    return "concept_summary"


def _infer_strategy(
    section: str,
    content: str,
    requested_strategy: Optional[str],
) -> str:
    if requested_strategy:
        return requested_strategy

    lowered = str(content).lower()
    if section == "definition":
        return "remedial"
    if section == "examples":
        return "practice"
    if section == "practice_ideas":
        if "challenge" in lowered:
            return "advanced"
        return "practice"
    return "practice"


def _normalize_grounded_chunks(
    grounded: Dict[str, Any],
    strategy: Optional[str],
    difficulty: Optional[str],
    content_type: Optional[str],
) -> List[Dict[str, Any]]:
    bundle = grounded.get("bundle") or {}
    mapping = grounded.get("mapping") or {}
    content_concept_id = (
        mapping.get("content_concept_id")
        or bundle.get("content_concept_id")
        or grounded.get("system_concept_id")
        or grounded.get("target_system_concept_id")
        or ""
    )

    normalized: List[Dict[str, Any]] = []
    for chunk in grounded.get("chunks", []) or []:
        section = str(chunk.get("section") or chunk.get("chunk_type") or "").strip()
        text = str(chunk.get("content") or chunk.get("chunk_text") or "").strip()
        if not section or not text:
            continue

        normalized.append(
            {
                "concept_id": str(content_concept_id),
                "strategy": _infer_strategy(section, text, strategy),
                "difficulty": difficulty or "medium",
                "content_type": _infer_content_type(section, text, content_type),
                "content": text,
                "section": section,
                "source": "grounded_rag",
            }
        )

    return normalized


def fetch_teaching_content(
    system_concept_id: str,
    strategy: Optional[str] = None,
    difficulty: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    grounded = retrieve_grounded_rag_context(
        system_concept_id=str(system_concept_id),
        strategy=strategy,
        difficulty=difficulty,
        content_type=content_type,
        limit=limit,
    )

    grounded_chunks = _normalize_grounded_chunks(
        grounded=grounded,
        strategy=strategy,
        difficulty=difficulty,
        content_type=content_type,
    )
    if grounded_chunks:
        return grounded_chunks[:limit]

    return _legacy_fetch_teaching_content(
        system_concept_id=system_concept_id,
        strategy=strategy,
        difficulty=difficulty,
        content_type=content_type,
        limit=limit,
    )


def retrieve_rag_context(
    system_concept_id: str,
    strategy: Optional[str] = None,
    difficulty: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    mapping = get_concept_mapping(system_concept_id)
    grounded = retrieve_grounded_rag_context(
        system_concept_id=str(system_concept_id),
        strategy=strategy,
        difficulty=difficulty,
        content_type=content_type,
        limit=limit,
    )

    chunks = _normalize_grounded_chunks(
        grounded=grounded,
        strategy=strategy,
        difficulty=difficulty,
        content_type=content_type,
    )

    if not chunks:
        chunks = _legacy_fetch_teaching_content(
            system_concept_id=system_concept_id,
            strategy=strategy,
            difficulty=difficulty,
            content_type=content_type,
            limit=limit,
        )

    return {
        "target_system_concept_id": str(system_concept_id),
        "mapping": mapping,
        "bundle": grounded.get("bundle"),
        "chunks": chunks,
        "chunk_count": len(chunks),
    }
