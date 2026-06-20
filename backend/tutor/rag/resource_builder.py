from pathlib import Path

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
CORE_DATA_DIR = BASE_DIR / "core_data"


EMPTY_RESOURCE = {
    "definition": "",
    "examples": [],
    "key_points": [],
    "misconceptions": [],
    "practice_ideas": [],
    "reference_text": "",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return CORE_DATA_DIR / "tutor.db"

    path = Path(db_path)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


def _first_existing_core_data_dir() -> Path:
    return CORE_DATA_DIR


def get_db_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    resolved = _normalize_db_path(db_path)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("SELECT 1").fetchone()
    return conn


def get_concept_mapping(system_concept_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT system_concept_id, content_concept_id, domain, concept_name, source_db
            FROM concept_id_map
            WHERE system_concept_id = ?
            """,
            (str(system_concept_id),),
        ).fetchone()
        if not row:
            raise ValueError(f"No mapping found for system_concept_id={system_concept_id}")
        return dict(row)
    finally:
        conn.close()


def _resolve_source_db_path(source_db: str) -> Path:
    return _first_existing_core_data_dir() / source_db


def _list_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row["name"] for row in rows}


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _parse_labeled_sections(content: str) -> dict[str, str]:
    headers = ["Definition", "Worked Example", "Explanation", "Task", "Instruction", "Problem"]
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        matched = None
        for header in headers:
            if line.startswith(f"{header}:"):
                matched = header
                break

        if matched is not None:
            if current_header is not None and current_lines:
                sections[current_header] = "\n".join(current_lines).strip()
            current_header = matched
            current_lines = [line[len(matched) + 1 :].strip()]
            continue

        if current_header is not None:
            current_lines.append(line)

    if current_header is not None and current_lines:
        sections[current_header] = "\n".join(current_lines).strip()

    return sections


def fetch_raw_concept_resources(content_concept_id: str, source_db: str) -> dict[str, Any]:
    db_path = _resolve_source_db_path(source_db)
    if not db_path.exists():
        return dict(EMPTY_RESOURCE)

    conn = get_db_connection(db_path)
    try:
        table_names = _list_table_names(conn)
        resource = dict(EMPTY_RESOURCE)
        all_text_parts: list[str] = []

        if "concepts" in table_names:
            concept_columns = _table_columns(conn, "concepts")
            if "concept_id" in concept_columns:
                rows = conn.execute(
                    "SELECT * FROM concepts WHERE concept_id = ?",
                    (content_concept_id,),
                ).fetchall()
                for row in rows:
                    row_dict = dict(row)
                    description = (row_dict.get("description") or "").strip()
                    if description and not resource["definition"]:
                        resource["definition"] = description

                    for value in row_dict.values():
                        if isinstance(value, str) and value.strip():
                            all_text_parts.append(value.strip())

        if "teaching_content" in table_names:
            tc_columns = _table_columns(conn, "teaching_content")
            if "concept_id" in tc_columns:
                rows = conn.execute(
                    "SELECT * FROM teaching_content WHERE concept_id = ?",
                    (content_concept_id,),
                ).fetchall()
                for row in rows:
                    row_dict = dict(row)
                    content = (row_dict.get("content") or "").strip()
                    content_type = (row_dict.get("content_type") or "").strip().lower()
                    if not content:
                        continue

                    all_text_parts.append(content)
                    sections = _parse_labeled_sections(content)

                    definition = sections.get("Definition", "").strip()
                    if definition and not resource["definition"]:
                        resource["definition"] = definition

                    worked_example = sections.get("Worked Example", "").strip()
                    if worked_example:
                        resource["examples"].append(worked_example)
                    elif content_type == "worked_example":
                        resource["examples"].append(content)

                    explanation = sections.get("Explanation", "").strip()
                    if explanation:
                        resource["key_points"].append(explanation)

                    task = sections.get("Task", "").strip()
                    problem = sections.get("Problem", "").strip()
                    instruction = sections.get("Instruction", "").strip()
                    if task:
                        resource["practice_ideas"].append(task)
                    if problem:
                        resource["practice_ideas"].append(problem)
                    if instruction:
                        resource["practice_ideas"].append(instruction)

                    if "misconception" in content.lower():
                        resource["misconceptions"].append(content)

        for key in ["examples", "key_points", "misconceptions", "practice_ideas"]:
            seen: set[str] = set()
            deduped: list[str] = []
            for item in resource[key]:
                normalized = item.strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                deduped.append(normalized)
            resource[key] = deduped

        if not resource["key_points"]:
            lines = [line.strip() for line in "\n".join(all_text_parts).splitlines() if line.strip()]
            resource["key_points"] = lines[:5]

        resource["reference_text"] = "\n".join(all_text_parts).strip()
        return resource
    finally:
        conn.close()


def fetch_raw_concept_data(source_db: str, content_concept_id: str) -> dict[str, Any]:
    # Backward-compatible alias for existing callers.
    return fetch_raw_concept_resources(content_concept_id=content_concept_id, source_db=source_db)


def build_resource_bundle(system_concept_id: str) -> dict[str, Any]:
    from tutor.rag.chunker import chunk_resource_bundle

    try:
        mapping = get_concept_mapping(system_concept_id)
    except ValueError as exc:
        return {
            "status": "error",
            "message": str(exc),
            "system_concept_id": str(system_concept_id),
        }

    raw = fetch_raw_concept_resources(
        content_concept_id=mapping["content_concept_id"],
        source_db=mapping["source_db"],
    )

    bundle = {
        "status": "success",
        "system_concept_id": str(mapping["system_concept_id"]),
        "content_concept_id": str(mapping["content_concept_id"]),
        "domain": mapping.get("domain") or "",
        "concept_name": mapping.get("concept_name") or "",
        "source_db": mapping.get("source_db") or "",
        "resource_bundle": {
            "definition": raw.get("definition", ""),
            "examples": raw.get("examples", []),
            "key_points": raw.get("key_points", []),
            "misconceptions": raw.get("misconceptions", []),
            "practice_ideas": raw.get("practice_ideas", []),
            "reference_text": raw.get("reference_text", ""),
        },
        "built_at": _utc_now_iso(),
    }
    bundle["chunks"] = chunk_resource_bundle(bundle)
    return bundle


if __name__ == "__main__":
    print(json.dumps(build_resource_bundle("1"), indent=2))
