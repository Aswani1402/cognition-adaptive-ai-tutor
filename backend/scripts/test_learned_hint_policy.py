"""
Tests for learned hint policy.

Run: python -m scripts.test_learned_hint_policy
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tutor.policy.adaptive_hint_policy import AdaptiveHintPolicy
from tutor.policy.learned_hint_policy import LearnedHintPolicy, evidence_to_feature_row
from scripts.training.hints.train_learned_hint_policy import build_training_dataframe, train_and_report

ROOT = Path(__file__).resolve().parent.parent


def _schema_keys(d: dict) -> None:
    for k in (
        "status",
        "module",
        "model_used",
        "fallback_used",
        "hint_type",
        "hint_level",
        "hint_text",
        "predicted_success_probability",
        "confidence",
        "top_features",
        "frontend_component",
        "limitations",
    ):
        assert k in d, f"missing {k}"


def main() -> None:
    df, _meta = build_training_dataframe(ROOT / "external" / "core_data" / "tutor.db")
    assert not df.empty

    report = train_and_report()
    assert report.get("dataset_size", 0) > 0
    assert (ROOT / "models" / "hints" / "learned_hint_policy_meta.json").exists()

    lh = LearnedHintPolicy()
    lh.load()
    ev = {
        "score": 0.35,
        "mastery_score": 0.4,
        "behaviour_risk": 0.5,
        "question_type": "output_prediction",
        "mistake_type": "wrong_output",
        "hint_count_used": 1.0,
        "difficulty": "medium",
    }
    evidence_to_feature_row(ev)
    out = lh.predict_hint(ev)
    _schema_keys(out)

    fb = AdaptiveHintPolicy().select_hint(ev)
    merged = lh.predict_with_fallback(ev, fb)
    _schema_keys(merged)

    bad = LearnedHintPolicy(model_dir=ROOT / "models" / "hints_missing_xyz")
    bad.load()
    fb2 = bad.predict_with_fallback(ev, fb)
    assert fb2.get("fallback_used") is True
    assert fb2.get("model_used") is False

    ap = AdaptiveHintPolicy()
    assert ap.select_hint(ev).get("status") == "success"

    r1 = subprocess.run(
        [sys.executable, "-m", "scripts.test_adaptive_hint_policy"],
        cwd=str(ROOT),
        check=False,
    )
    assert r1.returncode == 0, "scripts.test_adaptive_hint_policy must pass"

    r2 = subprocess.run(
        [sys.executable, "-m", "scripts.test_frontend_response_builder"],
        cwd=str(ROOT),
        check=False,
    )
    assert r2.returncode == 0, "scripts.test_frontend_response_builder must pass"

    print("STATUS: success")
    print("MODULE: learned_hint_policy_test")


if __name__ == "__main__":
    main()
