import json
import sqlite3
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _ensure_expected_schema(conn: sqlite3.Connection, table_name: str, expected_columns: list[str]) -> None:
    if not _table_exists(conn, table_name):
        return

    current = _table_columns(conn, table_name)
    if current != expected_columns:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")


def ensure_rag_tables(conn: sqlite3.Connection) -> None:
    bundle_expected = [
        "id",
        "system_concept_id",
        "content_concept_id",
        "domain",
        "concept_name",
        "source_db",
        "definition_text",
        "examples_json",
        "key_points_json",
        "misconceptions_json",
        "practice_ideas_json",
        "reference_text",
        "created_at",
        "updated_at",
    ]
    chunks_expected = [
        "id",
        "system_concept_id",
        "content_concept_id",
        "chunk_type",
        "chunk_text",
        "chunk_order",
        "source_db",
        "created_at",
    ]

    _ensure_expected_schema(conn, "rag_resource_bundle", bundle_expected)
    _ensure_expected_schema(conn, "rag_chunks", chunks_expected)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_resource_bundle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_concept_id TEXT NOT NULL,
            content_concept_id TEXT NOT NULL,
            domain TEXT,
            concept_name TEXT,
            source_db TEXT,
            definition_text TEXT,
            examples_json TEXT,
            key_points_json TEXT,
            misconceptions_json TEXT,
            practice_ideas_json TEXT,
            reference_text TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_concept_id TEXT NOT NULL,
            content_concept_id TEXT NOT NULL,
            chunk_type TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_order INTEGER,
            source_db TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()


def save_resource_bundle(conn: sqlite3.Connection, bundle: dict) -> bool:
    if not bundle or bundle.get("status") != "success":
        return False

    now = _utc_now_iso()
    rb = bundle.get("resource_bundle", {})

    conn.execute(
        "DELETE FROM rag_resource_bundle WHERE system_concept_id = ?",
        (str(bundle["system_concept_id"]),),
    )

    conn.execute(
        """
        INSERT INTO rag_resource_bundle (
            system_concept_id,
            content_concept_id,
            domain,
            concept_name,
            source_db,
            definition_text,
            examples_json,
            key_points_json,
            misconceptions_json,
            practice_ideas_json,
            reference_text,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(bundle["system_concept_id"]),
            str(bundle["content_concept_id"]),
            bundle.get("domain", ""),
            bundle.get("concept_name", ""),
            bundle.get("source_db", ""),
            rb.get("definition", ""),
            json.dumps(rb.get("examples", [])),
            json.dumps(rb.get("key_points", [])),
            json.dumps(rb.get("misconceptions", [])),
            json.dumps(rb.get("practice_ideas", [])),
            rb.get("reference_text", ""),
            now,
            now,
        ),
    )
    conn.commit()
    return True


def save_chunks(conn: sqlite3.Connection, chunks: list[dict]) -> bool:
    if not chunks:
        return False

    now = _utc_now_iso()
    system_concept_id = str(chunks[0]["system_concept_id"])

    conn.execute(
        "DELETE FROM rag_chunks WHERE system_concept_id = ?",
        (system_concept_id,),
    )

    for chunk in chunks:
        conn.execute(
            """
            INSERT INTO rag_chunks (
                system_concept_id,
                content_concept_id,
                chunk_type,
                chunk_text,
                chunk_order,
                source_db,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(chunk["system_concept_id"]),
                str(chunk["content_concept_id"]),
                chunk["chunk_type"],
                chunk["chunk_text"],
                chunk.get("chunk_order"),
                chunk.get("source_db", ""),
                now,
            ),
        )

    conn.commit()
    return True
