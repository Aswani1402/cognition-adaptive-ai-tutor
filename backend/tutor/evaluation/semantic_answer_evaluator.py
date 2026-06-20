from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "to",
    "of",
    "in",
    "on",
    "for",
    "and",
    "or",
    "with",
    "that",
    "this",
    "it",
    "as",
    "by",
    "be",
    "can",
    "we",
    "you",
    "they",
    "has",
    "have",
    "had",
}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _tokens(text: str) -> list[str]:
    return [
        _stem_token(token)
        for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|\d+", text.lower())
        if token not in STOPWORDS
    ]


def _stem_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 5:
        return token[:-3] + "y"
    if token.endswith("ces") and len(token) > 5:
        return token[:-1]
    if token.endswith("res") and len(token) > 5:
        return token[:-1]
    if token.endswith("les") and len(token) > 5:
        return token[:-1]
    if token.endswith("ed") and len(token) > 5:
        base = token[:-2]
        if base.endswith(("s", "r", "x", "t")):
            return base
        return base + "e"
    for suffix in ["ing", "ed", "es", "s"]:
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _token_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.84


def _label(
    score: float,
    semantic_similarity: float = 0.0,
    key_point_coverage: float = 0.0,
) -> str:
    if score >= 0.35 and (key_point_coverage >= 0.45 or semantic_similarity >= 0.50):
        return "strong"
    if score >= 0.25:
        return "partial"
    return "weak"


