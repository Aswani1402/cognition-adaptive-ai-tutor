from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tutor.system.multi_evidence_collector import collect_multi_evidence

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class GuessDetectionResult:
    learner_id: str
    concept_id: Optional[str]
    guess_score: float
    guess_level: str
    guessed_correct_ratio: float
    fast_correct_ratio: float
    retry_before_success_ratio: float
    unstable_pattern_ratio: float
    recommendation_flag: str
    reasons: List[str]


class GuessDetectionEngine:
    def __init__(
        self,
        low_conf_threshold: float = 2.0,
        fast_time_threshold: float = 15.0,
        high_guess_threshold: float = 0.60,
        moderate_guess_threshold: float = 0.35,
    ) -> None:
        self.low_conf_threshold = low_conf_threshold
        self.fast_time_threshold = fast_time_threshold
        self.high_guess_threshold = high_guess_threshold
        self.moderate_guess_threshold = moderate_guess_threshold

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

        quiz = evidence_bundle.get("evidence", {}).get("quiz", {})
        attempts = quiz.get("recent_attempts", []) or []

        guessed_correct_ratio = self._guessed_correct_ratio(attempts)
        fast_correct_ratio = self._fast_correct_ratio(attempts)
        retry_before_success_ratio = self._retry_before_success_ratio(attempts)
        unstable_pattern_ratio = self._unstable_pattern_ratio(attempts)

        guess_score = clamp(
            0.35 * guessed_correct_ratio
            + 0.25 * fast_correct_ratio
            + 0.20 * retry_before_success_ratio
            + 0.20 * unstable_pattern_ratio
        )

        guess_level = self._guess_level(guess_score)
        recommendation_flag = self._recommendation_flag(guess_score, len(attempts))

        reasons = self._build_reasons(
            attempts=attempts,
            guessed_correct_ratio=guessed_correct_ratio,
            fast_correct_ratio=fast_correct_ratio,
            retry_before_success_ratio=retry_before_success_ratio,
            unstable_pattern_ratio=unstable_pattern_ratio,
            guess_level=guess_level,
            recommendation_flag=recommendation_flag,
        )

        result = GuessDetectionResult(
            learner_id=str(learner_id),
            concept_id=str(concept_id) if concept_id is not None else evidence_bundle.get("target_concept_id"),
            guess_score=round(guess_score, 4),
            guess_level=guess_level,
            guessed_correct_ratio=round(guessed_correct_ratio, 4),
            fast_correct_ratio=round(fast_correct_ratio, 4),
            retry_before_success_ratio=round(retry_before_success_ratio, 4),
            unstable_pattern_ratio=round(unstable_pattern_ratio, 4),
            recommendation_flag=recommendation_flag,
            reasons=reasons,
        )

        return {
            "learner_id": result.learner_id,
            "concept_id": result.concept_id,
            "guess_score": result.guess_score,
            "guess_level": result.guess_level,
            "signals": {
                "guessed_correct_ratio": result.guessed_correct_ratio,
                "fast_correct_ratio": result.fast_correct_ratio,
                "retry_before_success_ratio": result.retry_before_success_ratio,
                "unstable_pattern_ratio": result.unstable_pattern_ratio,
            },
            "recommendation_flag": result.recommendation_flag,
            "reasons": result.reasons,
        }

    def _guessed_correct_ratio(self, attempts: List[Dict[str, Any]]) -> float:
        correct_attempts = [a for a in attempts if int(a.get("is_correct") or 0) == 1]
        if not correct_attempts:
            return 0.0

        guessed_correct = 0
        for a in correct_attempts:
            confidence = float(a.get("confidence") or 0.0)
            if confidence <= self.low_conf_threshold:
                guessed_correct += 1

        return guessed_correct / len(correct_attempts)

    def _fast_correct_ratio(self, attempts: List[Dict[str, Any]]) -> float:
        correct_attempts = [a for a in attempts if int(a.get("is_correct") or 0) == 1]
        if not correct_attempts:
            return 0.0

        fast_correct = 0
        for a in correct_attempts:
            time_taken = float(a.get("time_taken_sec") or 0.0)
            if 0 < time_taken <= self.fast_time_threshold:
                fast_correct += 1

        return fast_correct / len(correct_attempts)

    def _retry_before_success_ratio(self, attempts: List[Dict[str, Any]]) -> float:
        success_attempts = [a for a in attempts if int(a.get("is_correct") or 0) == 1]
        if not success_attempts:
            return 0.0

        retry_success = 0
        for a in success_attempts:
            attempt_no = int(a.get("attempt_no") or 1)
            if attempt_no > 1:
                retry_success += 1

        return retry_success / len(success_attempts)

    def _unstable_pattern_ratio(self, attempts: List[Dict[str, Any]]) -> float:
        if len(attempts) < 2:
            return 0.0

        ordered = list(reversed(attempts))
        flips = 0

        prev = int(ordered[0].get("is_correct") or 0)
        for a in ordered[1:]:
            curr = int(a.get("is_correct") or 0)
            if curr != prev:
                flips += 1
            prev = curr

        return flips / (len(ordered) - 1)

    def _guess_level(self, guess_score: float) -> str:
        if guess_score >= self.high_guess_threshold:
            return "high"
        if guess_score >= self.moderate_guess_threshold:
            return "moderate"
        return "low"

    def _recommendation_flag(self, guess_score: float, attempt_count: int) -> str:
        if attempt_count < 3:
            return "insufficient_evidence"
        if guess_score >= self.high_guess_threshold:
            return "block_promotion"
        if guess_score >= self.moderate_guess_threshold:
            return "verify_with_more_evidence"
        return "no_guess_concern"

    def _build_reasons(
        self,
        attempts: List[Dict[str, Any]],
        guessed_correct_ratio: float,
        fast_correct_ratio: float,
        retry_before_success_ratio: float,
        unstable_pattern_ratio: float,
        guess_level: str,
        recommendation_flag: str,
    ) -> List[str]:
        reasons: List[str] = []

        if len(attempts) < 3:
            reasons.append("Too few attempts to judge guessing reliably.")
            return reasons

        if guessed_correct_ratio >= 0.5:
            reasons.append("Many correct answers were given with very low confidence.")
        elif guessed_correct_ratio > 0:
            reasons.append("Some correct answers were given with low confidence.")

        if fast_correct_ratio >= 0.5:
            reasons.append("Many correct answers were unusually fast.")
        elif fast_correct_ratio > 0:
            reasons.append("Some correct answers were unusually fast.")

        if retry_before_success_ratio >= 0.5:
            reasons.append("Several correct answers happened only after multiple attempts.")
        elif retry_before_success_ratio > 0:
            reasons.append("Some correct answers happened after retries.")

        if unstable_pattern_ratio >= 0.5:
            reasons.append("Correctness pattern is unstable across recent attempts.")
        elif unstable_pattern_ratio > 0:
            reasons.append("Recent attempts show some instability.")

        if guess_level == "high":
            reasons.append("Guessing risk is high enough to affect progression decisions.")
        elif guess_level == "moderate":
            reasons.append("Guessing risk is moderate and should be verified.")
        else:
            reasons.append("Guessing risk appears low.")

        if recommendation_flag == "block_promotion":
            reasons.append("Promotion should be blocked until stronger evidence appears.")
        elif recommendation_flag == "verify_with_more_evidence":
            reasons.append("Use another assessment or explanation check before promotion.")
        elif recommendation_flag == "insufficient_evidence":
            reasons.append("Collect more attempts before using guess detection strongly.")
        else:
            reasons.append("No immediate guessing-based restriction is needed.")

        return reasons


def detect_guessing(
    learner_id: str,
    concept_id: Optional[str] = None,
    evidence_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    engine = GuessDetectionEngine()
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

    output = detect_guessing(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )
    print(json.dumps(output, indent=2))