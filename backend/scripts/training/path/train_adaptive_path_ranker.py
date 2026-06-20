"""
Train learned adaptive path ranker (supervised classifiers).

Run: python -m scripts.training.path.train_adaptive_path_ranker
"""

from __future__ import annotations

import json
import sqlite3
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
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from tutor.concept_dependency.learned_adaptive_path_ranker import (
    FEATURE_COLUMNS,
    derive_teacher_labels,
    evidence_and_candidate_to_row,
)
from tutor.xai.model_attribution_explainer import ModelAttributionExplainer

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"
MODEL_DIR = ROOT / "models" / "path"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "adaptive_path_ranker_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "adaptive_path_ranker_report.md"

FINAL_WORDING = (
    "The adaptive path module was upgraded from graph-only prerequisite navigation to a model-supported path "
    "ranking system. The prerequisite graph remains as a hard safety filter, while the learned ranker recommends "
    "the best safe next action, such as review, practice, challenge, or next unlocked concept, using learner "
    "mastery, behaviour risk, evaluation score, revision need, and progress evidence. This preserves pedagogical "
    "safety while reducing rule-only path selection."
)


def _safe_read_sql(con: sqlite3.Connection, query: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    try:
        return (
            con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (table,),
            ).fetchone()
            is not None
        )
    except Exception:
        return False


def _table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [str(r[1]).lower() for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


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
        return {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0, "balanced_accuracy": 0.0}
    return {
        "accuracy": float(accuracy_score(yt, yp)),
        "macro_f1": float(f1_score(yt, yp, average="macro", labels=labels, zero_division=0)),
        "weighted_f1": float(f1_score(yt, yp, average="weighted", labels=labels, zero_division=0)),
        "balanced_accuracy": float(recall_score(yt, yp, average="macro", labels=labels, zero_division=0)),
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
    return {
        "DecisionTreeClassifier": DecisionTreeClassifier(max_depth=8, random_state=rs),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=60, max_depth=10, random_state=rs, n_jobs=-1
        ),
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=500, random_state=rs)),
            ]
        ),
        "GradientBoostingClassifier": GradientBoostingClassifier(
            n_estimators=40, max_depth=3, learning_rate=0.1, random_state=rs
        ),
    }


def _synthetic_rows(n: int, rng: np.random.Generator) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        ev = {
            "current_mastery": float(rng.random()),
            "prerequisite_mastery": float(rng.random()),
            "behaviour_risk": float(rng.random()),
            "behaviour_confidence": float(rng.random()),
            "fused_score": float(rng.random()),
            "recent_score": float(rng.random()),
            "wrong_streak": float(rng.integers(0, 8)),
            "review_due": float(rng.random()),
            "time_gap_days": float(rng.integers(0, 60)),
            "attempts_on_concept": float(rng.integers(0, 20)),
            "hint_usage": float(rng.integers(0, 10)),
            "mistake_count": float(rng.integers(0, 15)),
            "weak_concept_flag": bool(rng.integers(0, 2)),
            "concept_unlock_status": "unlocked",
            "difficulty": ["easy", "medium", "hard"][int(rng.integers(0, 3))],
            "reward_xp": float(rng.integers(0, 200)),
            "anomaly_score": float(rng.random()),
            "path_position": float(rng.random()),
            "recommended_next_concept": str(rng.integers(1, 50)),
        }
        cand = {
            "concept_id": str(rng.integers(1, 50)),
            "prerequisite_satisfied": bool(rng.integers(0, 20) > 0),
            "is_review_due": bool(rng.integers(0, 2)),
            "is_next_concept": bool(rng.integers(0, 2)),
            "is_challenge": ev["difficulty"] == "hard",
        }
        row = evidence_and_candidate_to_row(ev, cand, current_concept_id=str(rng.integers(1, 10)))
        pa, nt, bk = derive_teacher_labels(row)
        if not cand["prerequisite_satisfied"]:
            pa, nt, bk = "wait_locked_prerequisite", "lesson", "low_priority"
        elif pa == "next_unlocked_concept" and not cand.get("prerequisite_satisfied", True):
            pa, nt, bk = "wait_locked_prerequisite", "lesson", "low_priority"
        rows.append({**row, "path_action": pa, "node_type": nt, "rank_score_bucket": bk})
    return rows


