from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tutor.system.multi_evidence_collector import collect_multi_evidence
from tutor.system.promotion_confidence import compute_promotion_confidence
from tutor.system.guess_detection import detect_guessing


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class ReviewNeedResult:
    learner_id: str
    concept_id: Optional[str]
    review_need_score: float
    urgency_level: str
    recommendation: str
    reasons: List[str]


class ReviewNeedPredictor:
    def __init__(
        self,
        decay_weight: float = 0.30,
        promotion_penalty_weight: float = 0.25,
        guess_weight: float = 0.20,
        behaviour_weight: float = 0.15,
        mastery_gap_weight: float = 0.10,
        high_threshold: float = 0.65,
        moderate_threshold: float = 0.40,
    ) -> None:
        self.decay_weight = decay_weight
        self.promotion_penalty_weight = promotion_penalty_weight
        self.guess_weight = guess_weight
        self.behaviour_weight = behaviour_weight
        self.mastery_gap_weight = mastery_gap_weight
        self.high_threshold = high_threshold
        self.moderate_threshold = moderate_threshold

    def evaluate(
        self,
        learner_id: str,
        concept_id: Optional[str] = None,
        evidence_bundle: Optional[Dict[str, Any]] = None,
        promotion_result: Optional[Dict[str, Any]] = None,
        guess_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if evidence_bundle is None:
            evidence_bundle = collect_multi_evidence(
                learner_id=learner_id,
                system_concept_id=concept_id,
            )

        if guess_result is None:
            guess_result = detect_guessing(
                learner_id=learner_id,
                concept_id=concept_id,
                evidence_bundle=evidence_bundle,
            )

        if promotion_result is None:
            promotion_result = compute_promotion_confidence(
                learner_id=learner_id,
                concept_id=concept_id,
                evidence_bundle=evidence_bundle,
            )

        summary = evidence_bundle.get("summary", {})
        mastery_score = float(summary.get("mastery_score", 0.0) or 0.0)
        recent_correctness = float(summary.get("recent_correctness", 0.0) or 0.0)
        behaviour_risk = float(summary.get("behaviour_risk", 0.0) or 0.0)
        decay_priority = float(summary.get("decay_priority", 0.0) or 0.0)

        promotion_confidence = float(promotion_result.get("promotion_confidence", 0.0) or 0.0)
        guess_score = float(guess_result.get("guess_score", 0.0) or 0.0)
        guess_level = guess_result.get("guess_level", "low")
        promotion_recommendation = promotion_result.get("recommendation", "review")

        mastery_gap = 1.0 - clamp(mastery_score)
        promotion_penalty = 1.0 - clamp(promotion_confidence)

        review_need_score = clamp(
            self.decay_weight * decay_priority
            + self.promotion_penalty_weight * promotion_penalty
            + self.guess_weight * guess_score
            + self.behaviour_weight * behaviour_risk
            + self.mastery_gap_weight * mastery_gap
        )

        recommendation = self._recommendation(
            review_need_score=review_need_score,
            decay_priority=decay_priority,
            promotion_recommendation=promotion_recommendation,
            guess_level=guess_level,
            mastery_score=mastery_score,
            recent_correctness=recent_correctness,
        )
        urgency_level = self._urgency_level(
            review_need_score=review_need_score,
            recommendation=recommendation,
        )
        reasons = self._build_reasons(
            mastery_score=mastery_score,
            recent_correctness=recent_correctness,
            behaviour_risk=behaviour_risk,
            decay_priority=decay_priority,
            promotion_confidence=promotion_confidence,
            promotion_recommendation=promotion_recommendation,
            guess_score=guess_score,
            guess_level=guess_level,
            review_need_score=review_need_score,
            recommendation=recommendation,
        )

        result = ReviewNeedResult(
            learner_id=str(learner_id),
            concept_id=str(concept_id) if concept_id is not None else evidence_bundle.get("target_concept_id"),
            review_need_score=round(review_need_score, 4),
            urgency_level=urgency_level,
            recommendation=recommendation,
            reasons=reasons,
        )

        return {
            "learner_id": result.learner_id,
            "concept_id": result.concept_id,
            "review_need_score": result.review_need_score,
            "urgency_level": result.urgency_level,
            "recommendation": result.recommendation,
            "signals": {
                "mastery_score": round(clamp(mastery_score), 4),
                "recent_correctness": round(clamp(recent_correctness), 4),
                "behaviour_risk": round(clamp(behaviour_risk), 4),
                "decay_priority": round(clamp(decay_priority), 4),
                "promotion_confidence": round(clamp(promotion_confidence), 4),
                "guess_score": round(clamp(guess_score), 4),
            },
            "promotion_result": promotion_result,
            "guess_result": guess_result,
            "reasons": result.reasons,
        }

    def _urgency_level(self, review_need_score: float, recommendation: str) -> str:
        if recommendation in {"immediate_review", "priority_review"}:
            return "high"

        if recommendation in {"review_before_next", "schedule_review"}:
            return "moderate"

        if review_need_score >= self.high_threshold:
            return "high"
        if review_need_score >= self.moderate_threshold:
            return "moderate"
        return "low"

    def _recommendation(
        self,
        review_need_score: float,
        decay_priority: float,
        promotion_recommendation: str,
        guess_level: str,
        mastery_score: float,
        recent_correctness: float,
    ) -> str:
        if guess_level == "high":
            return "immediate_review"

        if decay_priority >= 0.75 and mastery_score < 0.80:
            return "priority_review"

        if promotion_recommendation == "review" and review_need_score >= self.moderate_threshold:
            return "review_before_next"

        if review_need_score >= self.high_threshold:
            return "priority_review"

        if review_need_score >= self.moderate_threshold:
            return "schedule_review"

        if mastery_score >= 0.75 and recent_correctness >= 0.70:
            return "no_immediate_review"

        return "light_review"

    def _build_reasons(
        self,
        mastery_score: float,
        recent_correctness: float,
        behaviour_risk: float,
        decay_priority: float,
        promotion_confidence: float,
        promotion_recommendation: str,
        guess_score: float,
        guess_level: str,
        review_need_score: float,
        recommendation: str,
    ) -> List[str]:
        reasons: List[str] = []

        if mastery_score < 0.5:
            reasons.append("Mastery is low, so the concept likely needs reinforcement.")
        elif mastery_score < 0.75:
            reasons.append("Mastery is moderate, so review may still be useful.")
        else:
            reasons.append("Mastery is relatively strong.")

        if recent_correctness < 0.5:
            reasons.append("Recent correctness is weak.")
        elif recent_correctness < 0.7:
            reasons.append("Recent correctness is moderate.")
        else:
            reasons.append("Recent correctness is strong.")

        if behaviour_risk >= 0.7:
            reasons.append("Behaviour risk is high.")
        elif behaviour_risk >= 0.4:
            reasons.append("Behaviour risk is moderate.")
        else:
            reasons.append("Behaviour risk is low.")

        if decay_priority >= 0.7:
            reasons.append("Decay priority is high, so forgetting risk is important.")
        elif decay_priority >= 0.3:
            reasons.append("Decay priority is moderate.")
        else:
            reasons.append("Decay priority is low.")

        if promotion_confidence < 0.3:
            reasons.append("Promotion confidence is low.")
        elif promotion_confidence < 0.6:
            reasons.append("Promotion confidence is moderate.")
        else:
            reasons.append("Promotion confidence is strong.")

        if promotion_recommendation == "review":
            reasons.append("Promotion module already recommends review.")
        elif promotion_recommendation == "reinforce":
            reasons.append("Promotion module suggests reinforcement before advancement.")

        if guess_level == "high":
            reasons.append("Guessing risk is high and strongly increases review need.")
        elif guess_level == "moderate":
            reasons.append("Guessing risk is moderate and should be monitored.")
        else:
            reasons.append("Guessing risk is low.")

        if guess_score >= 0.6:
            reasons.append("Guess score is high enough to question answer reliability.")

        if recommendation in {"immediate_review", "priority_review"}:
            reasons.append("Overall review need is effectively high after safety checks.")
        elif recommendation in {"review_before_next", "schedule_review"}:
            reasons.append("Overall review need is moderate.")
        elif review_need_score >= self.high_threshold:
            reasons.append("Overall review need is high.")
        elif review_need_score >= self.moderate_threshold:
            reasons.append("Overall review need is moderate.")
        else:
            reasons.append("Overall review need is low.")


        if recommendation == "immediate_review":
            reasons.append("Concept should be reviewed immediately before progression.")
        elif recommendation == "priority_review":
            reasons.append("Concept should be prioritized for review soon.")
        elif recommendation == "review_before_next":
            reasons.append("Learner should review this concept before moving ahead.")
        elif recommendation == "schedule_review":
            reasons.append("Concept should be scheduled for review.")
        elif recommendation == "light_review":
            reasons.append("A light reinforcement review is sufficient.")
        else:
            reasons.append("No immediate review is necessary.")

        return reasons


def predict_review_need(
    learner_id: str,
    concept_id: Optional[str] = None,
    evidence_bundle: Optional[Dict[str, Any]] = None,
    promotion_result: Optional[Dict[str, Any]] = None,
    guess_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    predictor = ReviewNeedPredictor()
    return predictor.evaluate(
        learner_id=learner_id,
        concept_id=concept_id,
        evidence_bundle=evidence_bundle,
        promotion_result=promotion_result,
        guess_result=guess_result,
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    output = predict_review_need(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))