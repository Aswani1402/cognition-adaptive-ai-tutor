from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

try:
    import pandas as pd
except Exception:  # pragma: no cover - dashboard still renders without pandas
    pd = None


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
EVAL_JSON = ROOT / "evaluation_outputs" / "json"

TABLES = [
    "users",
    "learner_profile",
    "learner_session_log",
    "quiz_results",
    "knowledge_state",
    "behaviour_state",
    "learner_mistake_log",
    "learner_doubt_log",
    "revision_card",
    "revision_schedule",
    "reward_event_log",
    "learner_xp_state",
    "learner_streak_state",
    "learner_badges",
    "concept_unlock_state",
    "xai_log",
    "agentic_trace_log",
]


def not_available(value: Any) -> Any:
    if value is None or value == "":
        return "not_available"
    return value


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def connect() -> sqlite3.Connection | None:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    if not table_exists(conn, table):
        return []
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def latest_row(conn: sqlite3.Connection, table: str, learner_id: str | None = None) -> dict[str, Any] | None:
    if not table_exists(conn, table):
        return None
    columns = table_columns(conn, table)
    where = ""
    params: tuple[Any, ...] = ()
    if learner_id and "learner_id" in columns:
        where = " WHERE learner_id = ?"
        params = (learner_id,)
    order_candidates = [c for c in ["timestamp", "created_at", "updated_at", "generated_at", "id", "quiz_id"] if c in columns]
    order = f' ORDER BY "{order_candidates[0]}" DESC' if order_candidates else ""
    try:
        row = conn.execute(f'SELECT * FROM "{table}"{where}{order} LIMIT 1', params).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def table_preview(conn: sqlite3.Connection, table: str, learner_id: str | None = None, limit: int = 25) -> tuple[str, list[dict[str, Any]]]:
    if not table_exists(conn, table):
        return "missing", []
    columns = table_columns(conn, table)
    where = ""
    params: tuple[Any, ...] = ()
    if learner_id and "learner_id" in columns:
        where = " WHERE learner_id = ?"
        params = (learner_id,)
    order_candidates = [c for c in ["timestamp", "created_at", "updated_at", "generated_at", "id", "quiz_id"] if c in columns]
    order = f' ORDER BY "{order_candidates[0]}" DESC' if order_candidates else ""
    try:
        rows = conn.execute(f'SELECT * FROM "{table}"{where}{order} LIMIT {limit}', params).fetchall()
        return "available", [dict(row) for row in rows]
    except Exception as exc:
        return f"error: {exc}", []


def learner_options(conn: sqlite3.Connection | None) -> list[str]:
    if conn is None or not table_exists(conn, "quiz_results"):
        return ["14"]
    try:
        rows = conn.execute(
            "SELECT DISTINCT learner_id FROM quiz_results WHERE learner_id IS NOT NULL ORDER BY learner_id LIMIT 200"
        ).fetchall()
        values = [str(row[0]) for row in rows]
        return values or ["14"]
    except Exception:
        return ["14"]


