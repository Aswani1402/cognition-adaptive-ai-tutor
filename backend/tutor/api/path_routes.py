from __future__ import annotations

from fastapi import APIRouter

from tutor.api.dependencies import connect, rows_to_dicts, table_exists
from tutor.api.schemas import api_response


router = APIRouter(prefix="/path", tags=["path"])


@router.get("/{learner_id}")
def concept_path(learner_id: str) -> dict:
    module = "PathRoutes"
    conn = connect()
    try:
        nodes: list[dict] = []
        if table_exists(conn, "concept_unlock_state"):
            rows = rows_to_dicts(
                conn.execute(
                    """
                    SELECT concept_id, concept_name, domain, unlock_status, mastery_score,
                           promotion_confidence, prerequisites_met, locked_reason, updated_at
                    FROM concept_unlock_state
                    WHERE learner_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 50
                    """,
                    (learner_id,),
                ).fetchall()
            )
            nodes.extend(
                {
                    "concept_id": row.get("concept_id"),
                    "concept_name": row.get("concept_name"),
                    "domain": row.get("domain"),
                    "status": row.get("unlock_status"),
                    "mastery_score": row.get("mastery_score"),
                    "promotion_confidence": row.get("promotion_confidence"),
                    "prerequisites_met": bool(row.get("prerequisites_met")),
                    "locked_reason": row.get("locked_reason"),
                }
                for row in rows
            )
        if not nodes and table_exists(conn, "learner_concept_progress"):
            rows = rows_to_dicts(
                conn.execute(
                    """
                    SELECT concept_id, concept_name, domain, status, mastery, updated_at
                    FROM learner_concept_progress
                    WHERE learner_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 50
                    """,
                    (learner_id,),
                ).fetchall()
            )
            nodes.extend(
                {
                    "concept_id": row.get("concept_id"),
                    "concept_name": row.get("concept_name"),
                    "domain": row.get("domain"),
                    "status": row.get("status") or "current",
                    "mastery_score": row.get("mastery"),
                }
                for row in rows
            )
        return api_response(
            module=module,
            fallback_used=not bool(nodes),
            data={"learner_id": learner_id, "path_nodes": nodes},
            reason=None if nodes else "No persisted concept path state found.",
        )
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")
    finally:
        conn.close()
