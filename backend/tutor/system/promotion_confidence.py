from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from tutor.system.multi_evidence_collector import collect_multi_evidence
from tutor.system.guess_detection import detect_guessing

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class PromotionConfidenceResult:
    learner_id: str
    concept_id: Optional[str]
    promotion_confidence: float
    recommendation: str
    mastery_score: float
    recent_correctness: float
    behaviour_risk: float
    decay_priority: float
    evidence_confidence: float
    reasons: List[str]


class PromotionConfidenceEngine:
    def __init__(
        self,
        mastery_weight: float = 0.40,
        correctness_weight: float = 0.30,
        behaviour_weight: float = 0.20,
        decay_weight: float = 0.10,
        advance_threshold: float = 0.65,
        reinforce_threshold: float = 0.30,
    ) -> None:
        self.mastery_weight = mastery_weight
        self.correctness_weight = correctness_weight
        self.behaviour_weight = behaviour_weight
        self.decay_weight = decay_weight
        self.advance_threshold = advance_threshold
        self.reinforce_threshold = reinforce_threshold

    def evaluate(
        self,
        learner_id: str,
        concept_id: Optional[str] = None,
        evidence_bundle: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if evidence_bundle is None:
            evidence_bundle = collect_multi_evidence(
                learner_id=learner_id,
                system_concept_id=concept_id,
            )

        evidence = evidence_bundle.get("evidence", {})
        summary = evidence_bundle.get("summary", {})

        mastery_score = float(summary.get("mastery_score", 0.0) or 0.0)
        recent_correctness = float(summary.get("recent_correctness", 0.0) or 0.0)
        behaviour_risk = float(summary.get("behaviour_risk", 0.0) or 0.0)
        decay_priority = float(summary.get("decay_priority", 0.0) or 0.0)
        evidence_confidence = float(summary.get("evidence_confidence", 0.0) or 0.0)

        behaviour_label = evidence.get("behaviour", {}).get("label", "unknown")
        quiz_attempt_count = int(evidence.get("quiz", {}).get("attempt_count", 0) or 0)
        guess_result = detect_guessing(
            learner_id=learner_id,
            concept_id=concept_id,
            evidence_bundle=evidence_bundle,
        )
        confidence_score = self._compute_confidence(
            mastery_score=mastery_score,
            recent_correctness=recent_correctness,
            behaviour_risk=behaviour_risk,
            decay_priority=decay_priority,
        )

        recommendation = self._recommend(
            confidence_score=confidence_score,
            mastery_score=mastery_score,
            recent_correctness=recent_correctness,
            behaviour_risk=behaviour_risk,
            decay_priority=decay_priority,
            evidence_confidence=evidence_confidence,
            quiz_attempt_count=quiz_attempt_count,
        )

        recommendation = self._apply_guess_adjustment(
            recommendation=recommendation,
            guess_result=guess_result,
        )

        reasons = self._build_reasons(
            mastery_score=mastery_score,
            recent_correctness=recent_correctness,
            behaviour_risk=behaviour_risk,
            decay_priority=decay_priority,
            evidence_confidence=evidence_confidence,
            behaviour_label=behaviour_label,
            quiz_attempt_count=quiz_attempt_count,
            recommendation=recommendation,
            guess_result=guess_result,
        )

        result = PromotionConfidenceResult(
            learner_id=str(learner_id),
            concept_id=str(concept_id) if concept_id is not None else evidence_bundle.get("target_concept_id"),
            promotion_confidence=round(confidence_score, 4),
            recommendation=recommendation,
            mastery_score=round(clamp(mastery_score), 4),
            recent_correctness=round(clamp(recent_correctness), 4),
            behaviour_risk=round(clamp(behaviour_risk), 4),
            decay_priority=round(clamp(decay_priority), 4),
            evidence_confidence=round(clamp(evidence_confidence), 4),
            reasons=reasons,
        )

        return {
            "learner_id": result.learner_id,
            "concept_id": result.concept_id,
            "promotion_confidence": result.promotion_confidence,
            "recommendation": result.recommendation,
            "signals": {
                "mastery_score": result.mastery_score,
                "recent_correctness": result.recent_correctness,
                "behaviour_risk": result.behaviour_risk,
                "decay_priority": result.decay_priority,
                "evidence_confidence": result.evidence_confidence,
            },
            "guess_detection" : guess_result,
            "reasons": result.reasons,
            "source_summary": summary,

        }

    def _apply_guess_adjustment(self, recommendation: str, guess_result: Dict[str, Any]) -> str:
        guess_level = guess_result.get("guess_level", "low")
        recommendation_flag = guess_result.get("recommendation_flag", "no_guess_concern")

        if recommendation_flag == "block_promotion" or guess_level == "high":
            return "review"

        if recommendation_flag == "verify_with_more_evidence" or guess_level == "moderate":
            if recommendation == "advance":
                return "reinforce"

        return recommendation

    def _compute_confidence(
        self,
        mastery_score: float,
        recent_correctness: float,
        behaviour_risk: float,
        decay_priority: float,
    ) -> float:
        positive_signal = (
            self.mastery_weight * mastery_score
            + self.correctness_weight * recent_correctness
        )

        penalty_signal = (
            self.behaviour_weight * behaviour_risk
            + self.decay_weight * decay_priority
        )
        # handle missing correctness case
        if recent_correctness == 0.0 and mastery_score > 0.7:
            recent_correctness = 0.5  # fallback assumption

        confidence = (
                self.mastery_weight * mastery_score
                + self.correctness_weight * recent_correctness
                - penalty_signal
        )
        return clamp(confidence)

    def _recommend(
        self,
        confidence_score: float,
        mastery_score: float,
        recent_correctness: float,
        behaviour_risk: float,
        decay_priority: float,
        evidence_confidence: float,
        quiz_attempt_count: int,
    ) -> str:
        if quiz_attempt_count < 2 and evidence_confidence < 0.4:
            return "insufficient_evidence"

        if behaviour_risk >= 0.75:
            return "review"

        if decay_priority >= 0.70 and mastery_score < 0.75:
            return "review"

        if confidence_score >= 0.38 and mastery_score >= 0.65:
            return "advance"

        if confidence_score >= self.reinforce_threshold:
            return "reinforce"

        return "review"

    def _build_reasons(
            self,
            mastery_score: float,
            recent_correctness: float,
            behaviour_risk: float,
            decay_priority: float,
            evidence_confidence: float,
            behaviour_label: str,
            quiz_attempt_count: int,
            recommendation: str,
            guess_result: Dict[str, Any],
    ) -> List[str]:
        reasons: List[str] = []

        if quiz_attempt_count < 3:
            reasons.append("Too few quiz attempts for a reliable promotion decision.")

        if evidence_confidence < 0.5:
            reasons.append("Evidence coverage is low, so the decision is less reliable.")

        if mastery_score >= 0.70:
            reasons.append("Mastery score is strong enough to support progression.")
        elif mastery_score >= 0.50:
            reasons.append("Mastery score is moderate and may need reinforcement.")
        else:
            reasons.append("Mastery score is low and does not yet support progression.")

        if recent_correctness >= 0.70:
            reasons.append("Recent quiz correctness is strong.")
        elif recent_correctness >= 0.50:
            reasons.append("Recent quiz correctness is moderate.")
        else:
            reasons.append("Recent quiz correctness is weak.")

        if behaviour_risk >= 0.70:
            reasons.append("Behaviour risk is high, which reduces confidence in promotion.")
        elif behaviour_risk >= 0.40:
            reasons.append("Behaviour risk is moderate and should be considered.")
        else:
            reasons.append("Behaviour risk is low.")

        if behaviour_label and behaviour_label != "unknown":
            reasons.append(f"Behaviour pattern is currently classified as '{behaviour_label}'.")

        if decay_priority >= 0.70:
            reasons.append("Decay priority is high, so review is important.")
        elif decay_priority >= 0.30:
            reasons.append("Decay priority is moderate.")
        else:
            reasons.append("Decay priority is low.")

        if recommendation == "advance":
            reasons.append("Overall evidence supports moving to the next concept.")
        elif recommendation == "reinforce":
            reasons.append("Learner shows partial readiness, so reinforcement is safer than promotion.")
        elif recommendation == "review":
            reasons.append("Learner should review before moving forward.")
        else:
            reasons.append("More learner evidence is needed before deciding.")

        guess_level = guess_result.get("guess_level", "low")
        if guess_level == "high":
            reasons.append("High guessing behaviour detected, reducing confidence in promotion.")
        elif guess_level == "moderate":
            reasons.append("Moderate guessing behaviour detected; further validation recommended.")

        return reasons

def compute_promotion_confidence(
    learner_id: str,
    concept_id: Optional[str] = None,
    evidence_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    engine = PromotionConfidenceEngine()
    return engine.evaluate(
        learner_id=learner_id,
        concept_id=concept_id,
        evidence_bundle=evidence_bundle,
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    output = compute_promotion_confidence(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))