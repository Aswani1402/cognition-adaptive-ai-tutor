from __future__ import annotations

import sqlite3
from typing import Optional, Dict, Any

from tutor.utils.fetch_learning_content import get_learning_content

SUBJECT_DB_MAP = {
    "P": "external/core_data/python_learning.db",
    "D": "external/core_data/data_structures.db",
    "H": "external/core_data/html_web_basics.db",
    "G": "external/core_data/git_version_control.db",
    "S": "external/core_data/database_sql.db",
}


def normalize_teaching_concept_id(concept_id: Any) -> Optional[str]:
    """
    Normalize concept ids for legacy fallback teaching_content lookup only.

    Examples:
    - 1   -> P1
    - "1" -> P1
    - "p1" -> P1
    - "P1" -> P1
    """
    if concept_id is None:
        return None

    cid = str(concept_id).strip().upper()
    if not cid:
        return None

    if cid.isdigit():
        return f"P{cid}"

    return cid


def get_subject_db_path(concept_id: Any) -> str:
    """
    Resolve subject DB from normalized concept id prefix.
    Used only by legacy fallback path.
    """
    cid = normalize_teaching_concept_id(concept_id)

    if not cid:
        raise ValueError("Empty concept_id")

    prefix = cid[0]
    if prefix not in SUBJECT_DB_MAP:
        raise ValueError(f"Unknown concept prefix for concept_id={cid}")

    return SUBJECT_DB_MAP[prefix]


