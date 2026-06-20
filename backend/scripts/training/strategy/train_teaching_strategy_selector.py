"""
Train learned teaching-strategy models (comparison / model-supported mode).

Run from project root:
  python -m scripts.training.strategy.train_teaching_strategy_selector
"""

from __future__ import annotations

import json
import sqlite3
import warnings
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

from tutor.strategy.learned_teaching_strategy_selector import (
    FEATURE_COLUMNS,
    ASSESSMENT_GROUP_LABELS,
    DIFFICULTY_LABELS,
    NEXT_ACTION_LABELS,
    TEACHING_VIEW_LABELS,
    evidence_to_feature_row,
    infer_assessment_group_label,
    map_next_action_label,
    normalize_difficulty_label,
    normalize_teaching_view_label,
)
from tutor.xai.model_attribution_explainer import ModelAttributionExplainer

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"
MODEL_DIR = ROOT / "models" / "strategy"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "teaching_strategy_model_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "teaching_strategy_model_report.md"

FINAL_WORDING = (
    "The teaching strategy module was upgraded from an evidence-aware rule baseline to a learned "
    "model-supported selector. Tutor decision logs and engineered learner evidence are converted into "
    "feature-label datasets, and supervised models are trained to predict teaching view, difficulty, "
    "assessment group, and next action. The existing rule-based selector is retained as a safety fallback "
    "when model confidence is low or artifacts are unavailable."
)


