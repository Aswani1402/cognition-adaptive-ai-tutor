"""
FeatureContributionExplainer

Purpose:
- Upgrade XAI from simple explanation text to feature contribution reasoning.
- Shows which learner/system evidence influenced the final decision most.
- Works now with transparent weighted contribution.
- Later can be replaced/extended with trained RandomForest / LogisticRegression / SHAP.

Current features:
- mastery_score
- behaviour_score / behaviour_risk
- forgetting_priority
- evaluation_need
- view_reward_need
- adaptive_path_confidence
- bridge_override_signal
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


class FeatureContributionExplainer:
    def __init__(self) -> None:
        self.weights = {
            "mastery_need": 0.22,
            "behaviour_risk": 0.15,
            "forgetting_need": 0.18,
            "evaluation_need": 0.22,
            "view_reward_need": 0.13,
            "adaptive_path_confidence": 0.07,
            "bridge_override_signal": 0.03,
        }

    def explain(
        self,
        knowledge_state: Dict[str, Any],
        behaviour_state: Dict[str, Any],
        forgetting_state: Dict[str, Any],
        evaluation_output: Dict[str, Any],
        view_performance_output: Dict[str, Any],
        adaptive_path_output: Dict[str, Any],
        adaptive_policy_bridge_output: Dict[str, Any],
    ) -> Dict[str, Any]:

        features = self._extract_features(
            knowledge_state=knowledge_state,
            behaviour_state=behaviour_state,
            forgetting_state=forgetting_state,
            evaluation_output=evaluation_output,
            view_performance_output=view_performance_output,
            adaptive_path_output=adaptive_path_output,
            adaptive_policy_bridge_output=adaptive_policy_bridge_output,
        )

        contributions = []

        for feature_name, value in features.items():
            weight = self.weights.get(feature_name, 0.0)
            contribution = round(value * weight, 4)

            contributions.append(
                {
                    "feature": feature_name,
                    "value": round(value, 4),
                    "weight": weight,
                    "contribution": contribution,
                    "meaning": self._feature_meaning(feature_name, value),
                }
            )

        contributions = sorted(
            contributions,
            key=lambda item: item["contribution"],
            reverse=True,
        )

        total_pressure = round(sum(item["contribution"] for item in contributions), 4)

        if total_pressure >= 0.65:
            decision_pressure = "high_support_needed"
        elif total_pressure >= 0.40:
            decision_pressure = "moderate_support_needed"
        else:
            decision_pressure = "low_support_needed"

        return {
            "status": "success",
            "module": "FeatureContributionExplainer",
            "features": features,
            "ranked_contributions": contributions,
            "total_decision_pressure": total_pressure,
            "decision_pressure_label": decision_pressure,
            "top_factors": contributions[:3],
            "summary": self._build_summary(contributions[:3], decision_pressure),
        }

    def _extract_features(
        self,
        knowledge_state: Dict[str, Any],
        behaviour_state: Dict[str, Any],
        forgetting_state: Dict[str, Any],
        evaluation_output: Dict[str, Any],
        view_performance_output: Dict[str, Any],
        adaptive_path_output: Dict[str, Any],
        adaptive_policy_bridge_output: Dict[str, Any],
    ) -> Dict[str, float]:

        mastery = self._nested_float(
            knowledge_state,
            ["data", "data", "predicted_mastery_last"],
            default=0.5,
        )
        mastery_need = self._clamp(1.0 - mastery)

        behaviour_data = behaviour_state.get("data", {}) if isinstance(behaviour_state, dict) else {}
        if isinstance(behaviour_data.get("data"), dict):
            behaviour_data = behaviour_data.get("data", {})

        behaviour_score = self._safe_float(
            behaviour_data.get("behavior_score", behaviour_data.get("behaviour_score", 0.5)),
            0.5,
        )

        wrong_rate = self._safe_float(behaviour_data.get("wrong_rate"), 0.0)
        slow_rate = self._safe_float(behaviour_data.get("slow_rate"), 0.0)
        low_confidence_rate = self._safe_float(behaviour_data.get("low_confidence_rate"), 0.0)
        hint_rate = self._safe_float(behaviour_data.get("hint_rate"), 0.0)

        behaviour_risk = self._clamp(
            0.40 * (1.0 - behaviour_score)
            + 0.25 * wrong_rate
            + 0.15 * slow_rate
            + 0.15 * low_confidence_rate
            + 0.05 * hint_rate
        )

        review_priority = forgetting_state.get("data", {}).get("review_priority", {})
        if isinstance(review_priority, dict) and review_priority:
            forgetting_need = max(
                self._safe_float(value, 0.0)
                for value in review_priority.values()
            )
        else:
            forgetting_need = 0.0

        evaluation_score = self._safe_float(
            evaluation_output.get("overall_score", evaluation_output.get("score", 0.5)),
            0.5,
        )
        evaluation_need = self._clamp(1.0 - evaluation_score)

        view_reward = 0.5
        try:
            view_reward = self._safe_float(
                view_performance_output.get("logged", {}).get("reward"),
                0.5,
            )
        except Exception:
            view_reward = 0.5

        view_reward_need = self._clamp(1.0 - view_reward)

        adaptive_path_confidence = self._safe_float(
            adaptive_path_output.get("selected_score"),
            0.0,
        )

        bridge_override_signal = 1.0 if adaptive_policy_bridge_output.get("override_allowed") else 0.0

        return {
            "mastery_need": self._clamp(mastery_need),
            "behaviour_risk": self._clamp(behaviour_risk),
            "forgetting_need": self._clamp(forgetting_need),
            "evaluation_need": self._clamp(evaluation_need),
            "view_reward_need": self._clamp(view_reward_need),
            "adaptive_path_confidence": self._clamp(adaptive_path_confidence),
            "bridge_override_signal": self._clamp(bridge_override_signal),
        }

    def _feature_meaning(self, feature_name: str, value: float) -> str:
        if feature_name == "mastery_need":
            return "Higher value means learner mastery is weaker and more support is needed."
        if feature_name == "behaviour_risk":
            return "Higher value means learner behaviour suggests confusion, wrong attempts, slowness, or low confidence."
        if feature_name == "forgetting_need":
            return "Higher value means forgetting/review priority is stronger."
        if feature_name == "evaluation_need":
            return "Higher value means recent assessment performance is weaker."
        if feature_name == "view_reward_need":
            return "Higher value means the selected teaching view did not work strongly."
        if feature_name == "adaptive_path_confidence":
            return "Higher value means adaptive path strongly recommends its selected concept."
        if feature_name == "bridge_override_signal":
            return "Value 1 means the bridge marked adaptive override as allowed."
        return "Feature used in decision explanation."

    def _build_summary(
        self,
        top_factors: List[Dict[str, Any]],
        decision_pressure: str,
    ) -> str:
        if not top_factors:
            return f"Decision pressure is {decision_pressure}, but no major factors were found."

        factor_names = [item["feature"] for item in top_factors]

        return (
            f"Decision pressure is {decision_pressure}. "
            f"The strongest contributing factors were: {', '.join(factor_names)}."
        )

    def _nested_float(
        self,
        data: Dict[str, Any],
        path: List[str],
        default: float,
    ) -> float:
        current: Any = data

        try:
            for key in path:
                if not isinstance(current, dict):
                    return default
                current = current.get(key)

            return self._safe_float(current, default)
        except Exception:
            return default

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))