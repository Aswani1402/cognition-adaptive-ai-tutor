"""
Train retention / forgetting predictors from tutor.db interaction logs.

Run: python -m scripts.training.forgetting.train_retention_predictor
"""

from __future__ import annotations

import json
import random
import sqlite3
import time
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from tutor.forgetting.retention_predictor import FEATURE_NAMES

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"
MODEL_DIR = ROOT / "models" / "forgetting"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "retention_predictor_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "retention_predictor_report.md"

ALLOWED_TABLES = frozenset(
    {
        "quiz_results",
        "knowledge_state",
        "behaviour_state",
        "learner_mistake_log",
        "revision_schedule",
        "revision_card",
        "learner_revision_log",
        "reward_event_log",
        "learner_session_log",
        "learner_concept_progress",
        "fusion_decision_log",
        "view_performance_log",
    }
)

FINAL_WORDING = (
    "The forgetting and revision module was upgraded from fixed review scheduling to a model-supported "
    "retention prediction system. The predictor uses mastery, recent score, time gap, behaviour risk, "
    "confidence, mistake history, and revision evidence to estimate retention risk, review due status, "
    "revision priority, and recommended review interval. Existing revision logic is retained as a safe "
    "fallback when model evidence is unavailable."
)


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    if table not in ALLOWED_TABLES:
        return False
    try:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    if table not in ALLOWED_TABLES:
        return []
    try:
        return [str(r[1]).lower() for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def _safe_read_sql(con: sqlite3.Connection, query: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()


def _ts_epoch(val: Any) -> float:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    if isinstance(val, (int, float)):
        v = float(val)
        if v > 1e12:
            return v / 1000.0
        return v
    s = str(val).strip()
    if not s:
        return 0.0
    try:
        dt = pd.to_datetime(s, utc=True, errors="coerce")
        if pd.isna(dt):
            return 0.0
        return float(dt.timestamp())
    except Exception:
        return 0.0


def _model_top_features(model: Any, feature_names: List[str], k: int = 5) -> List[str]:
    try:
        est = model
        if hasattr(model, "named_steps"):
            est = model.named_steps.get("clf", model)
        if hasattr(est, "feature_importances_"):
            imp = np.asarray(est.feature_importances_, dtype=float)
            idx = np.argsort(imp)[::-1][:k]
            return [feature_names[i] for i in idx if i < len(feature_names)]
        if hasattr(est, "coef_"):
            coef = np.asarray(est.coef_, dtype=float)
            mag = np.mean(np.abs(coef), axis=0) if coef.ndim == 2 else np.abs(coef).ravel()
            idx = np.argsort(mag)[::-1][:k]
            return [feature_names[i] for i in idx if i < len(feature_names)]
    except Exception:
        pass
    return list(feature_names[:k])


def _metric_label_union(y_train: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    return np.sort(
        np.unique(
            np.concatenate(
                [
                    np.asarray(y_train, dtype=int).ravel(),
                    np.asarray(y_true, dtype=int).ravel(),
                    np.asarray(y_pred, dtype=int).ravel(),
                ]
            )
        )
    )


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray) -> Dict[str, Any]:
    labels = _metric_label_union(y_train, y_true, y_pred)
    yt = np.asarray(y_true).ravel()
    yp = np.asarray(y_pred).ravel()
    if labels.size == 0:
        return {
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "balanced_accuracy": 0.0,
        }
    return {
        "accuracy": float(accuracy_score(yt, yp)),
        "macro_f1": float(f1_score(yt, yp, average="macro", labels=labels, zero_division=0)),
        "weighted_f1": float(f1_score(yt, yp, average="weighted", labels=labels, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
    }


def _pick_best(comparison: Dict[str, Dict[str, Any]]) -> str:
    best = ""
    best_key = (-1.0, -1.0, -1.0)
    for name, m in comparison.items():
        if not isinstance(m, dict) or "error" in m:
            continue
        key = (m["macro_f1"], m["balanced_accuracy"], m["accuracy"])
        if key > best_key:
            best_key = key
            best = name
    return best


def _make_models(rs: int) -> Dict[str, Any]:
    models: Dict[str, Any] = {
        "DecisionTreeClassifier": DecisionTreeClassifier(max_depth=10, random_state=rs),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=32, max_depth=10, random_state=rs, n_jobs=-1
        ),
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=500, random_state=rs)),
            ]
        ),
    }
    try:
        models["GradientBoostingClassifier"] = GradientBoostingClassifier(
            n_estimators=32, max_depth=3, learning_rate=0.08, random_state=rs
        )
    except Exception:
        pass
    return models


