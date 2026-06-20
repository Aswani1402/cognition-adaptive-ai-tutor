"""
Train learned hint policy models (supervised; contextual bandit noted as future work).

Run: python -m scripts.training.hints.train_learned_hint_policy
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
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy
from tutor.policy.learned_hint_policy import (
    FEATURE_COLUMNS,
    evidence_to_feature_row,
    support_need_to_level,
)
from tutor.simulation.learner_answer_simulator import LearnerAnswerSimulator
from tutor.xai.model_attribution_explainer import ModelAttributionExplainer

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"
MODEL_DIR = ROOT / "models" / "hints"
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "learned_hint_policy_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "learned_hint_policy_report.md"

FINAL_WORDING = (
    "The hint module was upgraded from a deterministic evidence-scored policy to a learned model-supported "
    "hint selector. Learner evidence such as mastery, behaviour risk, score, mistake type, question type, "
    "difficulty, and prior hint usage is converted into a feature-label dataset, and supervised models are "
    "trained to predict hint type, hint level, and expected hint success. The previous adaptive hint policy is "
    "retained as a safe fallback when the learned model is unavailable or low confidence."
)

CLASS_BALANCE_LIMITATION = (
    "Some hint classes have limited support, so macro-F1 and per-class metrics should be interpreted "
    "with class-balance limitations."
)


def _target_label_distribution_and_rarity(df: pd.DataFrame) -> Tuple[Dict[str, Dict[str, int]], bool, List[str]]:
    """Per-target label counts (string labels), rare_class_warning, rare_classes as 'target:label'."""
    dist: Dict[str, Dict[str, int]] = {}
    rare_flat: List[str] = []
    for col in ("hint_type", "hint_level", "hint_success"):
        if col not in df.columns:
            continue
        c = Counter(df[col].astype(str))
        dist[col] = dict(c)
        for lab, n in c.items():
            if n < 2:
                rare_flat.append(f"{col}:{lab}")
    return dist, len(rare_flat) > 0, sorted(rare_flat)


def _metric_label_union(y_train: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Sorted unique encoded class ids seen in train, test, and predictions (for sklearn metrics)."""
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
        "balanced_accuracy": float(
            recall_score(yt, yp, average="macro", labels=labels, zero_division=0)
        ),
    }


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


def _sample_questions() -> List[Dict[str, Any]]:
    return [
        {
            "question_type": "mcq",
            "expected_answer": "A variable stores a value.",
            "text": "What is a variable?",
        },
        {
            "question_type": "output_prediction",
            "expected_answer": "0 1 2",
            "code": "for i in range(3):\n  print(i)",
        },
        {
            "question_type": "debug_task",
            "expected_answer": "Add quotes",
            "code": "print(hello)",
        },
        {
            "question_type": "syntax_completion",
            "expected_answer": "def f():",
            "snippet": "___ f():",
        },
    ]


def _simulated_rows() -> List[Dict[str, Any]]:
    policy = AdaptiveHintPolicy()
    sim = LearnerAnswerSimulator()
    profiles = ["strong", "average", "weak", "guessing", "careless", "low_confidence"]
    rows: List[Dict[str, Any]] = []
    for p in profiles:
        for qi, q in enumerate(_sample_questions()):
            seed = 100 + hash(p) % 10000 + qi * 17
            s = sim.simulate_answer(q, p, seed=seed)
            score = float(s.get("score_estimate", 0.5))
            evidence = {
                "learner_id": f"synth_{p}_{qi}",
                "concept_id": "1",
                "concept_name": "Variables",
                "question_type": s.get("question_type") or q.get("question_type", "mcq"),
                "learner_answer": str(s.get("simulated_answer", "")),
                "expected_answer": str(s.get("expected_answer", "")),
                "score": score,
                "evaluation_label": "weak" if score < 0.45 else "ok",
                "mistake_type": str(s.get("mistake_type", "unknown")),
                "weakest_skill": "output_prediction" if "output" in str(q.get("question_type")) else "concept recall",
                "behaviour_risk": 0.75 if p in {"weak", "guessing"} else 0.25,
                "mastery_score": 0.85 if p == "strong" else (0.25 if p == "weak" else 0.55),
                "hint_count_used": float(qi % 3),
                "previous_hint_success": 0.6 if p == "strong" else 0.4,
                "difficulty": "hard" if p == "weak" else "medium",
                "teaching_view": "definition_view",
                "confidence": float(s.get("confidence", 0.5)),
                "time_taken_sec": float(s.get("time_taken_sec", 40)),
                "wrong_streak": float(3 if p == "weak" else 0),
                "previous_score": max(0.0, score - 0.1),
                "anomaly_score": 0.7 if p == "guessing" else 0.2,
            }
            out = policy.select_hint(evidence)
            feats = evidence_to_feature_row(evidence)
            hl = support_need_to_level(float(out.get("support_need", 0.5)))
            succ = 1 if (s.get("is_expected_correct") or score >= 0.55) else 0
            rows.append(
                {
                    **feats,
                    "hint_type": str(out.get("hint_type", "guided_hint")),
                    "hint_level": hl,
                    "hint_success": succ,
                }
            )
    return rows


