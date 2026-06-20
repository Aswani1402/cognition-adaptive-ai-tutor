from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from tutor.system.frontend_response_builder import build_frontend_response
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


DB_PATH = Path("external/core_data/tutor.db")
JSON_REPORT = Path("evaluation_outputs/json/multi_user_integrated_evaluation_report.json")
MD_REPORT = Path("evaluation_outputs/reports/multi_user_integrated_evaluation_report.md")
CSV_OUTPUT = Path("evaluation_outputs/csv/multi_user_integrated_evaluation.csv")

FIELDS = [
    "learner_id",
    "pipeline_status",
    "frontend_response_status",
    "latest_concept_id",
    "concept_name",
    "interaction_count",
    "wrong_answer_count",
    "avg_confidence",
    "KT_source",
    "KT_mastery",
    "KT_model_used",
    "KT_fallback_used",
    "behaviour_label",
    "behaviour_risk",
    "behaviour_confidence",
    "behaviour_source",
    "fused_score",
    "fused_label",
    "weakest_skill",
    "dominant_mistake_type",
    "selected_teaching_view",
    "final_strategy",
    "final_difficulty",
    "next_activity",
    "reward_xp_awarded",
    "promotion_allowed",
    "xai_top_factors",
    "review_due",
    "error",
]


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _nested_get(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _learner_stats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT learner_id,
               COUNT(*) AS interaction_count,
               SUM(CASE WHEN COALESCE(is_correct, 0) = 0 THEN 1 ELSE 0 END) AS wrong_answer_count,
               AVG(COALESCE(confidence, 0)) AS avg_confidence,
               MAX(timestamp) AS latest_timestamp
        FROM quiz_results
        WHERE learner_id IS NOT NULL AND TRIM(learner_id) <> ''
        GROUP BY learner_id
        ORDER BY interaction_count DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def select_learners(limit: int = 10) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        stats = _learner_stats(conn)
    finally:
        conn.close()
    by_id = {str(row["learner_id"]): row for row in stats}
    selected: list[dict[str, Any]] = []

    def add(row: dict[str, Any] | None) -> None:
        if not row:
            return
        learner_id = str(row["learner_id"])
        if learner_id not in {str(item["learner_id"]) for item in selected}:
            selected.append(row)

    add(by_id.get("14"))
    for row in stats[:3]:
        add(row)
    for row in stats[len(stats) // 2 : len(stats) // 2 + 3]:
        add(row)
    for row in reversed(stats[-10:]):
        add(row)
    for row in sorted(stats, key=lambda item: item.get("wrong_answer_count") or 0, reverse=True)[:5]:
        add(row)
    for row in sorted(stats, key=lambda item: item.get("avg_confidence") or 0)[:3]:
        add(row)
    for row in sorted(stats, key=lambda item: item.get("avg_confidence") or 0, reverse=True)[:3]:
        add(row)

    return selected[:limit]


def _latest_concept_id(learner_id: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT concept_id
            FROM quiz_results
            WHERE learner_id = ?
            ORDER BY
                CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                timestamp DESC,
                quiz_id DESC
            LIMIT 1
            """,
            (learner_id,),
        ).fetchone()
        return str(row[0]) if row and row[0] is not None else None
    finally:
        conn.close()


def evaluate_learner(stat: dict[str, Any]) -> dict[str, Any]:
    learner_id = str(stat["learner_id"])
    base = {
        "learner_id": learner_id,
        "interaction_count": stat.get("interaction_count"),
        "wrong_answer_count": stat.get("wrong_answer_count"),
        "avg_confidence": round(_safe_float(stat.get("avg_confidence"), 0.0) or 0.0, 4),
    }
    try:
        output = run_integrated_tutor_once(learner_id=learner_id, reward_dry_run=True)
        frontend = build_frontend_response(output)
        demo = _as_dict(output.get("demo_summary"))
        kt_data = _as_dict(_nested_get(output, "knowledge_state", "data", "data", default={}))
        behaviour = _as_dict(_nested_get(output, "behaviour_state", "data", default={}))
        behaviour_data = _as_dict(behaviour.get("data") or behaviour)
        fusion = _as_dict(output.get("evaluation_fusion_output"))
        mistake = _as_dict(output.get("mistake_analysis_output"))
        strategy = _as_dict(output.get("evidence_aware_teaching_strategy_output"))
        reward = _as_dict(output.get("progression_reward_output"))
        progression = _as_dict(reward.get("progression_result"))
        xai_evidence = _as_dict(_nested_get(output, "xai", "data", "evidence", "feature_contributions", default={}))
        review_queue = _nested_get(output, "forgetting_state", "data", "review_queue", default=[])
        return {
            **base,
            "pipeline_status": output.get("status"),
            "frontend_response_status": frontend.get("status"),
            "latest_concept_id": _latest_concept_id(learner_id) or demo.get("final_concept"),
            "concept_name": demo.get("final_concept_name") or _nested_get(frontend, "concept", "concept_name"),
            "KT_source": kt_data.get("source"),
            "KT_mastery": _safe_float(kt_data.get("predicted_mastery_last")),
            "KT_model_used": kt_data.get("model_used"),
            "KT_fallback_used": kt_data.get("fallback_used"),
            "behaviour_label": behaviour_data.get("behavior_label") or behaviour_data.get("behaviour_label"),
            "behaviour_risk": _safe_float(behaviour_data.get("behavior_risk") or behaviour_data.get("behaviour_risk")),
            "behaviour_confidence": _safe_float(behaviour_data.get("behavior_confidence") or behaviour_data.get("confidence")),
            "behaviour_source": behaviour_data.get("behavior_source") or behaviour_data.get("behaviour_source"),
            "fused_score": _safe_float(demo.get("fused_score") or fusion.get("fused_score")),
            "fused_label": demo.get("fused_label") or fusion.get("fused_label"),
            "weakest_skill": demo.get("weakest_skill") or _nested_get(fusion, "weakest_skill_signal", "weakest_skill"),
            "dominant_mistake_type": demo.get("dominant_mistake_type") or mistake.get("dominant_mistake_type"),
            "selected_teaching_view": demo.get("teaching_view") or strategy.get("teaching_view") or frontend.get("selected_teaching_view"),
            "final_strategy": demo.get("final_strategy"),
            "final_difficulty": demo.get("final_difficulty"),
            "next_activity": demo.get("next_activity") or strategy.get("next_activity"),
            "reward_xp_awarded": demo.get("reward_xp_awarded") or _nested_get(reward, "reward_state", "xp_awarded"),
            "promotion_allowed": demo.get("promotion_allowed") if demo.get("promotion_allowed") is not None else progression.get("promotion_allowed"),
            "xai_top_factors": json.dumps(xai_evidence.get("top_factors", demo.get("xai_top_factors", []))),
            "review_due": bool(review_queue),
            "error": "",
        }
    except Exception as exc:
        return {
            **base,
            "pipeline_status": "error",
            "frontend_response_status": "error",
            "latest_concept_id": _latest_concept_id(learner_id),
            "concept_name": None,
            "KT_source": None,
            "KT_mastery": None,
            "KT_model_used": None,
            "KT_fallback_used": None,
            "behaviour_label": None,
            "behaviour_risk": None,
            "behaviour_confidence": None,
            "behaviour_source": None,
            "fused_score": None,
            "fused_label": None,
            "weakest_skill": None,
            "dominant_mistake_type": None,
            "selected_teaching_view": None,
            "final_strategy": None,
            "final_difficulty": None,
            "next_activity": None,
            "reward_xp_awarded": None,
            "promotion_allowed": None,
            "xai_top_factors": "[]",
            "review_due": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _variation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [row for row in rows if row.get("pipeline_status") == "success"]

    def range_for(key: str) -> dict[str, Any]:
        values = [_safe_float(row.get(key)) for row in successes if _safe_float(row.get(key)) is not None]
        return {
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": round(mean(values), 6) if values else None,
        }

    return {
        "mastery_range": range_for("KT_mastery"),
        "behaviour_risk_range": range_for("behaviour_risk"),
        "teaching_view_distribution": dict(Counter(row.get("selected_teaching_view") for row in successes if row.get("selected_teaching_view"))),
        "strategy_distribution": dict(Counter(row.get("final_strategy") for row in successes if row.get("final_strategy"))),
        "mistake_type_distribution": dict(Counter(row.get("dominant_mistake_type") for row in successes if row.get("dominant_mistake_type"))),
        "reward_xp_distribution": dict(Counter(str(row.get("reward_xp_awarded")) for row in successes if row.get("reward_xp_awarded") is not None)),
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in FIELDS})


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Multi-User Integrated Evaluation Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Number of learners tested: {report['number_of_learners_tested']}",
        f"- Success count: {report['success_count']}",
        f"- Failure count: {report['failure_count']}",
        "",
        "## Learner-Wise Table",
        "",
        "| Learner | Status | Interactions | Mastery | Behaviour risk | View | Strategy | Mistake | XP |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: |",
    ]
    for row in report["learner_rows"]:
        lines.append(
            f"| {row.get('learner_id')} | {row.get('pipeline_status')} | {row.get('interaction_count')} | "
            f"{row.get('KT_mastery')} | {row.get('behaviour_risk')} | {row.get('selected_teaching_view')} | "
            f"{row.get('final_strategy')} | {row.get('dominant_mistake_type')} | {row.get('reward_xp_awarded')} |"
        )
    lines.extend(
        [
            "",
            "## Learner 14 Context",
            "",
            report["learner_14_demo_evidence"],
            "",
            "## Variation Summary",
            "",
            "```json",
            json.dumps(report["variation_summary"], indent=2, default=str),
            "```",
            "",
            "## Limitations",
            "",
        ]
    )
    for item in report["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def build_report() -> dict[str, Any]:
    learners = select_learners(limit=10)
    rows = [evaluate_learner(stat) for stat in learners]
    write_csv(rows)
    success_count = sum(1 for row in rows if row.get("pipeline_status") == "success")
    failure_count = len(rows) - success_count
    report = {
        "status": "success" if success_count == len(rows) else "warning",
        "module": "multi_user_integrated_evaluation",
        "number_of_learners_tested": len(rows),
        "success_count": success_count,
        "failure_count": failure_count,
        "learner_selection_basis": "Learners selected from quiz_results using interaction-count, wrong-answer, and confidence aggregates; learner_id 14 is included as one demo learner.",
        "learner_14_demo_evidence": (
            "Learner 14 is one row in this multi-user batch, not the only evaluation basis. "
            "Module-level reports use dataset-level logs and model/evaluation artifacts across tutor.db and generated benchmark datasets."
        ),
        "learner_rows": rows,
        "variation_summary": _variation(rows),
        "csv_output": str(CSV_OUTPUT),
        "limitations": [
            "This is a backend dry-run, not live frontend user traffic.",
            "reward_dry_run may not persist all reward event updates.",
            "API/frontend multi-user routing remains pending.",
            "Some learners may share similar outputs if historical logs have similar correctness/confidence patterns.",
        ],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    MD_REPORT.write_text(_markdown(report), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: multi_user_integrated_evaluation")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")
    print(f"CSV_OUTPUT: {CSV_OUTPUT}")


if __name__ == "__main__":
    main()
