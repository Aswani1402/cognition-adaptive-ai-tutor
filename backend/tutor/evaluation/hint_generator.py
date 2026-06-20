from __future__ import annotations

import re
from typing import Any


class HintGenerator:
    """Creates learner-facing hint text for an already selected hint type."""

    def generate(self, hint_type: str, evidence: dict[str, Any] | None = None) -> str:
        evidence = evidence or {}
        concept = self._clean(evidence.get("concept_name")) or "this concept"
        question_type = self._clean(evidence.get("question_type")) or "question"
        mistake_type = self._clean(evidence.get("mistake_type")) or "the current mistake"
        weakest_skill = self._clean(evidence.get("weakest_skill")) or "the key skill"
        teaching_view = self._clean(evidence.get("teaching_view")) or "the lesson view"
        key_points = self._list(evidence.get("key_points"))
        example = self._clean(evidence.get("example"))

        main_point = key_points[0] if key_points else f"focus on the rule for {concept}"

        if hint_type == "small_hint":
            return (
                f"Look again at {concept}. Pay attention to this idea: {main_point}. "
                "What part of the question points to that rule?"
            )

        if hint_type == "guided_hint":
            return (
                f"Try this in two steps. First, identify what the {question_type} is asking about {concept}. "
                f"Next, use this clue: {main_point}. What would change in your answer?"
            )

        if hint_type == "worked_example":
            sample = example or f"For a similar {concept} question, start with the rule, then apply it to one small value."
            return (
                f"Here is a similar worked example, not the exact answer. {sample} "
                f"Now use the same pattern for this {question_type}."
            )

        if hint_type == "misconception_hint":
            return (
                f"This looks like a misconception about {concept}. Check whether you are mixing up {mistake_type} "
                f"with the actual rule: {main_point}. Which belief should you correct first?"
            )

        if hint_type == "debug_hint":
            return (
                f"For this debug task, do not rewrite everything. Look near the line where {weakest_skill} is used. "
                "What is the first statement that could cause the bug?"
            )

        if hint_type == "output_prediction_hint":
            return (
                f"For output prediction, trace {concept} one step at a time. Write each variable value after every line. "
                "What value changes just before the print or final output?"
            )

        if hint_type == "syntax_hint":
            return (
                f"This is likely a syntax rule issue in {concept}. Check the exact symbols, order, and spacing expected by Python. "
                "Which part breaks the syntax pattern?"
            )

        return (
            f"Next, return to {teaching_view} for {concept}. Use the main idea: {main_point}. "
            "What is the smallest next step you can try?"
        )

    def _clean(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip().replace("_", " ")
        return re.sub(r"\s+", " ", text)

    def _list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._clean(item) for item in value if self._clean(item)]
        if isinstance(value, str):
            if "|" in value:
                return [self._clean(item) for item in value.split("|") if self._clean(item)]
            if "\n" in value:
                return [self._clean(item) for item in value.splitlines() if self._clean(item)]
            return [self._clean(value)] if self._clean(value) else []
        return [self._clean(value)] if self._clean(value) else []