def _rows_from_quiz(con: sqlite3.Connection) -> List[Dict[str, Any]]:
    if not _table_exists(con, "quiz_results"):
        return []
    c = set(_table_columns(con, "quiz_results"))
    if "learner_id" not in c:
        return []
    sel = ["learner_id", "is_correct", "hint_used", "confidence", "time_taken_sec"]
    if "hint_count" in c:
        sel.insert(3, "hint_count")
    sel = [x for x in sel if x in c]
    if not sel:
        return []
    q = f"SELECT {', '.join(sel)} FROM quiz_results LIMIT 8000"
    df = _safe_read_sql(con, q)
    if df.empty:
        return []

    mistakes = pd.DataFrame()
    if _table_exists(con, "learner_mistake_log") and "learner_id" in set(
        _table_columns(con, "learner_mistake_log")
    ):
        mt = "mistake_type" if "mistake_type" in _table_columns(con, "learner_mistake_log") else None
        if mt:
            mistakes = _safe_read_sql(
                con,
                f"""
                SELECT learner_id, {mt} AS mistake_type
                FROM learner_mistake_log
                ORDER BY id DESC
                LIMIT 20000
                """,
            )
            if not mistakes.empty:
                mistakes = mistakes.drop_duplicates("learner_id", keep="first")

    policy = AdaptiveHintPolicy()
    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        lid = str(row.get("learner_id", ""))
        is_corr = int(row.get("is_correct") or 0)
        score = 0.92 if is_corr else float(np.clip(0.15 + (1 - is_corr) * 0.35, 0.05, 0.55))
        hint_used = float(row.get("hint_used") or 0)
        hint_count = float(row.get("hint_count") or hint_used)
        conf = float(row.get("confidence") or 50) / 100.0 if row.get("confidence") is not None else 0.6
        tsec = float(row.get("time_taken_sec") or 40.0)
        mt = "unknown"
        if not mistakes.empty and lid in mistakes["learner_id"].astype(str).values:
            sub = mistakes.loc[mistakes["learner_id"].astype(str) == lid, "mistake_type"]
            if len(sub) > 0:
                mt = str(sub.iloc[0])

        evidence = {
            "learner_id": lid,
            "concept_id": "1",
            "concept_name": "Concept",
            "question_type": "mcq",
            "score": score,
            "mastery_score": score,
            "behaviour_risk": 0.35,
            "hint_count_used": hint_count,
            "previous_hint_success": 0.55 if hint_used else 0.5,
            "mistake_type": mt,
            "weakest_skill": "mcq",
            "difficulty": "medium",
            "confidence": conf,
            "time_taken_sec": tsec,
            "wrong_streak": 0.0 if is_corr else 2.0,
            "previous_score": max(0.0, score - 0.05),
            "anomaly_score": 0.3,
        }
        out = policy.select_hint(evidence)
        feats = evidence_to_feature_row(evidence)
        hl = support_need_to_level(float(out.get("support_need", 0.5)))
        succ = 1 if is_corr or score >= 0.55 else 0
        rows.append(
            {
                **feats,
                "hint_type": str(out.get("hint_type", "guided_hint")),
                "hint_level": hl,
                "hint_success": succ,
            }
        )
    return rows