class SemanticAnswerEvaluator:
    def __init__(self) -> None:
        self._embedding_model: Any | None = None
        self._embedding_unavailable_reason: str | None = None

    def evaluate(
        self,
        learner_answer: Any,
        expected_answer: Any = None,
        key_points: list[str] | None = None,
        concept_name: str | None = None,
        task_type: str = "explanation",
        rubric_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        answer = _safe_str(learner_answer)
        expected = _safe_str(expected_answer or "")
        points = [str(point).strip() for point in (key_points or []) if str(point).strip()]

        if not expected and points:
            expected = " ".join(points)

        if not answer:
            return self._empty_result(task_type=task_type)

        semantic_similarity, method = self._semantic_similarity(answer, expected)
        key_point_coverage = self._key_point_coverage(answer, points if points else self._derive_key_points(expected))
        rubric_score = self._rubric_score(rubric_output, semantic_similarity, key_point_coverage)
        structure_score = self._structure_score(answer, expected, points, concept_name)

        weighted_score = _clamp(
            0.45 * semantic_similarity
            + 0.25 * key_point_coverage
            + 0.20 * rubric_score
            + 0.10 * structure_score
        )
        calibrated_score = self._calibrated_score(
            weighted_score=weighted_score,
            semantic_similarity=semantic_similarity,
            key_point_coverage=key_point_coverage,
            rubric_score=rubric_score,
            structure_score=structure_score,
        )
        final_score = calibrated_score
        label = _label(final_score, semantic_similarity, key_point_coverage)
        confidence = self._confidence(final_score, [semantic_similarity, key_point_coverage, rubric_score, structure_score])

        return {
            "status": "success",
            "module": "SemanticAnswerEvaluator",
            "task_type": task_type,
            "score": round(final_score, 4),
            "label": label,
            "semantic_similarity": round(semantic_similarity, 4),
            "key_point_coverage": round(key_point_coverage, 4),
            "rubric_score": round(rubric_score, 4),
            "structure_score": round(structure_score, 4),
            "confidence": round(confidence, 4),
            "method": method,
            "feedback": self._feedback(label, key_point_coverage, structure_score),
            "limitations": [
                "Semantic scores are automatic estimates and should be calibrated with human-rated answers.",
                "The strong/partial/weak thresholds follow existing evaluator label bands and need further calibration.",
            ],
            "evidence": {
                "learner_answer": answer,
                "expected_answer": expected,
                "key_points": points,
                "concept_name": concept_name,
                "weights": {
                    "semantic_similarity": 0.45,
                    "key_point_coverage": 0.25,
                    "rubric_score": 0.20,
                    "structure_score": 0.10,
                },
                "weighted_score_before_calibration": round(weighted_score, 4),
                "calibration_rule": (
                    "max(weighted_score, 0.50*key_point_coverage + 0.30*semantic_similarity "
                    "+ 0.15*rubric_score + 0.05*structure_score)"
                ),
                "label_rule": (
                    "strong if score>=0.35 and key_point_coverage>=0.45 or semantic_similarity>=0.50; "
                    "partial if score>=0.25; otherwise weak. These bands are benchmark-calibrated for local TF-IDF scoring."
                ),
                "embedding_unavailable_reason": self._embedding_unavailable_reason,
            },
        }

    def _empty_result(self, task_type: str) -> dict[str, Any]:
        return {
            "status": "success",
            "module": "SemanticAnswerEvaluator",
            "task_type": task_type,
            "score": 0.0,
            "label": "weak",
            "semantic_similarity": 0.0,
            "key_point_coverage": 0.0,
            "rubric_score": 0.0,
            "structure_score": 0.0,
            "confidence": 1.0,
            "method": "empty_answer",
            "feedback": "No answer was provided.",
            "limitations": [
                "Empty answers cannot be semantically evaluated.",
            ],
            "evidence": {
                "learner_answer": "",
                "expected_answer": "",
                "key_points": [],
                "weights": {
                    "semantic_similarity": 0.45,
                    "key_point_coverage": 0.25,
                    "rubric_score": 0.20,
                    "structure_score": 0.10,
                },
            },
        }

    def _semantic_similarity(self, answer: str, expected: str) -> tuple[float, str]:
        if not answer or not expected:
            return 0.0, "empty_reference"
        embedding_score = self._embedding_cosine(answer, expected)
        if embedding_score is not None:
            return embedding_score, "embedding_cosine"
        tfidf_score = self._tfidf_cosine(answer, expected)
        if tfidf_score is not None:
            return tfidf_score, "tfidf_cosine"
        return self._token_overlap(answer, expected), "token_overlap"

    def _embedding_cosine(self, answer: str, expected: str) -> float | None:
        if self._embedding_unavailable_reason:
            return None
        try:
            from sentence_transformers import SentenceTransformer, util

            if self._embedding_model is None:
                try:
                    self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
                except TypeError:
                    self._embedding_unavailable_reason = "sentence-transformers local_files_only not supported in this environment"
                    return None
            emb_a = self._embedding_model.encode(answer, convert_to_tensor=True)
            emb_b = self._embedding_model.encode(expected, convert_to_tensor=True)
            return _clamp(float(util.cos_sim(emb_a, emb_b).item()))
        except Exception as exc:
            self._embedding_unavailable_reason = f"{type(exc).__name__}: local embedding unavailable"
            return None

    def _tfidf_cosine(self, answer: str, expected: str) -> float | None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            word_matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform([answer, expected])
            word_score = float(cosine_similarity(word_matrix[0], word_matrix[1])[0][0])
            char_matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform([answer, expected])
            char_score = float(cosine_similarity(char_matrix[0], char_matrix[1])[0][0])
            sequence_score = SequenceMatcher(None, answer.lower(), expected.lower()).ratio()
            overlap_score = self._token_overlap(answer, expected)
            return _clamp(max(word_score, char_score, sequence_score, overlap_score))
        except Exception:
            return None

    def _token_overlap(self, answer: str, expected: str) -> float:
        answer_tokens = set(_tokens(answer))
        expected_tokens = set(_tokens(expected))
        if not expected_tokens:
            return 0.0
        matched_answer = set()
        matched_expected = set()
        for answer_token in answer_tokens:
            for expected_token in expected_tokens:
                if _token_match(answer_token, expected_token):
                    matched_answer.add(answer_token)
                    matched_expected.add(expected_token)
        precision = len(matched_answer) / max(1, len(answer_tokens))
        recall = len(matched_expected) / max(1, len(expected_tokens))
        if precision + recall == 0:
            return 0.0
        return _clamp(2 * precision * recall / (precision + recall))

    def _derive_key_points(self, expected: str) -> list[str]:
        if not expected:
            return []
        chunks = [chunk.strip() for chunk in re.split(r"[.;\n]", expected) if chunk.strip()]
        return chunks if chunks else [expected]

    def _key_point_coverage(self, answer: str, key_points: list[str]) -> float:
        if not key_points:
            return 0.0
        scores = []
        answer_tokens = set(_tokens(answer))
        for point in key_points:
            phrase_hit = point.lower() in answer.lower()
            point_tokens = set(_tokens(point))
            matched_points = {
                point_token
                for point_token in point_tokens
                if any(_token_match(answer_token, point_token) for answer_token in answer_tokens)
            }
            point_recall = len(matched_points) / max(1, len(point_tokens))
            overlap = self._token_overlap(answer, point)
            scores.append(1.0 if phrase_hit else max(point_recall, overlap))
        return _clamp(sum(scores) / len(scores))

    def _calibrated_score(
        self,
        weighted_score: float,
        semantic_similarity: float,
        key_point_coverage: float,
        rubric_score: float,
        structure_score: float,
    ) -> float:
        coverage_first_score = _clamp(
            0.50 * key_point_coverage
            + 0.30 * semantic_similarity
            + 0.15 * rubric_score
            + 0.05 * structure_score
        )
        return _clamp(max(weighted_score, coverage_first_score))

    def _rubric_score(
        self,
        rubric_output: dict[str, Any] | None,
        semantic_similarity: float,
        key_point_coverage: float,
    ) -> float:
        if isinstance(rubric_output, dict):
            for key in ["overall_score", "score"]:
                if rubric_output.get(key) is not None:
                    try:
                        return _clamp(float(rubric_output[key]))
                    except Exception:
                        pass
        return _clamp(0.55 * key_point_coverage + 0.45 * semantic_similarity)

    def _structure_score(
        self,
        answer: str,
        expected: str,
        key_points: list[str],
        concept_name: str | None,
    ) -> float:
        answer_tokens = _tokens(answer)
        expected_tokens = set(_tokens(expected))
        length_score = _clamp(len(answer_tokens) / 18.0)
        concept_terms = set(_tokens(concept_name or "")) | set().union(*(set(_tokens(point)) for point in key_points)) if key_points else set(_tokens(concept_name or ""))
        concept_hit = len(set(answer_tokens) & (concept_terms or expected_tokens)) / max(1, min(6, len(concept_terms or expected_tokens)))
        reason_markers = {"because", "so", "therefore", "for example", "example", "means", "used"}
        marker_score = 1.0 if any(marker in answer.lower() for marker in reason_markers) else 0.35
        return _clamp(0.40 * length_score + 0.35 * concept_hit + 0.25 * marker_score)

    def _confidence(self, final_score: float, components: list[float]) -> float:
        mean_component = sum(components) / len(components)
        variance = sum((value - mean_component) ** 2 for value in components) / len(components)
        agreement = 1.0 - min(1.0, math.sqrt(variance))
        distance = abs(final_score - 0.45) if final_score < 0.625 else abs(final_score - 0.80)
        return _clamp(0.65 * agreement + 0.35 * min(1.0, distance / 0.35))

    def _feedback(self, label: str, key_point_coverage: float, structure_score: float) -> str:
        if label == "strong":
            return "Strong answer: the response is semantically close to the reference and covers the key ideas."
        parts = []
        if key_point_coverage < 0.6:
            parts.append("Add more of the expected key points.")
        if structure_score < 0.5:
            parts.append("Explain the reasoning more clearly with a complete sentence or example.")
        if not parts:
            parts.append("The answer is partially correct but needs more precise detail.")
        return " ".join(parts)


def evaluate_semantic_answer(
    learner_answer: Any,
    expected_answer: Any = None,
    key_points: list[str] | None = None,
    concept_name: str | None = None,
    task_type: str = "explanation",
    rubric_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return SemanticAnswerEvaluator().evaluate(
        learner_answer=learner_answer,
        expected_answer=expected_answer,
        key_points=key_points,
        concept_name=concept_name,
        task_type=task_type,
        rubric_output=rubric_output,
    )
