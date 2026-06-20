from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, asdict

from typing import Any, Dict, List, Optional
from tutor.memory.anti_repetition import (
    fetch_recent_history,
    store_generated_item,
)
from tutor.generation.concept_expansion_engine import ConceptExpansionEngine

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class GeneratedContent:
    content_id: str
    concept_id: str
    concept_name: str
    content_type: str
    strategy: str
    difficulty: str
    title: str
    body: str
    bullets: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    content_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# MAIN GENERATOR
# ============================================================

class AdaptiveContentGenerator:
    """
    Generation-first teaching/revision builder.

    Goal:
    - Convert one concept resource into many teaching styles
    - Support revision formats
    - Add anti-repetition support
    - Keep DB content as source knowledge, not final static output

    Expected concept_resource example:
    {
        "concept_id": "P1",
        "concept_name": "Variables",
        "definition": "...",
        "key_points": ["...", "..."],
        "examples": ["...", "..."],
        "misconceptions": ["...", "..."],
        "real_world_use": "...",
        "syntax": "...",
        "difficulty": "easy"
    }
    """

    SUPPORTED_CONTENT_TYPES = {
        "teaching",
        "revision",
        "flashcard",
        "mind_map",
        "common_mistakes",
        "quick_recap",
    }

    SUPPORTED_STRATEGIES = {
        "definition_first",
        "example_first",
        "code_first",
        "misconception_first",
        "real_world_first",
        "step_by_step",
        "revision_summary",
        "weak_learner",
        "advanced_learner",
    }

    def __init__(
        self,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        history_limit: int = 30,
        random_seed: Optional[int] = None,
    ) -> None:
        self.recent_history = recent_history or []
        self.history_limit = history_limit
        self.rng = random.Random(random_seed)

    # ========================================================
    # PUBLIC API
    # ========================================================

    def generate_content(
        self,
        concept_resource: Dict[str, Any],
        content_type: str = "teaching",
        strategy: str = "definition_first",
        difficulty: str = "medium",
        learner_id: Optional[str] = None,
        max_attempts: int = 8,
    ) -> Dict[str, Any]:
        if content_type not in self.SUPPORTED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported content_type='{content_type}'. "
                f"Supported: {sorted(self.SUPPORTED_CONTENT_TYPES)}"
            )

        if strategy not in self.SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported strategy='{strategy}'. "
                f"Supported: {sorted(self.SUPPORTED_STRATEGIES)}"
            )

        generator_map = {
            ("teaching", "definition_first"): self._generate_definition_first,
            ("teaching", "example_first"): self._generate_example_first,
            ("teaching", "code_first"): self._generate_code_first,
            ("teaching", "misconception_first"): self._generate_misconception_first,
            ("teaching", "real_world_first"): self._generate_real_world_first,
            ("teaching", "step_by_step"): self._generate_step_by_step,
            ("teaching", "weak_learner"): self._generate_weak_learner_version,
            ("teaching", "advanced_learner"): self._generate_advanced_learner_version,
            ("revision", "revision_summary"): self._generate_revision_summary,
            ("quick_recap", "revision_summary"): self._generate_quick_recap,
            ("flashcard", "revision_summary"): self._generate_flashcards,
            ("mind_map", "revision_summary"): self._generate_mind_map,
            ("common_mistakes", "misconception_first"): self._generate_common_mistakes,
        }

        generator_fn = generator_map.get((content_type, strategy))
        if generator_fn is None:
            generator_fn = self._fallback_generator_for(content_type, strategy)

        for _ in range(max_attempts):
            content = generator_fn(concept_resource, difficulty=difficulty)
            content_hash = self._compute_content_hash(content)

            if not self._is_recent_duplicate(
                learner_id=learner_id,
                concept_id=content.concept_id,
                content_type=content.content_type,
                strategy=content.strategy,
                content_hash=content_hash,
            ):
                content.content_hash = content_hash
                return content.to_dict()

        content = generator_fn(concept_resource, difficulty=difficulty)
        content.content_hash = self._compute_content_hash(content)
        meta = content.metadata or {}
        meta["repeat_fallback_used"] = True
        content.metadata = meta
        return content.to_dict()

    def generate_content_bundle(
            self,
            concept_resource: Dict[str, Any],
            learner_id: Optional[str] = None,
            difficulty: str = "medium",
            requested_plan: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Example requested_plan:
        [
            {"content_type": "teaching", "strategy": "definition_first"},
            {"content_type": "revision", "strategy": "revision_summary"},
            {"content_type": "flashcard", "strategy": "revision_summary"},
        ]
        """
        if not requested_plan:
            requested_plan = [
                {"content_type": "teaching", "strategy": "definition_first"},
                {"content_type": "revision", "strategy": "revision_summary"},
                {"content_type": "flashcard", "strategy": "revision_summary"},
            ]

        items: List[Dict[str, Any]] = []
        for item in requested_plan:
            content_type = item.get("content_type", "teaching")
            strategy = item.get("strategy", "definition_first")
            generated = self.generate_content(
                concept_resource=concept_resource,
                content_type=content_type,
                strategy=strategy,
                difficulty=difficulty,
                learner_id=learner_id,
            )
            items.append(generated)

        concept_id, concept_name = self._basic_ids(concept_resource)

        expansion_engine = ConceptExpansionEngine()
        expanded_content = expansion_engine.expand(
            concept_resource=concept_resource,
            difficulty=difficulty,
        )

        adaptive_explanation = expanded_content.get("explanation_style", "")
        generation_mode = expanded_content.get("generation_mode", "")

        if items:
            items[0]["body"] = adaptive_explanation or items[0]["body"]
            items[0].setdefault("metadata", {})
            items[0]["metadata"]["generation_mode"] = generation_mode

        for item in items:
            item["body"] = self._trim_long_examples(item.get("body", ""))

        seen = set()
        filtered_items = []

        for item in items:
            key = item.get("content_hash") or item.get("body")
            if key not in seen:
                filtered_items.append(item)
                seen.add(key)

        items = filtered_items
            
        return {
            "status": "success",
            "concept_id": concept_id,
            "concept_name": concept_name,
            "difficulty": difficulty,
            "item_count": len(items),
            "items": items,

            # New richer generated outputs
            "expanded_content": expanded_content,
            "generated_summary": expanded_content.get("summary", ""),
            "generated_flashcards": expanded_content.get("flashcards", []),
            "generated_mindmap": expanded_content.get("mindmap", {}),
            "generated_challenge": expanded_content.get("challenge", ""),
            "generated_debug_task": expanded_content.get("debug_task", {}),
            "generated_transfer_task": expanded_content.get("transfer_task", ""),
            "generated_level_content": expanded_content.get("level_content", ""),
            "generation_note": expanded_content.get("source_note", ""),
        }


    # ========================================================
    # TEACHING STRATEGIES
    # ========================================================

    def _generate_definition_first(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        example = self._safe_choice(
            self._normalize_to_list_preserve_code(concept_resource.get("examples")),
            default="No direct example available.",
        )

        title = f"{concept_name} — Definition First"
        body_parts = [
            f"{concept_name} means: {definition or f'{concept_name} is an important lesson concept.'}",
            "Start with the main meaning before moving to examples.",
        ]
        if key_points:
            body_parts.append("Key idea: " + key_points[0])
        if example:
            body_parts.append("Simple example:\n" + self._format_example_block(example))

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "definition_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="definition_first",
            difficulty=difficulty,
            title=title,
            body="\n\n".join(body_parts),
            bullets=key_points[:4],
            metadata={"source_used": "definition/key_points/examples"},
        )

    def _generate_example_first(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))
        definition = self._clean_text(concept_resource.get("definition", ""))

        chosen_example = self._safe_choice(
            examples,
            default=f"Example placeholder for {concept_name}.",
        )

        body = self._join_sections(
            f"Let us understand {concept_name} through an example first.",
            self._format_example_block(chosen_example),
            f"From this example, we can understand that {definition or concept_name + ' has a specific role in programming.'}",
        )

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "example_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="example_first",
            difficulty=difficulty,
            title=f"{concept_name} — Example First",
            body=body,
            bullets=self._normalize_to_list(concept_resource.get("key_points"))[:4],
            metadata={"source_used": "examples/definition"},
        )

    def _generate_code_first(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))
        definition = self._clean_text(concept_resource.get("definition", ""))
        syntax = self._clean_text(concept_resource.get("syntax", ""))

        code = self._extract_code_example(examples)
        if not code:
            code = syntax or f"# Example use of {concept_name}"

        body = self._join_sections(
            "See the code first:",
            self._format_example_block(code),
            f"This code shows how {concept_name} works.\n{definition or f'The main idea is to understand the role of {concept_name} in the program.'}",
        )

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "code_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="code_first",
            difficulty=difficulty,
            title=f"{concept_name} — Code First",
            body=body,
            bullets=self._normalize_to_list(concept_resource.get("key_points"))[:4],
            metadata={"source_used": "examples/syntax/definition"},
        )

    def _generate_misconception_first(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))

        misconception = self._safe_choice(
            misconceptions,
            default=f"There are common mistakes learners make when learning {concept_name}.",
        )

        body = self._join_sections(
            "A common misconception is:",
            self._format_bullets([misconception]),
            "Correct understanding:\n"
            f"{definition or f'{concept_name} should be understood using its actual rule or purpose.'}",
        )

        if key_points:
            body += "\n\nWhat to remember:\n" + self._format_bullets(key_points[:4])

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "misconception_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="misconception_first",
            difficulty=difficulty,
            title=f"{concept_name} — Misconception First",
            body=body,
            bullets=key_points[:4],
            metadata={"source_used": "misconceptions/definition/key_points"},
        )

    def _generate_real_world_first(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        real_world_use = self._clean_text(concept_resource.get("real_world_use", ""))
        definition = self._clean_text(concept_resource.get("definition", ""))

        body = (
            f"Why does {concept_name} matter in real programs?\n\n"
            f"{self._clean_text(real_world_use) or f'{concept_name} appears in practical software tasks.'}\n\n"
            f"Now connect that to the lesson meaning:\n"
            f"{definition or f'{concept_name} is a core concept you need for correct programming logic.'}"
        )

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "real_world_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="real_world_first",
            difficulty=difficulty,
            title=f"{concept_name} — Real World First",
            body=body,
            bullets=self._normalize_to_list(concept_resource.get("key_points"))[:4],
            metadata={"source_used": "real_world_use/definition"},
        )

    def _generate_step_by_step(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))

        steps = [
            f"Step 1: What {concept_name} means: {definition or concept_name + ' has a specific purpose in the lesson.'}",
            "Step 2: Assignment connects a name to a value.",
        ]

        if examples:
            example = self._clean_teaching_code_example(examples[0])
            steps.append(
                f"Step 3: See a short example:\n{self._format_example_block(example)}"
            )

        steps.append("Step 4: Try changing one value and predict what prints.")

        body = "\n".join(steps)

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "step_by_step"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="step_by_step",
            difficulty=difficulty,
            title=f"{concept_name} — Step by Step",
            body=body,
            bullets=key_points[:4],
            metadata={"source_used": "definition/key_points/examples"},
        )

    def _generate_weak_learner_version(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))

        simple_definition = self._simplify_sentence(
            definition or f"{concept_name} is used in programming."
        )

        body_parts = [
            f"Let us learn {concept_name} in a simple way.",
            f"Meaning: {simple_definition}",
        ]

        if examples:
            body_parts.append("Small example:\n" + self._format_example_block(examples[0]))

        if misconceptions:
            body_parts.append("Avoid this mistake:\n" + self._format_bullets([misconceptions[0]]))

        body_parts.append("Focus on one idea at a time. First understand the meaning, then the example.")

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "weak_learner"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="weak_learner",
            difficulty=difficulty,
            title=f"{concept_name} — Simple Version",
            body="\n\n".join(body_parts),
            bullets=self._normalize_to_list(concept_resource.get("key_points"))[:3],
            metadata={"audience": "struggling_learner"},
        )

    def _generate_advanced_learner_version(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        real_world_use = self._clean_text(concept_resource.get("real_world_use", ""))
        syntax = self._clean_text(concept_resource.get("syntax", ""))

        body_parts = [
            f"Technical view of {concept_name}:",
            definition or f"{concept_name} has an operational role in program execution.",
        ]

        if syntax:
            body_parts.append("Syntax or representative form:\n" + self._format_example_block(syntax))

        if key_points:
            body_parts.append("Advanced reminders:\n" + self._format_bullets(key_points[:5]))

        if real_world_use:
            body_parts.append("Practical significance:\n" + self._clean_text(real_world_use))

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "teaching", "advanced_learner"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="teaching",
            strategy="advanced_learner",
            difficulty=difficulty,
            title=f"{concept_name} — Advanced View",
            body="\n\n".join(body_parts),
            bullets=key_points[:5],
            metadata={"audience": "advanced_learner"},
        )

    # ========================================================
    # REVISION FORMATS
    # ========================================================

    def _generate_revision_summary(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))

        body_parts = [
            f"Revision summary for {concept_name}",
            f"Definition: {definition or f'{concept_name} is an important concept.'}",
        ]

        if key_points:
            body_parts.append("Key points:\n" + self._format_bullets(key_points[:5]))

        if misconceptions:
            body_parts.append("Common mistake to avoid:\n" + self._format_bullets([misconceptions[0]]))

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "revision", "revision_summary"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="revision",
            strategy="revision_summary",
            difficulty=difficulty,
            title=f"{concept_name} — Revision Summary",
            body="\n\n".join(body_parts),
            bullets=key_points[:5],
            metadata={"format": "summary"},
        )

    def _generate_quick_recap(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        definition = self._clean_text(concept_resource.get("definition", ""))

        bullets = [definition] if definition else []
        bullets.extend(key_points[:4])

        body = f"Quick recap of {concept_name}:\n" + self._format_bullets(bullets)

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "quick_recap", "revision_summary"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="quick_recap",
            strategy="revision_summary",
            difficulty=difficulty,
            title=f"{concept_name} — Quick Recap",
            body=body,
            bullets=bullets[:5],
            metadata={"format": "recap"},
        )

    def _generate_flashcards(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        real_world_use = self._clean_text(concept_resource.get("real_world_use", ""))

        cards = []

        if definition:
            cards.append(f"Q: What is {concept_name}?\nA: {definition}")

        for kp in key_points[:3]:
            cards.append(f"Q: What should you remember about {concept_name}?\nA: {kp}")

        if real_world_use:
            cards.append(f"Q: Where is {concept_name} used?\nA: {real_world_use}")

        if not cards:
            cards.append(f"Q: What is {concept_name}?\nA: It is an important lesson concept.")

        body = "\n\n".join(cards)

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "flashcard", "revision_summary"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="flashcard",
            strategy="revision_summary",
            difficulty=difficulty,
            title=f"{concept_name} — Flashcards",
            body=body,
            bullets=cards[:5],
            metadata={"format": "flashcards", "card_count": len(cards)},
        )

    def _generate_mind_map(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))

        lines = [
            concept_name,
            f"├── Meaning: {definition or 'Core lesson concept'}",
        ]

        for idx, kp in enumerate(key_points[:3], start=1):
            branch = "├──" if idx < min(len(key_points[:3]), 3) else "└──"
            lines.append(f"{branch} Key Point {idx}: {kp}")

        if examples:
            lines.append(f"   ├── Example:\n{self._indent_block(self._format_example_block(examples[0]), '   │   ')}")
        if misconceptions:
            lines.append(f"   └── Common Mistake: {misconceptions[0]}")

        body = "\n".join(lines)

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "mind_map", "revision_summary"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="mind_map",
            strategy="revision_summary",
            difficulty=difficulty,
            title=f"{concept_name} — Mind Map Notes",
            body=body,
            bullets=key_points[:4],
            metadata={"format": "mind_map_text"},
        )

    def _generate_common_mistakes(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedContent:
        concept_id, concept_name = self._basic_ids(concept_resource)
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))
        definition = self._clean_text(concept_resource.get("definition", ""))

        if not misconceptions:
            misconceptions = [f"Learners may misuse {concept_name} if they skip the core rule."]

        body_parts = [
            f"Common mistakes in {concept_name}:",
            self._format_bullets(misconceptions[:5]),
            f"Correct understanding:\n{definition or f'Use the correct idea and syntax of {concept_name}.'}",
        ]

        return GeneratedContent(
            content_id=self._make_content_id(concept_id, "common_mistakes", "misconception_first"),
            concept_id=concept_id,
            concept_name=concept_name,
            content_type="common_mistakes",
            strategy="misconception_first",
            difficulty=difficulty,
            title=f"{concept_name} — Common Mistakes",
            body="\n\n".join(body_parts),
            bullets=misconceptions[:5],
            metadata={"format": "mistake_sheet"},
        )

    # ========================================================
    # FALLBACK
    # ========================================================

    def _fallback_generator_for(self, content_type: str, strategy: str):
        def _fallback(concept_resource: Dict[str, Any], difficulty: str) -> GeneratedContent:
            concept_id, concept_name = self._basic_ids(concept_resource)

            definition = self._clean_text(
                concept_resource.get("definition")
                or concept_resource.get("base_content")
                or concept_resource.get("content")
                or ""
            )

            key_points = self._normalize_to_list(
                concept_resource.get("key_points")
                or concept_resource.get("key_points_base")
            )

            examples = self._normalize_to_list_preserve_code(
                concept_resource.get("examples")
                or concept_resource.get("examples_base")
            )

            misconceptions = self._normalize_to_list(
                concept_resource.get("misconceptions")
                or concept_resource.get("misconceptions_base")
            )

            body_parts = [
                f"{concept_name} means: {definition or f'{concept_name} is an important concept.'}",
            ]

            if key_points:
                body_parts.append("Important points:\n" + self._format_bullets(key_points[:4]))

            if examples:
                body_parts.append("Example:\n" + self._format_example_block(examples[0]))

            if misconceptions:
                body_parts.append("Common mistake:\n" + self._format_bullets([misconceptions[0]]))

            return GeneratedContent(
                content_id=self._make_content_id(concept_id, content_type, strategy),
                concept_id=concept_id,
                concept_name=concept_name,
                content_type=content_type,
                strategy=strategy,
                difficulty=difficulty,
                title=f"{concept_name} — Generated Content",
                body="\n\n".join(body_parts),
                bullets=key_points[:5],
                metadata={
                    "fallback_used": True,
                    "source_used": "definition/key_points/examples/misconceptions",
                },
            )

        return _fallback
    # ========================================================
    # ANTI-REPETITION
    # ========================================================

    def _compute_content_hash(self, content: GeneratedContent) -> str:
        base = f"{content.concept_id}|{content.content_type}|{content.strategy}|{content.title}|{content.body}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    def _is_recent_duplicate(
        self,
        learner_id: Optional[str],
        concept_id: str,
        content_type: str,
        strategy: str,
        content_hash: str,
    ) -> bool:
        recent_items = self.recent_history[-self.history_limit:]
        for item in recent_items:
            if learner_id is not None and str(item.get("learner_id")) not in {"", str(learner_id)}:
                continue

            same_concept = str(item.get("concept_id")) == str(concept_id)
            same_type = str(item.get("content_type")) == str(content_type)
            same_strategy = str(item.get("strategy")) == str(strategy)
            same_hash = str(item.get("content_hash")) == str(content_hash)

            if same_concept and same_type and same_strategy and same_hash:
                return True
        return False

    # ========================================================
    # HELPERS
    # ========================================================

    def _basic_ids(self, concept_resource: Dict[str, Any]) -> tuple[str, str]:
        concept_id = (
            concept_resource.get("concept_id")
            or concept_resource.get("system_concept_id")
            or concept_resource.get("content_concept_id")
            or ""
        )

        concept_name = (
            concept_resource.get("concept_name")
            or concept_resource.get("topic")
            or concept_resource.get("title")
            or "Unknown Concept"
        )

        return str(concept_id), str(concept_name)

    def _make_content_id(self, concept_id: str, content_type: str, strategy: str) -> str:
        token = self.rng.randint(100000, 999999)
        return f"{concept_id}_{content_type}_{strategy}_{token}"

    def _normalize_to_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._clean_text(v) for v in value if self._clean_text(v)]
        if isinstance(value, str):
            if "|" in value:
                return [self._clean_text(v) for v in value.split("|") if self._clean_text(v)]
            if "\n" in value:
                return [self._clean_text(v) for v in value.split("\n") if self._clean_text(v)]
            return [self._clean_text(value)] if self._clean_text(value) else []
        return [self._clean_text(str(value))] if self._clean_text(str(value)) else []

    def _normalize_to_list_preserve_code(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            if "|" in value:
                return [part.strip() for part in value.split("|") if part.strip()]
            return [value.strip()] if value.strip() else []
        return [str(value).strip()] if str(value).strip() else []

    def _clean_text(self, text: Any) -> str:
        if text is None:
            return ""
        text = str(text).strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _trim_long_examples(self, text: Any) -> str:
        text = str(text or "")
        if "Example 2" in text:
            text = text.split("Example 2", 1)[0]
        text = text.strip()
        if text.count("```") % 2 == 1:
            text += "\n```"
        return text

    def _clean_teaching_code_example(self, text: Any) -> str:
        text = str(text or "").replace("Basic assignment and printing:", "").strip()
        if "Example 2" in text:
            text = text.split("Example 2", 1)[0]

        lines = []
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if clean.lower().startswith("example"):
                continue
            if "#" in clean:
                clean = clean.split("#", 1)[0].rstrip()
            if clean:
                lines.append(clean)

        preferred = [
            line for line in lines
            if (
                line.startswith("name =")
                or line.startswith("age =")
                or line.startswith("print(name)")
                or line.startswith("print(age)")
            )
        ]
        if len(preferred) >= 2:
            return "\n".join(preferred[:4])

        return "\n".join(lines[:4])

    def _safe_choice(self, items: List[str], default: str) -> str:
        clean = [x for x in items if self._clean_text(x)]
        return self.rng.choice(clean) if clean else default

    def _extract_code_example(self, examples: List[str]) -> str:
        for example in examples:
            if any(token in example for token in ["print(", "=", "if ", "for ", "while "]):
                return example.strip()
        return examples[0].strip() if examples else ""

    def _format_code_lines(self, code: str) -> str:
        if not code:
            return ""

        text = str(code).replace("\r\n", "\n").replace("\r", "\n").strip()
        text = re.sub(r";\s*", "\n", text)
        text = re.sub(r"(?<!\n)\s+(print\s*\()", r"\n\1", text)
        text = re.sub(r"(?<!\n)\s+((?:if|for|while|elif|else)\b)", r"\n\1", text)
        text = re.sub(
            r"(?<!\n)([A-Za-z_][A-Za-z0-9_]*\s*=\s*[^=\n][^\n]*?)(?=\s+[A-Za-z_][A-Za-z0-9_]*\s*=)",
            r"\1\n",
            text,
        )

        lines = [line.rstrip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _looks_like_code(self, text: str) -> bool:
        if not text:
            return False
        indicators = ["print(", "=", "if ", "for ", "while ", "def ", "return ", ":"]
        return any(token in text for token in indicators)

    def _format_example_block(self, text: str) -> str:
        if self._looks_like_code(text):
            code = self._format_code_lines(self._clean_teaching_code_example(text))
            return f"```python\n{code}\n```"
        return self._clean_text(text)

    def _sanitize_bullet_text(self, text: str) -> str:
        cleaned = self._clean_text(text)
        cleaned = re.sub(r"^[-*•]+\s*", "", cleaned)
        return cleaned

    def _format_bullets(self, items: List[str]) -> str:
        lines = []
        for item in items:
            cleaned = self._sanitize_bullet_text(item)
            if cleaned:
                lines.append(f"- {cleaned}")
        return "\n".join(lines)

    def _join_sections(self, *sections: str) -> str:
        return "\n\n".join(section for section in sections if section and section.strip())

    def _indent_block(self, text: str, prefix: str) -> str:
        return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in text.splitlines())

    def _simplify_sentence(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("utilized", "used")
        text = text.replace("represents", "shows")
        text = text.replace("storage location", "place to store data")
        return text

# ============================================================
# OPTIONAL SIMPLE WRAPPER
# ============================================================

def generate_content_bundle(
    concept_resource: Dict[str, Any],
    learner_id: Optional[str] = None,
    difficulty: str = "medium",
    requested_plan: Optional[List[Dict[str, str]]] = None,
    recent_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if recent_history is None and learner_id is not None:
        recent_history = fetch_recent_history(
            learner_id=learner_id,
            item_type="content",
            limit=30
        )

    generator = AdaptiveContentGenerator(
        recent_history=recent_history,
        random_seed=None,
    )

    result = generator.generate_content_bundle(
        concept_resource=concept_resource,
        learner_id=learner_id,
        difficulty=difficulty,
        requested_plan=requested_plan,
    )

    if learner_id is not None:
        for item in result.get("items", []):
            store_generated_item(
                learner_id=str(learner_id),
                concept_id=str(item.get("concept_id", "")),
                item_type="content",
                strategy=item.get("strategy") or "unknown",
                content_hash=item.get("content_hash"),
            )

    return result