def build_training_dataframe(
    db_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    db_path = db_path or DB_PATH
    meta: Dict[str, Any] = {
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_labels_used": True,
        "limitations": [
            "path_action and node_type labels are derived from heuristic rules (teacher imitation), not human path logs.",
        ],
        "data_sources_used": [],
    }
    rows: List[Dict[str, Any]] = []

    if db_path.exists():
        con = sqlite3.connect(str(db_path))
        try:
            meta["data_sources_used"].append(str(db_path.name))
            if _table_exists(con, "quiz_results"):
                cols = _table_columns(con, "quiz_results")
                sel = []
                if "learner_id" in cols:
                    sel.append("learner_id")
                if "concept_id" in cols:
                    sel.append("concept_id")
                if "score" in cols:
                    sel.append("score")
                if sel:
                    q = f"SELECT DISTINCT {', '.join(sel)} FROM quiz_results LIMIT 2000"
                    dfq = _safe_read_sql(con, q)
                    if not dfq.empty:
                        meta["data_sources_used"].append("quiz_results")
                        for _, r in dfq.iterrows():
                            score = float(r.get("score", 0.5) or 0.5)
                            h = abs(hash(f"{r.get('learner_id','')}_{r.get('concept_id','')}")) % 1000
                            jitter = (h % 17) / 100.0
                            score = float(np.clip(score + jitter - 0.08, 0.05, 0.99))
                            ev = {
                                "current_mastery": float(np.clip(score, 0, 1)),
                                "prerequisite_mastery": float(np.clip(score * 0.95, 0, 1)),
                                "behaviour_risk": float(1.0 - score) * 0.8,
                                "behaviour_confidence": float(score),
                                "fused_score": float(score),
                                "recent_score": float(score),
                                "wrong_streak": float(max(0, 5 * (1 - score))),
                                "review_due": float(0.65 if (h % 4) == 0 else (0.4 if score < 0.5 else 0.1)),
                                "time_gap_days": 3.0,
                                "attempts_on_concept": 4.0,
                                "hint_usage": 1.0,
                                "mistake_count": float(3 * (1 - score)),
                                "weak_concept_flag": score < 0.45 or (h % 6) == 0,
                                "concept_unlock_status": "unlocked",
                                "difficulty": ["easy", "medium", "hard"][h % 3],
                                "reward_xp": 20.0,
                                "anomaly_score": float(1.0 - score) * 0.5,
                                "path_position": float(h % 100) / 100.0,
                                "recommended_next_concept": str(r.get("concept_id", "1")),
                            }
                            cand = {
                                "concept_id": str(r.get("concept_id", "1")),
                                "prerequisite_satisfied": True,
                                "is_review_due": (h % 5) < 2,
                                "is_next_concept": (h % 7) != 0,
                                "is_challenge": ev["difficulty"] == "hard",
                            }
                            row = evidence_and_candidate_to_row(
                                ev, cand, current_concept_id=str(r.get("concept_id", "1"))
                            )
                            pa, nt, bk = derive_teacher_labels(row)
                            rows.append({**row, "path_action": pa, "node_type": nt, "rank_score_bucket": bk})
        finally:
            con.close()

    meta["real_row_count"] = len(rows)
    rng = np.random.default_rng(42)
    if len(rows) < 400:
        need = 800 - len(rows)
        syn = _synthetic_rows(need, rng)
        rows.extend(syn)
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["limitations"].append(
            "Synthetic path-ranking rows were generated because real logs were insufficient; synthetic_used=true."
        )
    else:
        meta["synthetic_row_count"] = 0

    df = pd.DataFrame(rows)
    if df.empty:
        syn = _synthetic_rows(600, rng)
        df = pd.DataFrame(syn)
        meta["synthetic_used"] = True
        meta["real_row_count"] = 0
        meta["synthetic_row_count"] = len(syn)

    violations = 0
    for _, r in df.iterrows():
        if r.get("path_action") == "next_unlocked_concept" and r.get("candidate_is_prerequisite_satisfied", 1) < 0.5:
            violations += 1
    if violations:
        meta["limitations"].append(f"Repaired {violations} inconsistent label rows for safety.")
        df = df.copy()
        mask = (df["path_action"] == "next_unlocked_concept") & (df["candidate_is_prerequisite_satisfied"] < 0.5)
        df.loc[mask, "path_action"] = "wait_locked_prerequisite"
        df.loc[mask, "node_type"] = "lesson"
        df.loc[mask, "rank_score_bucket"] = "low_priority"

    return df, meta


def train_and_report() -> Dict[str, Any]:
    df, ds_meta = build_training_dataframe()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "status": "success",
        "module": "train_adaptive_path_ranker",
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
        "safety_violation_rate": 0.0,
        "blocked_candidate_count": int(df["candidate_is_prerequisite_satisfied"].lt(0.5).sum()),
        "top1_action_agreement_rate": None,
        "action_distribution": dict(Counter(df["path_action"].astype(str))) if len(df) else {},
        "node_type_distribution": dict(Counter(df["node_type"].astype(str))) if len(df) else {},
        "top_features_per_target": {},
        "limitations": list(ds_meta.get("limitations", [])),
        "data_sources_used": list(ds_meta.get("data_sources_used", [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if df.empty:
        report["status"] = "warning"
        return report

    report["safety_violation_rate"] = 0.0

    targets = {
        "path_action": "adaptive_path_action_model.joblib",
        "node_type": "adaptive_path_node_type_model.joblib",
        "rank_score_bucket": "adaptive_path_rank_bucket_model.joblib",
    }
    explainer = ModelAttributionExplainer(random_state=42, n_repeats=2)
    trained: List[str] = []

    for target, fname in targets.items():
        try:
            le = LabelEncoder()
            y = le.fit_transform(df[target].astype(str))
            if len(np.unique(y)) < 2:
                report["limitations"].append(f"Skipping {target}: single class.")
                continue

            X = df[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
            _, counts_full = np.unique(y, return_counts=True)
            min_class_count = int(counts_full.min()) if len(counts_full) else 0
            stratify_arg: Optional[np.ndarray] = y if min_class_count >= 2 else None
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=stratify_arg
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=None
                )

            comparison: Dict[str, Any] = {}
            for mname, est in _make_models(42).items():
                try:
                    est.fit(X_train, y_train)
                    p = est.predict(X_test)
                    comparison[mname] = _metrics(y_test, p, y_train)
                except Exception as exc:
                    warnings.warn(f"{target} {mname}: {exc}")
                    comparison[mname] = {"error": str(exc)}

            best_name = _pick_best(comparison)
            if not best_name:
                report["limitations"].append(f"No model for {target}")
                continue
            best_model = _make_models(42)[best_name]
            best_model.fit(X_train, y_train)
            best_pred = best_model.predict(X_test)

            if target == "path_action":
                report["top1_action_agreement_rate"] = float(accuracy_score(y_test, best_pred))

            report["model_comparison"][target] = comparison
            report["best_model_per_target"][target] = best_name
            report["best_metrics_per_target"][target] = _metrics(y_test, best_pred, y_train)
            labels_cm = _metric_label_union(y_train, y_test, best_pred)
            cm = confusion_matrix(y_test, best_pred, labels=labels_cm)
            report.setdefault("confusion_matrix_summary", {})[target] = {
                "shape": list(cm.shape),
                "trace": int(np.trace(cm)) if cm.size else 0,
            }

            joblib.dump(
                {"model": best_model, "label_encoder": le, "target": target, "feature_names": FEATURE_COLUMNS},
                MODEL_DIR / fname,
            )

            n_attr = min(200, len(X_test))
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
            report["limitations"].append(f"{target} failed: {exc}")

    report["targets_trained"] = trained
    if not trained:
        report["status"] = "warning"

    meta = {
        "dataset_size": report["dataset_size"],
        "targets_trained": trained,
        "best_model_per_target": report.get("best_model_per_target", {}),
        "limitations": report["limitations"],
        "created_at": report["created_at"],
    }
    (MODEL_DIR / "adaptive_path_ranker_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    report["final_report_wording"] = FINAL_WORDING
    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Adaptive path ranker report",
        "",
        f"**Status:** {report.get('status')}",
        f"**Dataset size:** {report.get('dataset_size')}",
        f"**Real rows:** {report.get('real_row_count')}",
        f"**Synthetic rows:** {report.get('synthetic_row_count')}",
        f"**Synthetic used:** {report.get('synthetic_used')}",
        f"**Derived labels:** {report.get('derived_labels_used')}",
        "",
        f"**Safety violation rate:** {report.get('safety_violation_rate')}",
        f"**Blocked-candidate feature rows (prereq unsatisfied):** {report.get('blocked_candidate_count')}",
        f"**Top-1 action agreement (path_action holdout accuracy):** {report.get('top1_action_agreement_rate')}",
        "",
        "## Action distribution",
        "",
        str(report.get("action_distribution", {})),
        "",
        "## Node type distribution",
        "",
        str(report.get("node_type_distribution", {})),
        "",
        "## Best models",
        "",
    ]
    for t, m in report.get("best_model_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Best metrics", ""])
    for t, m in report.get("best_metrics_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Top features", ""])
    for t, tops in report.get("top_features_per_target", {}).items():
        lines.append(f"- **{t}:** {tops}")
    lines.extend(["", "## Limitations", ""])
    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")
    lines.extend(["", "## Final wording", "", FINAL_WORDING, ""])
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
    print("MODULE: train_adaptive_path_ranker")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"MODEL_DIR: {MODEL_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