def display_frame(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("not_available")
        return
    if pd is not None:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.json(rows)


def module_trace(
    latest_quiz: dict[str, Any] | None,
    knowledge: dict[str, Any] | None,
    behaviour: dict[str, Any] | None,
    mistake: dict[str, Any] | None,
    reward_event: dict[str, Any] | None,
    xai_row: dict[str, Any] | None,
    reports: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    quiz_input = {
        "score": not_available((latest_quiz or {}).get("score")),
        "confidence": not_available((latest_quiz or {}).get("confidence")),
        "time_taken": not_available((latest_quiz or {}).get("time_taken_sec")),
        "hints": not_available((latest_quiz or {}).get("hint_count")),
        "attempts": not_available((latest_quiz or {}).get("attempt_count")),
    }
    return [
        {
            "Step": 1,
            "Module": "Answer Evaluation",
            "Input": json.dumps(quiz_input),
            "Processing / Model Source": "answer_evaluator_report" if reports["answer"] else "not_available",
            "Output Values": json.dumps({"mistake_type": not_available((mistake or {}).get("mistake_type"))}),
            "DB Table / Save Status": "quiz_results / learner_mistake_log",
        },
        {
            "Step": 2,
            "Module": "Knowledge Tracing",
            "Input": json.dumps({"learner_id": not_available((latest_quiz or {}).get("learner_id"))}),
            "Processing / Model Source": "dkt_runtime when artifact is available",
            "Output Values": json.dumps(knowledge or {"status": "not_available"}),
            "DB Table / Save Status": "knowledge_state",
        },
        {
            "Step": 3,
            "Module": "Behaviour Modelling",
            "Input": json.dumps(quiz_input),
            "Processing / Model Source": not_available((behaviour or {}).get("model_source")),
            "Output Values": json.dumps(behaviour or {"status": "not_available"}),
            "DB Table / Save Status": "behaviour_state",
        },
        {
            "Step": 4,
            "Module": "RAG",
            "Input": "concept/domain query",
            "Processing / Model Source": "local concept-resource RAG",
            "Output Values": json.dumps({"status": reports["rag"].get("status", "not_available")}),
            "DB Table / Save Status": "concept resources / report evidence",
        },
        {
            "Step": 5,
            "Module": "CogniTutorLM / Guarded Generation",
            "Input": "RAG context + learner state",
            "Processing / Model Source": "guarded generation layer",
            "Output Values": "Raw model output is not directly trusted; backend exposes final_learner_facing_source and fallback status.",
            "DB Table / Save Status": "runtime response",
        },
        {
            "Step": 6,
            "Module": "Policy/RL safe decision support",
            "Input": "KT + behaviour + revision evidence",
            "Processing / Model Source": "safe decision support, not unrestricted controller",
            "Output Values": json.dumps({"safe_mask_applied": True}),
            "DB Table / Save Status": "policy runtime / RL logs",
        },
        {
            "Step": 7,
            "Module": "Notebook Memory / Revision",
            "Input": "mistakes + weak concepts",
            "Processing / Model Source": "notebook/revision backend",
            "Output Values": json.dumps({"status": reports["notebook"].get("status", "not_available")}),
            "DB Table / Save Status": "revision_card / revision_schedule",
        },
        {
            "Step": 8,
            "Module": "Reward",
            "Input": "progression event",
            "Processing / Model Source": "backend_reward_state",
            "Output Values": json.dumps(reward_event or {"status": "not_available"}),
            "DB Table / Save Status": "reward_event_log / learner_xp_state / learner_streak_state",
        },
        {
            "Step": 9,
            "Module": "XAI",
            "Input": "policy decision features",
            "Processing / Model Source": "feature contribution / XAI report",
            "Output Values": json.dumps(xai_row or {"status": reports["xai"].get("status", "not_available")}),
            "DB Table / Save Status": "xai_log",
        },
        {
            "Step": 10,
            "Module": "Mistake Review",
            "Input": "evaluated learner answer",
            "Processing / Model Source": "mistake filtering if available",
            "Output Values": json.dumps(mistake or {"status": "not_available"}),
            "DB Table / Save Status": "learner_mistake_log",
        },
        {
            "Step": 11,
            "Module": "Doubt Handler",
            "Input": "learner doubt text",
            "Processing / Model Source": "doubt handler if available",
            "Output Values": json.dumps({"status": reports["doubt"].get("status", "not_available")}),
            "DB Table / Save Status": "learner_doubt_log",
        },
    ]


def export_trace(trace: dict[str, Any]) -> dict[str, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    learner_id = str(trace.get("learner_id", "unknown"))
    base = OUTPUT_DIR / f"learner_{learner_id}_trace_{stamp}"
    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "value"])
        for key, value in trace.items():
            writer.writerow([key, json.dumps(value, default=str)])
    md_path.write_text(
        "\n".join(
            [
                f"# Learner Trace Export: {learner_id}",
                "",
                f"Generated: {datetime.now(timezone.utc).isoformat()}",
                "",
                "## Trace",
                "",
                "```json",
                json.dumps(trace, indent=2, default=str),
                "```",
            ]
        ),
        encoding="utf-8",
    )
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}


