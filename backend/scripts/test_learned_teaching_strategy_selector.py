"""
Tests for learned teaching strategy selector and training pipeline.

Run: python -m scripts.test_learned_teaching_strategy_selector
"""

from __future__ import annotations

from pathlib import Path

from tutor.strategy.learned_teaching_strategy_selector import (
    FEATURE_COLUMNS,
    LearnedTeachingStrategySelector,
    merge_pipeline_evidence,
)
from scripts.training.strategy.train_teaching_strategy_selector import (
    build_training_dataframe,
    train_and_report,
)

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    df, meta = build_training_dataframe(ROOT / "external" / "core_data" / "tutor.db")
    assert not df.empty, "dataset builder should return rows"
    for c in FEATURE_COLUMNS:
        assert c in df.columns, c

    report = train_and_report()
    assert report.get("dataset_size", 0) > 0
    assert report.get("status") in ("success", "warning")
    assert (ROOT / "models" / "strategy" / "teaching_strategy_model_meta.json").exists(), "meta json must exist after training"
    assert report.get("targets_trained") or report.get("status") == "warning"
    if report.get("targets_trained"):
        for t in report["targets_trained"]:
            fname = {
                "teaching_view": "teaching_strategy_view_model.joblib",
                "difficulty": "teaching_strategy_difficulty_model.joblib",
                "next_action": "teaching_strategy_next_action_model.joblib",
                "assessment_type_group": "teaching_strategy_assessment_group_model.joblib",
            }[t]
            assert (ROOT / "models" / "strategy" / fname).exists(), fname

    sel = LearnedTeachingStrategySelector()
    loaded = sel.load()
    merged = merge_pipeline_evidence(
        {
            "status": "success",
            "teaching_view": "code_view",
            "difficulty": "medium",
            "progression_action": "practice",
            "next_activity": "guided practice",
            "assessment_types": ["mcq", "output_prediction"],
            "evidence_used": {"mastery_score": 0.55, "behaviour_risk": 0.3},
            "evidence": {"fused_score": 0.5},
        },
        {"status": "success", "fused_score": 0.48, "fusion_confidence": 0.8},
        {"status": "success", "high_severity_count": 1, "dominant_mistake_type": "wrong_output"},
        {"status": "success", "data": {"difficulty": "medium"}},
    )
    out = sel.predict_with_fallback(
        merged,
        fallback_strategy={
            "teaching_view": "definition_view",
            "difficulty": "easy",
            "progression_action": "reteach",
            "next_activity": "retry",
            "assessment_types": ["mcq"],
        },
    )
    assert "teaching_view" in out and "difficulty" in out
    assert out.get("module") == "LearnedTeachingStrategySelector"

    bad = LearnedTeachingStrategySelector(model_dir=ROOT / "models" / "strategy_missing_xyz")
    bad.load()
    fb = bad.predict_with_fallback(merged, {"teaching_view": "revision_view", "difficulty": "hard"})
    assert fb.get("fallback_used") is True
    assert fb.get("model_used") is False

    try:
        from tutor.system.frontend_response_builder import build_frontend_response  # noqa: F401
    except ImportError:
        pass

    print("STATUS: success")
    print("MODULE: learned_teaching_strategy_selector_test")


if __name__ == "__main__":
    main()
