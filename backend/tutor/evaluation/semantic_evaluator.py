from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

try:
    from sentence_transformers import SentenceTransformer, util
    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - depends on local ML stack
    SentenceTransformer = None
    util = None
    _IMPORT_ERROR = exc


MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_model() -> SentenceTransformer:
    global _model
    if SentenceTransformer is None:
        raise RuntimeError(f"sentence_transformers unavailable: {_IMPORT_ERROR}")
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def semantic_similarity(a: str, b: str) -> float:
    try:
        model = get_model()
        emb1 = model.encode(a, convert_to_tensor=True)
        emb2 = model.encode(b, convert_to_tensor=True)
        score = util.cos_sim(emb1, emb2).item()
        return float(score)
    except Exception:
        return lexical_similarity(a, b)


def lexical_similarity(a: str, b: str) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0

    seq = SequenceMatcher(None, a_norm, b_norm).ratio()
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    overlap = len(a_words & b_words) / max(1, len(b_words))
    return float(max(seq, overlap))


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().strip().split())


def score_against_points(answer: str, expected_points: list[str]) -> tuple[float, list[str], list[str]]:
    if not answer or not expected_points:
        return 0.0, [], expected_points or []

    matched = []
    missing = []

    for point in expected_points:
        sim = semantic_similarity(answer, point)
        if sim >= 0.35:
            matched.append(point)
        else:
            missing.append(point)

    score = len(matched) / max(1, len(expected_points))
    return round(score, 3), matched, missing


def evaluate_semantic_explanation(
    learner_answer: str,
    expected_points: list[str],
) -> dict[str, Any]:
    score, matched, missing = score_against_points(learner_answer, expected_points)

    if score >= 0.8:
        quality = "strong"
        feedback = "Good explanation. Most expected ideas are covered."
    elif score >= 0.4:
        quality = "partial"
        feedback = "Partially correct explanation. Some important ideas are missing."
    else:
        quality = "weak"
        feedback = "Explanation is too limited or misses important ideas."

    if missing:
        feedback += " Missing: " + ", ".join(missing[:3])

    return {
        "score": score,
        "quality_label": quality,
        "matched_key_points": matched,
        "missing_key_points": missing,
        "feedback": feedback,
        "evaluated_at": now_iso(),
        "method": "semantic_embedding" if SentenceTransformer is not None else "lexical_fallback",
        "model_name": MODEL_NAME if SentenceTransformer is not None else "sequence_matcher",
    }


def evaluate_semantic_transfer(
    learner_answer: str,
    expected_points: list[str],
) -> dict[str, Any]:
    score, matched, missing = score_against_points(learner_answer, expected_points)

    if score >= 0.8:
        quality = "strong_transfer"
        feedback = "Good application of the concept in a new situation."
    elif score >= 0.4:
        quality = "partial_transfer"
        feedback = "Reasonable attempt, but the application is incomplete."
    else:
        quality = "weak_transfer"
        feedback = "The answer does not apply the concept well in a new situation."

    if missing:
        feedback += " Missing: " + ", ".join(missing[:3])

    return {
        "score": score,
        "quality_label": quality,
        "matched_key_points": matched,
        "missing_key_points": missing,
        "feedback": feedback,
        "evaluated_at": now_iso(),
        "method": "semantic_embedding" if SentenceTransformer is not None else "lexical_fallback",
        "model_name": MODEL_NAME if SentenceTransformer is not None else "sequence_matcher",
    }


if __name__ == "__main__":
    sample_answer = "A variable stores data and we can use it later in code, for example x = 5."
    expected_points = [
        "basic meaning of variable",
        "purpose of variable",
        "one simple example",
    ]

    import json
    print(json.dumps(evaluate_semantic_explanation(sample_answer, expected_points), indent=2))
