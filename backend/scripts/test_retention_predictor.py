"""
Smoke tests for retention predictor training and inference.

Run: python -m scripts.test_retention_predictor
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "forgetting"
META = MODEL_DIR / "retention_predictor_meta.json"


def main() -> None:
    # 1) imports
    from tutor.forgetting.retention_predictor import (  # noqa: WPS433
        FEATURE_NAMES,
        RetentionPredictor,
        evidence_to_feature_vector,
    )
    from scripts.training.forgetting.train_retention_predictor import (  # noqa: WPS433
        build_training_dataframe,
        train_and_report,
    )

    assert FEATURE_NAMES
    ev = {"learner_id": "t1", "mastery_score": 0.5, "recent_scores": [0.6, 0.4]}
    vec = evidence_to_feature_vector(ev)
    assert "mastery_score" in vec

    # 2) dataset builder
    df, meta = build_training_dataframe()
    assert not df.empty
    assert meta.get("derived_labels_used") is True

    # 3–4) train + save (skip full retrain when artifacts already present to keep CI fast)
    risk_path = MODEL_DIR / "retention_risk_model.joblib"
    if not risk_path.exists():
        report = train_and_report()
        assert report.get("status") in ("success", "warning")
    if risk_path.exists():
        for name in (
            "retention_risk_model.joblib",
            "review_due_model.joblib",
            "revision_priority_model.joblib",
            "review_interval_model.joblib",
        ):
            assert (MODEL_DIR / name).exists(), f"missing {name}"
        assert META.exists()

    # 5–6) load + predict schema
    rp = RetentionPredictor()
    rp.load()
    pred = rp.predict_retention(
        {
            "learner_id": "t1",
            "concept_id": "1",
            "mastery_score": 0.35,
            "recent_scores": [0.3, 0.2],
            "days_since_last_practice": 10.0,
            "behaviour_risk": 0.6,
        }
    )
    for key in (
        "status",
        "module",
        "model_used",
        "fallback_used",
        "retention_risk_label",
        "review_due",
        "revision_priority",
        "recommended_review_interval",
        "confidence",
        "top_features",
        "frontend_component",
        "limitations",
    ):
        assert key in pred, f"missing key {key}"

    expl = rp.explain_prediction({"learner_id": "t1", "mastery_score": 0.5, "recent_scores": [0.55, 0.6]})
    assert expl.get("module") == "RetentionPredictor"
    assert "per_target" in expl
    rec = rp.recommend_review_interval({"learner_id": "t1", "mastery_score": 0.9, "recent_scores": [0.9, 0.92]})
    assert "recommended_review_interval" in rec

    # 7) fallback when models missing
    alt_dir = ROOT / "models" / "forgetting_tmp_absent"
    if alt_dir.exists():
        shutil.rmtree(alt_dir)
    alt_dir.mkdir(parents=True, exist_ok=True)
    rp2 = RetentionPredictor(model_dir=alt_dir)
    assert rp2.load() is False
    fb = rp2.predict_with_fallback({"learner_id": "x", "mastery_score": 0.2}, {"revision_priority": "high", "review_due": True})
    assert fb.get("fallback_used") is True

    # 8) revision scheduler
    from tutor.memory.revision_scheduler import RevisionScheduler  # noqa: WPS433

    sched = RevisionScheduler().build_revision_plan(
        {
            "learner_id": "t1",
            "concept_id": "1",
            "concept_name": "Variables",
            "mastery_score": 0.3,
            "fused_score": 0.4,
            "review_due": True,
            "recent_scores": [0.4, 0.35],
            "behaviour_risk": 0.2,
        }
    )
    assert sched.get("status") == "success"
    assert "retention_prediction" in sched
    assert isinstance(sched["retention_prediction"], dict)

    # 9) frontend response builder
    from tutor.system.frontend_response_builder import build_frontend_response  # noqa: WPS433

    out = build_frontend_response(
        {
            "status": "success",
            "learner_id": "fe_test",
            "retention_prediction": pred,
            "current_teaching_content": {"concept_id": "1", "concept_name": "Variables", "domain": "Python"},
            "assessment": {"status": "success", "questions": []},
        }
    )
    assert out.get("status") == "success"
    assert "revision" in out
    assert "retention_prediction" in out["revision"]

    # restore meta if we moved things (noop)
    if META.exists():
        m = json.loads(META.read_text(encoding="utf-8"))
        assert m.get("feature_names")

    print("STATUS: success")
    print("MODULE: retention_predictor_test")


if __name__ == "__main__":
    main()
