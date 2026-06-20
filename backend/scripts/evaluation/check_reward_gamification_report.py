from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.migration.add_badge_goal_unlock_tables import run_migration
from tutor.reward.badge_engine import BadgeEngine
from tutor.reward.concept_unlock_store import ConceptUnlockStore
from tutor.reward.daily_goal_engine import DailyGoalEngine


DB_PATH = Path("external/core_data/tutor.db")
JSON_REPORT = Path("evaluation_outputs/json/reward_gamification_report.json")
MD_REPORT = Path("evaluation_outputs/reports/reward_gamification_report.md")
LEARNER_ID = "14"


TABLES = [
    "achievement_badges",
    "learner_badges",
    "daily_goal_state",
    "concept_unlock_state",
    "reward_event_log",
    "learner_xp_state",
    "learner_streak_state",
]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,)).fetchone())


def _count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "concept_unlock_state"):
        return {}
    return {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT unlock_status, COUNT(*) FROM concept_unlock_state GROUP BY unlock_status"
        ).fetchall()
    }


def _latest_mastery(conn: sqlite3.Connection, learner_id: str) -> float:
    row = conn.execute("SELECT state_json FROM knowledge_state WHERE student_id = ?", (learner_id,)).fetchone()
    if not row:
        return 0.0
    try:
        state = json.loads(row[0])
        return float(state.get("predicted_mastery_last") or 0.0)
    except Exception:
        return 0.0


def build_report() -> dict[str, Any]:
    run_migration(DB_PATH)
    badge_output = BadgeEngine(DB_PATH).evaluate_and_award(LEARNER_ID)
    daily_goal = DailyGoalEngine(DB_PATH).update_goal(LEARNER_ID)
    conn = sqlite3.connect(DB_PATH)
    try:
        mastery = _latest_mastery(conn, LEARNER_ID)
    finally:
        conn.close()
    concept_unlock = ConceptUnlockStore(DB_PATH).update_unlock_state(
        learner_id=LEARNER_ID,
        concept_id="1",
        domain="Python",
        concept_name="Variables",
        mastery_score=mastery,
        promotion_confidence=0.35,
        prerequisites_met=True,
        fused_score=0.32,
        review_due=True,
        evidence={"source": "reward_gamification_report_sample"},
    )
    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {table: {"exists": _table_exists(conn, table), "row_count": _count(conn, table)} for table in TABLES}
        unlock_counts = _status_counts(conn)
        metrics = {
            "badge_count": _count(conn, "achievement_badges"),
            "learner_badge_count": _count(conn, "learner_badges"),
            "daily_goal_completion_rate": daily_goal.get("completion_rate", 0.0),
            "concept_unlock_count": _count(conn, "concept_unlock_state"),
            "locked_count": unlock_counts.get("locked", 0),
            "recommended_count": unlock_counts.get("recommended", 0),
            "unlocked_count": unlock_counts.get("unlocked", 0),
            "review_count": unlock_counts.get("review", 0),
            "reward_event_count": _count(conn, "reward_event_log"),
            "streak_availability": tables["learner_streak_state"]["exists"] and tables["learner_streak_state"]["row_count"] > 0,
        }
    finally:
        conn.close()

    report = {
        "status": "success" if all(item["exists"] for item in tables.values()) else "warning",
        "module": "reward_gamification_report",
        "table_existence": tables,
        "badge_engine_status": badge_output.get("status"),
        "daily_goal_status": daily_goal.get("status"),
        "concept_unlock_status": concept_unlock.get("status"),
        "xp_streak_integration_status": {
            "reward_event_log": tables["reward_event_log"],
            "learner_xp_state": tables["learner_xp_state"],
            "learner_streak_state": tables["learner_streak_state"],
        },
        "sample_learner_gamification_packet": {
            "learner_id": LEARNER_ID,
            "badges": badge_output,
            "daily_goal": daily_goal,
            "concept_unlock": concept_unlock,
        },
        "metrics": metrics,
        "limitations": [
            "Badge criteria are transparent achievement thresholds over available tutor evidence.",
            "Daily goal progress depends on same-day reward, quiz, and revision logs.",
            "Unlock thresholds should be tuned against future learner outcome data.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    metrics = report["metrics"]
    lines = [
        "# Reward Gamification Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Metrics",
        "",
    ]
    for name, value in metrics.items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Table Existence", ""])
    for table, info in report["table_existence"].items():
        lines.append(f"- {table}: exists={info['exists']}, rows={info['row_count']}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: reward_gamification_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
