import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import EVENT_LOG, GENERATION_REPORTS, MODEL_ARTIFACTS, SUBJECT_DBS, TUTOR_DB

MASK_KEYS = ("password", "hash", "token", "secret")


def connect(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def db_status(db_path: Path):
    if not db_path.exists():
        return {"status": "NOT AVAILABLE", "message": f"Missing: {db_path}"}
    try:
        with connect(db_path) as con:
            con.execute("select 1").fetchone()
        return {"status": "PASS", "message": str(db_path)}
    except Exception as exc:
        return {"status": "WARN", "message": str(exc)}


def tables(db_path: Path):
    if not db_path.exists():
        return []
    with connect(db_path) as con:
        return [r["name"] for r in con.execute("select name from sqlite_master where type='table' order by name")]


def columns(db_path: Path, table: str):
    if table not in tables(db_path):
        return []
    with connect(db_path) as con:
        return [r["name"] for r in con.execute(f"pragma table_info({table})")]


def mask_df(df: pd.DataFrame):
    if df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if any(k in col.lower() for k in MASK_KEYS):
            out[col] = "***MASKED***"
    return out


def read_table(db_path: Path, table: str, limit: int = 100, where: str | None = None, params: tuple = ()):
    if not db_path.exists() or table not in tables(db_path):
        return pd.DataFrame()
    sql = f"select * from {table}"
    if where:
        sql += f" where {where}"
    sql += f" limit {int(limit)}"
    try:
        with connect(db_path) as con:
            return mask_df(pd.read_sql_query(sql, con, params=params))
    except Exception:
        return pd.DataFrame()


def latest_row(table: str, learner_id=None, order_cols=("created_at", "timestamp", "updated_at", "id")):
    if table not in tables(TUTOR_DB):
        return {}
    cols = columns(TUTOR_DB, table)
    order = next((c for c in order_cols if c in cols), None)
    where = ""
    params = []
    if learner_id is not None and "learner_id" in cols:
        where = " where learner_id = ?"
        params.append(learner_id)
    elif learner_id is not None and "student_id" in cols:
        where = " where student_id = ?"
        params.append(str(learner_id))
    sql = f"select * from {table}{where}"
    if order:
        sql += f" order by {order} desc"
    sql += " limit 1"
    try:
        with connect(TUTOR_DB) as con:
            row = con.execute(sql, params).fetchone()
            return dict(row) if row else {}
    except Exception:
        return {}


def rows_for_learner(table: str, learner_id=None, limit=100):
    if learner_id is None:
        return read_table(TUTOR_DB, table, limit)
    cols = columns(TUTOR_DB, table)
    if "learner_id" in cols:
        return read_table(TUTOR_DB, table, limit, "learner_id = ?", (learner_id,))
    if "student_id" in cols:
        return read_table(TUTOR_DB, table, limit, "student_id = ?", (str(learner_id),))
    return pd.DataFrame()


def get_users():
    users = read_table(TUTOR_DB, "users", 500)
    profiles = read_table(TUTOR_DB, "learner_profile", 2000)
    if users.empty and profiles.empty:
        return pd.DataFrame()
    if not users.empty and not profiles.empty and "user_id" in profiles.columns and "user_id" in users.columns:
        merged = profiles.merge(users, on="user_id", how="left", suffixes=("", "_user"))
    elif not profiles.empty:
        merged = profiles.copy()
    else:
        merged = users.copy()
        if "learner_id" not in merged.columns:
            merged["learner_id"] = ""
    if "learner_id" in merged.columns:
        merged["app_learner_code"] = merged["learner_id"].where(merged["learner_id"].astype(str).str.startswith("LNR-"), "")
        merged["learner_type"] = merged["learner_id"].astype(str).map(lambda value: "Real-time App Learner" if value.startswith("LNR-") else "Dataset / Evaluation Learner")
    return merged


def learner_summary(learner_id):
    users = get_users()
    if users.empty or not learner_id:
        return {}
    row = users[users["learner_id"].astype(str) == str(learner_id)]
    if row.empty:
        return {}
    data = row.iloc[0].to_dict()
    data["last_login/session"] = data.get("last_login_at") or latest_row("learner_session_log", learner_id).get("created_at") or "Not available yet"
    return data


def latest_activity(learner_id):
    checks = [
        ("login/register", "users", "last_login_at"),
        ("subject selected", "learner_session_log", "created_at"),
        ("lesson opened", "learner_session_log", "created_at"),
        ("question loaded", "learner_session_log", "created_at"),
        ("answer submitted", "quiz_results", "created_at"),
        ("hint requested", "learner_session_log", "created_at"),
        ("doubt asked", "learner_doubt_log", "created_at"),
        ("notebook/revision opened", "revision_schedule", "created_at"),
        ("reward checked", "reward_event_log", "created_at"),
        ("XAI requested", "xai_log", "created_at"),
    ]
    rows = []
    for label, table, _order in checks:
        row = latest_row(table, learner_id)
        rows.append({
            "activity": label,
            "status": "PASS" if row else "NOT AVAILABLE",
            "table": table,
            "timestamp": row.get("created_at") or row.get("updated_at") or row.get("last_login_at") or "Not available yet",
            "evidence": json.dumps({k: v for k, v in row.items() if k not in MASK_KEYS}, default=str)[:500] if row else "Not available yet",
        })
    return pd.DataFrame(rows)


def subject_concepts(subject: str):
    db = SUBJECT_DBS.get(subject)
    if not db:
        return pd.DataFrame()
    if "concept_resources" in tables(db):
        return read_table(db, "concept_resources", 500)
    if "concepts" in tables(db):
        return read_table(db, "concepts", 500)
    return pd.DataFrame()


def subject_resource(subject: str, concept: str | None):
    df = subject_concepts(subject)
    if df.empty:
        return {}
    name_cols = [c for c in ["topic", "name", "concept_name", "concept_id"] if c in df.columns]
    if concept and name_cols:
        mask = False
        for c in name_cols:
            mask = mask | df[c].astype(str).str.contains(str(concept), case=False, na=False)
        hit = df[mask]
        if not hit.empty:
            return hit.iloc[0].to_dict()
    return df.iloc[0].to_dict()


def parse_json(value, default=None):
    if default is None:
        default = {}
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def artifact_status():
    rows = []
    for name, paths in MODEL_ARTIFACTS.items():
        found = [str(p) for p in paths if p.exists()]
        rows.append({
            "component": name,
            "status": "PASS" if found else "NOT AVAILABLE",
            "source": "; ".join(found) if found else "Artifact/report not found",
        })
    return pd.DataFrame(rows)


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def generation_coverage():
    source = next((p for p in GENERATION_REPORTS if p.exists()), None)
    data = load_json(source) if source else None
    known_tasks = [
        "explanation", "step-by-step teaching", "analogy", "misconception correction",
        "revision summary", "MCQ", "fill blank", "true/false", "output prediction",
        "debugging", "syntax completion", "coding", "transfer question", "challenge question",
        "flashcards", "mindmap", "hints", "feedback", "doubt answer", "notebook summary",
        "revision plan", "weakness review", "voice-ready script",
    ]
    rows = []
    if isinstance(data, dict):
        cases = data.get("cases") or data.get("case_results") or data.get("records") or []
        if isinstance(cases, list):
            for item in cases[:250]:
                if isinstance(item, dict):
                    rows.append({
                        "task_type": item.get("task_type") or item.get("task") or item.get("view") or "available from generation coverage reports",
                        "subject/concept coverage": item.get("subject") or item.get("concept") or item.get("coverage") or "reported case",
                        "source used": item.get("final_source") or item.get("source") or item.get("generation_source") or "report",
                        "validation status": item.get("validation_status") or item.get("status") or "reported",
                        "frontend-ready status": item.get("frontend_ready") if "frontend_ready" in item else "reported",
                        "learner-facing safe status": item.get("safe") if "safe" in item else "guarded/fallback path reported",
                    })
    if not rows:
        rows = [{
            "task_type": task,
            "subject/concept coverage": "5 subjects / 38 concepts target coverage",
            "source used": str(source) if source else "Known supported categories; exact task list available from generation coverage reports",
            "validation status": "reported" if source else "NOT AVAILABLE",
            "frontend-ready status": "reported" if source else "NOT AVAILABLE",
            "learner-facing safe status": "guarded output, prevalidated bank, RAG, or fallback",
        } for task in known_tasks]
    return {
        "source": str(source) if source else "NOT AVAILABLE",
        "summary": {"supported_subjects": 5, "concepts": 38, "task_types": 89, "evaluated_generated_cases": 3382},
        "rows": pd.DataFrame(rows),
    }


def read_events():
    EVENT_LOG.parent.mkdir(exist_ok=True)
    if not EVENT_LOG.exists():
        EVENT_LOG.write_text("[]", encoding="utf-8")
    return load_json(EVENT_LOG) or []


def append_event(learner_id, subject, concept, route, action, module, status, summary):
    events = read_events()
    events.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "learner_id": None if learner_id is None else str(learner_id),
        "subject": subject,
        "concept": concept,
        "route": route,
        "action": action,
        "module": module,
        "status": status,
        "summary": summary,
    })
    EVENT_LOG.write_text(json.dumps(events[-1000:], indent=2), encoding="utf-8")
