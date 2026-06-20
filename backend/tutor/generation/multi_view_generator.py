"""
MultiViewGenerator

Purpose:
- Generate multiple learning views for the same concept.
- Avoid showing the learner only one static explanation.
- Support adaptive tutor flow: teach using different representations.
- Later, ViewPerformanceTracker + RL will learn which view works best.

Views generated:
1. definition_view
2. step_by_step_view
3. analogy_view
4. code_view
5. misconception_view
6. debug_view
7. challenge_view
8. transfer_view
9. revision_view
10. flashcard_view
"""

from __future__ import annotations

import ast
from typing import Dict, Any, List



class MultiViewGenerator:
    def __init__(self):
        self.supported_views = [
            "definition_view",
            "step_by_step_view",
            "analogy_view",
            "code_view",
            "misconception_view",
            "debug_view",
            "challenge_view",
            "transfer_view",
            "revision_view",
            "flashcard_view",
        ]

    def generate(
        self,
        concept_resource: Dict[str, Any],
        learner_profile: Dict[str, Any] | None = None,
        difficulty: str = "medium",
        requested_views: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Generate multiple teaching views from one concept resource.

        Args:
            concept_resource:
                Dict containing topic, base_content, examples, key_points,
                misconceptions, real_world_use, next_concept_link.

            learner_profile:
                Optional learner information from KT/behaviour/fusion.

            difficulty:
                easy / medium / hard

            requested_views:
                Optional list of views. If None, generate all views.

        Returns:
            Dict with metadata + generated views.
        """

        learner_profile = learner_profile or {}
        requested_views = requested_views or self.supported_views

        topic = self._safe_get(concept_resource, "topic", "Unknown Concept")
        base_content = self._safe_get(concept_resource, "base_content", "")
        examples = self._safe_get(concept_resource, "examples", "")
        key_points = self._safe_get(concept_resource, "key_points", "")
        misconceptions = self._safe_get(concept_resource, "misconceptions", "")
        real_world_use = self._safe_get(concept_resource, "real_world_use", "")
        next_concept_link = self._safe_get(concept_resource, "next_concept_link", "")

        views = {}

        if "definition_view" in requested_views:
            views["definition_view"] = self._definition_view(
                topic=topic,
                base_content=base_content,
                key_points=key_points,
                difficulty=difficulty,
            )

        if "step_by_step_view" in requested_views:
            views["step_by_step_view"] = self._step_by_step_view(
                topic=topic,
                base_content=base_content,
                key_points=key_points,
                difficulty=difficulty,
            )

        if "analogy_view" in requested_views:
            views["analogy_view"] = self._analogy_view(
                topic=topic,
                real_world_use=real_world_use,
                difficulty=difficulty,
            )

        if "code_view" in requested_views:
            views["code_view"] = self._code_view(
                topic=topic,
                examples=examples,
                difficulty=difficulty,
            )

        if "misconception_view" in requested_views:
            views["misconception_view"] = self._misconception_view(
                topic=topic,
                misconceptions=misconceptions,
                key_points=key_points,
            )

        if "debug_view" in requested_views:
            views["debug_view"] = self._debug_view(
                topic=topic,
                examples=examples,
                misconceptions=misconceptions,
                difficulty=difficulty,
            )

        if "challenge_view" in requested_views:
            views["challenge_view"] = self._challenge_view(
                topic=topic,
                key_points=key_points,
                difficulty=difficulty,
            )

        if "transfer_view" in requested_views:
            views["transfer_view"] = self._transfer_view(
                topic=topic,
                real_world_use=real_world_use,
                next_concept_link=next_concept_link,
                difficulty=difficulty,
            )

        if "revision_view" in requested_views:
            views["revision_view"] = self._revision_view(
                topic=topic,
                key_points=key_points,
                misconceptions=misconceptions,
            )

        if "flashcard_view" in requested_views:
            views["flashcard_view"] = self._flashcard_view(
                topic=topic,
                key_points=key_points,
                misconceptions=misconceptions,
            )

        recommended_view = self._select_initial_view(
            learner_profile=learner_profile,
            difficulty=difficulty,
            available_views=list(views.keys()),
        )

        return {
            "status": "success",
            "module": "MultiViewGenerator",
            "concept_id": concept_resource.get("concept_id"),
            "topic": topic,
            "difficulty": difficulty,
            "recommended_view": recommended_view,
            "available_views": list(views.keys()),
            "views": views,
        }

    def _definition_view(
        self,
        topic: str,
        base_content: str,
        key_points: Any,
        difficulty: str,
    ) -> Dict[str, Any]:
        bullet_points = self._bullet_text(key_points, limit=6)

        content_parts = []

        if base_content:
            content_parts.append(str(base_content).strip())

        if bullet_points:
            content_parts.append("Important points:\n" + bullet_points)

        content = "\n\n".join(content_parts)

        return {
            "view_type": "definition_view",
            "title": f"What is {topic}?",
            "content": self._difficulty_trim(
                text=content,
                difficulty=difficulty,
            ),
            "best_for": "learners who need a clear concept introduction",
        }

    def _step_by_step_view(
        self,
        topic: str,
        base_content: str,
        key_points: Any,
        difficulty: str,
    ) -> Dict[str, Any]:
        points = self._split_points(key_points)

        steps = []

        if base_content:
            steps.append(
                f"Understand the basic idea of {topic}: {str(base_content).strip()}"
            )

        for idx, point in enumerate(points[:5], start=1):
            steps.append(f"Step {idx}: {point}")

        if not steps:
            steps = [
                f"Step 1: Identify what {topic} means.",
                f"Step 2: Understand where {topic} is used.",
                f"Step 3: Try a simple example.",
            ]

        return {
            "view_type": "step_by_step_view",
            "title": f"{topic} step by step",
            "steps": steps,
            "best_for": "learners who struggle with long explanations",
        }

    def _analogy_view(
        self,
        topic: str,
        real_world_use: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        if real_world_use:
            analogy = (
                f"Think of {topic} like a real-world tool. "
                f"It helps in situations such as: {real_world_use}"
            )
        else:
            analogy = (
                f"Think of {topic} like a helper that organizes a task. "
                f"Instead of remembering everything manually, it gives structure to the idea."
            )

        return {
            "view_type": "analogy_view",
            "title": f"{topic} using an analogy",
            "content": self._difficulty_trim(analogy, difficulty),
            "best_for": "learners who understand better through real-life examples",
        }

    def _code_view(
        self,
        topic: str,
        examples: Any,
        difficulty: str,
    ) -> Dict[str, Any]:
        example_list = self._split_points(examples)

        if example_list:
            content_parts = []
            for example in example_list[:3]:
                if "\n" in example:
                    content_parts.append(example.strip())
                else:
                    content_parts.append(example.strip())
            content = "\n\n".join(content_parts)
        else:
            content = (
                f"No direct code example was found for {topic}. "
                f"Use this view to connect the concept with a small practical example."
            )

        return {
            "view_type": "code_view",
            "title": f"{topic} with example",
            "content": self._difficulty_trim(content, difficulty),
            "best_for": "learners who prefer practical/code-based learning",
        }

    def _misconception_view(
        self,
        topic: str,
        misconceptions: str,
        key_points: str,
    ) -> Dict[str, Any]:
        if misconceptions:
            content = misconceptions
        else:
            content = (
                f"A common mistake in {topic} is memorizing the definition "
                f"without understanding when and why it is used."
            )

        return {
            "view_type": "misconception_view",
            "title": f"Common mistakes in {topic}",
            "content": content,
            "correction_hint": self._split_points(key_points),
            "best_for": "learners who repeatedly answer similar questions incorrectly",
        }

    def _debug_view(
        self,
        topic: str,
        examples: str,
        misconceptions: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        return {
            "view_type": "debug_view",
            "title": f"Debug thinking for {topic}",
            "buggy_case": self._build_buggy_case(topic, examples, misconceptions),
            "task": "Find the mistake, explain why it is wrong, and correct it.",
            "difficulty": difficulty,
            "best_for": "learners who need error-based practice",
        }

    def _challenge_view(
        self,
        topic: str,
        key_points: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        if difficulty == "easy":
            prompt = f"Explain {topic} in your own words using one simple example."
        elif difficulty == "hard":
            prompt = (
                f"Create a new problem where {topic} is needed, solve it, "
                f"and explain why another approach would fail."
            )
        else:
            prompt = f"Use {topic} to solve a medium-level practical problem."

        return {
            "view_type": "challenge_view",
            "title": f"{topic} challenge",
            "prompt": prompt,
            "focus_points": self._split_points(key_points)[:4],
            "best_for": "learners ready for active practice",
        }

    def _transfer_view(
        self,
        topic: str,
        real_world_use: str,
        next_concept_link: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        content = (
            f"Now connect {topic} to a new situation. "
            f"Real-world use: {real_world_use or 'Apply this concept in a practical task.'}"
        )

        if next_concept_link:
            content += f"\n\nThis prepares you for: {next_concept_link}"

        return {
            "view_type": "transfer_view",
            "title": f"Apply {topic} in a new situation",
            "content": self._difficulty_trim(content, difficulty),
            "best_for": "checking whether the learner can transfer knowledge",
        }

    def _revision_view(
        self,
        topic: str,
        key_points: Any,
        misconceptions: Any,
    ) -> Dict[str, Any]:
        return {
            "view_type": "revision_view",
            "title": f"Quick revision: {topic}",
            "remember": self._split_points(key_points)[:5],
            "avoid": self._split_points(misconceptions)[:3],
            "best_for": "spaced revision and forgetting recovery",
        }

    def _flashcard_view(
        self,
        topic: str,
        key_points: Any,
        misconceptions: Any,
    ) -> Dict[str, Any]:
        key_list = self._split_points(key_points)
        misconception_list = self._split_points(misconceptions)

        cards = [
            {
                "front": f"What is {topic}?",
                "back": key_list[0] if key_list else f"{topic} is an important concept to understand and apply.",
            }
        ]

        for point in key_list[1:4]:
            cards.append(
                {
                    "front": f"Important point about {topic}",
                    "back": point,
                }
            )

        for mistake in misconception_list[:2]:
            cards.append(
                {
                    "front": f"Common mistake in {topic}",
                    "back": mistake,
                }
            )

        return {
            "view_type": "flashcard_view",
            "title": f"{topic} flashcards",
            "cards": cards,
            "best_for": "revision, memory recall, and quick practice",
        }

    def _select_initial_view(
        self,
        learner_profile: Dict[str, Any],
        difficulty: str,
        available_views: List[str],
    ) -> str:
        """
        First baseline selector.

        Later this will be replaced or overridden by:
        - ViewPerformanceTracker
        - RL policy
        - learner notebook memory
        """

        behaviour_label = str(learner_profile.get("behaviour_label", "")).lower()
        mastery = float(learner_profile.get("mastery", 0.5) or 0.5)

        if "struggling" in behaviour_label or mastery < 0.4:
            preferred = "step_by_step_view"
        elif mastery >= 0.75 and difficulty == "hard":
            preferred = "challenge_view"
        elif "confused" in behaviour_label:
            preferred = "analogy_view"
        else:
            preferred = "definition_view"

        if preferred in available_views:
            return preferred

        return available_views[0] if available_views else "definition_view"

    def _build_buggy_case(
        self,
        topic: str,
        examples: str,
        misconceptions: str,
    ) -> str:
        if misconceptions:
            return (
                f"Buggy understanding of {topic}:\n"
                f"{misconceptions}\n\n"
                f"Use the correct concept to fix this misunderstanding."
            )

        if examples:
            return (
                f"Look at this example related to {topic}:\n"
                f"{examples}\n\n"
                f"Now imagine one part is used incorrectly. Identify what could go wrong."
            )

        return (
            f"A learner tries to use {topic}, but applies it without checking the correct condition. "
            f"Find what is missing and correct the approach."
        )

    def _difficulty_trim(self, text: str, difficulty: str) -> str:
        text = text.strip()

        if not text:
            return ""

        if difficulty == "easy":
            sentences = text.split(".")
            return ".".join(sentences[:3]).strip() + ("." if len(sentences) > 1 else "")

        if difficulty == "hard":
            return text + "\n\nThink deeper: explain why this concept works and where it may fail."

        return text

    def _split_points(self, text: Any) -> List[str]:
        """
        Convert key_points / examples / misconceptions into a clean list.

        Handles:
        - normal string
        - Python list
        - stringified Python list: "['a', 'b']"
        - semicolon/newline/bullet separated text
        """

        if text is None:
            return []

        if isinstance(text, list):
            raw_parts = text

        elif isinstance(text, tuple):
            raw_parts = list(text)

        elif isinstance(text, str):
            cleaned_text = text.strip()

            if not cleaned_text:
                return []

            # Handle stringified list safely
            if cleaned_text.startswith("[") and cleaned_text.endswith("]"):
                try:
                    parsed = ast.literal_eval(cleaned_text)
                    if isinstance(parsed, list):
                        raw_parts = parsed
                    else:
                        raw_parts = [cleaned_text]
                except Exception:
                    raw_parts = [cleaned_text]
            else:
                raw_parts = (
                    cleaned_text
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .replace("|", ";")
                    .replace("•", ";")
                    .replace("\n", ";")
                    .split(";")
                )

        else:
            raw_parts = [str(text)]

        cleaned = []

        for part in raw_parts:
            item = str(part).strip(" -:\t\n\r")
            item = " ".join(item.split())

            if not item:
                continue

            if item.startswith("[") and item.endswith("]"):
                try:
                    parsed_inner = ast.literal_eval(item)
                    if isinstance(parsed_inner, list):
                        for inner in parsed_inner:
                            inner_item = str(inner).strip(" -:\t\n\r")
                            inner_item = " ".join(inner_item.split())
                            if inner_item:
                                cleaned.append(inner_item)
                        continue
                except Exception:
                    pass

            cleaned.append(item)

        # remove duplicates while keeping order
        seen = set()
        unique = []

        for item in cleaned:
            key = item.lower()
            if key not in seen:
                unique.append(item)
                seen.add(key)

        return unique

    def _bullet_text(self, points: Any, limit: int | None = None) -> str:
        items = self._split_points(points)

        if limit is not None:
            items = items[:limit]

        if not items:
            return ""

        return "\n".join(f"- {item}" for item in items)

    def _safe_get(self, data: Dict[str, Any], key: str, default: str) -> str:
        value = data.get(key, default)
        if value is None:
            return default
        return str(value)
