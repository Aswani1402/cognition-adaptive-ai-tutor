from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from typing import Any


QUESTION_TYPES = [
    "mcq",
    "output_prediction",
    "debug_task",
    "explanation_check",
    "transfer_question",
    "challenge_question",
    "syntax_completion",
    "puzzle",
]


@dataclass(frozen=True)
class LearnerProfileParameters:
    correct_probability: float
    partial_probability: float
    wrong_probability: float
    avg_confidence: float
    avg_time_taken_sec: float
    hint_usage_probability: float
    option_change_probability: float
    careless_error_probability: float
    guess_probability: float


PROFILE_PARAMETERS: dict[str, LearnerProfileParameters] = {
    "strong": LearnerProfileParameters(0.88, 0.10, 0.02, 0.86, 32, 0.10, 0.08, 0.04, 0.03),
    "average": LearnerProfileParameters(0.58, 0.28, 0.14, 0.62, 45, 0.32, 0.18, 0.10, 0.12),
    "weak": LearnerProfileParameters(0.22, 0.34, 0.44, 0.38, 72, 0.68, 0.24, 0.14, 0.18),
    "guessing": LearnerProfileParameters(0.28, 0.12, 0.60, 0.34, 18, 0.30, 0.58, 0.22, 0.72),
    "careless": LearnerProfileParameters(0.70, 0.14, 0.16, 0.74, 24, 0.18, 0.34, 0.34, 0.10),
    "low_confidence": LearnerProfileParameters(0.55, 0.30, 0.15, 0.30, 58, 0.50, 0.22, 0.08, 0.08),
}