def _safe_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _safe_read_sql(con: sqlite3.Connection, query: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()


def _table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    """Use PRAGMA table_info; returns lowercased column names if table exists."""
    try:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        return [str(r[1]).lower() for r in rows]
    except Exception:
        return []


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    try:
        cur = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False


def _select_existing_columns(
    con: sqlite3.Connection,
    table: str,
    wanted: List[str],
) -> Tuple[str, List[str]]:
    """
    Build SELECT list for columns that exist on table.
    Returns (comma-separated select expr, list of selected names).
    """
    if not _table_exists(con, table):
        return "", []
    have = set(_table_columns(con, table))
    picked: List[str] = []
    for c in wanted:
        if c.lower() in have:
            picked.append(c)
    if not picked:
        return "", []
    return ", ".join(picked), picked


def _quiz_xp_aggregates(con: sqlite3.Connection) -> Tuple[pd.DataFrame, pd.DataFrame]:
    quiz = pd.DataFrame()
    if _table_exists(con, "quiz_results") and "learner_id" in set(_table_columns(con, "quiz_results")):
        quiz = _safe_read_sql(
            con,
            """
            SELECT learner_id,
                   AVG(CAST(is_correct AS REAL)) AS previous_score,
                   AVG(CAST(hint_used AS REAL)) AS hint_usage
            FROM quiz_results
            GROUP BY learner_id
            """,
        )
    xp = pd.DataFrame()
    if _table_exists(con, "reward_event_log") and "learner_id" in set(
        _table_columns(con, "reward_event_log")
    ):
        xp = _safe_read_sql(
            con,
            """
            SELECT learner_id, SUM(xp_awarded) AS reward_xp
            FROM reward_event_log
            GROUP BY learner_id
            """,
        )
    return quiz, xp


def _normalize_agg(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    if df.empty or "learner_id" not in df.columns:
        return pd.DataFrame(columns=["learner_id", *columns])
    return df


def _behaviour_latest(con: sqlite3.Connection) -> pd.DataFrame:
    cols = _table_columns(con, "behaviour_state")
    id_col = "learner_id" if "learner_id" in cols else ("student_id" if "student_id" in cols else None)
    if not id_col or not _table_exists(con, "behaviour_state"):
        return pd.DataFrame()
    sel = [id_col]
    if "behavior_risk" in cols:
        sel.append("behavior_risk")
    if "behavior_confidence" in cols:
        sel.append("behavior_confidence")
    sort_col = None
    if "timestamp" in cols:
        sel.append("timestamp")
        sort_col = "timestamp"
    elif "updated_at" in cols:
        sel.append("updated_at")
        sort_col = "updated_at"
    q = f"SELECT {', '.join(sel)} FROM behaviour_state"
    df = _safe_read_sql(con, q)
    if df.empty:
        return pd.DataFrame()
    df = df.rename(columns={id_col: "learner_id"})
    if sort_col:
        df["_ts"] = pd.to_datetime(df[sort_col], errors="coerce")
        df = df.sort_values(["learner_id", "_ts"]).drop_duplicates("learner_id", keep="last")
    else:
        df = df.drop_duplicates("learner_id", keep="last")
    if "behavior_risk" in df.columns:
        df["behaviour_risk_agg"] = pd.to_numeric(df["behavior_risk"], errors="coerce").fillna(0.5)
    if "behavior_confidence" in df.columns:
        df["behaviour_confidence_agg"] = pd.to_numeric(df["behavior_confidence"], errors="coerce").fillna(0.5)
    keep = ["learner_id"] + [c for c in ("behaviour_risk_agg", "behaviour_confidence_agg") if c in df.columns]
    return df[keep]


def _knowledge_avg_mastery(con: sqlite3.Connection) -> pd.DataFrame:
    if not _table_exists(con, "knowledge_state"):
        return pd.DataFrame()
    cols = _table_columns(con, "knowledge_state")
    sid_col = "student_id" if "student_id" in cols else ("learner_id" if "learner_id" in cols else None)
    if not sid_col or "state_json" not in cols:
        return pd.DataFrame()
    df = _safe_read_sql(con, f"SELECT {sid_col} AS learner_id, state_json FROM knowledge_state")
    if df.empty:
        return pd.DataFrame()

    def avg_mastery(js: Any) -> float:
        state = _safe_json(js, {})
        vals: List[float] = []
        if isinstance(state.get("concepts"), dict):
            for _cid, item in state["concepts"].items():
                if isinstance(item, dict) and item.get("mastery") is not None:
                    try:
                        vals.append(float(item["mastery"]))
                    except Exception:
                        pass
        m = state.get("mastery", state)
        if isinstance(m, dict):
            for _k, v in m.items():
                try:
                    vals.append(float(v))
                except Exception:
                    pass
        return float(np.mean(vals)) if vals else 0.5

    df["mastery_from_kt"] = df["state_json"].map(avg_mastery)
    return df[["learner_id", "mastery_from_kt"]]


def _strategy_log_derived_targets(strategy: Any) -> Tuple[str, str, str, str]:
    s = str(strategy or "").strip().lower()
    if s == "revision_view":
        return "revision_view", "medium", "review", "revision_mix"
    if s == "debug_view":
        return "debug_view", "medium", "practice", "debug_practice"
    if s == "code_view":
        return "code_view", "medium", "practice", "code_practice"
    if s == "definition":
        return "definition_view", "easy", "continue", "mcq_basic"
    if s == "remedial":
        return "misconception_view", "easy", "reteach", "revision_mix"
    if s == "practice":
        return "code_view", "medium", "practice", "output_prediction_practice"
    if s == "advanced":
        return "challenge_view", "hard", "challenge", "challenge_mix"
    return "step_by_step_view", "medium", "continue", "mcq_basic"


def _load_teaching_strategy_log_frame(con: sqlite3.Connection) -> pd.DataFrame:
    if not _table_exists(con, "teaching_strategy_log"):
        return pd.DataFrame()
    cols = set(_table_columns(con, "teaching_strategy_log"))
    need = {"learner_id", "strategy"}
    if not need.issubset(cols):
        return pd.DataFrame()
    extra = ["concept_id", "strategy_source", "timestamp"] if "concept_id" in cols else []
    sel = ["learner_id", "strategy"] + [c for c in extra if c in cols]
    q = f"SELECT {', '.join(sel)} FROM teaching_strategy_log"
    return _safe_read_sql(con, q)


def _optional_fusion_extra(root: Path) -> Dict[str, Dict[str, float]]:
    """
    Best-effort: read JSON under evaluation_outputs/json matching *fusion* with per-learner scores.
    If file is a single dict without learner_id, skip.
    """
    out: Dict[str, Dict[str, float]] = {}
    jdir = root / "evaluation_outputs" / "json"
    if not jdir.is_dir():
        return out
    for path in sorted(jdir.glob("*fusion*.json"))[:25]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = data if isinstance(data, list) else data.get("rows") or data.get("samples") or []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            lid = row.get("learner_id") or row.get("student_id")
            if not lid:
                continue
            fs = row.get("fused_score")
            fc = row.get("fusion_confidence") or row.get("confidence")
            if fs is None and fc is None:
                continue
            key = str(lid)
            if key not in out:
                out[key] = {}
            if fs is not None:
                try:
                    out[key]["fused_score"] = float(fs)
                except Exception:
                    pass
            if fc is not None:
                try:
                    out[key]["fusion_confidence"] = float(fc)
                except Exception:
                    pass
    return out


def _optional_csv_extra(root: Path) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    cdir = root / "evaluation_outputs" / "csv"
    if not cdir.is_dir():
        return out
    for path in sorted(cdir.glob("*.csv"))[:30]:
        try:
            cdf = pd.read_csv(path, nrows=5000)
        except Exception:
            continue
        cols = {c.lower(): c for c in cdf.columns}
        lid_key = cols.get("learner_id") or cols.get("student_id")
        if not lid_key:
            continue
        fs_col = cols.get("fused_score") or cols.get("fusion_score")
        fc_col = cols.get("fusion_confidence") or cols.get("confidence")
        if not fs_col and not fc_col:
            continue
        for _, row in cdf.iterrows():
            lid = row.get(lid_key)
            if lid is None or (isinstance(lid, float) and np.isnan(lid)):
                continue
            key = str(lid)
            if key not in out:
                out[key] = {}
            if fs_col and row.get(fs_col) is not None:
                try:
                    out[key]["fused_score"] = float(row[fs_col])
                except Exception:
                    pass
            if fc_col and row.get(fc_col) is not None:
                try:
                    out[key]["fusion_confidence"] = float(row[fc_col])
                except Exception:
                    pass
    return out


def _mistake_aggregates_dynamic(con: sqlite3.Connection) -> pd.DataFrame:
    if not _table_exists(con, "learner_mistake_log"):
        return pd.DataFrame()
    c = set(_table_columns(con, "learner_mistake_log"))
    if "learner_id" not in c:
        return pd.DataFrame()
    sev = (
        "SUM(CASE WHEN LOWER(IFNULL(severity,'')) IN ('high','critical') THEN 1 ELSE 0 END)"
        if "severity" in c
        else "0"
    )
    mt = "mistake_type" if "mistake_type" in c else None
    wo = (
        f"SUM(CASE WHEN LOWER(IFNULL({mt},'')) LIKE '%wrong_output%' THEN 1 ELSE 0 END)"
        if mt
        else "0"
    )
    sy = (
        f"SUM(CASE WHEN LOWER(IFNULL({mt},'')) LIKE '%syntax%' THEN 1 ELSE 0 END)"
        if mt
        else "0"
    )
    q = f"""
        SELECT learner_id,
               COUNT(*) AS mistake_count,
               {sev} AS high_severity_mistake_count,
               {wo} AS wrong_output_count,
               {sy} AS syntax_mistake_count
        FROM learner_mistake_log
        GROUP BY learner_id
    """
    return _safe_read_sql(con, q)


def _rows_from_merged_frame(df: pd.DataFrame, fusion_extra: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        evidence = _safe_json(row.get("evidence_strategy_json"), {})
        if not isinstance(evidence, dict):
            evidence = {}
        evidence = {**evidence}
        lid = str(row.get("learner_id", ""))
        if lid in fusion_extra:
            for k, v in fusion_extra[lid].items():
                evidence.setdefault(k, v)
        if "mastery_from_kt" in row and row.get("mastery_from_kt") is not None:
            evidence.setdefault(
                "mastery_score",
                float(row["mastery_from_kt"]),
            )
        if "behaviour_risk_agg" in row and row.get("behaviour_risk_agg") is not None:
            evidence.setdefault("behaviour_risk", float(row["behaviour_risk_agg"]))
        if "behaviour_confidence_agg" in row and row.get("behaviour_confidence_agg") is not None:
            evidence.setdefault("behaviour_confidence", float(row["behaviour_confidence_agg"]))

        evidence["difficulty"] = row.get("difficulty") or evidence.get("difficulty")
        evidence["mistake_analysis"] = {
            "high_severity_count": float(row.get("high_severity_mistake_count") or 0.0),
            "mistake_type_counts": {},
            "dominant_mistake_type": evidence.get("dominant_mistake_type"),
        }
        evidence["mistake_count"] = float(row.get("mistake_count") or 0.0)
        evidence["wrong_output_count"] = float(row.get("wrong_output_count") or 0.0)
        evidence["syntax_mistake_count"] = float(row.get("syntax_mistake_count") or 0.0)
        evidence["previous_score"] = float(row.get("previous_score") or evidence.get("evaluation_score") or 0.5)
        evidence["hint_usage"] = float(row.get("hint_usage") or 0.0)
        evidence["reward_xp"] = float(row.get("reward_xp") or 0.0)
        evidence["evaluation_score"] = float(row.get("evaluation_score") or 0.5)
        evidence["fused_score"] = evidence.get("fused_score", evidence.get("evaluation_score", 0.5))

        feats = evidence_to_feature_row(evidence)
        atypes = _safe_json(row.get("assessment_types_json"), [])
        tgt_view = row.get("teaching_view")
        tgt_diff = row.get("difficulty")
        tgt_next = map_next_action_label(row.get("progression_action"), row.get("next_activity"))
        tgt_grp = infer_assessment_group_label(atypes if isinstance(atypes, list) else [])
        if row.get("_source") == "strategy_log":
            tv, td, tn, tg = _strategy_log_derived_targets(row.get("strategy"))
            tgt_view, tgt_diff, tgt_next, tgt_grp = tv, td, tn, tg

        target_row = {
            **feats,
            "teaching_view": normalize_teaching_view_label(tgt_view),
            "difficulty": normalize_difficulty_label(tgt_diff),
            "next_action": tgt_next,
            "assessment_type_group": tgt_grp,
        }
        rows.append(target_row)
    return rows


def build_training_dataframe(db_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    root = ROOT
    meta: Dict[str, Any] = {
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_labels_used": True,
        "data_sources_used": [],
        "limitations": [
            "Targets are derived from teaching_strategy_training_log and/or teaching_strategy_log "
            "and mapped into the project label schema; they are operational logs, not independent human labels.",
        ],
    }
    db = Path(db_path) if db_path else DB_PATH
    fusion_csv = _optional_csv_extra(root)
    fusion_json = _optional_fusion_extra(root)
    fusion_extra: Dict[str, Dict[str, float]] = {}
    for m in (fusion_csv, fusion_json):
        for lid, vals in m.items():
            fusion_extra.setdefault(lid, {}).update(vals)
    if fusion_extra:
        meta["data_sources_used"].append("evaluation_outputs/csv or json (fused_score enrichment)")
    if not db.exists():
        meta["limitations"].append("Database missing; using synthetic comparison dataset only.")
        df = _synthetic_training_frame(160)
        meta["synthetic_row_count"] = len(df)
        meta["synthetic_used"] = True
        return df, meta

    con = sqlite3.connect(str(db))
    wanted_training = [
        "learner_id",
        "concept_id",
        "teaching_view",
        "difficulty",
        "assessment_types_json",
        "progression_action",
        "next_activity",
        "evaluation_score",
        "evidence_strategy_json",
        "xai_json",
        "policy_output_json",
    ]
    select_sql, picked = _select_existing_columns(con, "teaching_strategy_training_log", wanted_training)
    log = pd.DataFrame()
    if select_sql and "learner_id" in picked:
        log = _safe_read_sql(con, f"SELECT {select_sql} FROM teaching_strategy_training_log")
        meta["data_sources_used"].append("teaching_strategy_training_log")

    mistakes = _mistake_aggregates_dynamic(con)
    quiz, xp = _quiz_xp_aggregates(con)
    beh = _behaviour_latest(con)
    kt = _knowledge_avg_mastery(con)
    slog = _load_teaching_strategy_log_frame(con)
    if not slog.empty:
        meta["data_sources_used"].append("teaching_strategy_log")
    con.close()

    mistakes = _normalize_agg(
        mistakes,
        [
            "mistake_count",
            "high_severity_mistake_count",
            "wrong_output_count",
            "syntax_mistake_count",
        ],
    )
    quiz = _normalize_agg(quiz, ["previous_score", "hint_usage"])
    xp = _normalize_agg(xp, ["reward_xp"])

    all_rows: List[Dict[str, Any]] = []

    if not log.empty:
        log = log.copy()
        log["learner_id"] = log["learner_id"].astype(str)
        log["_source"] = "training_log"
        for extra in (mistakes, quiz, xp, beh, kt):
            if not extra.empty and "learner_id" in extra.columns:
                log = log.merge(extra, on="learner_id", how="left")
        all_rows.extend(_rows_from_merged_frame(log, fusion_extra))

    if not slog.empty:
        slog = slog.copy()
        slog["learner_id"] = slog["learner_id"].astype(str)
        slog["_source"] = "strategy_log"
        for extra in (mistakes, quiz, xp, beh, kt):
            if not extra.empty and "learner_id" in extra.columns:
                slog = slog.merge(extra, on="learner_id", how="left")
        all_rows.extend(_rows_from_merged_frame(slog, fusion_extra))

    if not all_rows:
        meta["limitations"].append("No rows from teaching_strategy_training_log or teaching_strategy_log; synthetic only.")
        df = _synthetic_training_frame(160)
        meta["synthetic_row_count"] = len(df)
        meta["synthetic_used"] = True
        return df, meta

    out = pd.DataFrame(all_rows)
    meta["real_row_count"] = len(out)

    if len(out) < 50:
        extra = _synthetic_training_frame(50 - len(out) + 20)
        out = pd.concat([out, extra], ignore_index=True)
        meta["synthetic_row_count"] = int(len(extra))
        meta["synthetic_used"] = True
        meta["limitations"].append(
            "Synthetic rows added to reach minimum training size; labels are for model comparison only."
        )

    if meta["synthetic_used"]:
        meta["limitations"].append(
            "Synthetic_used=true means some rows are simulated; do not treat metrics as real-classroom ground truth."
        )

    return out, meta


def _synthetic_training_frame(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    views = list(TEACHING_VIEW_LABELS)
    diffs = list(DIFFICULTY_LABELS)
    actions = list(NEXT_ACTION_LABELS)
    groups = list(ASSESSMENT_GROUP_LABELS)
    for _ in range(n):
        ev = {
            "mastery_score": float(rng.uniform(0.1, 0.95)),
            "behaviour_risk": float(rng.uniform(0.05, 0.95)),
            "fused_score": float(rng.uniform(0.1, 0.95)),
            "mistake_analysis": {
                "high_severity_count": float(rng.integers(0, 4)),
                "dominant_mistake_type": rng.choice([None, "wrong_output", "syntax"]),
            },
        }
        feats = evidence_to_feature_row(ev)
        rows.append(
            {
                **feats,
                "teaching_view": rng.choice(views),
                "difficulty": rng.choice(diffs),
                "next_action": rng.choice(actions),
                "assessment_type_group": rng.choice(groups),
            }
        )
    return pd.DataFrame(rows)


def _make_models(rs: int) -> Dict[str, Any]:
    models: Dict[str, Any] = {
        "DecisionTreeClassifier": DecisionTreeClassifier(max_depth=8, random_state=rs),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=40, max_depth=10, random_state=rs, n_jobs=-1
        ),
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=400, random_state=rs)),
            ]
        ),
    }
    try:
        models["GradientBoostingClassifier"] = GradientBoostingClassifier(
            n_estimators=40, max_depth=3, learning_rate=0.1, random_state=rs
        )
    except Exception:
        pass
    return models


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    labels = np.unique(np.concatenate([y_true, y_pred]))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", labels=labels, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def _pick_best(comparison: Dict[str, Dict[str, float]]) -> str:
    best = ""
    best_key = (-1.0, -1.0, -1.0)
    for name, m in comparison.items():
        if "error" in m:
            continue
        key = (m["macro_f1"], m["balanced_accuracy"], m["accuracy"])
        if key > best_key:
            best_key = key
            best = name
    return best


