from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =========================================================
# PATHS
# =========================================================
BASE_DIR = Path(__file__).resolve().parents[2]
CORE_DATA_DIR = BASE_DIR / "external" / "core_data"
TUTOR_DB_PATH = CORE_DATA_DIR / "tutor.db"


# =========================================================
# DB HELPERS
# =========================================================
def get_db_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# TEXT HELPERS
# =========================================================
def normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    return [t for t in normalize_text(text).split() if len(t) > 2]


def safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value:
        return None

    try:
        return json.loads(value)
    except Exception:
        return None


def to_list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    parsed = safe_json_loads(value)
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if str(x).strip()]

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if isinstance(value, str):
        lines = []
        for line in value.splitlines():
            clean = line.strip().lstrip("-").strip()
            if clean:
                lines.append(clean)
        return lines

    return []


# =========================================================
# CONCEPT MAPPING
# =========================================================
def get_concept_mapping(system_concept_id: str) -> dict[str, Any] | None:
    conn = get_db_connection(TUTOR_DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT *
            FROM concept_id_map
            WHERE system_concept_id = ?
            LIMIT 1
            """,
            (str(system_concept_id),),
        ).fetchone()

        if not row:
            return None

        row_dict = dict(row)

        return {
            "system_concept_id": str(row_dict.get("system_concept_id", "")),
            "content_concept_id": str(row_dict.get("content_concept_id", "")),
            "domain": row_dict.get("content_domain") or row_dict.get("domain") or "",
            "source": row_dict.get("source") or row_dict.get("source_db") or "",
        }
    finally:
        conn.close()


def resolve_subject_db_path(mapping: dict[str, Any]) -> Path | None:
    content_concept_id = str(mapping.get("content_concept_id", "")).strip().upper()
    domain = str(mapping.get("domain", "")).strip().lower()
    source = str(mapping.get("source", "")).strip()

    if source:
        candidate = CORE_DATA_DIR / source
        if candidate.exists():
            return candidate

    prefix = content_concept_id[:1]

    prefix_map = {
        "P": CORE_DATA_DIR / "python_learning.db",
        "H": CORE_DATA_DIR / "html_web_basics.db",
        "S": CORE_DATA_DIR / "database_sql.db",
        "G": CORE_DATA_DIR / "git_version_control.db",
        "D": CORE_DATA_DIR / "data_structures.db",
    }

    if prefix in prefix_map and prefix_map[prefix].exists():
        return prefix_map[prefix]

    domain_map = {
        "python": CORE_DATA_DIR / "python_learning.db",
        "html": CORE_DATA_DIR / "html_web_basics.db",
        "sql": CORE_DATA_DIR / "database_sql.db",
        "git": CORE_DATA_DIR / "git_version_control.db",
        "data structures": CORE_DATA_DIR / "data_structures.db",
    }

    db_path = domain_map.get(domain)
    if db_path and db_path.exists():
        return db_path

    return None


# =========================================================
# REFERENCE FETCH
# =========================================================
def get_reference_from_learning_content(system_concept_id: str) -> dict[str, Any] | None:
    """
    Preferred source because it matches the current teaching pipeline.
    """
    try:
        from tutor.utils.fetch_learning_content import get_learning_content

        resource = get_learning_content(str(system_concept_id))
        if not resource:
            return None

        topic = resource.get("topic", "") or ""
        base_content = resource.get("base_content", "") or ""

        # Prefer stable, foundational key points from key_points_base
        key_points_base = to_list_of_strings(resource.get("key_points_base"))
        key_points = to_list_of_strings(resource.get("key_points"))

        # key_points sometimes contains generic/guidance text; prefer base if available
        final_key_points = key_points_base if key_points_base else key_points

        return {
            "topic": topic,
            "base_content": base_content,
            "key_points": final_key_points,
            "examples": resource.get("examples", "") or "",
            "source_used": "get_learning_content",
        }
    except Exception:
        return None


def get_reference_from_subject_db(system_concept_id: str) -> dict[str, Any] | None:
    mapping = get_concept_mapping(system_concept_id)
    if not mapping:
        return None

    content_concept_id = mapping["content_concept_id"]
    db_path = resolve_subject_db_path(mapping)
    if not db_path or not db_path.exists():
        return None

    conn = get_db_connection(db_path)
    try:
        topic = ""
        base_content = ""
        key_points: list[str] = []

        try:
            row = conn.execute(
                """
                SELECT *
                FROM concepts
                WHERE concept_id = ?
                LIMIT 1
                """,
                (content_concept_id,),
            ).fetchone()

            if row:
                row_dict = dict(row)
                topic = (
                    row_dict.get("topic")
                    or row_dict.get("name")
                    or row_dict.get("concept_name")
                    or ""
                )
                base_content = (
                    row_dict.get("description")
                    or row_dict.get("content")
                    or row_dict.get("base_content")
                    or ""
                )
        except Exception:
            pass

        try:
            rows = conn.execute(
                """
                SELECT *
                FROM teaching_content
                WHERE concept_id = ?
                """,
                (content_concept_id,),
            ).fetchall()

            collected_texts = []
            for row in rows:
                row_dict = dict(row)
                for key, val in row_dict.items():
                    if isinstance(val, str) and key != "concept_id":
                        cleaned = val.strip()
                        if cleaned:
                            collected_texts.append(cleaned)

            if collected_texts and not base_content:
                base_content = "\n".join(collected_texts[:5])
        except Exception:
            pass

        if base_content:
            key_points = build_key_points_from_text(base_content)

        return {
            "topic": topic,
            "base_content": base_content,
            "key_points": key_points,
            "examples": "",
            "source_used": str(db_path.name),
        }
    finally:
        conn.close()


def get_reference_material(system_concept_id: str) -> dict[str, Any] | None:
    reference = get_reference_from_learning_content(system_concept_id)
    if reference:
        return reference

    return get_reference_from_subject_db(system_concept_id)


# =========================================================
# KEY POINT BUILDING
# =========================================================
def clean_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()


def split_into_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [clean_sentence(p) for p in parts if clean_sentence(p)]


def is_useful_key_point(sentence: str) -> bool:
    words = tokenize(sentence)
    if len(words) < 4:
        return False

    bad_starts = (
        "example",
        "hint",
        "this",
        "try",
        "follow",
        "solve",
        "attempt",
    )

    sent_norm = normalize_text(sentence)
    if any(sent_norm.startswith(x) for x in bad_starts):
        return False

    return True


def build_key_points_from_text(text: str, max_points: int = 5) -> list[str]:
    sentences = split_into_sentences(text)
    points = []

    for sent in sentences:
        if is_useful_key_point(sent):
            points.append(sent)

    seen = set()
    unique_points = []
    for p in points:
        key = normalize_text(p)
        if key not in seen:
            unique_points.append(p)
            seen.add(key)

    return unique_points[:max_points]


def select_core_key_points(concept_name: str, all_key_points: list[str], max_points: int = 5) -> list[str]:
    """
    Prefer simpler, foundational points first.
    """
    if not all_key_points:
        return []

    concept_name_norm = normalize_text(concept_name)
    preferred_keywords = [
        "store",
        "value",
        "name",
        "used",
        "program",
        "update",
        "change",
        "basic",
        concept_name_norm,
    ]

    scored_points = []
    for point in all_key_points:
        point_norm = normalize_text(point)
        score = 0

        for kw in preferred_keywords:
            if kw and kw in point_norm:
                score += 1

        # Penalize advanced-heavy points for early evaluation
        advanced_keywords = [
            "pep",
            "snake_case",
            "pascalcase",
            "identity",
            "mutable",
            "constants",
            "reserved keywords",
            "object",
            "memory location",
        ]
        for kw in advanced_keywords:
            if kw in point_norm:
                score -= 1

        scored_points.append((score, point))

    scored_points.sort(key=lambda x: x[0], reverse=True)
    selected = [point for _, point in scored_points[:max_points]]

    # preserve original order among selected points
    selected_set = {normalize_text(p) for p in selected}
    ordered_selected = []
    for point in all_key_points:
        if normalize_text(point) in selected_set:
            ordered_selected.append(point)

    return ordered_selected[:max_points]


# =========================================================
# MATCHING / SCORING
# =========================================================
def keyword_overlap_ratio(point: str, learner_text: str) -> float:
    point_tokens = set(tokenize(point))
    learner_tokens = set(tokenize(learner_text))

    if not point_tokens:
        return 0.0

    overlap = point_tokens.intersection(learner_tokens)
    return len(overlap) / len(point_tokens)


def point_matches(point: str, learner_text: str, threshold: float = 0.3) -> bool:
    ratio = keyword_overlap_ratio(point, learner_text)
    return ratio >= threshold


def derive_quality_label(score: float) -> str:
    if score >= 0.8:
        return "good"
    if score >= 0.4:
        return "partial"
    return "weak"


def build_feedback(concept_name: str, matched: list[str], missing: list[str], score: float) -> str:
    concept_label = concept_name or "this concept"

    if score >= 0.8:
        return f"Good explanation of {concept_label}. You covered most key ideas."

    if score >= 0.4:
        if missing:
            return (
                f"Your explanation of {concept_label} is partially correct. "
                f"Try to include: {', '.join(missing[:3])}."
            )
        return f"Your explanation of {concept_label} is partially correct but could be more complete."

    if missing:
        return (
            f"Your explanation of {concept_label} is weak or incomplete. "
            f"Focus on these ideas: {', '.join(missing[:3])}."
        )

    return f"Your explanation of {concept_label} is weak or incomplete. Review the main definition and purpose."


# =========================================================
# OPTIONAL SAVE
# =========================================================
def ensure_explanation_results_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS explanation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            system_concept_id TEXT,
            content_concept_id TEXT,
            concept_name TEXT,
            response_text TEXT,
            score REAL,
            coverage_ratio REAL,
            matched_key_points TEXT,
            missing_key_points TEXT,
            quality_label TEXT,
            feedback TEXT,
            source_used TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()


def save_explanation_result(result: dict[str, Any], db_path: str | Path = TUTOR_DB_PATH) -> None:
    conn = get_db_connection(db_path)
    try:
        ensure_explanation_results_table(conn)

        conn.execute(
            """
            INSERT INTO explanation_results (
                learner_id,
                system_concept_id,
                content_concept_id,
                concept_name,
                response_text,
                score,
                coverage_ratio,
                matched_key_points,
                missing_key_points,
                quality_label,
                feedback,
                source_used,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("learner_id"),
                result.get("system_concept_id"),
                result.get("content_concept_id"),
                result.get("concept_name"),
                result.get("response_text"),
                result.get("score"),
                result.get("coverage_ratio"),
                json.dumps(result.get("matched_key_points", [])),
                json.dumps(result.get("missing_key_points", [])),
                result.get("quality_label"),
                result.get("feedback"),
                result.get("source_used"),
                result.get("evaluated_at"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# =========================================================
# MAIN EVALUATOR
# =========================================================
def evaluate_explanation(
    learner_id: str,
    system_concept_id: str,
    response_text: str,
    save_to_db: bool = False,
) -> dict[str, Any]:
    learner_id = str(learner_id)
    system_concept_id = str(system_concept_id)
    response_text = response_text or ""

    if not response_text.strip():
        return {
            "status": "failed",
            "message": "Empty response",
            "learner_id": learner_id,
            "system_concept_id": system_concept_id,
        }

    mapping = get_concept_mapping(system_concept_id)
    if not mapping:
        return {
            "status": "failed",
            "message": "Concept mapping not found",
            "learner_id": learner_id,
            "system_concept_id": system_concept_id,
        }

    reference = get_reference_material(system_concept_id)
    if not reference:
        return {
            "status": "failed",
            "message": "Reference material not found",
            "learner_id": learner_id,
            "system_concept_id": system_concept_id,
            "content_concept_id": mapping["content_concept_id"],
        }

    concept_name = reference.get("topic", "") or ""
    all_key_points = reference.get("key_points", []) or []
    base_content = reference.get("base_content", "") or ""
    source_used = reference.get("source_used", "unknown")

    if not all_key_points and base_content:
        all_key_points = build_key_points_from_text(base_content, max_points=8)

    key_points = select_core_key_points(concept_name, all_key_points, max_points=5)

    if not key_points and base_content:
        key_points = build_key_points_from_text(base_content, max_points=5)

    if not key_points:
        return {
            "status": "failed",
            "message": "No key points available for evaluation",
            "learner_id": learner_id,
            "system_concept_id": system_concept_id,
            "content_concept_id": mapping["content_concept_id"],
            "concept_name": concept_name,
        }

    matched_points = []
    missing_points = []

    for point in key_points:
        if point_matches(point, response_text):
            matched_points.append(point)
        else:
            missing_points.append(point)

    total_points = len(key_points)
    score = round(len(matched_points) / total_points, 3) if total_points > 0 else 0.0
    quality_label = derive_quality_label(score)
    feedback = build_feedback(concept_name, matched_points, missing_points, score)

    result = {
        "status": "success",
        "learner_id": learner_id,
        "system_concept_id": system_concept_id,
        "content_concept_id": mapping["content_concept_id"],
        "concept_name": concept_name,
        "domain": mapping.get("domain"),
        "score": score,
        "coverage_ratio": score,
        "matched_key_points": matched_points,
        "missing_key_points": missing_points,
        "quality_label": quality_label,
        "feedback": feedback,
        "reference_key_points": key_points,
        "source_used": source_used,
        "evaluated_at": now_iso(),
        "response_text": response_text,
    }

    if save_to_db:
        save_explanation_result(result)

    return result


# =========================================================
# CLI TEST
# =========================================================
if __name__ == "__main__":
    test_cases = [
        {
            "learner_id": "14",
            "system_concept_id": "1",
            "response_text": "A variable is a name used to store a value in Python. It can be updated later.",
        },
        {
            "learner_id": "14",
            "system_concept_id": "1",
            "response_text": "Variables are used in code and can hold data.",
        },
        {
            "learner_id": "14",
            "system_concept_id": "1",
            "response_text": "",
        },
    ]

    for i, test in enumerate(test_cases, start=1):
        print("\n" + "=" * 70)
        print(f"TEST CASE {i}")

        output = evaluate_explanation(
            learner_id=test["learner_id"],
            system_concept_id=test["system_concept_id"],
            response_text=test["response_text"],
            save_to_db=False,
        )

        print(json.dumps(output, indent=2))