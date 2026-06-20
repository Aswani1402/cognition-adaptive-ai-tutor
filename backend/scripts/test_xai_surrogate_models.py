"""
Smoke tests for XAI surrogate training pipeline.

Run: python -m scripts.test_xai_surrogate_models
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tutor.xai.model_attribution_explainer import ModelAttributionExplainer
from tutor.xai.xai_surrogate_trainer import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    XAISurrogateTrainer,
    build_surrogate_dataset,
)


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    # 1. Imports (implicit above)

    # 2–3. Dataset builder + feature columns
    df, _meta = build_surrogate_dataset(ROOT / "external" / "core_data" / "tutor.db")
    assert isinstance(df, pd.DataFrame)
    for c in FEATURE_COLUMNS:
        assert c in df.columns, f"missing feature {c}"

    # 4–5. Train and persist
    trainer = XAISurrogateTrainer(random_state=42, test_size=0.25)
    report = trainer.train_all_and_report(ROOT / "external" / "core_data" / "tutor.db")
    assert report.get("dataset_size", 0) > 0
    assert report.get("targets_trained"), "at least one target should train"
    model_dir = ROOT / "models" / "xai"
    meta_path = model_dir / "xai_surrogate_meta.json"
    assert meta_path.exists(), "meta json should exist"
    trained = report["targets_trained"]
    for t in trained:
        p = model_dir / f"xai_surrogate_{t}.joblib"
        assert p.exists(), f"missing model {p}"

    # 6. Attribution top features
    for t in trained:
        attr = report.get("attribution_per_target", {}).get(t, {})
        assert attr.get("top_features"), f"top features for {t}"

    # 7. Report schema
    for key in (
        "status",
        "dataset_size",
        "feature_names",
        "targets_trained",
        "best_model_per_target",
        "limitations",
        "synthetic_used",
        "derived_label_used",
    ):
        assert key in report, f"missing report key {key}"

    # 8. Frontend response builder import
    try:
        from tutor.system.frontend_response_builder import build_frontend_response  # noqa: F401
    except ImportError:
        pass

    explainer = ModelAttributionExplainer()
    assert hasattr(explainer, "compute_builtin_importance")
    assert hasattr(explainer, "summarize_top_features")

    print("STATUS: success")
    print("MODULE: xai_surrogate_models_test")


if __name__ == "__main__":
    main()