def train_and_report() -> Dict[str, Any]:
    df, ds_meta = build_training_dataframe()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "status": "success",
        "module": "train_teaching_strategy_selector",
        "dataset_size": len(df),
        "real_row_count": ds_meta.get("real_row_count", 0),
        "synthetic_row_count": ds_meta.get("synthetic_row_count", 0),
        "synthetic_used": bool(ds_meta.get("synthetic_used")),
        "derived_labels_used": bool(ds_meta.get("derived_labels_used")),
        "feature_names": list(FEATURE_COLUMNS),
        "targets_trained": [],
        "model_comparison": {},
        "best_model_per_target": {},
        "best_metrics_per_target": {},
        "confusion_matrices": {},
        "top_features_per_target": {},
        "limitations": list(ds_meta.get("limitations", [])),
        "data_sources_used": list(ds_meta.get("data_sources_used", [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if df.empty:
        report["status"] = "warning"
        report["limitations"].append("Empty training dataframe.")
        return report

    targets = {
        "teaching_view": "teaching_strategy_view_model.joblib",
        "difficulty": "teaching_strategy_difficulty_model.joblib",
        "next_action": "teaching_strategy_next_action_model.joblib",
        "assessment_type_group": "teaching_strategy_assessment_group_model.joblib",
    }

    explainer = ModelAttributionExplainer(random_state=42, n_repeats=2)
    trained: List[str] = []

    for target, fname in targets.items():
        try:
            y_raw = df[target].astype(str)
            le = LabelEncoder()
            y = le.fit_transform(y_raw)
            if len(np.unique(y)) < 2:
                report["limitations"].append(f"Skipping {target}: only one class in training data.")
                continue

            X = df[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=y
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=None
                )

            comparison: Dict[str, Any] = {}
            preds: Dict[str, np.ndarray] = {}
            best_model = None
            best_name = ""

            for mname, est in _make_models(42).items():
                try:
                    est.fit(X_train, y_train)
                    p = est.predict(X_test)
                    comparison[mname] = _metrics(y_test, p)
                    preds[mname] = p
                except Exception as exc:
                    warnings.warn(f"{target} {mname}: {exc}")
                    comparison[mname] = {"error": str(exc)}

            best_name = _pick_best(comparison)
            if not best_name or best_name not in preds:
                report["limitations"].append(f"No successful model for {target}.")
                continue

            best_model = _make_models(42)[best_name]
            best_model.fit(X_train, y_train)
            best_pred = best_model.predict(X_test)

            report["model_comparison"][target] = comparison
            report["best_model_per_target"][target] = best_name
            report["best_metrics_per_target"][target] = _metrics(y_test, best_pred)
            cm_arr = confusion_matrix(y_test, best_pred)
            report["confusion_matrices"][target] = cm_arr.tolist()
            tot = float(np.sum(cm_arr))
            diag = float(np.trace(cm_arr)) if cm_arr.size else 0.0
            report.setdefault("confusion_matrix_summary", {})[target] = {
                "total_labeled": int(tot),
                "correct_diagonal": int(diag),
                "accuracy_from_matrix": round(diag / tot, 4) if tot > 0 else 0.0,
            }

            bundle = {"model": best_model, "label_encoder": le, "target": target, "feature_names": FEATURE_COLUMNS}
            joblib.dump(bundle, MODEL_DIR / fname)

            n_attr = min(300, len(X_test))
            idx = np.random.RandomState(42).choice(len(X_test), size=n_attr, replace=False)
            attr = explainer.explain_model_object(
                model=best_model,
                X=X_test.iloc[idx],
                y=y_test[idx],
                target_name=target,
                feature_names=FEATURE_COLUMNS,
            )
            report["top_features_per_target"][target] = attr.get("top_features", [])

            trained.append(target)
        except Exception as exc:
            report["limitations"].append(f"Training failed for {target}: {exc}")

    report["targets_trained"] = trained

    meta = {
        "dataset_size": report["dataset_size"],
        "real_row_count": report["real_row_count"],
        "synthetic_row_count": report["synthetic_row_count"],
        "synthetic_used": report["synthetic_used"],
        "derived_labels_used": report["derived_labels_used"],
        "feature_names": FEATURE_COLUMNS,
        "targets_trained": trained,
        "best_model_per_target": report["best_model_per_target"],
        "shap_available": explainer.shap_available,
        "created_at": report["created_at"],
        "limitations": report["limitations"],
    }
    (MODEL_DIR / "teaching_strategy_model_meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    if not trained:
        report["status"] = "warning"

    return report


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Teaching strategy model report",
        "",
        f"**Status:** {report.get('status')}",
        "",
        f"**Dataset size:** {report.get('dataset_size')}",
        f"**Real rows:** {report.get('real_row_count')}",
        f"**Synthetic rows:** {report.get('synthetic_row_count')}",
        f"**Synthetic used:** {report.get('synthetic_used')}",
        f"**Derived labels used:** {report.get('derived_labels_used')}",
        "",
        "## Features",
        "",
        ", ".join(report.get("feature_names", [])),
        "",
        "## Targets trained",
        "",
        ", ".join(report.get("targets_trained", [])),
        "",
        "## Best model per target",
        "",
    ]
    for t, m in report.get("best_model_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Metrics (best model)", ""])
    for t, m in report.get("best_metrics_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Top features", ""])
    for t, tops in report.get("top_features_per_target", {}).items():
        lines.append(f"- **{t}:** {', '.join(tops) if isinstance(tops, list) else tops}")
    lines.extend(["", "## Confusion matrix summary", ""])
    for t, sm in report.get("confusion_matrix_summary", {}).items():
        lines.append(f"- **{t}:** {sm}")
    lines.extend(["", "## Confusion matrices (full)", ""])
    for t, cm in report.get("confusion_matrices", {}).items():
        lines.append(f"### {t}")
        lines.append(str(cm))
        lines.append("")
    lines.extend(["", "## Limitations", ""])
    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")
    lines.extend(["", "## Final report wording", "", FINAL_WORDING, ""])
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
    print("MODULE: train_teaching_strategy_selector")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"MODEL_DIR: {MODEL_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