def _rows_from_json_reports() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name in ("adaptive_hint_policy_report.json", "learner_simulator_report.json"):
        path = ROOT / "evaluation_outputs" / "json" / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        outs = data.get("test_outputs") or []
        if name == "learner_simulator_report.json":
            outs = data.get("answers") or data.get("rows") or []
        policy = AdaptiveHintPolicy()
        for item in outs:
            if not isinstance(item, dict):
                continue
            ev = item.get("evidence") if isinstance(item.get("evidence"), dict) else item
            if not isinstance(ev, dict):
                continue
            if "score" not in ev and item.get("score_estimate") is not None:
                ev = {**ev, "score": float(item.get("score_estimate", 0.5))}
            ev.setdefault("mastery_score", ev.get("score", 0.5))
            ev.setdefault("behaviour_risk", 0.3)
            ev.setdefault("question_type", "mcq")
            ev.setdefault("mistake_type", "unknown")
            ev.setdefault("hint_count_used", 0)
            out = policy.select_hint(ev)
            feats = evidence_to_feature_row(ev)
            hl = support_need_to_level(float(out.get("support_need", 0.5)))
            succ = 1 if float(ev.get("score", 0.5)) >= 0.55 or item.get("is_expected_correct") else 0
            rows.append(
                {
                    **feats,
                    "hint_type": str(out.get("hint_type", "guided_hint")),
                    "hint_level": hl,
                    "hint_success": succ,
                }
            )
    return rows


