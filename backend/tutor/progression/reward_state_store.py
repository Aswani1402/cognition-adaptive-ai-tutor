from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


DB_PATH = Path("external/core_data/tutor.db")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _same_day(previous_date: Optional[str], today: str) -> bool:
    return bool(previous_date) and previous_date == today


def _is_previous_day(previous_date: Optional[str], today: str) -> bool:
    if not previous_date:
        return False

    try:
        previous = date.fromisoformat(previous_date)
        current = date.fromisoformat(today)
        return (current - previous).days == 1
    except Exception:
        return False

def _same_iso_week(previous_date: Optional[str], today: str) -> bool:
    if not previous_date:
        return False

    try:
        previous = date.fromisoformat(previous_date)
        current = date.fromisoformat(today)
        return previous.isocalendar()[:2] == current.isocalendar()[:2]
    except Exception:
        return False

def persist_reward_state(
        progression_reward_output: Dict[str, Any],
        db_path: Path | str = DB_PATH,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
    db_path = Path(db_path)

    learner_id = _safe_str(progression_reward_output.get("learner_id"))
    concept_id = _safe_str(progression_reward_output.get("concept_id"))
    concept_name = _safe_str(progression_reward_output.get("concept_name"))

    progression_result = progression_reward_output.get("progression_result", {})
    reward_state = progression_reward_output.get("reward_state", {})
    celebration = progression_reward_output.get("celebration", {})
    model_output = progression_reward_output.get("model_comparison_output", {})

    xp_awarded = _safe_int(reward_state.get("xp_awarded"), 0)
    reward_reason = _safe_str(reward_state.get("reward_reason"))
    celebration_type = _safe_str(celebration.get("type"))
    progression_action = _safe_str(progression_result.get("progression_action"))

    promotion_allowed = 1 if progression_result.get("promotion_allowed") else 0
    model_progression_action = _safe_str(model_output.get("model_progression_action"))
    model_promotion_allowed = 1 if model_output.get("model_promotion_allowed") else 0

    if not learner_id:
        return {
            "status": "error",
            "module": "RewardStateStore",
            "reason": "Missing learner_id.",
        }
    if dry_run:
        return {
            "status": "success",
            "module": "RewardStateStore",
            "mode": "dry_run",
            "learner_id": learner_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "xp_awarded": xp_awarded,
            "total_xp": None,
            "daily_xp": None,
            "weekly_xp": None,
            "current_level": None,
            "current_streak": None,
            "longest_streak": None,
            "event_logged": False,
            "reward_reason": reward_reason,
            "celebration_type": celebration_type,
            "progression_action": progression_action,
            "promotion_allowed": bool(promotion_allowed),
            "model_progression_action": model_progression_action,
            "model_promotion_allowed": bool(model_promotion_allowed),
            "reason": "Dry run enabled. Reward state was computed but not written to DB.",
        }

    today = date.today().isoformat()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT total_xp,
               daily_xp,
               weekly_xp,
               current_level,
               last_daily_reset_date,
               last_weekly_reset_date
        FROM learner_xp_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    xp_row = cursor.fetchone()

    if xp_row:
        (
            existing_total_xp,
            existing_daily_xp,
            existing_weekly_xp,
            existing_level,
            last_daily_reset_date,
            last_weekly_reset_date,
        ) = xp_row

        if _same_day(last_daily_reset_date, today):
            new_daily_xp = _safe_int(existing_daily_xp) + xp_awarded
        else:
            new_daily_xp = xp_awarded

        if _same_iso_week(last_weekly_reset_date, today):
            new_weekly_xp = _safe_int(existing_weekly_xp) + xp_awarded
        else:
            new_weekly_xp = xp_awarded

        new_total_xp = _safe_int(existing_total_xp) + xp_awarded
        new_level = max(_safe_int(existing_level, 1), 1 + new_total_xp // 100)

        cursor.execute(
            """
            UPDATE learner_xp_state
            SET total_xp = ?,
                daily_xp = ?,
                weekly_xp = ?,
                current_level = ?,
                last_daily_reset_date = ?,
                last_weekly_reset_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
            """,
            (
                new_total_xp,
                new_daily_xp,
                new_weekly_xp,
                new_level,
                today,
                today,
                learner_id,
            ),
        )
    else:
        new_total_xp = xp_awarded
        new_daily_xp = xp_awarded
        new_weekly_xp = xp_awarded
        new_level = max(1, 1 + new_total_xp // 100)

        cursor.execute(
            """
            INSERT INTO learner_xp_state (
                learner_id,
                total_xp,
                daily_xp,
                weekly_xp,
                current_level,
                last_daily_reset_date,
                last_weekly_reset_date,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                learner_id,
                new_total_xp,
                new_daily_xp,
                new_weekly_xp,
                new_level,
                today,
                today,
            ),
        )

    cursor.execute(
        """
        SELECT current_streak, longest_streak, last_active_date
        FROM learner_streak_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    row = cursor.fetchone()

    if row:
        current_streak, longest_streak, last_active_date = row

        if _same_day(last_active_date, today):
            new_streak = current_streak
        elif _is_previous_day(last_active_date, today):
            new_streak = current_streak + 1
        else:
            new_streak = 1

        new_longest = max(longest_streak, new_streak)

        cursor.execute(
            """
            UPDATE learner_streak_state
            SET current_streak = ?,
                longest_streak = ?,
                last_active_date = ?,
                streak_updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
            """,
            (new_streak, new_longest, today, learner_id),
        )
    else:
        new_streak = 1
        new_longest = 1

        cursor.execute(
            """
            INSERT INTO learner_streak_state (
                learner_id,
                current_streak,
                longest_streak,
                last_active_date,
                streak_updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (learner_id, new_streak, new_longest, today),
        )

    cursor.execute(
        """
        INSERT INTO reward_event_log (
            learner_id,
            concept_id,
            concept_name,
            xp_awarded,
            reward_reason,
            celebration_type,
            progression_action,
            promotion_allowed,
            model_progression_action,
            model_promotion_allowed,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            learner_id,
            concept_id,
            concept_name,
            xp_awarded,
            reward_reason,
            celebration_type,
            progression_action,
            promotion_allowed,
            model_progression_action,
            model_promotion_allowed,
        ),
    )

    conn.commit()

    cursor.execute(
        """
        SELECT total_xp,
               daily_xp,
               weekly_xp,
               current_level,
               last_daily_reset_date,
               last_weekly_reset_date
        FROM learner_xp_state
        WHERE learner_id = ?
        """,
        (learner_id,),
    )
    xp_row = cursor.fetchone()

    conn.close()

    (
        total_xp,
        daily_xp,
        weekly_xp,
        current_level,
        last_daily_reset_date,
        last_weekly_reset_date,
    ) = xp_row if xp_row else (0, 0, 0, 1, None, None)


    return {
        "status": "success",
        "module": "RewardStateStore",
        "learner_id": learner_id,
        "xp_awarded": xp_awarded,
        "total_xp": total_xp,
        "daily_xp": daily_xp,
        "weekly_xp": weekly_xp,
        "current_level": current_level,
        "last_daily_reset_date": last_daily_reset_date,
        "last_weekly_reset_date": last_weekly_reset_date,
        "current_streak": new_streak,
        "longest_streak": new_longest,
        "event_logged": True,
    }