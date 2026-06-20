from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional


class ExplanationVariantEngine:
    """
    Adaptive explanation generator with grounded rule generation
    and optional LLM fallback.

    Goal:
    Same concept -> different explanation based on learner state and mode.
    """

    def __init__(self, use_llm: bool = True) -> None:
        self.use_llm = use_llm

    def generate(
        self,
        concept_resource: Dict[str, Any],
        mode: str = "simple",
        difficulty: str = "easy",
        learner_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        learner_state = learner_state or {}

        if self._learner_confidence(learner_state) <= 1:
            mode = "step_by_step"
            difficulty = "easy"

        normalized_resource = self._normalize_resource(concept_resource)

        generated = self._generate_grounded_variant(
            concept_resource=normalized_resource,
            mode=mode,
            difficulty=difficulty,
            learner_state=learner_state,
        )

        if generated and len(generated.strip()) > 40:
            return {
                "status": "success",
                "engine": "ExplanationVariantEngine",
                "generation_type": "grounded_rule_generation",
                "mode": mode,
                "difficulty": difficulty,
                "topic": normalized_resource["topic"],
                "explanation": generated.strip(),
            }

        if self.use_llm and self._llm_available():
            try:
                explanation = self._generate_with_llm(
                    concept_resource=normalized_resource,
                    mode=mode,
                    difficulty=difficulty,
                    learner_state=learner_state,
                )

                if explanation and len(explanation.strip()) > 40:
                    return {
                        "status": "success",
                        "engine": "ExplanationVariantEngine",
                        "generation_type": "llm",
                        "mode": mode,
                        "difficulty": difficulty,
                        "topic": normalized_resource["topic"],
                        "explanation": explanation.strip(),
                    }

            except Exception as e:
                fallback_reason = str(e)
            else:
                fallback_reason = "LLM output was empty or too short"
        else:
            fallback_reason = "LLM unavailable"

        fallback = self._generate_with_template(
            concept_resource=normalized_resource,
            mode=mode,
            difficulty=difficulty,
        )

        fallback["generation_type"] = "template_fallback"
        fallback["fallback_reason"] = fallback_reason
        return fallback

    # =========================
    # Main grounded generation
    # =========================

    def _generate_grounded_variant(
        self,
        concept_resource: Dict[str, str],
        mode: str,
        difficulty: str,
        learner_state: Dict[str, Any],
    ) -> str:

        topic = concept_resource["topic"]
        content = concept_resource["content"]
        examples = concept_resource["examples"]
        key_points = concept_resource["key_points"]
        misconceptions = concept_resource["misconceptions"]
        real_world_use = concept_resource["real_world_use"]

        if self._learner_confidence(learner_state) <= 1:
            mode = "step_by_step"
            difficulty = "easy"

        if difficulty == "easy":
            max_chars = 250
            kp_limit = 3
        elif difficulty == "medium":
            max_chars = 400
            kp_limit = 4
        else:
            max_chars = 600
            kp_limit = 6

        first_key_points = self._take_lines(key_points, limit=kp_limit)
        first_examples = self._take_example_blocks(examples, limit=1)
        first_examples = self._clean_teaching_code_example(first_examples)

        if mode == "code":
            first_examples = self._shorten(first_examples, 280)

        first_misconceptions = self._take_lines(misconceptions, limit=2)
        first_real_world = self._take_lines(real_world_use, limit=2)

        if mode == "simple":
            return (
                f"Let's understand {topic} in a simple way.\n\n"
                f"{self._shorten(content, max_chars)}\n\n"
                f"Remember these points:\n"
                f"{first_key_points}\n\n"
                f"Quick check: Can you explain {topic} in one sentence?"
            )

        if mode == "analogy":
            return (
                f"Think of {topic} using a real-life comparison.\n\n"
                f"Imagine giving a clear name to something you want to reuse later. "
                f"That is the main idea behind {topic}.\n\n"
                f"Concept:\n{self._shorten(content, max_chars)}\n\n"
                f"Where it is used:\n{first_real_world}\n\n"
                f"Quick check: What real-life object can you compare this concept to?"
            )

        if mode == "code":
            return (
                f"Let's understand {topic} using code.\n\n"
                f"Concept:\n{self._shorten(content, max_chars)}\n\n"
                f"Example:\n```python\n{first_examples}\n```\n\n"
                f"What to observe:\n"
                f"{first_key_points}\n\n"
                f"Quick check: What is being named, stored, changed, or reused here?"
            )

        if mode == "step_by_step":
            return (
                f"Let's learn {topic} step by step.\n\n"
                f"Step 1: Main idea\n{self._shorten(content, max_chars)}\n\n"
                f"Step 2: Important points\n{first_key_points}\n\n"
                f"Step 3: Example\n```python\n{first_examples}\n```\n\n"
                f"Step 4: Explain it back in your own words."
            )

        if mode == "misconception":
            return (
                f"Let's clear common confusion about {topic}.\n\n"
                f"Correct idea:\n{self._shorten(content, max_chars)}\n\n"
                f"Common mistakes:\n{first_misconceptions}\n\n"
                f"Remember: understanding when and why to use it matters more than memorizing words."
            )

        if mode == "challenge":
            return (
                f"You are ready for a harder task on {topic}.\n\n"
                f"Concept reminder:\n{self._shorten(content, max_chars)}\n\n"
                f"Challenge:\nCreate your own example using {topic}. "
                f"Then explain what changes if the input or value changes.\n\n"
                f"Use these ideas:\n{first_key_points}"
            )

        if mode == "revision":
            return (
                f"Quick revision for {topic}.\n\n"
                f"Must remember:\n{first_key_points}\n\n"
                f"Avoid:\n{first_misconceptions}\n\n"
                f"Revision task: write one example and one mistake to avoid."
            )

        return ""

    # =========================
    # Cleaning helpers
    # =========================

    def _shorten(self, text: str, max_chars: int = 500) -> str:
        text = str(text or "").strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0] + "..."

    def _take_lines(self, text: str, limit: int = 4) -> str:
        lines = []

        for line in str(text or "").splitlines():
            clean = line.strip()
            if not clean:
                continue

            if clean.startswith("-"):
                clean = clean[1:].strip()

            lines.append(f"- {clean}")

            if len(lines) >= limit:
                break

        return "\n".join(lines)

    def _take_example_blocks(self, text: str, limit: int = 1) -> str:
        text = str(text or "").strip()

        if not text:
            return ""

        # Remove markdown fences early
        text = text.replace("```python", "").replace("```", "").strip()

        # If multiple examples are present, keep only the first useful block
        split_points = re.split(
            r"(?=Example\s+\d+\s*[—:\-])",
            text,
            flags=re.IGNORECASE,
        )

        blocks = [block.strip() for block in split_points if block.strip()]

        if not blocks:
            blocks = [text]

        selected = "\n\n".join(blocks[:limit])
        return self._clean_teaching_code_example(selected)

    def _clean_teaching_code_example(self, text: str) -> str:
        """
        Remove teaching/example noise from code blocks.

        Converts:
            Basic assignment and printing:
            name = "Alice"
            print(name) # Alice

        Into:
            name = "Alice"
            print(name)
        """

        text = str(text or "")
        text = text.replace("```python", "").replace("```", "")
        text = text.replace("Basic assignment and printing:", "")
        text = text.replace("Basic assignment:", "")
        text = text.strip()

        if "Example 2" in text:
            text = text.split("Example 2", 1)[0]

        cleaned_lines = []

        for line in text.splitlines():
            clean = line.strip()

            if not clean:
                continue

            lower = clean.lower()

            # Remove labels/headings
            if lower.startswith("example"):
                continue
            if lower.startswith("output"):
                continue
            if lower.startswith("explanation"):
                continue
            if lower.startswith("basic assignment"):
                continue

            # Remove inline comments from code
            if "#" in clean:
                clean = clean.split("#", 1)[0].rstrip()

            if clean:
                cleaned_lines.append(clean)

        # Prefer small, readable Python variable example
        preferred = []

        for line in cleaned_lines:
            stripped = line.strip()
            if (
                stripped.startswith("name =")
                or stripped.startswith("age =")
                or stripped.startswith("price =")
                or stripped.startswith("quantity =")
                or stripped.startswith("total =")
                or stripped.startswith("print(name)")
                or stripped.startswith("print(age)")
                or stripped.startswith("print(total)")
            ):
                preferred.append(stripped)

        if preferred:
            # Keep only one compact example
            return "\n".join(preferred[:4])

        # Generic fallback: keep only code-looking lines
        code_lines = [
            line for line in cleaned_lines
            if self._looks_like_code(line)
        ]

        if code_lines:
            return "\n".join(code_lines[:4])

        return "\n".join(cleaned_lines[:4])

    def _looks_like_code(self, line: str) -> bool:
        return any(
            token in line
            for token in ["print(", "=", "if ", "for ", "while ", "def "]
        )

    def _learner_confidence(self, learner_state: Dict[str, Any]) -> float:
        try:
            return float(learner_state.get("confidence", 2))
        except (TypeError, ValueError):
            return 2.0

    def _normalize_resource(self, concept_resource: Dict[str, Any]) -> Dict[str, str]:
        topic = (
            concept_resource.get("topic")
            or concept_resource.get("concept_name")
            or "this concept"
        )

        content = (
            concept_resource.get("content")
            or concept_resource.get("base_content")
            or concept_resource.get("definition")
            or ""
        )

        examples = self._safe_join(
            concept_resource.get("examples")
            or concept_resource.get("examples_base")
            or ""
        )

        # Clean examples once at normalization level also
        examples = self._clean_teaching_code_example(examples)

        key_points = self._safe_join(
            concept_resource.get("key_points")
            or concept_resource.get("key_points_base")
            or ""
        )

        misconceptions = self._safe_join(
            concept_resource.get("misconceptions")
            or concept_resource.get("misconceptions_base")
            or ""
        )

        real_world_use = self._safe_join(
            concept_resource.get("real_world_use")
            or concept_resource.get("applications")
            or ""
        )

        return {
            "topic": str(topic),
            "content": str(content),
            "examples": str(examples),
            "key_points": str(key_points),
            "misconceptions": str(misconceptions),
            "real_world_use": str(real_world_use),
        }

    def _safe_join(self, value: Any) -> str:
        if isinstance(value, list):
            return "\n".join(str(v) for v in value if v)
        if isinstance(value, dict):
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        return str(value or "")

    # =========================
    # Optional LLM support
    # =========================

    def _llm_available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def _generate_with_llm(
        self,
        concept_resource: Dict[str, str],
        mode: str,
        difficulty: str,
        learner_state: Dict[str, Any],
    ) -> str:

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai"
            ) from exc

        client = OpenAI()

        prompt = self._build_prompt(
            concept_resource=concept_resource,
            mode=mode,
            difficulty=difficulty,
            learner_state=learner_state,
        )

        response = client.chat.completions.create(
            model=os.getenv("TUTOR_LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an adaptive AI tutor. "
                        "Generate grounded explanations only from the provided concept resource. "
                        "Do not invent unsupported facts. "
                        "Make the explanation clear, learner-friendly, and non-repetitive."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.45,
        )

        return response.choices[0].message.content or ""

    def _build_prompt(
        self,
        concept_resource: Dict[str, str],
        mode: str,
        difficulty: str,
        learner_state: Dict[str, Any],
    ) -> str:

        return f"""
Generate an adaptive explanation.

Topic:
{concept_resource["topic"]}

Difficulty:
{difficulty}

Explanation mode:
{mode}

Learner state:
{learner_state}

Ground truth concept content:
{concept_resource["content"]}

Examples:
{concept_resource["examples"]}

Key points:
{concept_resource["key_points"]}

Common misconceptions:
{concept_resource["misconceptions"]}

Real-world use:
{concept_resource["real_world_use"]}

Instructions:
- Use only the given concept resource.
- Match the explanation mode.
- Avoid repeating the same wording from the source.
- Keep it suitable for the learner difficulty.
- Include a small check-for-understanding question at the end.
- If mode is simple, make it beginner-friendly.
- If mode is analogy, use one clear analogy.
- If mode is code, explain using code.
- If mode is step_by_step, break the explanation into numbered steps.
- If mode is misconception, directly correct common mistakes.
- If mode is challenge, give a harder thinking task.
- If mode is revision, make it short and memory-friendly.
""".strip()

    # =========================
    # Template fallback
    # =========================

    def _generate_with_template(
        self,
        concept_resource: Dict[str, str],
        mode: str,
        difficulty: str,
    ) -> Dict[str, Any]:

        topic = concept_resource["topic"]
        content = concept_resource["content"]
        examples = concept_resource["examples"]
        key_points = concept_resource["key_points"]
        misconceptions = concept_resource["misconceptions"]
        real_world_use = concept_resource["real_world_use"]

        if mode == "simple":
            explanation = self._simple(topic, content, key_points)

        elif mode == "analogy":
            explanation = self._analogy(topic, content, real_world_use)

        elif mode == "code":
            explanation = self._code(topic, content, examples)

        elif mode == "step_by_step":
            explanation = self._step_by_step(topic, content, key_points, examples)

        elif mode == "misconception":
            explanation = self._misconception(topic, content, misconceptions)

        elif mode == "challenge":
            explanation = self._challenge(topic, content, examples, difficulty)

        elif mode == "revision":
            explanation = self._revision(topic, key_points, misconceptions)

        else:
            explanation = self._simple(topic, content, key_points)

        return {
            "status": "success",
            "engine": "ExplanationVariantEngine",
            "mode": mode,
            "difficulty": difficulty,
            "topic": topic,
            "explanation": explanation,
        }

    def _simple(self, topic: str, content: str, key_points: str) -> str:
        return f"""
{topic} in simple words:

{content}

Important things to remember:
{key_points}

Quick check:
Can you explain {topic} in one sentence?
""".strip()

    def _analogy(self, topic: str, content: str, real_world_use: str) -> str:
        return f"""
Think of {topic} like a label system in real life.

When you label a box, the label helps you find what is inside later.
Similarly, in programming, {topic} helps us name and reuse information.

Concept:
{content}

Where this is useful:
{real_world_use}

Quick check:
What is one real-life situation where naming something makes it easier to reuse?
""".strip()

    def _code(self, topic: str, content: str, examples: str) -> str:
        examples = self._clean_teaching_code_example(examples)

        return f"""
Let's understand {topic} using code.

Concept:
{content}

Code example:
```python
{examples}
```

Quick check:
What value or idea is being named and reused in this example?
""".strip()

    def _step_by_step(
        self,
        topic: str,
        content: str,
        key_points: str,
        examples: str,
    ) -> str:
        examples = self._clean_teaching_code_example(examples)

        return f"""
Let's break {topic} into steps.

1. Start with the main idea:
{content}

2. Focus on the key points:
{key_points}

3. Look at an example:
```python
{examples}
```

Quick check:
Which step helped you understand {topic} the most?
""".strip()

    def _misconception(self, topic: str, content: str, misconceptions: str) -> str:
        return f"""
A common mistake with {topic}:
{misconceptions}

Correct idea:
{content}

Quick check:
What is one mistake you should avoid when using {topic}?
""".strip()

    def _challenge(
        self,
        topic: str,
        content: str,
        examples: str,
        difficulty: str,
    ) -> str:
        examples = self._clean_teaching_code_example(examples)

        return f"""
Challenge explanation for {topic} ({difficulty}):

{content}

Use this example as a starting point:
```python
{examples}
```

Challenge:
Create a new example that uses {topic} in a slightly different situation.
""".strip()

    def _revision(self, topic: str, key_points: str, misconceptions: str) -> str:
        return f"""
Quick revision: {topic}

Remember:
{key_points}

Avoid:
{misconceptions}

Quick check:
What is the most important thing to remember about {topic}?
""".strip()


if __name__ == "__main__":
    sample_resource = {
        "topic": "Python Variables",
        "content": "Variables are names used to store values in memory.",
        "examples": """
Basic assignment and printing:
name = "Alice"
age = 30
height = 5.6
is_student = False
print(name)        # Alice
print(age)         # 30
print(type(age))   # <class 'int'>
""",
        "key_points": [
            "Variables store data.",
            "Variable values can change.",
            "Names should be meaningful.",
        ],
        "misconceptions": [
            "A variable is not the value itself; it is a name pointing to a value."
        ],
        "real_world_use": "Variables can store scores, names, prices, and settings.",
    }

    engine = ExplanationVariantEngine(use_llm=False)
    print(engine.generate(sample_resource, mode="code", difficulty="medium"))
