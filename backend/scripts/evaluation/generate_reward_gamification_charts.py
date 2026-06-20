from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt

from scripts.migration.add_badge_goal_unlock_tables import run_migration


DB_PATH = Path("external/core_data/tutor.db")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/reward_gamification_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/reward_gamification_visualization_report.md")


def _rows(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    try:
        return conn.execute(sql).fetchall()
    except Exception:
        return []


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    run_migration(DB_PATH)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    charts = {}
    try:
        rows = _rows(
            conn,
            """
            SELECT b.badge_name, COUNT(lb.id)
            FROM achievement_badges b
            LEFT JOIN learner_badges lb ON lb.badge_id = b.badge_id
            GROUP BY b.badge_id, b.badge_name
            ORDER BY b.badge_name
            """,
        )
        path = CHART_DIR / "reward_badge_distribution.png"
        plt.figure(figsize=(9, 4.5))
        plt.bar([row[0] for row in rows], [row[1] for row in rows])
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Awards")
        plt.title("Reward Badge Distribution")
        _save(path)
        charts["reward_badge_distribution"] = str(path)

        rows = _rows(
            conn,
            "SELECT learner_id, completion_rate FROM daily_goal_state ORDER BY updated_at DESC LIMIT 20",
        )
        path = CHART_DIR / "reward_daily_goal_progress.png"
        plt.figure(figsize=(9, 4.5))
        plt.bar([row[0] for row in rows], [row[1] for row in rows])
        plt.xticks(rotation=35, ha="right")
        plt.ylim(0, 1)
        plt.ylabel("Completion rate")
        plt.title("Reward Daily Goal Progress")
        _save(path)
        charts["reward_daily_goal_progress"] = str(path)

        rows = _rows(
            conn,
            "SELECT unlock_status, COUNT(*) FROM concept_unlock_state GROUP BY unlock_status",
        )
        path = CHART_DIR / "reward_concept_unlock_status.png"
        plt.figure(figsize=(7, 4.5))
        plt.bar([row[0] for row in rows], [row[1] for row in rows])
        plt.ylabel("Concept count")
        plt.title("Reward Concept Unlock Status")
        _save(path)
        charts["reward_concept_unlock_status"] = str(path)

        rows = _rows(
            conn,
            "SELECT learner_id, total_xp FROM learner_xp_state ORDER BY total_xp DESC LIMIT 20",
        )
        path = CHART_DIR / "reward_xp_distribution.png"
        plt.figure(figsize=(9, 4.5))
        plt.bar([row[0] for row in rows], [row[1] for row in rows])
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Total XP")
        plt.title("Reward XP Distribution")
        _save(path)
        charts["reward_xp_distribution"] = str(path)

        rows = _rows(
            conn,
            "SELECT learner_id, current_streak FROM learner_streak_state ORDER BY current_streak DESC LIMIT 20",
        )
        path = CHART_DIR / "reward_streak_distribution.png"
        plt.figure(figsize=(9, 4.5))
        plt.bar([row[0] for row in rows], [row[1] for row in rows])
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Current streak")
        plt.title("Reward Streak Distribution")
        _save(path)
        charts["reward_streak_distribution"] = str(path)
    finally:
        conn.close()

    return {
        "status": "success" if charts else "warning",
        "module": "reward_gamification_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": charts,
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Reward Gamification Visualization Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: reward_gamification_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