def derive_retention_labels(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule-based teacher labels for supervised training.
    These are NOT human retention labels; they are documented derived heuristics.
    """
    mastery = float(row.get("mastery_score", 0.5) or 0.5)
    avg_r = float(row.get("average_recent_score", 0.5) or 0.5)
    days = float(row.get("days_since_last_practice", 0.0) or 0.0)
    streak = int(float(row.get("wrong_streak", 0) or 0))
    attempts = int(float(row.get("attempt_count", 1) or 1))
    rev_due = float(row.get("revision_due_existing", 0.0) or 0.0) >= 0.5

    high = (
        mastery < 0.35
        or (avg_r < 0.4 and attempts >= 2)
        or days >= 14.0
        or streak >= 4
        or rev_due
    )
    low = mastery >= 0.78 and days <= 3.0 and avg_r >= 0.7 and streak == 0 and not rev_due
    if high:
        risk = "high"
    elif low:
        risk = "low"
    else:
        risk = "medium"

    review_due = bool(
        rev_due
        or (days >= 7.0 and mastery < 0.65)
        or (days >= 3.0 and mastery < 0.45)
        or streak >= 3
    )

    if risk == "high" or (review_due and mastery < 0.5):
        prio = "high_priority"
    elif risk == "low" and not review_due:
        prio = "low_priority"
    else:
        prio = "medium_priority"

    if mastery >= 0.85 and avg_r >= 0.85 and not review_due:
        interval = "one_week"
    elif mastery >= 0.65 and days < 2.0:
        interval = "three_days"
    elif review_due or mastery < 0.5:
        interval = "same_day"
    else:
        interval = "next_day"

    return {
        "retention_risk_label": risk,
        "review_due": int(1 if review_due else 0),
        "revision_priority": prio,
        "review_interval_bucket": interval,
    }


def _synthetic_rows(n: int = 96, seed: int = 42) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        mastery = rng.uniform(0.15, 0.95)
        days = rng.uniform(0.0, 18.0)
        avg_r = rng.uniform(0.2, 0.95)
        streak = rng.randint(0, 5)
        attempts = rng.randint(1, 12)
        rev = 1.0 if rng.random() < 0.25 else 0.0
        row = {
            "learner_id": f"synth_learner_{i % 9}",
            "concept_id": str(rng.randint(1, 20)),
            "mastery_score": mastery,
            "previous_mastery_score": max(0.0, min(1.0, mastery - rng.uniform(-0.1, 0.1))),
            "recent_score": avg_r + rng.uniform(-0.08, 0.08),
            "average_recent_score": avg_r,
            "correctness_rate": avg_r,
            "wrong_streak": float(streak),
            "attempt_count": float(attempts),
            "time_gap_hours": days * 24.0,
            "time_gap_days": days,
            "days_since_last_practice": days,
            "behaviour_risk": rng.uniform(0.0, 1.0),
            "behaviour_confidence": rng.uniform(0.3, 0.95),
            "confidence": rng.uniform(0.35, 0.9),
            "hint_usage": float(rng.randint(0, 4)),
            "mistake_count": float(rng.randint(0, 8)),
            "high_severity_mistake_count": float(rng.randint(0, 3)),
            "review_count": float(rng.randint(0, 6)),
            "last_review_score": rng.uniform(0.0, 1.0),
            "revision_due_existing": rev,
            "difficulty_encoded": float(rng.choice([0.0, 1.0, 2.0])),
            "concept_position": rng.uniform(0.0, 1.0),
            "reward_xp": float(rng.randint(0, 120)),
            "anomaly_score": rng.uniform(0.0, 1.0),
        }
        labs = derive_retention_labels(row)
        rows.append({**row, **labs})
    return rows


def build_retention_rows(con: sqlite3.Connection, ref_epoch: float) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta = {
        "data_sources_used": [],
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_labels_used": True,
        "limitations": [
            "retention_risk_label, review_due, revision_priority, and review_interval_bucket are derived from "
            "interaction signals using documented heuristics (not human-labeled forgetting outcomes).",
        ],
    }
    rows: List[Dict[str, Any]] = []

    base = pd.DataFrame()
    if _table_exists(con, "learner_concept_progress"):
        cols = set(_table_columns(con, "learner_concept_progress"))
        need = {"learner_id", "concept_id", "mastery", "attempts", "last_score", "last_activity_at"}
        if need.issubset(cols):
            base = _safe_read_sql(
                con,
                """
                SELECT learner_id, concept_id, mastery, attempts, last_score, last_activity_at, updated_at
                FROM learner_concept_progress
                LIMIT 6000
                """,
            )
            if "last_activity_at" in base.columns:
                base["last_ts"] = base["last_activity_at"].map(_ts_epoch)
            else:
                base["last_ts"] = 0.0
            if "updated_at" in base.columns:
                base["last_ts"] = np.maximum(base["last_ts"], base["updated_at"].map(_ts_epoch))
            meta["data_sources_used"].append("learner_concept_progress")

    quiz_g = pd.DataFrame()
    if _table_exists(con, "quiz_results"):
        qc = set(_table_columns(con, "quiz_results"))
        if {"learner_id", "concept_id"}.issubset(qc):
            time_col = "timestamp" if "timestamp" in qc else None
            if time_col:
                q = f"""
                SELECT learner_id, concept_id, is_correct, confidence, hint_used, hint_count, {time_col} AS ts
                FROM quiz_results
                ORDER BY learner_id, concept_id, ts
                LIMIT 20000
                """
                qdf = _safe_read_sql(con, q)
                if not qdf.empty:
                    qdf["ts_epoch"] = qdf["ts"].map(_ts_epoch)
                    qdf["score"] = qdf["is_correct"].apply(lambda x: 1.0 if int(x or 0) else 0.0)
                    meta["data_sources_used"].append("quiz_results")

                    agg_rows: List[Dict[str, Any]] = []
                    for (lid, cid), g in qdf.groupby(["learner_id", "concept_id"]):
                        g = g.sort_values("ts_epoch")
                        scores = g["score"].tolist()
                        last = scores[-1] if scores else 0.0
                        tail = scores[-5:] if scores else [0.0]
                        avg5 = float(np.mean(tail)) if tail else 0.0
                        corr = float(np.mean(scores)) if scores else 0.0
                        streak = 0
                        for s in reversed(scores):
                            if s < 0.5:
                                streak += 1
                            else:
                                break
                        first_half = scores[: max(1, len(scores) // 2)]
                        prev_m = float(np.mean(first_half)) if first_half else last
                        last_t = float(g["ts_epoch"].max() or 0.0)
                        hint_u = 0.0
                        if "hint_count" in g.columns:
                            hint_u = float(g["hint_count"].fillna(0).mean())
                        elif "hint_used" in g.columns:
                            hint_u = float(g["hint_used"].fillna(0).mean())
                        conf = (
                            float(g["confidence"].fillna(50).mean()) / 100.0 if "confidence" in g.columns else 0.5
                        )
                        agg_rows.append(
                            {
                                "learner_id": lid,
                                "concept_id": cid,
                                "attempt_count": float(len(scores)),
                                "recent_score": last,
                                "average_recent_score": avg5,
                                "correctness_rate": corr,
                                "wrong_streak": float(streak),
                                "previous_mastery_score": float(np.clip(prev_m, 0.0, 1.0)),
                                "last_quiz_ts": last_t,
                                "hint_usage": hint_u,
                                "confidence": conf,
                            }
                        )
                    quiz_g = pd.DataFrame(agg_rows)

    beh = pd.DataFrame()
    if _table_exists(con, "behaviour_state"):
        bc = set(_table_columns(con, "behaviour_state"))
        if "learner_id" in bc:
            cols = ["learner_id"]
            for c in ("behavior_risk", "behavior_confidence", "timestamp", "id"):
                if c in bc and c not in cols:
                    cols.append(c)
            beh = _safe_read_sql(con, f"SELECT {', '.join(cols)} FROM behaviour_state")
            if not beh.empty and "timestamp" in beh.columns:
                beh["_ts"] = beh["timestamp"].map(_ts_epoch)
                beh = beh.sort_values("_ts", ascending=False).drop_duplicates("learner_id", keep="first")
            elif not beh.empty:
                beh = beh.sort_values("learner_id").drop_duplicates("learner_id", keep="last")
            meta["data_sources_used"].append("behaviour_state")

    mistakes = pd.DataFrame()
    if _table_exists(con, "learner_mistake_log"):
        mc = set(_table_columns(con, "learner_mistake_log"))
        if {"learner_id", "concept_id"}.issubset(mc):
            sev = "severity" if "severity" in mc else None
            if sev:
                mistakes = _safe_read_sql(
                    con,
                    f"""
                    SELECT learner_id, concept_id,
                      COUNT(*) AS mistake_count,
                      SUM(CASE WHEN LOWER(CAST({sev} AS TEXT)) IN ('high','critical','3','2') THEN 1 ELSE 0 END)
                        AS high_severity_mistake_count
                    FROM learner_mistake_log
                    GROUP BY learner_id, concept_id
                    """,
                )
            else:
                mistakes = _safe_read_sql(
                    con,
                    """
                    SELECT learner_id, concept_id, COUNT(*) AS mistake_count, 0 AS high_severity_mistake_count
                    FROM learner_mistake_log
                    GROUP BY learner_id, concept_id
                    """,
                )
            meta["data_sources_used"].append("learner_mistake_log")

    rev_due = pd.DataFrame()
    if _table_exists(con, "revision_schedule"):
        rc = set(_table_columns(con, "revision_schedule"))
        if {"learner_id", "concept_id"}.issubset(rc):
            st = "status" if "status" in rc else None
            due_c = "due_at" if "due_at" in rc else None
            if st and due_c:
                rev_due = _safe_read_sql(
                    con,
                    f"""
                    SELECT learner_id, concept_id,
                      MAX(CASE WHEN LOWER(COALESCE({st},'')) != 'completed' THEN 1 ELSE 0 END) AS revision_due_existing
                    FROM revision_schedule
                    GROUP BY learner_id, concept_id
                    """,
                )
            else:
                rev_due = _safe_read_sql(
                    con,
                    """
                    SELECT learner_id, concept_id, 1.0 AS revision_due_existing
                    FROM revision_schedule
                    GROUP BY learner_id, concept_id
                    """,
                )
            meta["data_sources_used"].append("revision_schedule")

    rev_log = pd.DataFrame()
    if _table_exists(con, "learner_revision_log"):
        lc = set(_table_columns(con, "learner_revision_log"))
        if {"learner_id", "concept_id"}.issubset(lc):
            rev_log = _safe_read_sql(
                con,
                """
                SELECT learner_id, concept_id,
                  COUNT(*) AS review_count,
                  MAX(CASE WHEN score IS NOT NULL THEN score ELSE 0 END) AS last_review_score
                FROM learner_revision_log
                GROUP BY learner_id, concept_id
                """,
            )
            meta["data_sources_used"].append("learner_revision_log")

    rewards = pd.DataFrame()
    if _table_exists(con, "reward_event_log"):
        rc = set(_table_columns(con, "reward_event_log"))
        if {"learner_id", "concept_id"}.issubset(rc):
            rewards = _safe_read_sql(
                con,
                """
                SELECT learner_id, concept_id, SUM(COALESCE(xp_awarded,0)) AS reward_xp
                FROM reward_event_log
                GROUP BY learner_id, concept_id
                """,
            )
            meta["data_sources_used"].append("reward_event_log")

    anomaly = pd.DataFrame()
    if _table_exists(con, "view_performance_log"):
        vc = set(_table_columns(con, "view_performance_log"))
        if {"learner_id", "concept_id", "assessment_score"}.issubset(vc):
            anomaly = _safe_read_sql(
                con,
                """
                SELECT learner_id, concept_id,
                  AVG(
                    CASE WHEN assessment_score IS NULL THEN 0.5
                    ELSE (1.0 - assessment_score) END
                  ) AS anomaly_score
                FROM view_performance_log
                GROUP BY learner_id, concept_id
                """,
            )
            meta["data_sources_used"].append("view_performance_log")

    fusion = pd.DataFrame()
    if _table_exists(con, "fusion_decision_log"):
        fc = set(_table_columns(con, "fusion_decision_log"))
        if {"learner_id", "concept_id", "review_due"}.issubset(fc):
            fusion = _safe_read_sql(
                con,
                """
                SELECT learner_id, concept_id, MAX(review_due) AS fusion_review_due
                FROM fusion_decision_log
                GROUP BY learner_id, concept_id
                """,
            )
            meta["data_sources_used"].append("fusion_decision_log")

    if base.empty and not quiz_g.empty:
        base = quiz_g.copy()
        base["mastery"] = base["average_recent_score"]
        base["attempts"] = base["attempt_count"]
        base["last_score"] = base["recent_score"]
        base["last_ts"] = base["last_quiz_ts"]

    if base.empty:
        meta["limitations"].append("No learner_concept_progress or usable quiz_results rows for feature assembly.")
        return [], meta

    for _, r in base.iterrows():
        lid = str(r.get("learner_id", ""))
        cid = str(r.get("concept_id", ""))
        if not lid or not cid:
            continue
        mastery = float(r.get("mastery") or 0.0)
        attempts = float(r.get("attempts") or 0.0)
        last_score = float(r.get("last_score") or 0.0)
        last_ts = float(r.get("last_ts") or 0.0)

        qrow = quiz_g[(quiz_g["learner_id"].astype(str) == lid) & (quiz_g["concept_id"].astype(str) == cid)]
        if not qrow.empty:
            qd = qrow.iloc[0].to_dict()
            recent_score = float(qd.get("recent_score", last_score))
            average_recent_score = float(qd.get("average_recent_score", recent_score))
            correctness_rate = float(qd.get("correctness_rate", average_recent_score))
            wrong_streak = float(qd.get("wrong_streak", 0.0))
            attempt_count = float(qd.get("attempt_count", attempts or 1.0))
            previous_mastery_score = float(qd.get("previous_mastery_score", max(0.0, mastery - 0.05)))
            hint_usage = float(qd.get("hint_usage", 0.0))
            conf_q = float(qd.get("confidence", 0.5))
            last_ts = max(last_ts, float(qd.get("last_quiz_ts", 0.0)))
        else:
            recent_score = last_score if last_score else mastery
            average_recent_score = recent_score
            correctness_rate = recent_score
            wrong_streak = 0.0
            attempt_count = max(1.0, attempts)
            previous_mastery_score = max(0.0, min(1.0, mastery - 0.05))
            hint_usage = 0.0
            conf_q = 0.5

        if last_ts <= 0:
            last_ts = ref_epoch - 86400.0
        days = max(0.0, (ref_epoch - last_ts) / 86400.0)
        hours = days * 24.0

        br, bc = 0.0, 0.5
        if not beh.empty and "learner_id" in beh.columns:
            b = beh[beh["learner_id"].astype(str) == lid]
            if not b.empty:
                row_b = b.iloc[0]
                if "behavior_risk" in b.columns:
                    br = float(row_b.get("behavior_risk", 0.0) or 0.0)
                if "behavior_confidence" in b.columns:
                    bc = float(row_b.get("behavior_confidence", 0.5) or 0.5)

        mc = hc = 0.0
        if not mistakes.empty:
            mm = mistakes[(mistakes["learner_id"].astype(str) == lid) & (mistakes["concept_id"].astype(str) == cid)]
            if not mm.empty:
                mc = float(mm.iloc[0].get("mistake_count", 0) or 0)
                hc = float(mm.iloc[0].get("high_severity_mistake_count", 0) or 0)

        rev_flag = 0.0
        if not rev_due.empty:
            rr = rev_due[(rev_due["learner_id"].astype(str) == lid) & (rev_due["concept_id"].astype(str) == cid)]
            if not rr.empty:
                rev_flag = float(rr.iloc[0].get("revision_due_existing", 0) or 0)

        if not fusion.empty:
            fr = fusion[(fusion["learner_id"].astype(str) == lid) & (fusion["concept_id"].astype(str) == cid)]
            if not fr.empty and int(float(fr.iloc[0].get("fusion_review_due", 0) or 0)):
                rev_flag = 1.0

        rc = 0.0
        lrs = 0.0
        if not rev_log.empty:
            lg = rev_log[(rev_log["learner_id"].astype(str) == lid) & (rev_log["concept_id"].astype(str) == cid)]
            if not lg.empty:
                rc = float(lg.iloc[0].get("review_count", 0) or 0)
                lrs = float(lg.iloc[0].get("last_review_score", 0) or 0)

        xp = 0.0
        if not rewards.empty:
            rg = rewards[(rewards["learner_id"].astype(str) == lid) & (rewards["concept_id"].astype(str) == cid)]
            if not rg.empty:
                xp = float(rg.iloc[0].get("reward_xp", 0) or 0)

        ano = 0.0
        if not anomaly.empty:
            ag = anomaly[(anomaly["learner_id"].astype(str) == lid) & (anomaly["concept_id"].astype(str) == cid)]
            if not ag.empty:
                ano = float(ag.iloc[0].get("anomaly_score", 0) or 0)

        diff_enc = 1.0
        concept_pos = 0.1
        try:
            concept_pos = min(1.0, abs(int(str(cid).strip() or "0")) / 50.0)
        except Exception:
            concept_pos = 0.1

        row = {
            "learner_id": lid,
            "concept_id": cid,
            "mastery_score": float(np.clip(mastery, 0.0, 1.0)),
            "previous_mastery_score": float(np.clip(previous_mastery_score, 0.0, 1.0)),
            "recent_score": float(np.clip(recent_score, 0.0, 1.0)),
            "average_recent_score": float(np.clip(average_recent_score, 0.0, 1.0)),
            "correctness_rate": float(np.clip(correctness_rate, 0.0, 1.0)),
            "wrong_streak": wrong_streak,
            "attempt_count": attempt_count,
            "time_gap_hours": hours,
            "time_gap_days": days,
            "days_since_last_practice": days,
            "behaviour_risk": br,
            "behaviour_confidence": bc,
            "confidence": conf_q,
            "hint_usage": hint_usage,
            "mistake_count": mc,
            "high_severity_mistake_count": hc,
            "review_count": rc,
            "last_review_score": lrs,
            "revision_due_existing": rev_flag,
            "difficulty_encoded": diff_enc,
            "concept_position": concept_pos,
            "reward_xp": xp,
            "anomaly_score": ano,
        }
        labs = derive_retention_labels(row)
        rows.append({**row, **labs})

    meta["real_row_count"] = len(rows)
    return rows, meta


def build_training_dataframe(db_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    db = Path(db_path) if db_path else DB_PATH
    ref_epoch = time.time()
    meta: Dict[str, Any] = {
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_labels_used": True,
        "limitations": [],
        "data_sources_used": [],
    }
    rows: List[Dict[str, Any]] = []
    if db.exists():
        con = sqlite3.connect(str(db))
        try:
            rrows, m = build_retention_rows(con, ref_epoch)
            rows.extend(rrows)
            meta.update({k: v for k, v in m.items() if k in ("limitations", "data_sources_used", "derived_labels_used")})
            meta["limitations"] = list(dict.fromkeys(meta.get("limitations", []) + m.get("limitations", [])))
            meta["data_sources_used"] = m.get("data_sources_used", [])
            meta["real_row_count"] = m.get("real_row_count", len(rrows))
        finally:
            con.close()

    if len(rows) < 100:
        syn = _synthetic_rows()
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["limitations"].append(
            "synthetic_used=true: appended simulator-style rows because real assembled rows were fewer than 100."
        )
        rows.extend(syn)

    if not rows:
        syn = _synthetic_rows(120)
        rows = syn
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["limitations"].append("No DB rows assembled; using synthetic-only dataset.")

    df = pd.DataFrame(rows)
    return df, meta


def train_and_report() -> Dict[str, Any]:
    df, ds_meta = build_training_dataframe()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    feature_cols = list(FEATURE_NAMES)

    report: Dict[str, Any] = {
        "status": "success",
        "module": "train_retention_predictor",
        "dataset_size": len(df),
        "real_row_count": ds_meta.get("real_row_count", 0),
        "synthetic_row_count": ds_meta.get("synthetic_row_count", 0),
        "synthetic_used": bool(ds_meta.get("synthetic_used")),
        "derived_labels_used": bool(ds_meta.get("derived_labels_used", True)),
        "feature_names": feature_cols,
        "targets_trained": [],
        "model_comparison": {},
        "best_model_per_target": {},
        "best_metrics_per_target": {},
        "label_distributions": {},
        "per_class_support": {},
        "confusion_matrices": {},
        "confusion_matrix_summary": {},
        "top_features_per_target": {},
        "rare_class_warning": False,
        "rare_classes": [],
        "fallback_behavior": {
            "description": (
                "At inference, RetentionPredictor.predict_with_fallback uses rule-based mapping when "
                "artifacts are missing or evidence is insufficient; tutor.memory.revision_scheduler remains "
                "the primary spaced-repetition and revision packet builder."
            ),
        },
        "limitations": list(ds_meta.get("limitations", [])),
        "data_sources_used": list(ds_meta.get("data_sources_used", [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "final_report_wording": FINAL_WORDING,
    }

    if df.empty:
        report["status"] = "warning"
        report["limitations"].append("Empty dataframe.")
        return report

    for tgt, col in (
        ("retention_risk", "retention_risk_label"),
        ("review_due", "review_due"),
        ("revision_priority", "revision_priority"),
        ("review_interval", "review_interval_bucket"),
    ):
        vc = df[col].astype(str) if col in df.columns else pd.Series([], dtype=str)
        report["label_distributions"][tgt] = dict(Counter(vc))

    rare_flat: List[str] = []
    for tgt, col in (
        ("retention_risk", "retention_risk_label"),
        ("review_due", "review_due"),
        ("revision_priority", "revision_priority"),
        ("review_interval", "review_interval_bucket"),
    ):
        c = Counter(df[col].astype(str))
        for lab, n in c.items():
            if n < 2:
                rare_flat.append(f"{tgt}:{lab}")
    report["rare_class_warning"] = len(rare_flat) > 0
    report["rare_classes"] = sorted(rare_flat)
    if report["rare_class_warning"]:
        report["limitations"].append(
            "rare_class_warning: some label bins have fewer than two examples; macro-F1 may be unstable."
        )

    targets = {
        "retention_risk": ("retention_risk_label", "retention_risk_model.joblib"),
        "review_due": ("review_due", "review_due_model.joblib"),
        "revision_priority": ("revision_priority", "revision_priority_model.joblib"),
        "review_interval": ("review_interval_bucket", "review_interval_model.joblib"),
    }

    trained: List[str] = []

    for key, (ycol, fname) in targets.items():
        try:
            if ycol == "review_due":

                def _rd_label(v: Any) -> str:
                    try:
                        return "1" if int(float(v)) != 0 else "0"
                    except Exception:
                        return "1" if str(v).strip().lower() in {"1", "true", "yes"} else "0"

                y_raw = df[ycol].apply(_rd_label)
            else:
                y_raw = df[ycol].astype(str)

            le = LabelEncoder()
            y = le.fit_transform(y_raw)

            if len(np.unique(y)) < 2:
                report["limitations"].append(f"Skipping {key}: single class in labels.")
                continue

            report["per_class_support"][key] = dict(Counter(y_raw))

            X = df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
            _, counts_full = np.unique(y, return_counts=True)
            min_class_count = int(counts_full.min()) if len(counts_full) else 0
            stratify_arg: Optional[np.ndarray] = y if min_class_count >= 2 else None
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=stratify_arg
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=None)

            comparison: Dict[str, Any] = {}
            for mname, est in _make_models(42).items():
                try:
                    est.fit(X_train, y_train)
                    p = est.predict(X_test)
                    comparison[mname] = _metrics(y_test, p, y_train)
                except Exception as exc:
                    warnings.warn(f"{key} {mname}: {exc}")
                    comparison[mname] = {"error": str(exc)}

            best_name = _pick_best(comparison)
            if not best_name:
                report["limitations"].append(f"No trainable model for {key}")
                continue
            best_model = _make_models(42)[best_name]
            best_model.fit(X_train, y_train)
            best_pred = best_model.predict(X_test)

            report["model_comparison"][key] = comparison
            report["best_model_per_target"][key] = best_name
            report["best_metrics_per_target"][key] = _metrics(y_test, best_pred, y_train)
            labels_cm = _metric_label_union(y_train, y_test, best_pred)
            cm = confusion_matrix(y_test, best_pred, labels=labels_cm)
            report["confusion_matrices"][key] = cm.tolist()
            tot = float(np.sum(cm))
            diag = float(np.trace(cm)) if cm.size else 0.0
            report["confusion_matrix_summary"][key] = {
                "total": int(tot),
                "diagonal_correct": int(diag),
                "matrix_accuracy": round(diag / tot, 4) if tot else 0.0,
            }

            joblib.dump(
                {"model": best_model, "label_encoder": le, "target": key, "feature_names": feature_cols},
                MODEL_DIR / fname,
            )
            report["top_features_per_target"][key] = _model_top_features(best_model, feature_cols, k=6)
            trained.append(key)
        except Exception as exc:
            report["limitations"].append(f"{key} training failed: {exc}")

    report["targets_trained"] = trained

    meta = {
        "dataset_size": report["dataset_size"],
        "real_row_count": report["real_row_count"],
        "synthetic_row_count": report["synthetic_row_count"],
        "synthetic_used": report["synthetic_used"],
        "derived_labels_used": report["derived_labels_used"],
        "feature_names": feature_cols,
        "targets_trained": trained,
        "best_model_per_target": report.get("best_model_per_target", {}),
        "limitations": report["limitations"],
        "created_at": report["created_at"],
        "label_derivation": (
            "High retention risk if mastery is low, recent performance is weak, time gap is long, wrong streak is "
            "high, or revision is already due. Medium risk covers partial mastery or moderate gaps. Low risk when "
            "mastery and recent scores are strong with short gaps. review_due, revision_priority, and interval "
            "bucket follow the same evidence thresholds documented in derive_retention_labels()."
        ),
    }
    (MODEL_DIR / "retention_predictor_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if not trained:
        report["status"] = "warning"

    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Retention predictor report",
        "",
        f"**Status:** {report.get('status')}",
        "",
        f"**Dataset size:** {report.get('dataset_size')}",
        f"**Real rows:** {report.get('real_row_count')}",
        f"**Synthetic rows:** {report.get('synthetic_row_count')}",
        f"**Synthetic used:** {report.get('synthetic_used')}",
        f"**Derived labels used:** {report.get('derived_labels_used')}",
        "",
        "## Label distributions",
        "",
        str(report.get("label_distributions", {})),
        "",
        f"**Rare class warning:** {report.get('rare_class_warning')}",
        f"**Rare classes:** {report.get('rare_classes', [])}",
        "",
        "## Data sources",
        "",
        ", ".join(report.get("data_sources_used", []) or ["(none noted)"]),
        "",
        "## Model comparison (metrics by target / estimator)",
        "",
        str(report.get("model_comparison", {})),
        "",
        "## Best model per target",
        "",
    ]
    for t, m in report.get("best_model_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Best metrics", ""])
    for t, m in report.get("best_metrics_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Confusion matrix summary", ""])
    for t, m in report.get("confusion_matrix_summary", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Top features", ""])
    for t, tops in report.get("top_features_per_target", {}).items():
        lines.append(f"- **{t}:** {tops}")
    lines.extend(["", "## Fallback behavior", "", str(report.get("fallback_behavior", {})), ""])
    lines.extend(["", "## Limitations", ""])
    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")
    lines.extend(
        [
            "",
            "## Label derivation (derived, not human-labeled)",
            "",
            "All targets are heuristic labels from interaction logs for supervised learning; they are not clinical "
            "or human-judged forgetting outcomes.",
            "",
            "## Final report wording",
            "",
            str(report.get("final_report_wording", "")),
            "",
        ]
    )
    return "\n".join(lines)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    report = train_and_report()
    save_json(JSON_REPORT, report)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.write_text(build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report.get('status', 'warning')}")
    print("MODULE: train_retention_predictor")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"MODEL_DIR: {MODEL_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
