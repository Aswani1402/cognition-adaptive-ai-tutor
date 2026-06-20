import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from tutor.utils.sklearn_safe_loader import (
    merge_model_metadata,
    safe_joblib_load,
    safe_model_call,
)


MODEL_DIR = Path("models/teaching_strategy")

DEFAULT_TEACHING_VIEW_MODEL = MODEL_DIR / "target_teaching_view_decision_tree.joblib"
DEFAULT_PROGRESSION_MODEL = MODEL_DIR / "target_progression_action_decision_tree.joblib"


FEATURE_COLUMNS = [
    "concept_id",
    "concept_name",

    "mastery_before",
    "behaviour_score",
    "wrong_rate",
    "slow_rate",
    "low_confidence_rate",
    "forgetting_priority",
    "evaluation_score",
    "view_reward",
    "adaptive_path_score",

    "final_strategy",
    "difficulty",
    "assessment_difficulty",
    "evaluation_verdict",
    "behavior_label",
    "policy_strategy",
    "policy_difficulty",

    "assessment_type_count",
    "fallback_view_count",
    "weak_type_count",

    "has_debug_weakness",
    "has_output_prediction_weakness",
    "has_syntax_weakness",
    "has_transfer_weakness",
    "has_explanation_weakness",
    "has_mcq_weakness",

    "xai_mastery_need",
    "xai_evaluation_need",
    "xai_view_reward_need",
    "xai_forgetting_need",
    "xai_behaviour_risk",
    "xai_mastery_strength",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_json(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _extract_policy_data(policy_output: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(policy_output, dict):
        return {}

    return policy_output.get("data", policy_output)


def _extract_behaviour_data(behaviour_state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(behaviour_state, dict):
        return {}

    data = behaviour_state.get("data", behaviour_state)

    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data.get("data", {})

    return data if isinstance(data, dict) else {}


def _extract_evaluation_score(evaluation_output: Dict[str, Any]) -> float:
    if not isinstance(evaluation_output, dict):
        return 0.5

    return _safe_float(
        evaluation_output.get("overall_score", evaluation_output.get("score", 0.5)),
        0.5,
    )


def _extract_evaluation_verdict(evaluation_output: Dict[str, Any]) -> str:
    if not isinstance(evaluation_output, dict):
        return "unknown"

    return str(evaluation_output.get("verdict", "unknown"))


def _extract_weak_types(evaluation_output: Dict[str, Any], learner_notebook_memory_output: Dict[str, Any]) -> List[str]:
    weak = []

    if isinstance(evaluation_output, dict):
        for item in evaluation_output.get("results", []):
            score = _safe_float(item.get("score"), 0.0)
            assessment_type = item.get("assessment_type")

            if assessment_type and score < 0.75:
                weak.append(str(assessment_type))

        feedback_summary = str(evaluation_output.get("feedback_summary", "")).lower()

        if not weak:
            if "debug" in feedback_summary:
                weak.append("debug")
            if "output" in feedback_summary:
                weak.append("output_prediction")
            if "syntax" in feedback_summary:
                weak.append("syntax_completion")
            if "transfer" in feedback_summary:
                weak.append("transfer")

    if isinstance(learner_notebook_memory_output, dict):
        for item in learner_notebook_memory_output.get("weak_assessment_types", []):
            weak.append(str(item))

    return _unique(weak)


def _unique(items: List[str]) -> List[str]:
    seen = set()
    output = []

    for item in items:
        key = str(item).lower().strip()
        if not key:
            continue
        if key not in seen:
            output.append(str(item))
            seen.add(key)

    return output


def _extract_view_reward(view_performance_output: Dict[str, Any]) -> float:
    if not isinstance(view_performance_output, dict):
        return 0.5

    logged = view_performance_output.get("logged", {})

    return _safe_float(
        logged.get("reward", view_performance_output.get("reward", 0.5)),
        0.5,
    )


def _extract_mastery(knowledge_state: Dict[str, Any]) -> float:
    if not isinstance(knowledge_state, dict):
        return 0.5

    try:
        return _safe_float(
            knowledge_state.get("data", {}).get("data", {}).get("predicted_mastery_last"),
            0.5,
        )
    except Exception:
        return 0.5


def _extract_forgetting_priority(forgetting_state: Dict[str, Any], concept_id: str) -> float:
    if not isinstance(forgetting_state, dict):
        return 0.0

    data = forgetting_state.get("data", {})
    priority = data.get("review_priority", {})

    if isinstance(priority, dict):
        return _safe_float(priority.get(str(concept_id), 0.0), 0.0)

    return 0.0


def _extract_adaptive_score(adaptive_path_output: Dict[str, Any]) -> float:
    if not isinstance(adaptive_path_output, dict):
        return 0.0

    return _safe_float(adaptive_path_output.get("selected_score", 0.0), 0.0)


def _extract_xai_flags(xai_output: Dict[str, Any]) -> Dict[str, int]:
    factors = []

    if isinstance(xai_output, dict):
        evidence = xai_output.get("data", {}).get("evidence", {})
        feature_contributions = evidence.get("feature_contributions", {})

        for item in feature_contributions.get("top_factors", []):
            if isinstance(item, dict) and item.get("feature"):
                factors.append(str(item.get("feature")))

    factor_set = set(factors)

    return {
        "xai_mastery_need": int("mastery_need" in factor_set),
        "xai_evaluation_need": int("evaluation_need" in factor_set),
        "xai_view_reward_need": int("view_reward_need" in factor_set),
        "xai_forgetting_need": int("forgetting_need" in factor_set),
        "xai_behaviour_risk": int("behaviour_risk" in factor_set),
        "xai_mastery_strength": int("mastery_strength" in factor_set),
    }


def _difficulty_from_policy(policy_output: Dict[str, Any]) -> str:
    policy_data = _extract_policy_data(policy_output)
    difficulty = str(policy_data.get("difficulty", "medium")).lower()

    if difficulty == "difficult":
        return "hard"

    if difficulty in {"easy", "medium", "hard"}:
        return difficulty

    return "medium"


def _strategy_from_policy(policy_output: Dict[str, Any]) -> str:
    policy_data = _extract_policy_data(policy_output)
    return str(policy_data.get("strategy", "practice")).lower()


def _assessment_types_for_view(teaching_view: str, weak_types: List[str]) -> List[str]:
    view_map = {
        "definition_view": ["mcq", "short_explanation"],
        "syntax_view": ["syntax_completion", "mcq"],
        "step_by_step_view": ["mcq", "short_explanation"],
        "analogy_view": ["short_explanation", "mcq"],
        "code_view": ["output_prediction", "short_explanation"],
        "debug_view": ["debug", "output_prediction"],
        "misconception_view": ["mcq", "debug"],
        "challenge_view": ["debug", "transfer", "code_writing"],
        "transfer_view": ["transfer", "short_explanation"],
        "revision_view": ["mcq", "flashcard_recall"],
        "flashcard_view": ["flashcard_recall", "mcq"],
    }

    selected = list(view_map.get(teaching_view, ["mcq", "short_explanation"]))

    for weak in weak_types:
        if weak not in selected:
            selected.append(weak)

    return selected[:4]


def _fallback_views_for(teaching_view: str) -> List[str]:
    fallback_map = {
        "definition_view": ["step_by_step_view", "analogy_view", "code_view", "revision_view"],
        "step_by_step_view": ["analogy_view", "code_view", "revision_view"],
        "analogy_view": ["definition_view", "step_by_step_view", "code_view"],
        "code_view": ["debug_view", "step_by_step_view", "misconception_view"],
        "debug_view": ["code_view", "misconception_view", "step_by_step_view", "revision_view"],
        "misconception_view": ["step_by_step_view", "code_view", "revision_view"],
        "challenge_view": ["transfer_view", "debug_view", "code_view"],
        "transfer_view": ["challenge_view", "code_view", "debug_view"],
        "revision_view": ["flashcard_view", "definition_view"],
        "flashcard_view": ["revision_view", "definition_view"],
        "syntax_view": ["step_by_step_view", "code_view", "debug_view"],
    }

    return fallback_map.get(teaching_view, ["step_by_step_view", "revision_view"])


def _next_activity_for(teaching_view: str, weak_types: List[str]) -> str:
    weak_set = set(weak_types)

    if teaching_view == "debug_view" or "debug" in weak_set:
        return "short code tracing and debugging practice"

    if teaching_view == "code_view" or "output_prediction" in weak_set:
        return "guided output prediction practice"

    if teaching_view == "syntax_view" or "syntax_completion" in weak_set:
        return "syntax completion and small code correction"

    if teaching_view == "transfer_view" or "transfer" in weak_set:
        return "real-world transfer question"

    if teaching_view == "challenge_view":
        return "challenge problem with feedback"

    if teaching_view == "definition_view":
        return "basic concept check with simple MCQ or short explanation"

    if teaching_view == "step_by_step_view":
        return "step-by-step guided concept check"

    return "matched practice for current teaching view"


def _predict_with_confidence(model: Any, X: pd.DataFrame) -> Dict[str, Any]:
    prediction = model.predict(X)[0]

    confidence = None
    probabilities = None

    if hasattr(model, "predict_proba"):
        try:
            probs = model.predict_proba(X)[0]
            classes = list(model.classes_)

            probabilities = {
                str(label): round(float(prob), 4)
                for label, prob in zip(classes, probs)
            }
            confidence = round(float(max(probs)), 4)
        except Exception:
            pass

    return {
        "prediction": str(prediction),
        "confidence": confidence,
        "probabilities": probabilities,
    }


def _safe_predict_with_confidence(model: Any, X: pd.DataFrame, model_path: Path) -> Dict[str, Any]:
    pred_result = safe_model_call(model, model_path, lambda: model.predict(X))
    if not pred_result["ok"]:
        raise RuntimeError(pred_result["metadata"].get("error_message") or pred_result["metadata"].get("fallback_reason"))
    prediction = pred_result["value"][0]

    confidence = None
    probabilities = None
    if hasattr(model, "predict_proba"):
        proba_result = safe_model_call(model, model_path, lambda: model.predict_proba(X))
        if proba_result["ok"]:
            probs = proba_result["value"][0]
            classes = list(model.classes_)
            probabilities = {
                str(label): round(float(prob), 4)
                for label, prob in zip(classes, probs)
            }
            confidence = round(float(max(probs)), 4)

    return {
        "prediction": str(prediction),
        "confidence": confidence,
        "probabilities": probabilities,
    }


class ModelBasedTeachingStrategySelector:
    def __init__(
        self,
        teaching_view_model_path: Path = DEFAULT_TEACHING_VIEW_MODEL,
        progression_model_path: Path = DEFAULT_PROGRESSION_MODEL,
    ) -> None:
        self.teaching_view_model_path = Path(teaching_view_model_path)
        self.progression_model_path = Path(progression_model_path)

        self.teaching_view_model = None
        self.progression_model = None
        self.teaching_view_model_metadata = {}
        self.progression_model_metadata = {}
        self.model_metadata = {}

        self._load_models()

    def _load_models(self) -> None:
        if self.teaching_view_model_path.exists():
            loaded = safe_joblib_load(self.teaching_view_model_path)
            self.teaching_view_model = loaded["model"]
            self.teaching_view_model_metadata = loaded["metadata"]

        if self.progression_model_path.exists():
            loaded = safe_joblib_load(self.progression_model_path)
            self.progression_model = loaded["model"]
            self.progression_model_metadata = loaded["metadata"]

        self.model_metadata = merge_model_metadata(
            self.teaching_view_model_metadata,
            self.progression_model_metadata,
        )

    def is_ready(self) -> bool:
        return self.teaching_view_model is not None and self.progression_model is not None

    def build_feature_row(
        self,
        learner_id: str,
        concept_id: str,
        concept_name: str,
        policy_output: Dict[str, Any],
        evaluation_output: Dict[str, Any],
        behaviour_state: Dict[str, Any],
        view_performance_output: Dict[str, Any],
        learner_notebook_memory_output: Dict[str, Any],
        xai_output: Dict[str, Any],
        adaptive_path_output: Dict[str, Any],
        knowledge_state: Optional[Dict[str, Any]] = None,
        forgetting_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        policy_data = _extract_policy_data(policy_output)
        behaviour_data = _extract_behaviour_data(behaviour_state)

        difficulty = _difficulty_from_policy(policy_output)
        strategy = _strategy_from_policy(policy_output)

        weak_types = _extract_weak_types(
            evaluation_output=evaluation_output,
            learner_notebook_memory_output=learner_notebook_memory_output,
        )

        mastery = _extract_mastery(knowledge_state or {})
        forgetting_priority = _extract_forgetting_priority(forgetting_state or {}, concept_id)

        assessment_types = _assessment_types_for_view("debug_view" if "debug" in weak_types else "code_view", weak_types)
        fallback_views = _fallback_views_for("debug_view" if "debug" in weak_types else "code_view")

        xai_flags = _extract_xai_flags(xai_output)

        row = {
            "concept_id": str(concept_id),
            "concept_name": str(concept_name),

            "mastery_before": mastery,
            "behaviour_score": _safe_float(
                behaviour_data.get("behavior_score", behaviour_data.get("behaviour_score", 0.5)),
                0.5,
            ),
            "wrong_rate": _safe_float(behaviour_data.get("wrong_rate", 0.0), 0.0),
            "slow_rate": _safe_float(behaviour_data.get("slow_rate", 0.0), 0.0),
            "low_confidence_rate": _safe_float(behaviour_data.get("low_confidence_rate", 0.0), 0.0),
            "forgetting_priority": forgetting_priority,
            "evaluation_score": _extract_evaluation_score(evaluation_output),
            "view_reward": _extract_view_reward(view_performance_output),
            "adaptive_path_score": _extract_adaptive_score(adaptive_path_output),

            "final_strategy": strategy,
            "difficulty": difficulty,
            "assessment_difficulty": difficulty,
            "evaluation_verdict": _extract_evaluation_verdict(evaluation_output),
            "behavior_label": str(
                behaviour_data.get("behavior_label", behaviour_data.get("behaviour_label", "unknown"))
            ),
            "policy_strategy": str(policy_data.get("strategy", strategy)),
            "policy_difficulty": str(policy_data.get("difficulty", difficulty)),

            "assessment_type_count": len(assessment_types),
            "fallback_view_count": len(fallback_views),
            "weak_type_count": len(weak_types),

            "has_debug_weakness": int("debug" in weak_types),
            "has_output_prediction_weakness": int("output_prediction" in weak_types),
            "has_syntax_weakness": int("syntax_completion" in weak_types or "syntax" in weak_types),
            "has_transfer_weakness": int("transfer" in weak_types),
            "has_explanation_weakness": int(
                "short_explanation" in weak_types or "explanation" in weak_types
            ),
            "has_mcq_weakness": int("mcq" in weak_types),
        }

        row.update(xai_flags)

        return row

    def predict(
        self,
        learner_id: str,
        concept_id: str,
        concept_name: str,
        policy_output: Dict[str, Any],
        evaluation_output: Dict[str, Any],
        behaviour_state: Dict[str, Any],
        view_performance_output: Dict[str, Any],
        learner_notebook_memory_output: Dict[str, Any],
        xai_output: Dict[str, Any],
        adaptive_path_output: Dict[str, Any],
        knowledge_state: Optional[Dict[str, Any]] = None,
        forgetting_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if not self.is_ready():
            teaching_view = "revision_view"
            progression_action = "stay_same_level"
            return {
                "status": "success",
                "module": "ModelBasedTeachingStrategySelector",
                "reason": "Model files are missing or version-incompatible; rule fallback used for comparison metadata.",
                "teaching_view_model_path": str(self.teaching_view_model_path),
                "progression_model_path": str(self.progression_model_path),
                "model_teaching_view": teaching_view,
                "model_progression_action": progression_action,
                "progression_model_status": self.model_metadata.get("model_status", "unavailable_version_mismatch"),
                "progression_model_reason": "Fallback used because sklearn model artifacts are unavailable or version-incompatible.",
                "teaching_view_confidence": 0.0,
                "progression_confidence": 0.0,
                "teaching_view_probabilities": {},
                "progression_probabilities": {},
                "model_loaded": False,
                "fallback_used": True,
                "fallback_reason": self.model_metadata.get("fallback_reason", "model_unavailable"),
                "current_sklearn_version": self.model_metadata.get("current_sklearn_version"),
                "warning_count": self.model_metadata.get("warning_count", 0),
                "recommendation": self.model_metadata.get("recommendation", "retrain_or_resave_model_with_current_sklearn"),
            }

        feature_row = self.build_feature_row(
            learner_id=learner_id,
            concept_id=concept_id,
            concept_name=concept_name,
            policy_output=policy_output,
            evaluation_output=evaluation_output,
            behaviour_state=behaviour_state,
            view_performance_output=view_performance_output,
            learner_notebook_memory_output=learner_notebook_memory_output,
            xai_output=xai_output,
            adaptive_path_output=adaptive_path_output,
            knowledge_state=knowledge_state,
            forgetting_state=forgetting_state,
        )

        X = pd.DataFrame([feature_row], columns=FEATURE_COLUMNS)

        try:
            teaching_view_pred = _safe_predict_with_confidence(self.teaching_view_model, X, self.teaching_view_model_path)
            progression_pred = _safe_predict_with_confidence(self.progression_model, X, self.progression_model_path)
        except Exception:
            teaching_view_pred = {"prediction": "revision_view", "confidence": 0.0, "probabilities": {}}
            progression_pred = {"prediction": "stay_same_level", "confidence": 0.0, "probabilities": {}}
            self.model_metadata = {
                **self.model_metadata,
                "model_status": "unavailable_runtime_error",
                "model_loaded": False,
                "fallback_used": True,
                "fallback_reason": "model_prediction_error",
                "recommendation": "retrain_or_resave_model_with_current_sklearn",
            }

        teaching_view = teaching_view_pred["prediction"]
        progression_action = progression_pred["prediction"]

        weak_types = _extract_weak_types(
            evaluation_output=evaluation_output,
            learner_notebook_memory_output=learner_notebook_memory_output,
        )

        policy_data = _extract_policy_data(policy_output)
        difficulty = _difficulty_from_policy(policy_output)

        assessment_types = _assessment_types_for_view(teaching_view, weak_types)
        fallback_views = _fallback_views_for(teaching_view)
        next_activity = _next_activity_for(teaching_view, weak_types)

        return {
            "status": "success",
            "module": "ModelBasedTeachingStrategySelector",
            "learner_id": str(learner_id),
            "concept_id": str(concept_id),
            "concept_name": str(concept_name),

            "model_teaching_view": teaching_view,
            "model_progression_action": progression_action,
            "progression_model_status": "experimental_not_used",
            "progression_model_reason": (
                "Progression model is currently logged for comparison only. "
                "It is not used for final progression decisions because agreement with "
                "the evidence-aware selector is still low."
            ),
            "progression_model_status": "experimental_not_used",

            "teaching_view_confidence": teaching_view_pred.get("confidence"),
            "progression_confidence": progression_pred.get("confidence"),

            "teaching_view_probabilities": teaching_view_pred.get("probabilities"),
            "progression_probabilities": progression_pred.get("probabilities"),

            "difficulty": difficulty,
            "final_strategy": str(policy_data.get("strategy", "practice")),
            "assessment_difficulty": difficulty,
            "assessment_types": assessment_types,
            "fallback_views": fallback_views,
            "next_activity": next_activity,

            "feature_row": feature_row,
            "model_paths": {
                "teaching_view": str(self.teaching_view_model_path),
                "progression": str(self.progression_model_path),
            },
            "model_status": self.model_metadata.get("model_status", "available"),
            "model_loaded": not bool(self.model_metadata.get("fallback_used")),
            "fallback_used": bool(self.model_metadata.get("fallback_used")),
            "fallback_reason": self.model_metadata.get("fallback_reason"),
            "current_sklearn_version": self.model_metadata.get("current_sklearn_version"),
            "warning_count": self.model_metadata.get("warning_count", 0),
            "recommendation": self.model_metadata.get("recommendation", "model_available"),
            "reason": (
                f"Model predicted teaching_view={teaching_view} "
                f"and progression_action={progression_action} from learner evidence."
            ),


        }
