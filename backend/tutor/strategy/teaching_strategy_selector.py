"""
Teaching strategy entrypoints.

The evidence-aware **rule baseline** lives in ``tutor.strategy.selector`` (large module). This package
exposes a stable import path and documents the layered design:

- **Rule baseline:** ``recommend_evidence_aware_teaching_strategy`` — always available, logged, safe.
- **Learned selector:** ``LearnedTeachingStrategySelector`` — model-supported comparison mode; requires
  artifacts under ``models/strategy/``; never final when missing (use ``predict_with_fallback``).
"""

from __future__ import annotations

from tutor.strategy.learned_teaching_strategy_selector import LearnedTeachingStrategySelector
from tutor.strategy.selector import recommend_evidence_aware_teaching_strategy


class TeachingStrategySelector:
    """
    Thin wrapper around the evidence-aware rule baseline (same behavior as calling the function).

    Use ``LearnedTeachingStrategySelector`` for the learned model-supported path.
    """

    @staticmethod
    def recommend(**kwargs):  # type: ignore[no-untyped-def]
        return recommend_evidence_aware_teaching_strategy(**kwargs)


__all__ = [
    "TeachingStrategySelector",
    "LearnedTeachingStrategySelector",
    "recommend_evidence_aware_teaching_strategy",
]