class LearnerAnswerSimulator:
    """Profile-based learner answer simulator for testing and evaluation."""

    MODULE = "LearnerAnswerSimulator"

    def simulate_answer(
        self,
        question_payload: dict[str, Any],
        profile: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        rng = random.Random(seed)
        profile_name = self._profile(profile)
        params = PROFILE_PARAMETERS[profile_name]
        question_type = self._question_type(question_payload)
        expected_answer = self._expected_answer(question_payload)
        outcome = self._sample_outcome(params, profile_name, rng)
        simulated_answer, mistake_type = self._build_answer(
            question_payload=question_payload,
            question_type=question_type,
            expected_answer=expected_answer,
            outcome=outcome,
            profile=profile_name,
            rng=rng,
        )
        score = self._score_for_outcome(outcome, mistake_type)
        confidence = self._sample_metric(params.avg_confidence, rng, spread=0.12)
        if profile_name == "low_confidence":
            confidence = min(confidence, 0.48)
        if outcome == "correct" and profile_name == "guessing":
            confidence = min(confidence, 0.55)

        time_taken = max(1, int(round(rng.gauss(params.avg_time_taken_sec, params.avg_time_taken_sec * 0.18))))
        hint_used = rng.random() < params.hint_usage_probability
        option_changes = self._sample_option_changes(params.option_change_probability, rng)

        return {
            "status": "success",
            "module": self.MODULE,
            "profile": profile_name,
            "question_type": question_type,
            "simulated_answer": simulated_answer,
            "expected_answer": expected_answer,
            "is_expected_correct": outcome == "correct",
            "score_estimate": round(score, 4),
            "confidence": round(confidence, 4),
            "time_taken_sec": time_taken,
            "hint_used": hint_used,
            "option_changes": option_changes,
            "mistake_type": mistake_type,
            "simulation_parameters": asdict(params),
        }

    def simulate_session(
        self,
        question_list: list[dict[str, Any]],
        profile: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        profile_name = self._profile(profile)
        answers = []
        for index, question in enumerate(question_list):
            item_seed = None if seed is None else seed + index * 997
            answers.append(self.simulate_answer(question, profile_name, seed=item_seed))
        return {
            "status": "success",
            "module": self.MODULE,
            "profile": profile_name,
            "question_count": len(answers),
            "answers": answers,
            "summary": self._summarize(answers),
        }

    def simulate_profiles(
        self,
        question_list: list[dict[str, Any]],
        profiles: list[str] | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        profile_names = [self._profile(profile) for profile in (profiles or list(PROFILE_PARAMETERS))]
        sessions = {}
        for index, profile in enumerate(profile_names):
            profile_seed = None if seed is None else seed + index * 10007
            sessions[profile] = self.simulate_session(question_list, profile, seed=profile_seed)
        return {
            "status": "success",
            "module": self.MODULE,
            "profiles": profile_names,
            "question_count": len(question_list),
            "sessions": sessions,
        }

    def _sample_outcome(
        self,
        params: LearnerProfileParameters,
        profile: str,
        rng: random.Random,
    ) -> str:
        if profile == "careless" and rng.random() < params.careless_error_probability:
            return "wrong"
        roll = rng.random()
        if roll < params.correct_probability:
            return "correct"
        if roll < params.correct_probability + params.partial_probability:
            return "partial"
        return "wrong"

    def _build_answer(
        self,
        question_payload: dict[str, Any],
        question_type: str,
        expected_answer: str,
        outcome: str,
        profile: str,
        rng: random.Random,
    ) -> tuple[str, str]:
        if outcome == "correct":
            return expected_answer or self._generic_correct(question_type), "none"

        if outcome == "partial":
            return self._partial_answer(question_payload, question_type, expected_answer), "partial"

        if question_type == "mcq":
            return self._wrong_mcq(question_payload, expected_answer, rng), "wrong_option" if profile != "guessing" else "guessed_option"
        if question_type == "output_prediction":
            return self._wrong_output(expected_answer), "wrong_output"
        if question_type in {"debug_task", "debug"}:
            return "The code looks mostly fine, but maybe one line needs changing.", "syntax_misunderstanding"
        if question_type == "syntax_completion":
            return self._broken_syntax(expected_answer), "syntax_misunderstanding"
        if question_type in {"explanation_check", "explanation"}:
            return "It is something used in coding.", "vague_answer"
        if question_type in {"transfer_question", "challenge_question"}:
            return "I would use it somehow in the program.", "vague_answer"
        if question_type == "puzzle":
            return "wrong order", "puzzle_sequence_error"
        return "I am not sure.", "unknown"

    def _partial_answer(self, question_payload: dict[str, Any], question_type: str, expected_answer: str) -> str:
        key_points = question_payload.get("key_points") or question_payload.get("expected_points") or []
        if isinstance(key_points, list) and key_points:
            return str(key_points[0])
        if expected_answer:
            words = expected_answer.split()
            return " ".join(words[: max(1, len(words) // 2)])
        if question_type == "output_prediction":
            return "one value changes"
        return "partly correct idea"

    def _summarize(self, answers: list[dict[str, Any]]) -> dict[str, Any]:
        if not answers:
            return {
                "average_score": 0.0,
                "average_confidence": 0.0,
                "average_time_taken_sec": 0.0,
                "hint_usage_rate": 0.0,
                "option_change_rate": 0.0,
            }
        count = len(answers)
        return {
            "average_score": round(sum(item["score_estimate"] for item in answers) / count, 6),
            "average_confidence": round(sum(item["confidence"] for item in answers) / count, 6),
            "average_time_taken_sec": round(sum(item["time_taken_sec"] for item in answers) / count, 6),
            "hint_usage_rate": round(sum(1 for item in answers if item["hint_used"]) / count, 6),
            "option_change_rate": round(sum(item["option_changes"] for item in answers) / count, 6),
        }

    def _profile(self, profile: str | None) -> str:
        profile_name = str(profile or "average").strip().lower()
        return profile_name if profile_name in PROFILE_PARAMETERS else "average"

    def _question_type(self, question_payload: dict[str, Any]) -> str:
        value = (
            question_payload.get("question_type")
            or question_payload.get("assessment_type")
            or question_payload.get("task_type")
            or "explanation_check"
        )
        value = str(value).strip()
        aliases = {
            "debug": "debug_task",
            "explanation": "explanation_check",
            "transfer": "transfer_question",
            "challenge": "challenge_question",
        }
        return aliases.get(value, value)

    def _expected_answer(self, question_payload: dict[str, Any]) -> str:
        expected = (
            question_payload.get("expected_answer")
            or question_payload.get("correct_answer")
            or question_payload.get("answer")
            or question_payload.get("expected_output")
            or ""
        )
        if isinstance(expected, dict):
            expected = (
                expected.get("answer")
                or expected.get("expected_output")
                or expected.get("expected_fix")
                or expected.get("value")
                or ""
            )
        if not expected and question_payload.get("options") and question_payload.get("correct_option_index") is not None:
            options = question_payload.get("options") or []
            index = question_payload.get("correct_option_index")
            if isinstance(index, int) and 0 <= index < len(options):
                expected = options[index]
        return str(expected)

    def _wrong_mcq(self, question_payload: dict[str, Any], expected_answer: str, rng: random.Random) -> str:
        options = [str(option) for option in question_payload.get("options", [])]
        wrong = [option for option in options if option.strip().lower() != expected_answer.strip().lower()]
        return rng.choice(wrong) if wrong else "incorrect option"

    def _wrong_output(self, expected_answer: str) -> str:
        mapping = {"15": "10", "10": "20", "5": "0", "true": "false", "false": "true"}
        key = str(expected_answer).strip().lower()
        return mapping.get(key, "0")

    def _broken_syntax(self, expected_answer: str) -> str:
        if "==" in expected_answer:
            return expected_answer.replace("==", "=").rstrip(":")
        if ":" in expected_answer:
            return expected_answer.replace(":", "")
        return "if value = 10"

    def _generic_correct(self, question_type: str) -> str:
        if question_type == "output_prediction":
            return "expected output"
        if question_type == "syntax_completion":
            return "correct syntax"
        return "correct answer"

    def _score_for_outcome(self, outcome: str, mistake_type: str) -> float:
        if outcome == "correct":
            return 1.0
        if outcome == "partial":
            return 0.55
        if mistake_type in {"guessed_option", "wrong_option", "wrong_output", "syntax_misunderstanding"}:
            return 0.15
        return 0.25

    def _sample_metric(self, mean: float, rng: random.Random, spread: float) -> float:
        return max(0.0, min(1.0, rng.gauss(mean, spread)))

    def _sample_option_changes(self, probability: float, rng: random.Random) -> int:
        if rng.random() >= probability:
            return 0
        return 1 + int(rng.random() < probability * 0.8) + int(rng.random() < probability * 0.35)


def simulate_answer(
    question_payload: dict[str, Any],
    profile: str,
    seed: int | None = None,
) -> dict[str, Any]:
    return LearnerAnswerSimulator().simulate_answer(question_payload, profile, seed)


def simulate_session(
    question_list: list[dict[str, Any]],
    profile: str,
    seed: int | None = None,
) -> dict[str, Any]:
    return LearnerAnswerSimulator().simulate_session(question_list, profile, seed)


def simulate_profiles(
    question_list: list[dict[str, Any]],
    profiles: list[str] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    return LearnerAnswerSimulator().simulate_profiles(question_list, profiles, seed)
