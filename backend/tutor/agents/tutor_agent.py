from __future__ import annotations

from typing import Any, Dict, List, Optional

from tutor.generation.adaptive_content_generator import generate_content_bundle
from tutor.generation.generation_policy import GenerationPolicy
from tutor.generation.explanation_variant_engine import ExplanationVariantEngine
from tutor.generation.multi_view_generator import MultiViewGenerator

GENERATION_STRATEGY_MAP = {
    "remedial": "weak_learner",
    "practice": "example_first",
    "advanced": "advanced_learner",
    "guided_practice": "step_by_step",
    "challenge": "advanced_learner",
    "revision": "revision_summary",
}


class TutorAgent:
    def __init__(self, default_plan: Optional[List[Dict[str, str]]] = None) -> None:
        self.default_plan = default_plan or [
            {"content_type": "teaching", "strategy": "definition_first"},
            {"content_type": "teaching", "strategy": "example_first"},
            {"content_type": "teaching", "strategy": "step_by_step"},
            {"content_type": "revision", "strategy": "revision_summary"},
            {"content_type": "flashcard", "strategy": "revision_summary"},
        ]

        self.gen_policy = GenerationPolicy()
        self.explainer = ExplanationVariantEngine()
        self.multi_view_generator = MultiViewGenerator()
    def build_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mastery_score": context.get("mastery_score", 0.5),
            "behavior_score": context.get("behavior_score", 0.5),
            "time_taken": context.get("time_taken", 20),
            "confidence": context.get("confidence", 2),
            "hint_used": context.get("hint_used", 0),
        }

    def _extract_decision_field(
        self,
        context: Dict[str, Any],
        key: str,
        default: Any,
    ) -> Any:
        """
        Supports both:
        context["explanation_mode"]
        context["decision_output"]["policy_output"]["data"]["explanation_mode"]
        """

        if key in context and context.get(key) is not None:
            return context.get(key)

        decision_output = context.get("decision_output", {})
        if isinstance(decision_output, dict):
            policy_data = (
                decision_output
                .get("policy_output", {})
                .get("data", {})
            )

            if isinstance(policy_data, dict) and policy_data.get(key) is not None:
                return policy_data.get(key)

            if decision_output.get(key) is not None:
                return decision_output.get(key)

        return default

    def run(
        self,
        concept_resource: Dict[str, Any],
        learner_id: Optional[str] = None,
        difficulty: str = "medium",
        requested_plan: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        context = context or {}
        plan = requested_plan or self.default_plan
        state = self.build_state(context)
        concept_resource = dict(concept_resource)

        if "concept_id" not in concept_resource or not concept_resource.get("concept_id"):
            concept_resource["concept_id"] = (
                concept_resource.get("system_concept_id")
                or concept_resource.get("content_concept_id")
                or "unknown"
            )

        explanation_mode = self._extract_decision_field(
            context=context,
            key="explanation_mode",
            default="simple",
        )

        difficulty = self._extract_decision_field(
            context=context,
            key="difficulty",
            default=difficulty,
        )

        strategy = self._extract_decision_field(
            context=context,
            key="strategy",
            default="practice",
        )

        gen_output = None

        if self.gen_policy.is_available():
            gen_output = self.gen_policy.predict(state)

            if gen_output:
                model_difficulty = gen_output.get("difficulty")
                raw_strategy = gen_output.get("strategy", strategy)

                # Policy wins. Model only fills if missing.
                if not difficulty:
                    difficulty = model_difficulty or "medium"

                generator_strategy = GENERATION_STRATEGY_MAP.get(
                    raw_strategy,
                    "definition_first",
                )

                plan = [
                    {"content_type": "teaching", "strategy": generator_strategy},
                    {"content_type": "teaching", "strategy": "example_first"},
                    {"content_type": "teaching", "strategy": "step_by_step"},
                    {"content_type": "revision", "strategy": "revision_summary"},
                    {"content_type": "flashcard", "strategy": "revision_summary"},
                ]

        content_output = generate_content_bundle(
            concept_resource=concept_resource,
            learner_id=learner_id,
            difficulty=difficulty,
            requested_plan=plan,
        )

        explanation_output = self.explainer.generate(
            concept_resource=concept_resource,
            mode=explanation_mode,
            difficulty=difficulty,
            learner_state=state,
        )

        if isinstance(content_output, dict):
            content_output["adaptive_explanation"] = str(
                explanation_output.get("explanation") or ""
            ).strip()
            content_output["explanation_mode"] = explanation_mode
            content_output["explanation_engine_output"] = explanation_output

            # Make ExplanationVariantEngine output the primary teaching body
            items = content_output.get("items", [])
            adaptive_explanation = content_output.get("adaptive_explanation", "")

            if items and adaptive_explanation:
                items[0]["body"] = adaptive_explanation
                items[0].setdefault("metadata", {})
                items[0]["metadata"]["explanation_mode"] = explanation_mode
                items[0]["metadata"]["source"] = "adaptive_generation"

                if len(items) > 1:
                    items[1].setdefault("metadata", {})
                    items[1]["metadata"]["variant"] = "supporting_example"

        multi_view_output = self.multi_view_generator.generate(
            concept_resource={
                "concept_id": concept_resource.get("concept_id"),
                "topic": (
                    concept_resource.get("topic")
                    or concept_resource.get("concept_name")
                    or concept_resource.get("name")
                    or "Unknown Concept"
                ),
                "base_content": (
                    concept_resource.get("base_content")
                    or concept_resource.get("content")
                    or concept_resource.get("description")
                    or (
                        content_output.get("adaptive_explanation", "")
                        if isinstance(content_output, dict)
                        else ""
                    )
                ),
                "examples": concept_resource.get("examples", ""),
                "key_points": concept_resource.get("key_points", ""),
                "misconceptions": concept_resource.get("misconceptions", ""),
                "real_world_use": concept_resource.get("real_world_use", ""),
                "next_concept_link": concept_resource.get("next_concept_link", ""),
            },
            learner_profile={
                "learner_id": learner_id,
                "mastery": context.get("mastery_score", 0.5),
                "behaviour_label": context.get(
                    "behavior_label",
                    context.get("behaviour_label", ""),
                ),
            },
            difficulty=difficulty,
        )

        if isinstance(content_output, dict):
            content_output["multi_view_output"] = multi_view_output
            content_output["recommended_view"] = multi_view_output.get("recommended_view")
            content_output["available_views"] = multi_view_output.get("available_views")
            content_output["views"] = multi_view_output.get("views")

        return {
            "status": "success",
            "agent": "TutorAgent",
            "data": content_output,
            "generation_policy_output": gen_output,
            "used_plan": plan,
            "used_difficulty": difficulty,
            "used_strategy": strategy,
            "explanation_mode": explanation_mode,
            "multi_view_output": multi_view_output,
            "recommended_view": multi_view_output.get("recommended_view"),
            "available_views": multi_view_output.get("available_views"),
            "views": multi_view_output.get("views"),
        }


if __name__ == "__main__":
    sample_resource = {
        "system_concept_id": "1",
        "content_concept_id": "P1",
        "topic": "Python Variables",
        "content": "Variables are names used to store values in memory.",
        "examples": "x = 10\nname = 'Aswani'",
        "key_points": "Variables store data. They can change. Names should be meaningful.",
        "misconceptions": "A variable is not the value itself; it is a name pointing to a value.",
    }

    agent = TutorAgent()

    output = agent.run(
        concept_resource=sample_resource,
        learner_id="LNR-DEMO-SAMPLE",
        difficulty="easy",
        context={
            "mastery_score": 0.3,
            "behavior_score": 0.7,
            "confidence": 0.3,
            "explanation_mode": "step_by_step",
            "strategy": "guided_practice",
        },
    )

    print(output)
