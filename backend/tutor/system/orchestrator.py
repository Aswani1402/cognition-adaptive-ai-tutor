from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tutor.system.multi_evidence_collector import collect_multi_evidence
from tutor.system.promotion_confidence import compute_promotion_confidence
from tutor.system.guess_detection import detect_guessing
from tutor.system.review_need_predictor import predict_review_need


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class OrchestratorDecision:
    learner_id: str
    concept_id: Optional[str]
    final_action: str
    confidence: float
    reasons: List[str]


class TutorOrchestrator:
    def evaluate(
        self,
        learner_id: str,
        concept_id: Optional[str] = None,
        evidence_bundle: Optional[Dict[str, Any]] = None,
        promotion_result: Optional[Dict[str, Any]] = None,
        guess_result: Optional[Dict[str, Any]] = None,
        review_result: Optional[Dict[str, Any]] = None,
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

        if review_result is None:
            review_result = predict_review_need(
                learner_id=learner_id,
                concept_id=concept_id,
                evidence_bundle=evidence_bundle,
                promotion_result=promotion_result,
                guess_result=guess_result,
            )

        final_action = self._decide_action(
            promotion_result=promotion_result,
            guess_result=guess_result,
            review_result=review_result,
        )

        final_confidence = self._decision_confidence(
            evidence_bundle=evidence_bundle,
            promotion_result=promotion_result,
            guess_result=guess_result,
            review_result=review_result,
            final_action=final_action,
        )

        reasons = self._build_reasons(
            promotion_result=promotion_result,
            guess_result=guess_result,
            review_result=review_result,
            final_action=final_action,
        )

        result = OrchestratorDecision(
            learner_id=str(learner_id),
            concept_id=str(concept_id) if concept_id is not None else evidence_bundle.get("target_concept_id"),
            final_action=final_action,
            confidence=round(final_confidence, 4),
            reasons=reasons,
        )

        return {
            "learner_id": result.learner_id,
            "concept_id": result.concept_id,
            "final_action": result.final_action,
            "decision_confidence": result.confidence,
            "reasons": result.reasons,
            "evidence_summary": evidence_bundle.get("summary", {}),
            "promotion_result": promotion_result,
            "guess_result": guess_result,
            "review_result": review_result,
        }

    def _decide_action(
        self,
        promotion_result: Dict[str, Any],
        guess_result: Dict[str, Any],
        review_result: Dict[str, Any],
    ) -> str:
        promotion_recommendation = promotion_result.get("recommendation", "review")
        guess_flag = guess_result.get("recommendation_flag", "no_guess_concern")
        guess_level = guess_result.get("guess_level", "low")
        review_recommendation = review_result.get("recommendation", "light_review")

        if review_recommendation in {"immediate_review", "review_before_next"} and guess_level == "high":
            return "review_current"

        if guess_flag == "block_promotion" and guess_level == "high":
            return "review_current"

        if review_recommendation == "priority_review":
            return "schedule_review"

        if promotion_recommendation == "advance":
            return "advance"

        if promotion_recommendation == "reinforce":
            return "reinforce_current"

        if promotion_recommendation == "review":
            return "review_current"

        return "reinforce_current"

    def _decision_confidence(
        self,
        evidence_bundle: Dict[str, Any],
        promotion_result: Dict[str, Any],
        guess_result: Dict[str, Any],
        review_result: Dict[str, Any],
        final_action: str,
    ) -> float:
        summary = evidence_bundle.get("summary", {})

        evidence_confidence = float(summary.get("evidence_confidence", 0.0) or 0.0)
        promotion_confidence = float(promotion_result.get("promotion_confidence", 0.0) or 0.0)
        guess_score = float(guess_result.get("guess_score", 0.0) or 0.0)
        review_need_score = float(review_result.get("review_need_score", 0.0) or 0.0)

        if final_action == "advance":
            score = (
                0.50 * promotion_confidence
                + 0.30 * evidence_confidence
                + 0.20 * (1.0 - guess_score)
            )
        else:
            score = (
                0.40 * evidence_confidence
                + 0.30 * review_need_score
                + 0.30 * guess_score
            )

        return clamp(score)

    def _build_reasons(
        self,
        promotion_result: Dict[str, Any],
        guess_result: Dict[str, Any],
        review_result: Dict[str, Any],
        final_action: str,
    ) -> List[str]:
        reasons: List[str] = []

        promotion_recommendation = promotion_result.get("recommendation", "review")
        promotion_confidence = promotion_result.get("promotion_confidence", 0.0)

        guess_level = guess_result.get("guess_level", "low")
        guess_score = guess_result.get("guess_score", 0.0)

        review_recommendation = review_result.get("recommendation", "light_review")
        review_need_score = review_result.get("review_need_score", 0.0)
        urgency_level = review_result.get("urgency_level", "low")

        reasons.append(
            f"Promotion module recommends '{promotion_recommendation}' with confidence {promotion_confidence}."
        )
        reasons.append(
            f"Guess detection reports '{guess_level}' guessing risk with score {guess_score}."
        )
        reasons.append(
            f"Review module recommends '{review_recommendation}' with urgency '{urgency_level}' and score {review_need_score}."
        )

        if final_action == "advance":
            reasons.append("Signals are strong enough to move forward.")
        elif final_action == "reinforce_current":
            reasons.append("Learner should continue on the current concept with reinforcement.")
        elif final_action == "review_current":
            reasons.append("Learner should review the current concept before progressing.")
        else:
            reasons.append("Concept should be placed into the review schedule.")

        return reasons


def run_orchestrator(
    learner_id: str,
    concept_id: Optional[str] = None,
    evidence_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    orchestrator = TutorOrchestrator()
    return orchestrator.evaluate(
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

    output = run_orchestrator(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))