import sys
sys.path.append("tutor/long_term_personalization")


import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Tuple

from tutor.long_term_personalization.utils import (
    mean,
    normalize_mastery_values,
    parse_json_object,
    parse_timestamp,
    safe_float,
    safe_int,
    safe_round,
    top_domains,
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [str(r[1]) for r in rows]
    except Exception:
        return []


def _has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _pick_first(columns: List[str], candidates: List[str]) -> str | None:
    for c in candidates:
        if c in columns:
            return c
    return None


def _read_quiz_rows(conn: sqlite3.Connection, learner_id: str) -> List[sqlite3.Row]:
    if not _has_table(conn, "quiz_results"):
        return []

    cols = _table_columns(conn, "quiz_results")

    learner_col = _pick_first(cols, ["learner_id", "student_id", "user_id"])
    correct_col = _pick_first(cols, ["is_correct", "correct"])
    time_col = _pick_first(cols, ["time_taken_sec", "elapsed_time", "time_taken"])
    ts_col = _pick_first(cols, ["timestamp", "created_at", "attempted_at"])
    concept_col = _pick_first(cols, ["concept_id", "content_concept_id"])
    quiz_id_col = _pick_first(cols, ["quiz_id", "id"])

    if learner_col is None:
        return []

    select_parts = [learner_col]
    alias_parts = [f"{learner_col} AS learner_id"]

    if correct_col:
        alias_parts.append(f"{correct_col} AS is_correct")
    else:
        alias_parts.append("NULL AS is_correct")

    if time_col:
        alias_parts.append(f"{time_col} AS time_taken_sec")
    else:
        alias_parts.append("NULL AS time_taken_sec")

    if ts_col:
        alias_parts.append(f"{ts_col} AS timestamp")
    else:
        alias_parts.append("NULL AS timestamp")

    if concept_col:
        alias_parts.append(f"{concept_col} AS concept_id")
    else:
        alias_parts.append("NULL AS concept_id")

    if quiz_id_col:
        alias_parts.append(f"{quiz_id_col} AS quiz_id")
    else:
        alias_parts.append("NULL AS quiz_id")

    sql = f"""
        SELECT {", ".join(alias_parts)}
        FROM quiz_results
        WHERE {learner_col} = ?
    """

    if ts_col:
        sql += f" ORDER BY {ts_col} ASC"
    elif quiz_id_col:
        sql += f" ORDER BY {quiz_id_col} ASC"

    conn.row_factory = sqlite3.Row
    return conn.execute(sql, (str(learner_id),)).fetchall()


def _read_knowledge_state(conn: sqlite3.Connection, learner_id: str) -> Dict[str, float]:
    if not _has_table(conn, "knowledge_state"):
        return {}

    cols = _table_columns(conn, "knowledge_state")
    learner_col = _pick_first(cols, ["learner_id", "student_id", "user_id"])
    state_col = _pick_first(cols, ["state_json", "mastery_json", "knowledge_state_json"])

    if learner_col is None or state_col is None:
        return {}

    row = conn.execute(
        f"""
        SELECT {state_col}
        FROM knowledge_state
        WHERE {learner_col} = ?
        ORDER BY ROWID DESC
        LIMIT 1
        """,
        (str(learner_id),),
    ).fetchone()

    if not row:
        return {}

    raw = row[0]
    parsed = parse_json_object(raw)
    return normalize_mastery_values(parsed)


def _read_behaviour_rows(conn: sqlite3.Connection, learner_id: str) -> List[sqlite3.Row]:
    if not _has_table(conn, "behaviour_state"):
        return []

    cols = _table_columns(conn, "behaviour_state")
    learner_col = _pick_first(cols, ["learner_id", "student_id", "user_id"])
    id_col = _pick_first(cols, ["id", "row_id"])

    score_col = _pick_first(cols, ["behavior_score", "behaviour_score", "anomaly_score"])
    wrong_col = _pick_first(cols, ["wrong_rate"])
    slow_col = _pick_first(cols, ["slow_rate"])
    low_conf_col = _pick_first(cols, ["low_confidence_rate"])
    hint_col = _pick_first(cols, ["hint_rate"])
    option_col = _pick_first(cols, ["option_change_rate"])

    if learner_col is None:
        return []

    alias_parts = []
    alias_parts.append(f"{learner_col} AS learner_id")

    alias_parts.append(f"{score_col} AS behavior_score" if score_col else "NULL AS behavior_score")
    alias_parts.append(f"{wrong_col} AS wrong_rate" if wrong_col else "NULL AS wrong_rate")
    alias_parts.append(f"{slow_col} AS slow_rate" if slow_col else "NULL AS slow_rate")
    alias_parts.append(
        f"{low_conf_col} AS low_confidence_rate" if low_conf_col else "NULL AS low_confidence_rate"
    )
    alias_parts.append(f"{hint_col} AS hint_rate" if hint_col else "NULL AS hint_rate")
    alias_parts.append(
        f"{option_col} AS option_change_rate" if option_col else "NULL AS option_change_rate"
    )

    sql = f"""
        SELECT {", ".join(alias_parts)}
        FROM behaviour_state
        WHERE {learner_col} = ?
    """
    if id_col:
        sql += f" ORDER BY {id_col} ASC"

    conn.row_factory = sqlite3.Row
    return conn.execute(sql, (str(learner_id),)).fetchall()


def _read_concept_domains(conn: sqlite3.Connection) -> Dict[str, str]:
    if not _has_table(conn, "concept_id_map"):
        return {}

    cols = _table_columns(conn, "concept_id_map")
    concept_col = _pick_first(cols, ["content_concept_id", "concept_id", "system_concept_id"])
    domain_col = _pick_first(cols, ["domain", "subject", "topic"])

    if concept_col is None or domain_col is None:
        return {}

    rows = conn.execute(
        f"""
        SELECT {concept_col}, {domain_col}
        FROM concept_id_map
        """
    ).fetchall()

    output: Dict[str, str] = {}
    for concept_id, domain in rows:
        if concept_id is None:
            continue
        output[str(concept_id)] = str(domain) if domain is not None else str(concept_id)
    return output


def _compute_consistency_score(timestamps: List[datetime]) -> float:
    if len(timestamps) <= 1:
        return 0.0

    timestamps = sorted(timestamps)
    gaps = []
    for i in range(1, len(timestamps)):
        gap_days = (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400.0
        gaps.append(max(0.0, gap_days))

    if not gaps:
        return 0.0

    avg_gap = mean(gaps, default=0.0)
    if avg_gap <= 0:
        return 1.0

    gap_variation = mean([abs(g - avg_gap) for g in gaps], default=0.0)
    score = 1.0 / (1.0 + gap_variation)
    return max(0.0, min(1.0, score))


def _compute_performance_trend(correctness: List[float]) -> float:
    if len(correctness) < 2:
        return 0.0

    half = max(1, len(correctness) // 2)
    first_half = mean(correctness[:half], default=0.0)
    second_half = mean(correctness[half:], default=0.0)
    return safe_round(second_half - first_half, 4)


def _compute_repeated_failure_count(quiz_rows: List[sqlite3.Row]) -> int:
    failures_by_concept: Dict[str, int] = {}
    for row in quiz_rows:
        concept_id = row["concept_id"]
        if concept_id is None:
            continue
        is_correct = safe_int(row["is_correct"], 0)
        if is_correct == 0:
            failures_by_concept[str(concept_id)] = failures_by_concept.get(str(concept_id), 0) + 1
    return sum(1 for _, cnt in failures_by_concept.items() if cnt >= 2)


def extract_features(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    quiz_rows = _read_quiz_rows(conn, learner_id)
    mastery = _read_knowledge_state(conn, learner_id)
    behaviour_rows = _read_behaviour_rows(conn, learner_id)
    concept_to_domain = _read_concept_domains(conn)

    correctness_values = [safe_float(r["is_correct"], 0.0) for r in quiz_rows]
    time_values = [safe_float(r["time_taken_sec"], 0.0) for r in quiz_rows if r["time_taken_sec"] is not None]

    timestamps = []
    active_days = set()
    for r in quiz_rows:
        ts = parse_timestamp(r["timestamp"])
        if ts is not None:
            timestamps.append(ts)
            active_days.add(ts.date().isoformat())

    avg_mastery = mean(list(mastery.values()), default=0.0)
    weak_concept_count = sum(1 for v in mastery.values() if v < 0.4)
    strong_concept_count = sum(1 for v in mastery.values() if v >= 0.75)

    strength_areas = top_domains(
        concept_scores=mastery,
        concept_to_domain=concept_to_domain,
        threshold=0.75,
        reverse=True,
        limit=5,
    )
    weak_areas = top_domains(
        concept_scores=mastery,
        concept_to_domain=concept_to_domain,
        threshold=0.4,
        reverse=False,
        limit=5,
    )

    avg_anomaly_score = mean(
        [safe_float(r["behavior_score"], 0.0) for r in behaviour_rows],
        default=0.0,
    )
    avg_wrong_rate = mean(
        [safe_float(r["wrong_rate"], 0.0) for r in behaviour_rows],
        default=0.0,
    )
    avg_slow_rate = mean(
        [safe_float(r["slow_rate"], 0.0) for r in behaviour_rows],
        default=0.0,
    )
    avg_low_confidence_rate = mean(
        [safe_float(r["low_confidence_rate"], 0.0) for r in behaviour_rows],
        default=0.0,
    )
    avg_hint_rate = mean(
        [safe_float(r["hint_rate"], 0.0) for r in behaviour_rows],
        default=0.0,
    )
    avg_option_change_rate = mean(
        [safe_float(r["option_change_rate"], 0.0) for r in behaviour_rows],
        default=0.0,
    )

    struggle_score = safe_round(
        (
            avg_wrong_rate
            + avg_slow_rate
            + avg_low_confidence_rate
            + avg_hint_rate
            + avg_option_change_rate
        ) / 5.0,
        4,
    )

    features: Dict[str, Any] = {
        "learner_id": str(learner_id),
        "total_attempts": len(quiz_rows),
        "avg_correctness": safe_round(mean(correctness_values, default=0.0), 4),
        "avg_time_taken_sec": safe_round(mean(time_values, default=0.0), 4),
        "active_days": len(active_days),
        "consistency_score": safe_round(_compute_consistency_score(timestamps), 4),
        "repeated_failure_count": _compute_repeated_failure_count(quiz_rows),
        "performance_trend_score": safe_round(_compute_performance_trend(correctness_values), 4),
        "avg_mastery": safe_round(avg_mastery, 4),
        "weak_concept_count": weak_concept_count,
        "strong_concept_count": strong_concept_count,
        "strength_areas": strength_areas,
        "weak_areas": weak_areas,
        "avg_anomaly_score": safe_round(avg_anomaly_score, 4),
        "avg_wrong_rate": safe_round(avg_wrong_rate, 4),
        "avg_slow_rate": safe_round(avg_slow_rate, 4),
        "avg_low_confidence_rate": safe_round(avg_low_confidence_rate, 4),
        "avg_hint_rate": safe_round(avg_hint_rate, 4),
        "avg_option_change_rate": safe_round(avg_option_change_rate, 4),
        "struggle_score": struggle_score,
    }

    return features