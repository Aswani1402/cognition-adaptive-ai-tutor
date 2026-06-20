"""
Tests for learned adaptive path ranker.

Run: python -m scripts.test_learned_adaptive_path_ranker
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tutor.concept_dependency.learned_adaptive_path_ranker import LearnedAdaptivePathRanker
from scripts.training.path.train_adaptive_path_ranker import build_training_dataframe, train_and_report

ROOT = Path(__file__).resolve().parent.parent


def _schema(d: dict) -> None:
    for k in (
        "status",
        "module",
        "model_used",
        "fallback_used",
        "recommended_action",
        "recommended_node_type",
        "recommended_concept_id",
        "rank_score_bucket",
        "confidence",
        "safe_candidates_count",
        "blocked_candidates_count",
        "safety_violation",
        "top_features",
        "frontend_component",
        "limitations",
    ):
        assert k in d, f"missing {k}"


def main() -> None:
    df, _ = build_training_dataframe()
    assert not df.empty

    report = train_and_report()
    assert report.get("dataset_size", 0) > 0
    assert (ROOT / "models" / "path" / "adaptive_path_ranker_meta.json").exists()

    ranker = LearnedAdaptivePathRanker()
    ranker.load()

    dep = {
        "unlocked_concepts": ["1", "2", "3"],
        "blocked_concepts": [{"concept_id": "99", "blocked_by": ["1"]}],
        "recommended_next_concept": "2",
    }
    ev = {
        "current_mastery": 0.45,
        "prerequisite_mastery": 0.6,
        "behaviour_risk": 0.3,
        "behaviour_confidence": 0.7,
        "fused_score": 0.4,
        "recent_score": 0.42,
        "wrong_streak": 2.0,
        "review_due": 0.2,
        "difficulty": "medium",
    }
    out = ranker.predict_with_fallback(
        "L_test",
        "1",
        dep,
        ev,
        fallback_path={"selected_next_concept": "2", "recommended_strategy": "practice"},
    )
    _schema(out)

    bad = LearnedAdaptivePathRanker(model_dir=ROOT / "models" / "path_missing")
    bad.load()
    fb = bad.predict_with_fallback("L", "1", dep, ev, fallback_path={"selected_next_concept": "2"})
    assert fb.get("fallback_used") is True

    filt = ranker.filter_safe_candidates(
        "L",
        [
            {"concept_id": "2", "prerequisite_satisfied": True},
            {"concept_id": "99", "prerequisite_satisfied": True},
        ],
        dep,
    )
    assert len(filt["safe_candidates"]) == 1
    assert filt["safe_candidates"][0]["concept_id"] == "2"
    assert filt["blocked_candidates_count"] >= 1

    r3 = subprocess.run(
        [sys.executable, "-m", "scripts.test_frontend_response_builder"],
        cwd=str(ROOT),
        check=False,
    )
    assert r3.returncode == 0

    print("STATUS: success")
    print("MODULE: learned_adaptive_path_ranker_test")


if __name__ == "__main__":
    main()
