from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path("external/core_data/tutor.db")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def load_concept_id_map(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        return {}

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        if not _table_exists(conn, "concept_id_map"):
            return {}
        rows = conn.execute(
            """
            SELECT system_concept_id, content_concept_id, domain, concept_name, source_db
            FROM concept_id_map
            """
        ).fetchall()

    return {
        _safe_str(row["system_concept_id"]): {
            "system_concept_id": _safe_str(row["system_concept_id"]),
            "content_concept_id": _safe_str(row["content_concept_id"]),
            "domain": _safe_str(row["domain"]),
            "concept_name": _safe_str(row["concept_name"]),
            "source_db": _safe_str(row["source_db"]),
        }
        for row in rows
    }


def validate_selected_concept_id(
    selected_concept_id: Any,
    concept_id_map: dict[str, dict[str, Any]] | None = None,
    fallback_concept_id: Any = None,
    *,
    current_domain: str | None = None,
    dependency_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    concept_id_map = concept_id_map or load_concept_id_map()
    selected = _safe_str(selected_concept_id)
    fallback = _safe_str(fallback_concept_id) or selected
    current_domain_clean = _safe_str(current_domain).lower()
    dependency_output = dependency_output or {}

    fallback_meta = concept_id_map.get(fallback, {})

    def _fallback(reason: str, selected_valid: bool = False) -> dict[str, Any]:
        return {
            "valid": bool(selected_valid),
            "selected_concept_id": selected,
            "resolved_concept_id": fallback,
            "resolved_concept_name": fallback_meta.get("concept_name", "Unknown Concept"),
            "resolved_domain": fallback_meta.get("domain", ""),
            "fallback_used": True,
            "reason": reason,
        }

    if not selected:
        return _fallback("No adaptive path concept was selected.")

    selected_meta = concept_id_map.get(selected)
    if not selected_meta:
        return _fallback(f"Selected concept {selected} is not present in concept_id_map.")

    unlocked = {str(item) for item in dependency_output.get("unlocked_concepts", []) or []}
    blocked_items = dependency_output.get("blocked_concepts", []) or []
    blocked = {
        str(item.get("concept_id"))
        for item in blocked_items
        if isinstance(item, dict) and item.get("concept_id") is not None
    }

    if selected in blocked:
        return _fallback(f"Selected concept {selected} is blocked by prerequisite constraints.")

    if unlocked and selected not in unlocked:
        return _fallback(f"Selected concept {selected} is not currently unlocked by dependency constraints.")

    selected_domain = _safe_str(selected_meta.get("domain"))
    if current_domain_clean and selected_domain.lower() != current_domain_clean:
        return _fallback(
            f"Selected concept {selected} maps to domain {selected_domain}, which does not match current domain {current_domain}.",
        )

    return {
        "valid": True,
        "selected_concept_id": selected,
        "resolved_concept_id": selected,
        "resolved_concept_name": selected_meta.get("concept_name", "Unknown Concept"),
        "resolved_domain": selected_meta.get("domain", ""),
        "fallback_used": False,
        "reason": f"Selected concept {selected} is mapped and dependency-valid.",
    }


def build_frontend_path_output(
    *,
    concept_id_map: dict[str, dict[str, Any]] | None = None,
    dependency_output: dict[str, Any] | None = None,
    validation_output: dict[str, Any] | None = None,
    current_concept_id: Any = None,
    mastery: dict[str, Any] | None = None,
    review_queue: list[Any] | None = None,
    current_domain: str | None = None,
) -> dict[str, Any]:
    concept_id_map = concept_id_map or load_concept_id_map()
    dependency_output = dependency_output or {}
    validation_output = validation_output or {}
    mastery = mastery or {}
    review_due = {str(item) for item in (review_queue or [])}
    current = _safe_str(current_concept_id)
    selected = _safe_str(validation_output.get("resolved_concept_id"))
    current_domain_clean = _safe_str(current_domain).lower()
    unlocked = {str(item) for item in dependency_output.get("unlocked_concepts", []) or []}
    blocked_items = dependency_output.get("blocked_concepts", []) or []
    blocked = {
        str(item.get("concept_id"))
        for item in blocked_items
        if isinstance(item, dict) and item.get("concept_id") is not None
    }

    nodes = []
    for concept_id in sorted(concept_id_map.keys(), key=lambda value: int(value) if value.isdigit() else value):
        meta = concept_id_map[concept_id]
        if current_domain_clean and _safe_str(meta.get("domain")).lower() != current_domain_clean:
            continue

        value = _safe_float(mastery.get(concept_id), None)
        status = "locked"
        reason = "Concept is locked until prerequisites are met."

        if concept_id in unlocked:
            status = "unlocked"
            reason = "Concept is unlocked by dependency constraints."
        if value is not None and value >= 0.75:
            status = "mastered"
            reason = "Learner mastery is high for this concept."
        if concept_id in review_due:
            status = "review_due"
            reason = "Forgetting module marked this concept for review."
        if concept_id == current:
            status = "current"
            reason = "Current concept."
        if concept_id == selected:
            status = "recommended"
            reason = validation_output.get("reason") or "Recommended adaptive path concept."

        nodes.append(
            {
                "concept_id": concept_id,
                "concept_name": meta.get("concept_name", "Unknown Concept"),
                "domain": meta.get("domain", ""),
                "status": status,
                "mastery": value,
                "prerequisites": _blocked_by_for(concept_id, blocked_items),
                "reason": reason,
            }
        )

    selected_node = next((node for node in nodes if node["concept_id"] == selected), None)

    return {
        "status": "success",
        "module": "AdaptivePathFrontendOutput",
        "path_nodes": nodes,
        "selected_node": selected_node,
        "blocked_concepts": sorted(blocked),
        "unlocked_concepts": sorted(unlocked),
        "review_due_concepts": sorted(review_due),
        "validation": validation_output,
    }


def _blocked_by_for(concept_id: str, blocked_items: list[Any]) -> list[str]:
    for item in blocked_items:
        if isinstance(item, dict) and str(item.get("concept_id")) == str(concept_id):
            return [str(value) for value in item.get("blocked_by", [])]
    return []