def fetch_teaching_content(
    concept_id: Any,
    difficulty: Optional[str] = None,
    strategy: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch teaching content for the integrated pipeline.

    New path:
    system_concept_id -> concept_id_map -> subject DB -> concept_resources

    Fallback path:
    old teaching_content lookup
    """

    print(f"[DEBUG] fetch_teaching_content called with concept_id={concept_id}")

    # ---------------------------------------------------------
    # 1) NEW PATH: concept_resources through concept_id_map
    # ---------------------------------------------------------
    try:
        resource = get_learning_content(str(concept_id))
        print(f"[DEBUG] concept_resources hit = {bool(resource)}")
    except Exception as e:
        resource = None
        new_path_error = str(e)
        print(f"[DEBUG] concept_resources error = {new_path_error}")
    else:
        new_path_error = None

    if resource:
        return {
            "status": "success",
            "module": "teaching_content",
            "source": "concept_resources",
            "concept_id": concept_id,  # system concept id from policy
            "normalized_concept_id": resource.get("concept_id"),  # subject concept id like P1
            "difficulty": difficulty,
            "strategy": strategy,
            "content_type": content_type,
            "content": {
                "concept_id": resource.get("concept_id"),
                "topic": resource.get("topic"),
                "content": resource.get("base_content"),
                "base_content": resource.get("base_content"),
                "examples": resource.get("examples"),
                "key_points": resource.get("key_points"),
                "misconceptions": resource.get("misconceptions"),
                "real_world_use": resource.get("real_world_use"),
                "next_concept_link": resource.get("next_concept_link"),
            },
        }

    # ---------------------------------------------------------
    # 2) FALLBACK PATH: legacy teaching_content table
    # ---------------------------------------------------------
    normalized_id = normalize_teaching_concept_id(concept_id)

    if not normalized_id:
        return {
            "status": "error",
            "module": "teaching_content",
            "source": "concept_resources_then_legacy_teaching_content",
            "error": "No concept_id provided",
            "concept_id": concept_id,
            "new_path_error": new_path_error,
        }

    try:
        db_path = get_subject_db_path(normalized_id)
    except Exception as e:
        return {
            "status": "error",
            "module": "teaching_content",
            "source": "concept_resources_then_legacy_teaching_content",
            "error": f"Could not determine subject DB for concept_id={concept_id}: {e}",
            "concept_id": concept_id,
            "normalized_concept_id": normalized_id,
            "new_path_error": new_path_error,
        }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        table_row = c.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='teaching_content'
        """).fetchone()

        if not table_row:
            return {
                "status": "no_content_found",
                "module": "teaching_content",
                "source": "concept_resources_then_legacy_teaching_content",
                "concept_id": concept_id,
                "normalized_concept_id": normalized_id,
                "difficulty": difficulty,
                "strategy": strategy,
                "content_type": content_type,
                "db_path": db_path,
                "new_path_error": new_path_error,
                "fallback_note": "Legacy teaching_content table does not exist in this subject DB",
            }

        columns_info = c.execute("PRAGMA table_info(teaching_content)").fetchall()
        columns = [row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in columns_info]

        row = None

        has_strategy = "strategy" in columns
        has_difficulty = "difficulty" in columns
        has_content_type = "content_type" in columns
        has_content_id = "content_id" in columns

        order_clause = "ORDER BY content_id" if has_content_id else "ORDER BY rowid"

        if (
            strategy
            and difficulty
            and content_type
            and has_strategy
            and has_difficulty
            and has_content_type
        ):
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                  AND LOWER(TRIM(strategy)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(difficulty)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(content_type)) = LOWER(TRIM(?))
                {order_clause}
                LIMIT 1
                """,
                (normalized_id, strategy, difficulty, content_type),
            ).fetchone()

        if not row and strategy and content_type and has_strategy and has_content_type:
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                  AND LOWER(TRIM(strategy)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(content_type)) = LOWER(TRIM(?))
                {order_clause}
                LIMIT 1
                """,
                (normalized_id, strategy, content_type),
            ).fetchone()

        if not row and strategy and difficulty and has_strategy and has_difficulty:
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                  AND LOWER(TRIM(strategy)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(difficulty)) = LOWER(TRIM(?))
                {order_clause}
                LIMIT 1
                """,
                (normalized_id, strategy, difficulty),
            ).fetchone()

        if not row and strategy and has_strategy:
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                  AND LOWER(TRIM(strategy)) = LOWER(TRIM(?))
                {order_clause}
                LIMIT 1
                """,
                (normalized_id, strategy),
            ).fetchone()

        if not row and content_type and has_content_type:
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                  AND LOWER(TRIM(content_type)) = LOWER(TRIM(?))
                {order_clause}
                LIMIT 1
                """,
                (normalized_id, content_type),
            ).fetchone()

        if not row:
            row = c.execute(
                f"""
                SELECT *
                FROM teaching_content
                WHERE UPPER(TRIM(concept_id)) = ?
                {order_clause}
                LIMIT 1
                """,
                (normalized_id,),
            ).fetchone()

        if not row:
            return {
                "status": "no_content_found",
                "module": "teaching_content",
                "source": "concept_resources_then_legacy_teaching_content",
                "concept_id": concept_id,
                "normalized_concept_id": normalized_id,
                "difficulty": difficulty,
                "strategy": strategy,
                "content_type": content_type,
                "db_path": db_path,
                "new_path_error": new_path_error,
            }

        result = dict(row)

        return {
            "status": "success",
            "module": "teaching_content",
            "source": "legacy_teaching_content",
            "concept_id": concept_id,
            "normalized_concept_id": normalized_id,
            "difficulty": difficulty,
            "strategy": strategy,
            "content_type": content_type,
            "db_path": db_path,
            "new_path_error": new_path_error,
            "content": result,
        }

    except Exception as e:
        return {
            "status": "error",
            "module": "teaching_content",
            "source": "concept_resources_then_legacy_teaching_content",
            "concept_id": concept_id,
            "normalized_concept_id": normalized_id,
            "difficulty": difficulty,
            "strategy": strategy,
            "content_type": content_type,
            "db_path": db_path,
            "new_path_error": new_path_error,
            "error": str(e),
        }
    finally:
        conn.close()


def run_teaching_fetch(
    policy_output: Dict[str, Any],
    strategy_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Entry point used by integrated pipeline.
    """
    strategy_output = strategy_output or {}

    policy_data = policy_output.get("data", {}) if isinstance(policy_output, dict) else {}
    strategy_data = strategy_output.get("data", {}) if isinstance(strategy_output, dict) else {}

    concept_id = policy_data.get("next_concept_id")
    difficulty = policy_data.get("difficulty")
    content_type = policy_data.get("content_type")
    strategy = strategy_data.get("final_strategy", policy_data.get("strategy"))

    return fetch_teaching_content(
        concept_id=concept_id,
        difficulty=difficulty,
        strategy=strategy,
        content_type=content_type,
    )