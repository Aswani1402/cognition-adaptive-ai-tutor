"""
Train surrogate sklearn models that approximate tutor decisions from logs/features.

Does not replace the evidence-card XAI dashboard; complements it with model-based attribution.
"""

from __future__ import annotations

import json
import sqlite3
import warnings
from dataclasses import dataclass, field
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

from tutor.xai.model_attribution_explainer import ModelAttributionExplainer

FEATURE_COLUMNS: List[str] = [
    "mastery_score",
    "behaviour_risk",
    "behaviour_confidence",
    "fused_score",
    "debug_score",
    "output_prediction_score",
    "mistake_count",
    "wrong_output_count",
    "syntax_mistake_count",
    "rag_support_score",
    "review_priority",
    "hint_usage",
    "previous_score",
    "reward_xp",
    "anomaly_score",
    "difficulty_encoded",
    "weak_skill_encoded",
]

TARGET_COLUMNS: List[str] = [
    "selected_teaching_view",
    "next_action",
    "promotion_allowed",
    "difficulty_selected",
    "revision_needed",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_read_sql(con: Any, query: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()


def _encode_weak_skill(label: Any) -> float:
    if label is None or (isinstance(label, float) and np.isnan(label)):
        return 0.0
    s = str(label).lower()
    mapping = {
        "disengaged": 4.0,
        "struggling": 3.0,
        "neutral": 2.0,
        "engaged": 1.0,
        "expert": 0.0,
    }
    for k, v in mapping.items():
        if k in s:
            return v
    return float(pd.Series([label]).astype(str).factorize()[0][0])


def _difficulty_to_code(d: Any) -> float:
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return 1.0
    s = str(d).lower().strip()
    if s == "easy":
        return 0.0
    if s == "medium":
        return 1.0
    if s == "hard":
        return 2.0
    return 1.0


def _map_teaching_view_from_fusion(row: pd.Series) -> str:
    if int(row.get("review_due") or 0) == 1:
        return "revision_view"
    s = str(row.get("recommended_strategy") or "").lower()
    if s == "remedial":
        return "misconception_view"
    if s == "practice":
        return "code_view"
    if s == "advanced":
        return "challenge_view"
    return "definition_view"


def _map_next_action(row: pd.Series) -> str:
    fa = str(row.get("final_action") or "").lower().strip()
    mapping = {
        "reinforce_current": "practice",
        "light_review": "review",
        "progress_with_review_later": "next_concept",
    }
    return mapping.get(fa, "continue")


def _map_promotion_allowed(row: pd.Series, promo_by_learner: Dict[str, int]) -> int:
    lid = str(row.get("learner_id") or "")
    if lid in promo_by_learner:
        return int(promo_by_learner[lid])
    m = float(row.get("mastery_score") or 0.0)
    s = str(row.get("recommended_strategy") or "").lower()
    return 1 if (m >= 0.65 and s == "advanced") else 0


def _build_aggregates(con: Any) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mistakes = _safe_read_sql(
        con,
        """
        SELECT learner_id,
               COUNT(*) AS mistake_count,
               SUM(CASE WHEN LOWER(IFNULL(mistake_type,'')) LIKE '%wrong_output%' THEN 1 ELSE 0 END) AS wrong_output_count,
               SUM(CASE WHEN LOWER(IFNULL(mistake_type,'')) LIKE '%syntax%' THEN 1 ELSE 0 END) AS syntax_mistake_count,
               SUM(CASE WHEN LOWER(IFNULL(task_type,'')) LIKE '%debug%' OR LOWER(IFNULL(mistake_type,'')) LIKE '%debug%' THEN 1 ELSE 0 END) AS debug_rows
        FROM learner_mistake_log
        GROUP BY learner_id
        """,
    )
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
    xp = _safe_read_sql(
        con,
        """
        SELECT learner_id, SUM(xp_awarded) AS reward_xp
        FROM reward_event_log
        GROUP BY learner_id
        """,
    )
    rev = _safe_read_sql(
        con,
        """
        SELECT learner_id,
               MAX(CASE LOWER(IFNULL(priority,''))
                     WHEN 'high' THEN 3.0
                     WHEN 'medium' THEN 2.0
                     WHEN 'low' THEN 1.0
                     ELSE 1.0 END) AS review_priority
        FROM revision_schedule
        GROUP BY learner_id
        """,
    )
    beh = _safe_read_sql(
        con,
        """
        SELECT learner_id, behavior_risk, behavior_confidence, behavior_label, timestamp
        FROM behaviour_state
        ORDER BY learner_id, timestamp
        """,
    )
    return mistakes, quiz, xp, rev, beh


def _latest_behaviour(beh: pd.DataFrame) -> pd.DataFrame:
    if beh.empty or "learner_id" not in beh.columns:
        return pd.DataFrame(columns=["learner_id", "behavior_risk", "behavior_confidence", "behavior_label"])
    beh = beh.copy()
    beh["_ts"] = pd.to_datetime(beh["timestamp"], errors="coerce")
    beh = beh.sort_values(["learner_id", "_ts"]).drop_duplicates("learner_id", keep="last")
    return beh[["learner_id", "behavior_risk", "behavior_confidence", "behavior_label"]]


def _promotion_from_rewards(con: Any) -> Dict[str, int]:
    df = _safe_read_sql(
        con,
        """
        SELECT learner_id, MAX(promotion_allowed) AS promotion_allowed
        FROM reward_event_log
        GROUP BY learner_id
        """,
    )
    if df.empty:
        return {}
    return {str(r["learner_id"]): int(r["promotion_allowed"]) for _, r in df.iterrows()}


def build_surrogate_dataset(db_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Build training dataframe + metadata (synthetic flags, derived labels, limitations).
    """
    root = _project_root()
    db = Path(db_path) if db_path else root / "external" / "core_data" / "tutor.db"
    meta: Dict[str, Any] = {
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_label_used": False,
        "limitations": [],
        "db_path": str(db),
    }

    if not db.exists():
        meta["limitations"].append("SQLite database missing; using synthetic demo dataset only.")
        syn = _generate_synthetic_dataset(120, random_state=42)
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["derived_label_used"] = True
        meta["limitations"].append(
            "Synthetic decision labels are for demonstration and model comparison only."
        )
        return syn, meta

    con = sqlite3.connect(str(db))
    fusion = _safe_read_sql(
        con,
        """
        SELECT learner_id, concept_id, mastery_score, behavior_score AS behaviour_score_legacy,
               evaluation_score, review_due, final_action, recommended_strategy,
               recommended_difficulty, learning_signal, created_at
        FROM fusion_decision_log
        """,
    )
    mistakes, quiz, xp, rev, beh_raw = _build_aggregates(con)
    beh_latest = _latest_behaviour(beh_raw)
    promo_map = _promotion_from_rewards(con)
    con.close()

    if mistakes.empty or "learner_id" not in mistakes.columns:
        mistakes = pd.DataFrame(
            columns=[
                "learner_id",
                "mistake_count",
                "wrong_output_count",
                "syntax_mistake_count",
                "debug_rows",
            ]
        )
    if quiz.empty or "learner_id" not in quiz.columns:
        quiz = pd.DataFrame(columns=["learner_id", "previous_score", "hint_usage"])
    if xp.empty or "learner_id" not in xp.columns:
        xp = pd.DataFrame(columns=["learner_id", "reward_xp"])
    if rev.empty or "learner_id" not in rev.columns:
        rev = pd.DataFrame(columns=["learner_id", "review_priority"])

    if fusion.empty:
        meta["limitations"].append("fusion_decision_log empty; using synthetic demo dataset only.")
        syn = _generate_synthetic_dataset(120, random_state=42)
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["derived_label_used"] = True
        meta["limitations"].append(
            "Synthetic decision labels are for demonstration and model comparison only."
        )
        return syn, meta

    df = fusion.copy()
    df["learner_id"] = df["learner_id"].astype(str)
    df["mastery_score"] = pd.to_numeric(df["mastery_score"], errors="coerce").fillna(0.0)

    df = df.merge(mistakes, on="learner_id", how="left")
    df = df.merge(quiz, on="learner_id", how="left")
    df = df.merge(xp, on="learner_id", how="left")
    df = df.merge(rev, on="learner_id", how="left")
    df = df.merge(beh_latest, on="learner_id", how="left")

    df["mistake_count"] = pd.to_numeric(df["mistake_count"], errors="coerce").fillna(0.0)
    df["wrong_output_count"] = pd.to_numeric(df["wrong_output_count"], errors="coerce").fillna(0.0)
    df["syntax_mistake_count"] = pd.to_numeric(df["syntax_mistake_count"], errors="coerce").fillna(0.0)
    if "debug_rows" in df.columns:
        dbg_hint = pd.to_numeric(df["debug_rows"], errors="coerce").fillna(0.0)
        mx = float(dbg_hint.max()) if len(dbg_hint) else 0.0
        df["debug_score"] = np.clip(dbg_hint / (mx + 1e-6), 0.0, 1.0) if mx > 0 else 0.1
    else:
        df["debug_score"] = 0.1

    df["behaviour_risk"] = pd.to_numeric(df["behavior_risk"], errors="coerce").fillna(
        1.0 - pd.to_numeric(df["behaviour_score_legacy"], errors="coerce").fillna(0.5)
    )
    df["behaviour_confidence"] = pd.to_numeric(df["behavior_confidence"], errors="coerce").fillna(0.5)

    eval_sc = pd.to_numeric(df["evaluation_score"], errors="coerce").fillna(df["mastery_score"])
    df["fused_score"] = 0.55 * df["mastery_score"] + 0.35 * eval_sc + 0.10 * (1.0 - df["behaviour_risk"])
    df["fused_score"] = df["fused_score"].clip(0.0, 1.0)

    df["output_prediction_score"] = np.where(
        df["wrong_output_count"] > 0,
        np.clip(1.0 - np.log1p(df["wrong_output_count"]) / 5.0, 0.0, 1.0),
        df["fused_score"],
    )

    df["rag_support_score"] = 0.55
    df["review_priority"] = pd.to_numeric(df["review_priority"], errors="coerce").fillna(1.0)
    df["hint_usage"] = pd.to_numeric(df["hint_usage"], errors="coerce").fillna(0.0)
    df["previous_score"] = pd.to_numeric(df["previous_score"], errors="coerce").fillna(df["mastery_score"])
    df["reward_xp"] = pd.to_numeric(df["reward_xp"], errors="coerce").fillna(0.0)
    df["anomaly_score"] = df["behaviour_risk"]

    df["difficulty_encoded"] = df["recommended_difficulty"].map(_difficulty_to_code)
    df["weak_skill_encoded"] = df["behavior_label"].map(_encode_weak_skill)

    meta["derived_label_used"] = True
    meta["limitations"].append(
        "Teaching views and several targets are mapped from fusion_decision_log fields; "
        "they reflect logged tutor/fusion outputs, not independent human labels."
    )
    if promo_map:
        meta["limitations"].append("promotion_allowed merges sparse reward_event_log where available; otherwise rule-derived from mastery/strategy.")

    df["selected_teaching_view"] = df.apply(_map_teaching_view_from_fusion, axis=1)
    df["next_action"] = df.apply(_map_next_action, axis=1)
    df["promotion_allowed"] = df.apply(lambda r: _map_promotion_allowed(r, promo_map), axis=1).astype(int)
    df["difficulty_selected"] = df["recommended_difficulty"].fillna("medium").astype(str).str.lower()
    df["revision_needed"] = pd.to_numeric(df["review_due"], errors="coerce").fillna(0).astype(int)

    out = df[[*FEATURE_COLUMNS, *TARGET_COLUMNS]].copy()
    out[FEATURE_COLUMNS] = (
        out[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    out["promotion_allowed"] = pd.to_numeric(out["promotion_allowed"], errors="coerce").fillna(0).astype(int)
    out["revision_needed"] = pd.to_numeric(out["revision_needed"], errors="coerce").fillna(0).astype(int)
    for col in ("selected_teaching_view", "next_action", "difficulty_selected"):
        out[col] = out[col].fillna("").astype(str)

    meta["real_row_count"] = len(out)

    if len(out) < 50:
        syn_extra = _generate_synthetic_dataset(max(50 - len(out), 30), random_state=43)
        out = pd.concat([out, syn_extra], ignore_index=True)
        meta["synthetic_row_count"] = int(len(syn_extra))
        meta["synthetic_used"] = True
        meta["limitations"].append(
            "Combined synthetic rows to reach minimum dataset size for stable surrogate training."
        )
    else:
        meta["synthetic_row_count"] = 0

    if meta["synthetic_used"]:
        meta["limitations"].append(
            "Synthetic decision labels are for demonstration and model comparison only; they are not ground-truth learner decisions."
        )

    return out, meta


def _generate_synthetic_dataset(n: int, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    mastery = rng.uniform(0.05, 0.98, n)
    beh_risk = rng.uniform(0.05, 0.95, n)
    fused = 0.5 * mastery + 0.4 * (1.0 - beh_risk) + rng.normal(0, 0.05, n)
    fused = np.clip(fused, 0.0, 1.0)

    mistake_count = rng.integers(0, 12, n)
    wrong_out = rng.integers(0, 6, n)
    syntax_m = rng.integers(0, 4, n)

    teaching = []
    next_a = []
    promo = []
    diff = []
    rev = []

    views = [
        "definition_view",
        "code_view",
        "revision_view",
        "debug_view",
        "misconception_view",
        "challenge_view",
        "transfer_view",
    ]
    actions = ["continue", "reteach", "review", "practice", "challenge", "next_concept"]
    diffs = ["easy", "medium", "hard"]

    for i in range(n):
        m, fr, br = float(mastery[i]), float(fused[i]), float(beh_risk[i])
        dbg = float(wrong_out[i]) / 6.0
        if m < 0.45 or fr < 0.42:
            teaching.append("revision_view" if rng.random() > 0.35 else "misconception_view")
            next_a.append("reteach" if rng.random() > 0.5 else "review")
            promo.append(0)
            diff.append("easy" if m < 0.35 else "medium")
            rev.append(1)
        elif br > 0.72 and dbg > 0.4:
            teaching.append("debug_view")
            next_a.append("practice")
            promo.append(0)
            diff.append(rng.choice(diffs))
            rev.append(int(rng.random() > 0.6))
        elif m > 0.78 and fr > 0.72 and br < 0.45:
            teaching.append(rng.choice(["challenge_view", "transfer_view"]))
            next_a.append("next_concept" if rng.random() > 0.4 else "challenge")
            promo.append(1)
            diff.append(rng.choice(["medium", "hard"]))
            rev.append(int(rng.random() > 0.85))
        else:
            teaching.append(rng.choice(views))
            next_a.append(rng.choice(actions))
            promo.append(int(rng.random() > 0.55))
            diff.append(rng.choice(diffs))
            rev.append(int(br > 0.65 or m < 0.55))

    debug_score = np.clip(wrong_out.astype(float) / 6.0, 0.0, 1.0)
    out_pred = np.clip(1.0 - wrong_out.astype(float) / 8.0, 0.0, 1.0)

    df = pd.DataFrame(
        {
            "mastery_score": mastery,
            "behaviour_risk": beh_risk,
            "behaviour_confidence": np.clip(1.0 - beh_risk + rng.normal(0, 0.05, n), 0.0, 1.0),
            "fused_score": fused,
            "debug_score": debug_score,
            "output_prediction_score": out_pred,
            "mistake_count": mistake_count.astype(float),
            "wrong_output_count": wrong_out.astype(float),
            "syntax_mistake_count": syntax_m.astype(float),
            "rag_support_score": rng.uniform(0.2, 0.85, n),
            "review_priority": rng.choice([1.0, 2.0, 3.0], n),
            "hint_usage": rng.uniform(0.0, 1.0, n),
            "previous_score": np.clip(mastery + rng.normal(0, 0.06, n), 0.0, 1.0),
            "reward_xp": rng.integers(0, 5000, n).astype(float),
            "anomaly_score": beh_risk,
            "difficulty_encoded": rng.choice([0.0, 1.0, 2.0], n),
            "weak_skill_encoded": rng.uniform(0.0, 4.0, n),
            "selected_teaching_view": teaching,
            "next_action": next_a,
            "promotion_allowed": promo,
            "difficulty_selected": diff,
            "revision_needed": rev,
        }
    )
    return df


def _make_sklearn_models(random_state: int) -> Dict[str, Any]:
    # Smaller / faster defaults: surrogate training runs many fits per session.
    models: Dict[str, Any] = {
        "DecisionTreeClassifier": DecisionTreeClassifier(max_depth=8, random_state=random_state),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=40,
            max_depth=10,
            random_state=random_state,
            n_jobs=-1,
        ),
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(max_iter=500, random_state=random_state),
                ),
            ]
        ),
    }
    try:
        models["GradientBoostingClassifier"] = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=random_state,
        )
    except Exception:
        pass
    return models


def _prepare_xy(
    df: pd.DataFrame,
    target: str,
) -> Tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    d = df.dropna(subset=[target]).copy()
    y_raw = d[target]
    le = LabelEncoder()
    y = le.fit_transform(y_raw.astype(str))
    X = d[FEATURE_COLUMNS].copy()
    return X, y, le


def _score_model(y_true: np.ndarray, y_pred: np.ndarray, labels: Optional[np.ndarray] = None) -> Dict[str, float]:
    labels = labels if labels is not None else np.unique(np.concatenate([y_true, y_pred]))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(
            f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
        ),
        "weighted_f1": float(
            f1_score(y_true, y_pred, average="weighted", labels=labels, zero_division=0)
        ),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def _compare_models(
    models: Dict[str, Any],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> Tuple[str, Dict[str, Dict[str, float]], Dict[str, np.ndarray], Any]:
    comparison: Dict[str, Dict[str, float]] = {}
    preds: Dict[str, np.ndarray] = {}
    best_name = ""
    best_model = None
    best_key: Tuple[float, float, float] = (-1.0, -1.0, -1.0)

    for name, est in models.items():
        try:
            est.fit(X_train, y_train)
            pred = est.predict(X_test)
            scores = _score_model(y_test, pred)
            comparison[name] = scores
            preds[name] = pred
            key = (scores["macro_f1"], scores["balanced_accuracy"], scores["accuracy"])
            if key > best_key:
                best_key = key
                best_name = name
                best_model = est
        except Exception as exc:
            warnings.warn(f"Model {name} failed: {exc}")
            comparison[name] = {
                "accuracy": 0.0,
                "macro_f1": 0.0,
                "weighted_f1": 0.0,
                "balanced_accuracy": 0.0,
                "error": str(exc),
            }

    if best_model is None:
        raise RuntimeError("No surrogate model trained successfully.")

    return best_name, comparison, preds, best_model


def _subsample_for_attribution(
    X: pd.DataFrame,
    y: np.ndarray,
    max_rows: int,
    random_state: int,
) -> Tuple[pd.DataFrame, np.ndarray]:
    if len(X) <= max_rows:
        return X, y
    rng = np.random.RandomState(random_state)
    idx = rng.choice(len(X), size=max_rows, replace=False)
    return X.iloc[idx], y[idx]


@dataclass
class XAISurrogateTrainer:
    random_state: int = 42
    test_size: float = 0.25
    """Max test rows used for permutation importance (full test set still used for metrics)."""
    attribution_max_rows: int = 350
    """Fewer repeats = faster permutation importance with slightly noisier std."""
    permutation_n_repeats: int = 2
    root: Path = field(default_factory=_project_root)

    def __post_init__(self) -> None:
        self.explainer = ModelAttributionExplainer(
            random_state=self.random_state,
            n_repeats=self.permutation_n_repeats,
        )
        self.shap_available = self.explainer.shap_available

    def build_training_dataframe(self, db_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        return build_surrogate_dataset(db_path)

    def train_all_and_report(self, db_path: Optional[Path] = None) -> Dict[str, Any]:
        df, ds_meta = self.build_training_dataframe(db_path)
        models_dir = self.root / "models" / "xai"
        models_dir.mkdir(parents=True, exist_ok=True)

        report: Dict[str, Any] = {
            "status": "success",
            "module": "XAISurrogateTrainer",
            "dataset_size": len(df),
            "real_row_count": ds_meta.get("real_row_count", 0),
            "synthetic_row_count": ds_meta.get("synthetic_row_count", 0),
            "synthetic_used": bool(ds_meta.get("synthetic_used")),
            "derived_label_used": bool(ds_meta.get("derived_label_used")),
            "feature_names": list(FEATURE_COLUMNS),
            "target_labels": {t: sorted(df[t].astype(str).unique().tolist()) for t in TARGET_COLUMNS},
            "model_comparison": {},
            "best_model_per_target": {},
            "best_metrics_per_target": {},
            "confusion_matrices": {},
            "attribution_per_target": {},
            "attribution_method": "permutation_importance",
            "attribution_max_rows": self.attribution_max_rows,
            "permutation_n_repeats": self.permutation_n_repeats,
            "shap_available": self.shap_available,
            "limitations": list(ds_meta.get("limitations", [])),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if df.empty:
            report["status"] = "warning"
            report["limitations"].append("Empty dataset; cannot train surrogate models.")
            return report

        targets_trained: List[str] = []

        for target in TARGET_COLUMNS:
            try:
                sklearn_models = _make_sklearn_models(self.random_state)
                X, y, le = _prepare_xy(df, target)
                if len(np.unique(y)) < 2:
                    report["limitations"].append(f"Skipping {target}: only one class present.")
                    continue

                try:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X,
                        y,
                        test_size=self.test_size,
                        random_state=self.random_state,
                        stratify=y,
                    )
                except ValueError:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X,
                        y,
                        test_size=self.test_size,
                        random_state=self.random_state,
                        stratify=None,
                    )

                best_name, comparison, preds, best_model = _compare_models(
                    sklearn_models,
                    X_train,
                    X_test,
                    y_train,
                    y_test,
                )

                report["model_comparison"][target] = comparison
                report["best_model_per_target"][target] = best_name
                best_pred = preds[best_name]
                metrics = _score_model(y_test, best_pred)
                report["best_metrics_per_target"][target] = metrics

                cm = confusion_matrix(y_test, best_pred)
                report["confusion_matrices"][target] = cm.tolist()

                bundle = {
                    "model": best_model,
                    "label_encoder": le,
                    "feature_names": FEATURE_COLUMNS,
                    "target": target,
                }
                out_path = models_dir / f"xai_surrogate_{target}.joblib"
                joblib.dump(bundle, out_path)

                X_attr, y_attr = _subsample_for_attribution(
                    X_test,
                    y_test,
                    max_rows=self.attribution_max_rows,
                    random_state=self.random_state,
                )
                attr = self.explainer.explain_model_object(
                    model=best_model,
                    X=X_attr,
                    y=y_attr,
                    target_name=target,
                    feature_names=FEATURE_COLUMNS,
                )
                attr["attribution_rows_used"] = int(len(X_attr))
                report["attribution_per_target"][target] = attr
                if attr.get("method_used"):
                    report["attribution_method"] = attr.get("method_used")

                targets_trained.append(target)
            except Exception as exc:
                report["limitations"].append(f"Target {target} training failed: {exc}")

        report["targets_trained"] = targets_trained

        if report.get("derived_label_used"):
            report["limitations"].append(
                "Labels are derived or mapped from fusion/log fields alongside engineered features; "
                "holdout metrics can be optimistically high when labels are nearly deterministic from those inputs. "
                "Use attribution for relative feature ranking rather than absolute performance claims."
            )

        meta = {
            "dataset_size": report["dataset_size"],
            "real_row_count": report["real_row_count"],
            "synthetic_row_count": report["synthetic_row_count"],
            "synthetic_used": report["synthetic_used"],
            "feature_names": FEATURE_COLUMNS,
            "targets_trained": targets_trained,
            "best_model_per_target": report["best_model_per_target"],
            "shap_available": self.shap_available,
            "derived_label_used": report["derived_label_used"],
            "created_at": report["created_at"],
        }
        meta_path = models_dir / "xai_surrogate_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        if not targets_trained:
            report["status"] = "warning"
        elif report["synthetic_used"] or report["derived_label_used"]:
            if report["status"] == "success":
                pass

        return report


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


XAI_SURROGATE_FINAL_WORDING = (
    "The XAI layer was upgraded from evidence-card explanations to a trained surrogate-model approach. "
    "Tutor decision logs are converted into feature-label datasets, and machine-learning models are trained "
    "to predict decisions such as teaching view, next action, difficulty, promotion, and revision need. "
    "Feature attribution is computed using permutation importance and tree-based importance, making the "
    "explanations model-based rather than manually weighted. Existing evidence cards are retained only for "
    "readable frontend presentation and fallback."
)


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_xai_surrogate_markdown(report: Dict[str, Any]) -> str:
    status = report.get("status", "unknown")
    lines = [
        "# XAI Surrogate Model Report",
        "",
        f"**Status:** {status}",
        "",
        f"**Dataset size:** {report.get('dataset_size', 0)}",
        "",
        f"**Synthetic used:** {report.get('synthetic_used', False)}",
        "",
        f"**Derived labels used:** {report.get('derived_label_used', False)}",
        "",
        "## Features used",
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
    lines.extend(["", "## Metrics table", ""])

    comp = report.get("model_comparison", {})
    table_rows: List[List[str]] = []
    for target, models in comp.items():
        for model_name, metrics in models.items():
            if not isinstance(metrics, dict):
                continue
            if "error" in metrics:
                table_rows.append(
                    [
                        target,
                        model_name,
                        str(metrics.get("accuracy", "")),
                        str(metrics.get("macro_f1", "")),
                        str(metrics.get("weighted_f1", "")),
                        str(metrics.get("balanced_accuracy", "")),
                        str(metrics.get("error", ""))[:48],
                    ]
                )
            else:
                table_rows.append(
                    [
                        target,
                        model_name,
                        f"{metrics.get('accuracy', 0):.4f}",
                        f"{metrics.get('macro_f1', 0):.4f}",
                        f"{metrics.get('weighted_f1', 0):.4f}",
                        f"{metrics.get('balanced_accuracy', 0):.4f}",
                        "",
                    ]
                )
    if table_rows:
        lines.append(
            _md_table(
                ["Target", "Model", "Accuracy", "Macro F1", "Weighted F1", "Balanced Acc", "Notes"],
                table_rows,
            )
        )
    else:
        lines.append("_No model comparison rows._")

    lines.extend(["", "## Top features per target", ""])
    for target, attr in report.get("attribution_per_target", {}).items():
        tops = attr.get("top_features", [])
        lines.append(f"- **{target}:** {', '.join(tops) if tops else 'n/a'}")

    lines.extend(
        [
            "",
            "## Attribution method",
            "",
            str(report.get("attribution_method", "permutation_importance")),
            "",
            "## SHAP available",
            "",
            str(report.get("shap_available", False)),
            "",
            "## Limitations",
            "",
        ]
    )
    for lim in report.get("limitations", []) or ["None noted."]:
        lines.append(f"- {lim}")

    lines.extend(["", "## Final report wording", "", XAI_SURROGATE_FINAL_WORDING, ""])
    return "\n".join(lines)