def build_training_dataframe(db_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    meta: Dict[str, Any] = {
        "real_row_count": 0,
        "synthetic_row_count": 0,
        "synthetic_used": False,
        "derived_labels_used": True,
        "limitations": [
            "hint_type and hint_level labels are produced by running AdaptiveHintPolicy on each row (teacher "
            "imitation / distillation), not human hint labels.",
            "Contextual bandit online learning is future work; current artifacts are supervised classifiers.",
        ],
        "data_sources_used": [],
    }
    db = Path(db_path) if db_path else DB_PATH
    all_rows: List[Dict[str, Any]] = []

    if db.exists():
        con = sqlite3.connect(str(db))
        qrows = _rows_from_quiz(con)
        con.close()
        all_rows.extend(qrows)
        if qrows:
            meta["data_sources_used"].append("quiz_results (+ optional learner_mistake_log)")

    jrows = _rows_from_json_reports()
    all_rows.extend(jrows)
    if jrows:
        meta["data_sources_used"].append("evaluation_outputs/json (adaptive_hint / learner_simulator)")

    meta["real_row_count"] = len(all_rows)

    if len(all_rows) < 80:
        syn = _simulated_rows()
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["limitations"].append(
            "synthetic_used=true: added LearnerAnswerSimulator-based rows because real logs were insufficient."
        )
        all_rows.extend(syn)

    if not all_rows:
        syn = _simulated_rows()
        all_rows = syn
        meta["synthetic_row_count"] = len(syn)
        meta["synthetic_used"] = True
        meta["limitations"].append("No DB/JSON rows; using simulator-only dataset.")

    df = pd.DataFrame(all_rows)
    return df, meta


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


def train_and_report() -> Dict[str, Any]:
    df, ds_meta = build_training_dataframe()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    hint_type_dist = dict(Counter(df["hint_type"].astype(str))) if len(df) else {}
    hint_level_dist = dict(Counter(df["hint_level"].astype(str))) if len(df) else {}
    succ_dist = dict(Counter(df["hint_success"].astype(int))) if len(df) else {}

    report: Dict[str, Any] = {
        "status": "success",
        "module": "train_learned_hint_policy",
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
        "per_class_support": {},
        "confusion_matrices": {},
        "confusion_matrix_summary": {},
        "hint_type_distribution": hint_type_dist,
        "hint_level_distribution": hint_level_dist,
        "predicted_success_distribution": succ_dist,
        "fallback_behavior": {
            "confidence_threshold": 0.38,
            "description": "At inference, predict_with_fallback uses AdaptiveHintPolicy output when models are missing or mean classifier confidence is below threshold.",
        },
        "fallback_rate": 0.0,
        "top_features_per_target": {},
        "limitations": list(ds_meta.get("limitations", [])),
        "data_sources_used": list(ds_meta.get("data_sources_used", [])),
        "bandit_note": "Contextual bandit (epsilon-greedy over hint_type with reward = score gain) deferred as future work.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_label_distribution": {},
        "rare_class_warning": False,
        "rare_classes": [],
    }

    if df.empty:
        report["status"] = "warning"
        report["limitations"].append("Empty dataframe.")
        return report

    tld, rare_warn, rare_list = _target_label_distribution_and_rarity(df)
    report["target_label_distribution"] = tld
    report["rare_class_warning"] = rare_warn
    report["rare_classes"] = rare_list
    if rare_warn and CLASS_BALANCE_LIMITATION not in report["limitations"]:
        report["limitations"].append(CLASS_BALANCE_LIMITATION)

    targets = {
        "hint_type": "learned_hint_type_model.joblib",
        "hint_level": "learned_hint_level_model.joblib",
        "hint_success": "hint_success_predictor.joblib",
    }
    explainer = ModelAttributionExplainer(random_state=42, n_repeats=2)
    trained: List[str] = []

    for target, fname in targets.items():
        try:
            y_raw = df[target]
            le = LabelEncoder()
            y = le.fit_transform(y_raw.astype(str))

            if len(np.unique(y)) < 2:
                report["limitations"].append(f"Skipping {target}: single class.")
                continue

            report["per_class_support"][target] = dict(Counter(y_raw.astype(str)))

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

            report["model_comparison"][target] = comparison
            report["best_model_per_target"][target] = best_name
            report["best_metrics_per_target"][target] = _metrics(y_test, best_pred, y_train)
            labels_cm = _metric_label_union(y_train, y_test, best_pred)
            cm = confusion_matrix(y_test, best_pred, labels=labels_cm)
            report["confusion_matrices"][target] = cm.tolist()
            tot = float(np.sum(cm))
            diag = float(np.trace(cm)) if cm.size else 0.0
            report["confusion_matrix_summary"][target] = {
                "total": int(tot),
                "diagonal_correct": int(diag),
                "matrix_accuracy": round(diag / tot, 4) if tot else 0.0,
            }

            joblib.dump(
                {"model": best_model, "label_encoder": le, "target": target, "feature_names": FEATURE_COLUMNS},
                MODEL_DIR / fname,
            )

            n_attr = min(250, len(X_test))
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

    meta = {
        "dataset_size": report["dataset_size"],
        "real_row_count": report["real_row_count"],
        "synthetic_row_count": report["synthetic_row_count"],
        "synthetic_used": report["synthetic_used"],
        "derived_labels_used": report["derived_labels_used"],
        "feature_names": FEATURE_COLUMNS,
        "targets_trained": trained,
        "best_model_per_target": report.get("best_model_per_target", {}),
        "limitations": report["limitations"],
        "created_at": report["created_at"],
        "bandit_note": report["bandit_note"],
    }
    (MODEL_DIR / "learned_hint_policy_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if not trained:
        report["status"] = "warning"

    report["final_report_wording"] = FINAL_WORDING
    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Learned hint policy report",
        "",
        f"**Status:** {report.get('status')}",
        "",
        f"**Dataset size:** {report.get('dataset_size')}",
        f"**Real rows:** {report.get('real_row_count')}",
        f"**Synthetic rows:** {report.get('synthetic_row_count')}",
        f"**Synthetic used:** {report.get('synthetic_used')}",
        f"**Derived labels used:** {report.get('derived_labels_used')}",
        "",
        "## Target label distribution (per target)",
        "",
        str(report.get("target_label_distribution", {})),
        "",
        f"**Rare class warning:** {report.get('rare_class_warning')}",
        f"**Rare classes:** {report.get('rare_classes', [])}",
        "",
        "## Data sources",
        "",
        ", ".join(report.get("data_sources_used", []) or ["(none noted)"]),
        "",
        "## Hint type distribution",
        "",
        str(report.get("hint_type_distribution", {})),
        "",
        "## Hint level distribution",
        "",
        str(report.get("hint_level_distribution", {})),
        "",
        "## Predicted success (training labels) distribution",
        "",
        str(report.get("predicted_success_distribution", {})),
        "",
        "## Fallback behavior",
        "",
        str(report.get("fallback_behavior", {})),
        "",
        "## Best model per target",
        "",
    ]
    for t, m in report.get("best_model_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Metrics (best)", ""])
    for t, m in report.get("best_metrics_per_target", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Per-class support", ""])
    for t, m in report.get("per_class_support", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Confusion matrix summary", ""])
    for t, m in report.get("confusion_matrix_summary", {}).items():
        lines.append(f"- **{t}:** {m}")
    lines.extend(["", "## Top features", ""])
    for t, tops in report.get("top_features_per_target", {}).items():
        lines.append(f"- **{t}:** {tops}")
    lines.extend(["", "## Bandit / future work", "", str(report.get("bandit_note", "")), ""])
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
    print("MODULE: train_learned_hint_policy")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"MODEL_DIR: {MODEL_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
