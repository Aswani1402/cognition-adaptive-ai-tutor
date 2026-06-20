from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tutor.utils.sklearn_safe_loader import safe_model_call, safe_pickle_load


MODEL_PATH = Path("models/doubt/doubt_intent_classifier.pkl")
VECTORIZER_PATH = Path("models/doubt/doubt_intent_vectorizer.pkl")
META_PATH = Path("models/doubt/doubt_intent_meta.json")
CONFIDENCE_THRESHOLD = 0.55

ROUTE_BY_INTENT = {
    "concept_doubt": ("rag_concept_explanation", False, True),
    "syntax_doubt": ("syntax_help", True, True),
    "debug_doubt": ("debug_help", True, True),
    "output_prediction_doubt": ("trace_output_help", True, True),
    "example_request": ("example_generation", False, True),
    "difference_doubt": ("comparison_explanation", False, True),
    "real_world_request": ("real_world_application", False, True),
    "revision_doubt": ("revision_recap", False, True),
    "challenge_help": ("challenge_support", False, True),
    "next_step_doubt": ("adaptive_next_step", False, True),
    "low_confidence_doubt": ("supportive_reteach", False, True),
}


def _safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


class DoubtIntentClassifier:
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD) -> None:
        self.confidence_threshold = confidence_threshold
        self.model: Any | None = None
        self.vectorizer: Any | None = None
        self.meta: dict[str, Any] = {}
        self.model_metadata: dict[str, Any] = {}
        self.vectorizer_metadata: dict[str, Any] = {}

    def load(self) -> "DoubtIntentClassifier":
        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            model_loaded = safe_pickle_load(MODEL_PATH)
            vectorizer_loaded = safe_pickle_load(VECTORIZER_PATH)
            self.model = model_loaded["model"]
            self.vectorizer = vectorizer_loaded["model"]
            self.model_metadata = model_loaded["metadata"]
            self.vectorizer_metadata = vectorizer_loaded["metadata"]
        if META_PATH.exists():
            self.meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        return self

    def predict(
        self,
        doubt_text: str,
        concept_name: str | None = None,
        domain: str | None = None,
        code_context: str | None = None,
    ) -> dict[str, Any]:
        return self.classify(
            doubt_text=doubt_text,
            concept_name=concept_name,
            domain=domain,
            code_context=code_context,
        )

    def classify(
        self,
        doubt_text: str,
        concept_name: str | None = None,
        domain: str | None = None,
        code_context: str | None = None,
    ) -> dict[str, Any]:
        text = _safe_text(doubt_text)
        if not text:
            return self._result("low_confidence_doubt", 1.0, "empty_doubt_fallback", True)

        if self.model is None or self.vectorizer is None:
            try:
                self.load()
            except Exception:
                return self._fallback(text, code_context, reason="model_unavailable")

        try:
            transform_result = safe_model_call(
                self.vectorizer,
                VECTORIZER_PATH,
                lambda: self.vectorizer.transform([text]),
            )
            if not transform_result["ok"]:
                return self._fallback(text, code_context, reason=transform_result["metadata"].get("fallback_reason", "model_unavailable"))
            features = transform_result["value"]
            predict_result = safe_model_call(
                self.model,
                MODEL_PATH,
                lambda: self.model.predict(features),
            )
            if not predict_result["ok"]:
                return self._fallback(text, code_context, reason=predict_result["metadata"].get("fallback_reason", "model_unavailable"))
            predicted = str(predict_result["value"][0])
            confidence, top_intents = self._confidence(features)
            if confidence >= self.confidence_threshold:
                return self._result(predicted, confidence, self._runtime_method(), False, top_intents)
            fallback = self._fallback(text, code_context, reason="low_confidence")
            fallback["ml_intent"] = predicted
            fallback["ml_confidence"] = round(confidence, 6)
            fallback["top_intents"] = top_intents
            return fallback
        except Exception:
            return self._fallback(text, code_context, reason="prediction_error")

    def _confidence(self, features: Any) -> tuple[float, list[dict[str, Any]]]:
        if hasattr(self.model, "predict_proba"):
            proba_result = safe_model_call(
                self.model,
                MODEL_PATH,
                lambda: self.model.predict_proba(features),
            )
            if not proba_result["ok"]:
                return 0.0, []
            probs = proba_result["value"][0]
            classes = list(self.model.classes_)
            pairs = sorted(zip(classes, probs), key=lambda item: item[1], reverse=True)
            return float(pairs[0][1]), [
                {"intent": str(intent), "confidence": round(float(score), 6)}
                for intent, score in pairs[:5]
            ]
        if hasattr(self.model, "decision_function"):
            decision_result = safe_model_call(
                self.model,
                MODEL_PATH,
                lambda: self.model.decision_function(features),
            )
            if not decision_result["ok"]:
                return 0.0, []
            scores = decision_result["value"]
            values = scores[0] if hasattr(scores, "__len__") else [scores]
            classes = list(getattr(self.model, "classes_", []))
            exp_scores = [pow(2.718281828, float(value)) for value in values]
            total = sum(exp_scores) or 1.0
            pairs = sorted(zip(classes, [value / total for value in exp_scores]), key=lambda item: item[1], reverse=True)
            return float(pairs[0][1]), [
                {"intent": str(intent), "confidence": round(float(score), 6)}
                for intent, score in pairs[:5]
            ]
        return 0.0, []

    def _runtime_method(self) -> str:
        return str(self.meta.get("model_type") or "tfidf_logistic_regression")

    def _fallback(self, text: str, code_context: str | None, reason: str) -> dict[str, Any]:
        lowered = text.lower()
        intent = "concept_doubt"
        patterns = [
            (r"\b(error|debug|bug|wrong output|not working)\b", "debug_doubt"),
            (r"\b(print|output|trace|what will.*print)\b", "output_prediction_doubt"),
            (r"\b(syntax|invalid|tag syntax|2score)\b", "syntax_doubt"),
            (r"\b(example|show me|sample)\b", "example_request"),
            (r"\b(difference|compare|versus| vs )\b", "difference_doubt"),
            (r"\b(real project|real world|where.*use)\b", "real_world_request"),
            (r"\b(revise|recap|forgot|review)\b", "revision_doubt"),
            (r"\b(harder|challenge|problem)\b", "challenge_help"),
            (r"\b(next|after|study)\b", "next_step_doubt"),
            (r"\b(confused|don't know|not sure|understood)\b", "low_confidence_doubt"),
        ]
        for pattern, label in patterns:
            if re.search(pattern, lowered):
                intent = label
                break
        if code_context and intent == "concept_doubt":
            intent = "debug_doubt"
        result = self._result(intent, 0.45, f"fallback_{reason}", True)
        result["fallback_reason"] = reason
        return result

    def _result(
        self,
        intent: str,
        confidence: float,
        method: str,
        fallback_used: bool,
        top_intents: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        route, needs_code, needs_rag = ROUTE_BY_INTENT.get(intent, ROUTE_BY_INTENT["concept_doubt"])
        return {
            "status": "success",
            "module": "DoubtIntentClassifier",
            "intent": intent,
            "confidence": round(float(confidence), 6),
            "method": method,
            "needs_code_context": bool(needs_code),
            "needs_rag_context": bool(needs_rag),
            "recommended_route": route,
            "fallback_used": bool(fallback_used),
            "top_intents": top_intents or [{"intent": intent, "confidence": round(float(confidence), 6)}],
            "confidence_threshold": self.confidence_threshold,
        }
