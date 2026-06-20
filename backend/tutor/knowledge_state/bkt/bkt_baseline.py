from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


EPS = 1e-6


@dataclass
class BKTParams:
    p_init: float = 0.25
    p_learn: float = 0.12
    p_guess: float = 0.2
    p_slip: float = 0.1

    def clamped(self) -> "BKTParams":
        return BKTParams(
            p_init=_clamp(self.p_init),
            p_learn=_clamp(self.p_learn),
            p_guess=_clamp(self.p_guess),
            p_slip=_clamp(self.p_slip),
        )

    def to_dict(self) -> dict[str, float]:
        return asdict(self.clamped())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BKTParams":
        return cls(
            p_init=float(data.get("p_init", 0.25)),
            p_learn=float(data.get("p_learn", 0.12)),
            p_guess=float(data.get("p_guess", 0.2)),
            p_slip=float(data.get("p_slip", 0.1)),
        ).clamped()


def _clamp(value: float) -> float:
    return max(EPS, min(1.0 - EPS, float(value)))


def predict_correct(mastery: float, params: BKTParams) -> float:
    params = params.clamped()
    mastery = _clamp(mastery)
    return _clamp(mastery * (1.0 - params.p_slip) + (1.0 - mastery) * params.p_guess)


def update_mastery(mastery: float, is_correct: int | bool, params: BKTParams) -> float:
    params = params.clamped()
    mastery = _clamp(mastery)
    p_correct = predict_correct(mastery, params)

    if bool(is_correct):
        posterior = mastery * (1.0 - params.p_slip) / p_correct
    else:
        p_incorrect = _clamp(1.0 - p_correct)
        posterior = mastery * params.p_slip / p_incorrect

    learned = posterior + (1.0 - posterior) * params.p_learn
    return _clamp(learned)


def sequence_predictions(
    correctness: list[int],
    params: BKTParams,
    initial_mastery: float | None = None,
) -> tuple[list[float], list[float]]:
    mastery = params.p_init if initial_mastery is None else initial_mastery
    predictions: list[float] = []
    mastery_values: list[float] = []
    for correct in correctness:
        predictions.append(predict_correct(mastery, params))
        mastery = update_mastery(mastery, correct, params)
        mastery_values.append(mastery)
    return predictions, mastery_values


def log_loss_for_sequence(correctness: list[int], params: BKTParams) -> float:
    if not correctness:
        return 0.0
    losses = []
    mastery = params.p_init
    for correct in correctness:
        prob = predict_correct(mastery, params)
        losses.append(-(correct * math.log(prob) + (1 - correct) * math.log(1.0 - prob)))
        mastery = update_mastery(mastery, correct, params)
    return sum(losses) / len(losses)


def fit_bkt_params_grid(correctness: list[int]) -> BKTParams:
    if not correctness:
        return BKTParams()

    best = BKTParams()
    best_loss = float("inf")
    grids = {
        "p_init": [0.1, 0.2, 0.35, 0.5, 0.65, 0.8],
        "p_learn": [0.03, 0.08, 0.15, 0.25, 0.4],
        "p_guess": [0.1, 0.2, 0.3],
        "p_slip": [0.05, 0.1, 0.2, 0.3],
    }

    for p_init in grids["p_init"]:
        for p_learn in grids["p_learn"]:
            for p_guess in grids["p_guess"]:
                for p_slip in grids["p_slip"]:
                    if p_guess >= 1.0 - p_slip:
                        continue
                    params = BKTParams(p_init, p_learn, p_guess, p_slip)
                    loss = log_loss_for_sequence(correctness, params)
                    if loss < best_loss:
                        best_loss = loss
                        best = params

    return best.clamped()


class BKTModel:
    def __init__(
        self,
        concept_params: dict[str, BKTParams] | None = None,
        global_params: BKTParams | None = None,
    ) -> None:
        self.concept_params = concept_params or {}
        self.global_params = global_params or BKTParams()
        self.mastery_by_key: dict[tuple[str, str], float] = {}

    def params_for(self, concept_id: str) -> BKTParams:
        return self.concept_params.get(str(concept_id), self.global_params)

    def predict(self, learner_id: str, concept_id: str) -> float:
        params = self.params_for(concept_id)
        mastery = self.mastery_by_key.get((str(learner_id), str(concept_id)), params.p_init)
        return predict_correct(mastery, params)

    def update(self, learner_id: str, concept_id: str, is_correct: int | bool) -> float:
        params = self.params_for(concept_id)
        key = (str(learner_id), str(concept_id))
        mastery = self.mastery_by_key.get(key, params.p_init)
        updated = update_mastery(mastery, is_correct, params)
        self.mastery_by_key[key] = updated
        return updated

    def predict_then_update(self, learner_id: str, concept_id: str, is_correct: int | bool) -> float:
        prediction = self.predict(learner_id, concept_id)
        self.update(learner_id, concept_id, is_correct)
        return prediction

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": "bkt_baseline",
            "global_params": self.global_params.to_dict(),
            "concept_params": {
                str(concept_id): params.to_dict()
                for concept_id, params in self.concept_params.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BKTModel":
        concept_params = {
            str(concept_id): BKTParams.from_dict(params)
            for concept_id, params in (data.get("concept_params") or {}).items()
            if isinstance(params, dict)
        }
        return cls(
            concept_params=concept_params,
            global_params=BKTParams.from_dict(data.get("global_params") or {}),
        )
