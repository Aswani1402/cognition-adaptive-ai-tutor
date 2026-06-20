from __future__ import annotations

import sqlite3
from typing import Any

from tutor.knowledge_state.behavior import BehaviourBuffer
from tutor.knowledge_state.behavior_model.infer import predict_behavior


BEHAVIOUR_BUFFER = BehaviourBuffer(seq_len=20)


def _build_feature_vectors_from_recent_quiz(
    conn: sqlite3.Connection, learner_id: str
) -> list[list[float]]:
    rows = conn.execute(
        """
        SELECT
            COALESCE(is_correct, 0),
            COALESCE(time_taken_sec, 0),
            COALESCE(confidence, 0),
            COALESCE(hint_count, 0),
            COALESCE(option_changes_count, 0)
        FROM quiz_results
        WHERE learner_id = ?
        ORDER BY quiz_id DESC
        LIMIT 20
        """,
        (learner_id,),
    ).fetchall()

    if not rows:
        return []

    feature_vectors = []
    for row in reversed(rows):
        is_correct = float(row[0])
        time_taken = float(row[1])
        confidence = float(row[2])
        hint_count = float(row[3])
        option_changes_count = float(row[4])

        wrong_flag = 0.0 if is_correct == 1.0 else 1.0
        slow_flag = 1.0 if time_taken > 30 else 0.0
        low_conf_flag = 1.0 if confidence < 0.5 else 0.0
        hint_flag = 1.0 if hint_count > 0 else 0.0
        option_change_flag = 1.0 if option_changes_count > 0 else 0.0

        feature_vectors.append([
            wrong_flag, slow_flag, low_conf_flag, hint_flag, option_change_flag
        ])

    return feature_vectors

def _label_from_score(score: float) -> str:
    if score >= 0.75:
        return "high_risk"
    if score >= 0.4:
        return "moderate_risk"
    return "stable"


def update_behavior_state(conn: sqlite3.Connection, learner_id: str) -> dict[str, Any]:
    feat_vecs = _build_feature_vectors_from_recent_quiz(conn, learner_id)
    if not feat_vecs:
        return {
            "learner_id": learner_id,
            "status": "no_quiz_data",
        }

    for feat_vec in feat_vecs:
        sequence = BEHAVIOUR_BUFFER.add(learner_id, feat_vec)


    wrong_rate = sum(v[0] for v in sequence) / len(sequence)
    slow_rate = sum(v[1] for v in sequence) / len(sequence)
    low_confidence_rate = sum(v[2] for v in sequence) / len(sequence)
    hint_rate = sum(v[3] for v in sequence) / len(sequence)
    option_change_rate = sum(v[4] for v in sequence) / len(sequence)

    if BEHAVIOUR_BUFFER.ready(learner_id):
        behavior_score = float(predict_behavior(sequence))
        model_used = True
    else:
        behavior_score = (
            wrong_rate
            + slow_rate
            + low_confidence_rate
            + hint_rate
            + option_change_rate
        ) / 5.0
        model_used = False

    behavior_score = round(behavior_score, 4)
    wrong_rate = round(wrong_rate, 4)
    slow_rate = round(slow_rate, 4)
    low_confidence_rate = round(low_confidence_rate, 4)
    hint_rate = round(hint_rate, 4)
    option_change_rate = round(option_change_rate, 4)

    behavior_label = _label_from_score(behavior_score)

    conn.execute(
        """
        INSERT INTO behaviour_state (
            learner_id,
            behavior_label,
            behavior_score,
            wrong_rate,
            slow_rate,
            low_confidence_rate,
            hint_rate,
            option_change_rate,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            learner_id,
            behavior_label,
            behavior_score,
            wrong_rate,
            slow_rate,
            low_confidence_rate,
            hint_rate,
            option_change_rate,
        ),
    )
    conn.commit()

    return {
        "learner_id": learner_id,
        "status": "success",
        "behavior_label": behavior_label,
        "behavior_score": behavior_score,
        "wrong_rate": wrong_rate,
        "slow_rate": slow_rate,
        "low_confidence_rate": low_confidence_rate,
        "hint_rate": hint_rate,
        "option_change_rate": option_change_rate,
        "sequence_length": len(sequence),
        "model_used": model_used,
    }