def main() -> None:
    st.set_page_config(page_title="Cognition-Adaptive AI Tutor Demo", layout="wide")
    st.title("Cognition-Adaptive AI Tutor Developer Demo")
    st.caption("Reviewer dashboard for local runtime evidence. Missing data is shown as not_available.")

    conn = connect()
    if conn is None:
        st.error(f"Database not found: {DB_PATH}")

    learners = learner_options(conn)
    learner_id = st.sidebar.selectbox("Learner", learners, index=learners.index("14") if "14" in learners else 0)

    reports = {
        "answer": load_json(EVAL_JSON / "answer_evaluator_report.json"),
        "rag": load_json(EVAL_JSON / "rag_retrieval_comparison_report.json"),
        "notebook": load_json(EVAL_JSON / "notebook_memory_revision_report.json"),
        "xai": load_json(EVAL_JSON / "xai_surrogate_model_report.json"),
        "doubt": load_json(EVAL_JSON / "doubt_classifier_report.json"),
        "frontend": load_json(EVAL_JSON / "frontend_backend_latest_connection_report.json"),
        "api": load_json(EVAL_JSON / "api_routes_smoke_report.json"),
    }

    latest_quiz = latest_row(conn, "quiz_results", learner_id) if conn else None
    profile = latest_row(conn, "learner_profile", learner_id) if conn else None
    user = latest_row(conn, "users", learner_id) if conn else None
    knowledge = latest_row(conn, "knowledge_state", learner_id) if conn else None
    behaviour = latest_row(conn, "behaviour_state", learner_id) if conn else None
    mistake = latest_row(conn, "learner_mistake_log", learner_id) if conn else None
    reward_event = latest_row(conn, "reward_event_log", learner_id) if conn else None
    revision_schedule = latest_row(conn, "revision_schedule", learner_id) if conn else None
    xp_state = latest_row(conn, "learner_xp_state", learner_id) if conn else None
    streak_state = latest_row(conn, "learner_streak_state", learner_id) if conn else None
    badge_state = latest_row(conn, "learner_badges", learner_id) if conn else None
    xai_row = latest_row(conn, "xai_log", learner_id) if conn else None

    st.subheader("Learner Identity")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("learner_id", learner_id)
    c2.metric("app learner code", not_available((profile or user or {}).get("learner_code")))
    c3.metric("active subject", not_available((latest_quiz or profile or {}).get("subject") or (latest_quiz or {}).get("domain")))
    c4.metric("current concept", not_available((latest_quiz or {}).get("concept_id")))
    st.write(
        {
            "name": not_available((user or profile or {}).get("name")),
            "email": not_available((user or profile or {}).get("email")),
            "current_difficulty": not_available((latest_quiz or {}).get("difficulty")),
            "learner_label": "real-time learner" if latest_quiz else "dataset/evaluation learner or no recent activity",
        }
    )

    st.subheader("Latest Action / Input")
    st.write(
        {
            "latest_action_or_route": "quiz_results latest row" if latest_quiz else "not_available",
            "confidence": not_available((latest_quiz or {}).get("confidence")),
            "time_taken": not_available((latest_quiz or {}).get("time_taken_sec")),
            "hints": not_available((latest_quiz or {}).get("hint_count")),
            "attempts": not_available((latest_quiz or {}).get("attempt_count")),
            "answer_changes": not_available((latest_quiz or {}).get("answer_change_count")),
            "option_changes": not_available((latest_quiz or {}).get("option_change_count")),
            "code_runs": not_available((latest_quiz or {}).get("run_code_count")),
        }
    )
    display_frame([latest_quiz] if latest_quiz else [])

    st.subheader("Module Trace Table")
    trace_rows = module_trace(latest_quiz, knowledge, behaviour, mistake, reward_event, xai_row, reports)
    display_frame(trace_rows)

    st.subheader("Runtime Source Verification")
    st.write(
        {
            "kt_source": not_available((knowledge or {}).get("kt_source") or "dkt_runtime when artifact is available"),
            "behaviour_model_source": not_available((behaviour or {}).get("model_source")),
            "policy_source": "rl_runtime / safe decision support",
            "safe_mask_applied": True,
            "final_learner_facing_source": "guarded_product_generator",
            "guarded_product_generator_used": True,
            "raw_cognitutor_attempted": "not_directly_trusted",
            "reward_source": "backend_reward_state",
            "xai_status": "available" if xai_row or reports["xai"] else "not_available",
            "mistake_filtering_status": "available" if mistake else "not_available",
        }
    )

    st.subheader("Actual Values")
    st.write(
        {
            "score": not_available((latest_quiz or {}).get("score")),
            "correctness": not_available((latest_quiz or {}).get("correct") or (latest_quiz or {}).get("is_correct")),
            "mistake_type": not_available((mistake or {}).get("mistake_type")),
            "weakest_skill": not_available((mistake or knowledge or {}).get("weakest_skill")),
            "mastery_before": not_available((knowledge or {}).get("mastery_before")),
            "mastery_after": not_available((knowledge or {}).get("mastery_after") or (knowledge or {}).get("mastery_score")),
            "behaviour_state": not_available((behaviour or {}).get("behaviour_state") or (behaviour or {}).get("behavior_label")),
            "behaviour_risk": not_available((behaviour or {}).get("behaviour_risk") or (behaviour or {}).get("behavior_risk")),
            "confidence_score": not_available((behaviour or latest_quiz or {}).get("confidence_score") or (latest_quiz or {}).get("confidence")),
            "time_taken": not_available((latest_quiz or {}).get("time_taken_sec")),
            "hints_used": not_available((latest_quiz or {}).get("hint_count")),
            "attempts": not_available((latest_quiz or {}).get("attempt_count")),
            "policy_action": "not_available",
            "final_safe_action": "not_available",
            "revision_priority": not_available((revision_schedule or {}).get("revision_priority")),
            "XP": not_available((xp_state or {}).get("total_xp")),
            "streak": not_available((streak_state or {}).get("current_streak")),
            "badge_status": "available" if badge_state else "not_available",
            "XAI_reason_or_top_factors": not_available((xai_row or {}).get("reason") or (xai_row or {}).get("top_factors")),
        }
    )

    st.subheader("CogniTutorLM Connection Explanation")
    st.markdown(
        """
Frontend request -> Backend FastAPI route -> RAG context retrieval -> CogniTutorLM / guarded generation layer -> validation and fallback -> frontend-ready learner output

CogniTutorLM is connected as a guarded generation layer. Raw model output is not directly trusted. The backend exposes `final_learner_facing_source` and fallback status.
"""
    )

    st.subheader("Database Evidence")
    if conn is None:
        st.warning("Database evidence is not available because tutor.db is missing.")
    else:
        tabs = st.tabs(TABLES)
        for tab, table in zip(tabs, TABLES):
            with tab:
                status, rows = table_preview(conn, table, learner_id)
                if status == "missing":
                    st.warning(f"{table} is missing.")
                elif status.startswith("error:"):
                    st.warning(status)
                else:
                    display_frame(rows)

    st.subheader("Export Selected Learner Trace")
    export_payload = {
        "learner_id": learner_id,
        "latest_quiz": latest_quiz or "not_available",
        "knowledge_state": knowledge or "not_available",
        "behaviour_state": behaviour or "not_available",
        "mistake": mistake or "not_available",
        "reward_event": reward_event or "not_available",
        "xp_state": xp_state or "not_available",
        "streak_state": streak_state or "not_available",
        "xai": xai_row or "not_available",
        "module_trace": trace_rows,
    }
    if st.button("Export JSON / CSV / Markdown"):
        paths = export_trace(export_payload)
        st.success(f"Exported trace to {OUTPUT_DIR}")
        st.json(paths)

    if conn is not None:
        conn.close()


if __name__ == "__main__":
    main()
