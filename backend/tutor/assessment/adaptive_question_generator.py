from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from tutor.memory.anti_repetition import (
    fetch_recent_history,
    store_generated_item,
)

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class GeneratedQuestion:
    question_id: str
    concept_id: str
    concept_name: str
    question_type: str
    difficulty: str
    prompt: str
    expected_answer: Any
    options: Optional[List[str]] = None
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    question_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# MAIN GENERATOR
# ============================================================

class AdaptiveQuestionGenerator:
    """
    Generation-first assessment builder.
    """

    SUPPORTED_TYPES = {
        "mcq",
        "short_explanation",
        "output_prediction",
        "debug",
        "code_writing",
        "fill_blank",
        "transfer",
        "trace",
        "misconception_identification",
        "match_the_following",
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

    def generate_question(
        self,
        concept_resource: Dict[str, Any],
        question_type: str,
        difficulty: str = "medium",
        learner_id: Optional[str] = None,
        max_attempts: int = 8,
    ) -> Dict[str, Any]:
        if question_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported question_type='{question_type}'. "
                f"Supported: {sorted(self.SUPPORTED_TYPES)}"
            )

        generator_map = {
            "mcq": self._generate_mcq,
            "short_explanation": self._generate_short_explanation,
            "output_prediction": self._generate_output_prediction,
            "debug": self._generate_debug_question,
            "code_writing": self._generate_code_writing_question,
            "fill_blank": self._generate_fill_blank_question,
            "transfer": self._generate_transfer_question,
            "trace": self._generate_trace_question,
            "misconception_identification": self._generate_misconception_identification,
            "match_the_following": self._generate_match_the_following,
        }

        generator_fn = generator_map[question_type]

        for _ in range(max_attempts):
            question = generator_fn(concept_resource, difficulty=difficulty)
            question_hash = self._compute_question_hash(question)

            if not self._is_recent_duplicate(
                learner_id=learner_id,
                concept_id=question.concept_id,
                question_type=question.question_type,
                question_hash=question_hash,
            ):
                question.question_hash = question_hash
                return question.to_dict()

        question = generator_fn(concept_resource, difficulty=difficulty)
        question.question_hash = self._compute_question_hash(question)
        meta = question.metadata or {}
        meta["repeat_fallback_used"] = True
        question.metadata = meta
        return question.to_dict()

    def generate_assessment_bundle(
            self,
            concept_resource: Dict[str, Any],
            learner_id: Optional[str] = None,
            difficulty: str = "medium",
            requested_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not requested_types:
            requested_types = [
                "mcq",
                "output_prediction",
                "debug",
                "short_explanation",
                "transfer",
            ]

        bundle: List[Dict[str, Any]] = []
        for qtype in requested_types:
            if qtype not in self.SUPPORTED_TYPES:
                continue
            bundle.append(
                self.generate_question(
                    concept_resource=concept_resource,
                    question_type=qtype,
                    difficulty=difficulty,
                    learner_id=learner_id,
                )
            )

        return {
            "status": "success",
            "concept_id": str(concept_resource.get("concept_id", "")),
            "concept_name": concept_resource.get("concept_name", ""),
            "difficulty": difficulty,
            "question_count": len(bundle),
            "questions": bundle,
        }
    # ========================================================
    # QUESTION TYPE GENERATORS
    # ========================================================

    def _generate_mcq(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")

        definition = self._clean_text(concept_resource.get("definition", ""))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))

        correct_answer = self._build_central_mcq_answer(
            concept_name=concept_name,
            definition=definition,
            key_points=key_points,
        )

        wrong_answers = self._build_distractors(
            correct_answer=correct_answer,
            misconceptions=misconceptions,
            concept_name=concept_name,
            key_points=key_points,
        )

        options = wrong_answers + [correct_answer]
        self.rng.shuffle(options)
        correct_index = options.index(correct_answer)

        prompt_templates = [
            f"Which of the following best describes {concept_name}?",
            f"Choose the correct statement about {concept_name}.",
            f"What is true about {concept_name}?",
        ]
        prompt = self._safe_choice(prompt_templates, default=f"What is {concept_name}?")

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "mcq"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="mcq",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=correct_answer,
            options=options,
            correct_option_index=correct_index,
            explanation=f"The correct choice matches the concept definition or key idea of {concept_name}.",
            metadata={"source_used": "definition/key_points/misconceptions"},
        )

    def _generate_short_explanation(
            self,
            concept_resource: Dict[str, Any],
            difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")

        prompt_variants = [
            f"Explain {concept_name} in your own words.",
            f"Write a short explanation of {concept_name}.",
            f"Describe {concept_name} briefly and clearly.",
        ]

        definition = self._clean_text(concept_resource.get("definition", ""))

        if definition:
            expected_answer = definition
        else:
            expected_answer = f"A correct answer should explain the meaning and role of {concept_name}."

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "short_explanation"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="short_explanation",
            difficulty=difficulty,
            prompt=self._safe_choice(prompt_variants, default=f"Explain {concept_name}."),
            expected_answer=expected_answer,
            explanation="Check semantic similarity, concept coverage, and misconception absence.",
            metadata={"evaluation_hint": "semantic"},
        )
    def _generate_output_prediction(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        raw_examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))

        code = self._extract_python_like_example(raw_examples)
        if not code:
            code = self._fallback_output_code(concept_name)

        code = self._focused_output_code(code)
        output = self._infer_simple_output(code)

        prompt = (
            "What is the output of the following code?\n\n"
            f"{code}"
        )

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "output_prediction"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="output_prediction",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=output,
            explanation="Evaluate exact output or normalized equivalent output.",
            metadata={"code": code},
        )

    def _generate_debug_question(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        buggy_code = 'name = Alice"\nprint(name)'
        fix = {
            "bug_category": "string_syntax",
            "fix_text": "Fix the string quotes so the syntax becomes valid.",
        }

        prompt = (
            "Find the mistake in the code below and say how to fix it:\n\n"
            f"{buggy_code}"
        )

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "debug"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="debug",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=fix,
            explanation="Check whether learner identifies the actual bug and provides a valid correction.",
            metadata={"buggy_code": buggy_code, "bug_category": fix.get("bug_category")},
        )

    def _generate_code_writing_question(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        real_world_use = self._clean_text(concept_resource.get("real_world_use", ""))
        syntax = self._clean_text(concept_resource.get("syntax", ""))

        if real_world_use:
            prompt = (
                f"Write a small code snippet that uses {concept_name} in a practical way.\n"
                f"Context: {real_world_use}"
            )
        else:
            prompt = f"Write a small code snippet that demonstrates {concept_name}."

        expected_answer = {
            "rubric": [
                f"Uses {concept_name} correctly",
                "Syntax is valid or mostly valid",
                "Shows understanding of the concept",
            ],
            "reference_hint": syntax or f"Should demonstrate the correct use of {concept_name}.",
        }

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "code_writing"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="code_writing",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=expected_answer,
            explanation="Use rubric-based and partial scoring evaluation.",
            metadata={"evaluation_hint": "rubric_partial"},
        )

    def _generate_fill_blank_question(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        definition = self._clean_text(concept_resource.get("definition", ""))

        if definition:
            sentence, answer = self._mask_definition(definition)
        else:
            sentence = f"{concept_name} is used to ______."
            answer = "store or represent information"

        prompt = f"Fill in the blank:\n\n{sentence}"

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "fill_blank"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="fill_blank",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=answer,
            explanation="Accept close paraphrases where appropriate.",
            metadata={"masked_source": "definition"},
        )

    def _generate_transfer_question(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        real_world_use = self._clean_text(concept_resource.get("real_world_use", ""))

        if real_world_use:
            prompt = (
                f"How would you apply {concept_name} in a real situation?\n"
                f"You may use this as context: {real_world_use}"
            )
            expected_answer = real_world_use
        else:
            prompt = f"Give one real-world use case of {concept_name}."
            expected_answer = f"A correct answer should connect {concept_name} to a practical application."

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "transfer"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="transfer",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=expected_answer,
            explanation="Check whether learner transfers concept understanding into a practical context.",
            metadata={"evaluation_hint": "semantic_transfer"},
        )

    def _generate_trace_question(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        raw_examples = self._normalize_to_list_preserve_code(concept_resource.get("examples"))

        code = self._extract_python_like_example(raw_examples)
        if not code:
            code = self._fallback_trace_code()

        code = self._format_code_block(code)

        prompt = (
            "Trace the code step by step and state the final output:\n\n"
            f"{code}"
        )

        expected_answer = {
            "steps": self._simple_trace_steps(code),
            "final_output": self._infer_simple_output(code),
        }

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "trace"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="trace",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=expected_answer,
            explanation="Check both intermediate reasoning and final output.",
            metadata={"code": code},
        )

    def _generate_misconception_identification(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        misconceptions = self._normalize_to_list(concept_resource.get("misconceptions"))
        key_points = self._normalize_to_list(concept_resource.get("key_points"))

        misconception = self._safe_choice(
            misconceptions,
            default=f"{concept_name} can be used without understanding its rules."
        )
        correct = misconception
        distractors = self._unique_nonempty_strings(key_points)[:3]

        while len(distractors) < 3:
            distractors.append(f"{concept_name} is an important topic in the course.")

        options = distractors + [correct]
        self.rng.shuffle(options)
        correct_index = options.index(correct)

        prompt = f"Which of the following is a common misconception about {concept_name}?"

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "misconception_identification"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="misconception_identification",
            difficulty=difficulty,
            prompt=prompt,
            expected_answer=correct,
            options=options,
            correct_option_index=correct_index,
            explanation="Learner should identify the wrong belief, not the correct fact.",
            metadata={"source_used": "misconceptions"},
        )

    def _generate_match_the_following(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str,
    ) -> GeneratedQuestion:
        concept_id = str(concept_resource.get("concept_id", ""))
        concept_name = concept_resource.get("concept_name", "Unknown Concept")
        key_points = self._normalize_to_list(concept_resource.get("key_points"))

        left_items = []
        right_items = []

        for idx, kp in enumerate(key_points[:4], start=1):
            left_items.append(f"{idx}. {concept_name} point {idx}")
            right_items.append(kp)

        if not left_items:
            left_items = ["1. Definition", "2. Use", "3. Rule"]
            right_items = [
                f"What {concept_name} means",
                f"How {concept_name} is applied",
                f"A key rule of {concept_name}",
            ]

        shuffled_right = right_items[:]
        self.rng.shuffle(shuffled_right)

        prompt_lines = ["Match the following:"]
        prompt_lines.append("\nLeft:")
        prompt_lines.extend(left_items)
        prompt_lines.append("\nRight:")
        labels = ["A", "B", "C", "D", "E", "F"]
        for label, item in zip(labels, shuffled_right):
            prompt_lines.append(f"{label}. {item}")

        expected_mapping = {}
        label_lookup = {item: label for label, item in zip(labels, shuffled_right)}
        for idx, original_item in enumerate(right_items, start=1):
            expected_mapping[str(idx)] = label_lookup.get(original_item)

        return GeneratedQuestion(
            question_id=self._make_question_id(concept_id, "match_the_following"),
            concept_id=concept_id,
            concept_name=concept_name,
            question_type="match_the_following",
            difficulty=difficulty,
            prompt="\n".join(prompt_lines),
            expected_answer=expected_mapping,
            explanation="Accept equivalent match mapping format.",
            metadata={"left_items": left_items, "right_items": shuffled_right},
        )

    # ========================================================
    # ANTI-REPETITION
    # ========================================================

    def _compute_question_hash(self, question: GeneratedQuestion) -> str:
        base = f"{question.concept_id}|{question.question_type}|{question.prompt}|{question.expected_answer}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    def _is_recent_duplicate(
        self,
        learner_id: Optional[str],
        concept_id: str,
        question_type: str,
        question_hash: str,
    ) -> bool:
        recent_items = self.recent_history[-self.history_limit:]
        for item in recent_items:
            if learner_id is not None and str(item.get("learner_id")) not in {"", str(learner_id)}:
                continue

            same_concept = str(item.get("concept_id")) == str(concept_id)
            same_type = str(item.get("question_type")) == str(question_type)
            same_hash = str(item.get("question_hash")) == str(question_hash)

            if same_concept and same_type and same_hash:
                return True
        return False

    # ========================================================
    # HELPERS
    # ========================================================

    def _make_question_id(self, concept_id: str, question_type: str) -> str:
        token = self.rng.randint(100000, 999999)
        return f"{concept_id}_{question_type}_{token}"

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

    def _safe_choice(self, items: List[str], default: str) -> str:
        clean = [x for x in items if self._clean_text(x)]
        return self.rng.choice(clean) if clean else default

    def _unique_nonempty_strings(self, items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            cleaned = self._clean_text(item)
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                seen.add(lowered)
                result.append(cleaned)
        return result

    def _build_distractors(
        self,
        correct_answer: str,
        misconceptions: List[str],
        concept_name: str,
        key_points: Optional[List[str]] = None,
    ) -> List[str]:
        distractors = []
        for misconception in self._unique_nonempty_strings(misconceptions):
            short_item = self._shorten_mcq_statement(misconception, concept_name, force_concise=True)
            if short_item and self._is_good_distractor(short_item, correct_answer, concept_name):
                distractors.append(short_item)

        for point in self._unique_nonempty_strings(key_points or []):
            transformed = self._derive_wrong_statement_from_key_point(point, concept_name)
            if transformed and self._is_good_distractor(transformed, correct_answer, concept_name):
                distractors.append(transformed)

        distractors.extend(self._generic_misconception_pool(concept_name, correct_answer))
        distractors = self._unique_nonempty_strings(distractors)
        self.rng.shuffle(distractors)

        final = []
        seen = {correct_answer.lower()}
        for d in distractors:
            if d.lower() not in seen:
                final.append(d)
                seen.add(d.lower())
            if len(final) == 3:
                break

        while len(final) < 3:
            filler = f"{concept_name} works without following rules."
            if filler.lower() not in seen:
                final.append(filler)
                seen.add(filler.lower())
            else:
                break

        return final

    def _build_central_mcq_answer(
        self,
        concept_name: str,
        definition: str,
        key_points: List[str],
    ) -> str:
        if definition:
            cleaned_definition = self._shorten_mcq_statement(definition, concept_name)
            if cleaned_definition:
                return cleaned_definition

        ranked_key_points = sorted(
            self._unique_nonempty_strings(key_points),
            key=lambda kp: self._score_key_point_centrality(kp, concept_name),
            reverse=True,
        )

        for point in ranked_key_points:
            if self._score_key_point_centrality(point, concept_name) >= 2:
                cleaned_point = self._shorten_mcq_statement(point, concept_name)
                if cleaned_point:
                    return cleaned_point

        return f"{concept_name} is a basic programming concept."

    def _score_key_point_centrality(self, key_point: str, concept_name: str) -> int:
        text = self._clean_text(key_point).lower()
        if not text:
            return -10

        score = 0
        concept_tokens = [token for token in re.findall(r"[a-z]+", concept_name.lower()) if len(token) > 2]
        central_terms = concept_tokens + [
            "store", "stores", "value", "values", "data", "name", "named",
            "variable", "variables", "hold", "holds", "assign", "assignment",
        ]
        noisy_terms = [
            "example", "debug", "identity", "constant", "comparison", "advanced",
            "practice", "remember", "syntax rule", "output", "line by line",
        ]

        for term in central_terms:
            if term in text:
                score += 2
        for term in noisy_terms:
            if term in text:
                score -= 2

        word_count = len(text.split())
        if 4 <= word_count <= 12:
            score += 1
        elif word_count > 18:
            score -= 2

        if any(text.startswith(prefix) for prefix in ["a ", "an ", f"{concept_name.lower()} "]):
            score += 1

        return score

    def _shorten_mcq_statement(self, text: str, concept_name: str, force_concise: bool = False) -> str:
        sentence = self._to_single_sentence(text)
        if not sentence:
            return ""

        sentence = re.sub(r"^[-*•]+\s*", "", sentence)
        sentence = re.sub(r'^["\']+', "", sentence)
        sentence = sentence.replace(" - ", ". ")
        sentence = self._to_single_sentence(sentence)
        sentence = re.sub(r"^[Tt]his means\s+", "", sentence).strip()
        sentence = re.sub(r"^[Ii]n programming,\s*", "", sentence).strip()
        sentence = re.sub(r"^[Aa] common misconception is:? ?", "", sentence).strip()
        sentence = re.sub(r"\bthat is used to\b", "used to", sentence)
        sentence = re.sub(r"\bis a named storage location used to hold\b", "stores", sentence)
        sentence = re.sub(r"\bis used to store\b", "stores", sentence)
        sentence = re.sub(r"\bcan be reused or updated during program execution\b", "can be reused or updated", sentence)
        sentence = re.sub(r"\s+", " ", sentence).strip(" -")

        max_words = 11 if force_concise else 14
        if len(sentence.split()) > max_words:
            if " is " in sentence:
                left, right = sentence.split(" is ", 1)
                sentence = f"{left} is {right.split(',')[0].split(';')[0].strip()}"
            elif "," in sentence:
                sentence = sentence.split(",", 1)[0].strip()
            elif " and " in sentence and force_concise:
                sentence = sentence.split(" and ", 1)[0].strip()

        if concept_name.lower() == "variables":
            sentence = sentence.replace("Variables is", "Variables are")
        sentence = sentence.strip().strip("\"'")

        return sentence.rstrip(".") + "."

    def _to_single_sentence(self, text: str) -> str:
        cleaned = self._clean_text(text)
        if not cleaned:
            return ""
        return re.split(r"(?<=[.!?])\s+", cleaned)[0].strip()

    def _is_good_distractor(self, text: str, correct_answer: str, concept_name: str) -> bool:
        lowered = text.lower()
        if lowered == correct_answer.lower():
            return False
        if text_similarity := self._simple_similarity(text, correct_answer):
            if text_similarity > 0.92:
                return False
        blocked_terms = [
            "example",
            "debug",
            "file path",
            "class object",
            "identity",
            "==",
            "fixed types",
            "constant",
            "reference bound",
            "independent copy",
            "mutable objects",
            "copy.deepcopy",
        ]
        if any(term in lowered for term in blocked_terms):
            return False
        if lowered.startswith(("is and", "== checks", "pythonic swap")):
            return False
        if len(text.split()) > 14:
            return False
        return True

    def _generic_misconception_pool(self, concept_name: str, correct_answer: str) -> List[str]:
        plural = concept_name.strip().lower().endswith("s")
        never_change = "never change once they are created" if plural else "never changes once it is created"
        any_name = "can have any names without following naming rules" if plural else "can have any name without following naming rules"
        no_value = "can be used without assigning values" if plural else "can be used without assigning any value"
        advanced_only = "are only for advanced programs" if plural else "is only for advanced programs"
        base_pool = [
            f"{concept_name} {no_value}.",
            f"{concept_name} {never_change}.",
            f"{concept_name} {any_name}.",
            f"{concept_name} {advanced_only}.",
        ]
        return [item for item in base_pool if item.lower() != correct_answer.lower()]

    def _derive_wrong_statement_from_key_point(self, key_point: str, concept_name: str) -> str:
        text = self._clean_text(key_point)
        lowered = text.lower()
        if not text:
            return ""

        replacements = [
            ("store values", "do not store values"),
            ("stores values", "does not store values"),
            ("stores data", "does not store data"),
            ("must start with", "can start with"),
            ("cannot", "can"),
            ("can be updated", "cannot be updated"),
            ("are case-sensitive", "are not case-sensitive"),
            ("is case-sensitive", "is not case-sensitive"),
        ]
        for source, target in replacements:
            if source in lowered:
                pattern = re.compile(re.escape(source), re.IGNORECASE)
                transformed = pattern.sub(target, text, count=1)
                return self._shorten_mcq_statement(transformed, concept_name, force_concise=True)
        return ""

    def _simple_similarity(self, a: str, b: str) -> float:
        a_words = set(self._clean_text(a).lower().split())
        b_words = set(self._clean_text(b).lower().split())
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / max(len(a_words), len(b_words))

    def _extract_python_like_example(self, examples: List[str]) -> str:
        for example in examples:
            if any(token in example for token in ["print(", "=", "if ", "for ", "while "]):
                return self._short_code_example(example)

        return self._short_code_example(examples)

    def _short_code_example(self, examples: Any) -> str:
        if isinstance(examples, list) and examples:
            text = examples[0]
        else:
            text = str(examples or "")

        if "Example 2" in text:
            text = text.split("Example 2", 1)[0]

        lines = [line for line in str(text).splitlines() if line.strip()]
        return "\n".join(lines[:6])

    def _remove_text_noise(self, text: Any) -> str:
        text = str(text or "")
        text = text.replace("Basic assignment and printing:", "")
        return text.strip()

    def _remove_inline_comments(self, code: Any) -> str:
        cleaned_lines = []
        for line in str(code or "").splitlines():
            if "#" in line:
                line = line.split("#", 1)[0].rstrip()
            if line.strip():
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _focused_output_code(self, code: str) -> str:
        if "Basic assignment" in code:
            code = code.split("Basic assignment", 1)[-1].strip()

        code = self._remove_text_noise(code)
        code = self._remove_inline_comments(code)
        code = self._format_code_block(code)

        lines = [line for line in code.splitlines() if line.strip()]
        print_lines = [line for line in lines if line.strip().startswith("print(")]
        assign_lines = [
            line for line in lines
            if "=" in line and not line.strip().startswith("print(")
        ]

        if assign_lines and print_lines:
            return assign_lines[0] + "\n" + print_lines[0]
        return "\n".join(lines[:2])

    def _format_code_block(self, code: str) -> str:
        if not code:
            return ""

        code = code.replace("\r\n", "\n").replace("\r", "\n")
        code = code.replace(";", "\n")

        code = re.sub(r"\s+(print\s*\()", r"\n\1", code)
        code = re.sub(r"\s+(if\s+)", r"\n\1", code)
        code = re.sub(r"\s+(for\s+)", r"\n\1", code)
        code = re.sub(r"\s+(while\s+)", r"\n\1", code)

        code = re.sub(
            r"(?<!\n)([A-Za-z_][A-Za-z0-9_]*\s*=\s*[^=\n][^\n]*?)(?=\s+[A-Za-z_][A-Za-z0-9_]*\s*=)",
            r"\1\n",
            code,
        )

        lines = [re.sub(r"\s+", " ", line).strip() for line in code.split("\n")]
        lines = [line for line in lines if line]

        return "\n".join(lines)

    def _fallback_output_code(self, concept_name: str) -> str:
        if "variable" in concept_name.lower():
            return "x = 5\ny = x + 2\nprint(y)"
        return "a = 2\nb = 3\nprint(a + b)"

    def _fallback_trace_code(self) -> str:
        return "x = 1\nx = x + 2\nprint(x)"

    def _infer_simple_output(self, code: str) -> str:
        try:
            env: Dict[str, Any] = {}
            lines = [line.strip() for line in code.splitlines() if line.strip()]

            outputs = []
            for line in lines:
                shown_output = ""
                if "#" in line:
                    line, shown_output = line.split("#", 1)
                    line = line.strip()
                    shown_output = shown_output.strip()

                if not line:
                    continue

                if line.startswith("print(") and line.endswith(")"):
                    expr = line[6:-1].strip()
                    try:
                        val = eval(expr, {"__builtins__": {}}, {**env, "type": type})  # noqa: S307
                        outputs.append(str(val))
                    except Exception:
                        if shown_output:
                            outputs.append(shown_output)
                elif "=" in line and "==" not in line:
                    lhs, rhs = line.split("=", 1)
                    lhs = lhs.strip()
                    rhs = rhs.strip()
                    env[lhs] = eval(rhs, {"__builtins__": {}}, env)  # noqa: S307

            if outputs:
                return "\n".join(outputs)
            if "print(" in code:
                return "Expected output depends on correct line-by-line tracing."
            return "\n".join(outputs) if outputs else "No output"
        except Exception:
            if "print(" in code:
                return "Expected output depends on correct line-by-line tracing."
            return "Expected output depends on correct line-by-line tracing."

    def _inject_bug(
        self,
        base_code: str,
        concept_name: str,
        misconceptions: List[str],
    ) -> Tuple[str, Dict[str, str]]:
        if not base_code:
            base_code = "x = 5\nprint(x)"

        if "==" in base_code:
            buggy_code = base_code.replace("==", "=", 1)
            return buggy_code, {
                "bug_category": "comparison_vs_assignment",
                "fix_text": "Use '==' for comparison instead of '='.",
            }

        if "print(" in base_code and '"' in base_code:
            buggy_code = base_code.replace('"', "", 1)
            return buggy_code, {
                "bug_category": "string_syntax",
                "fix_text": "Fix the string quotes so the syntax becomes valid.",
            }

        assignment_lines = [line for line in base_code.splitlines() if "=" in line and "==" not in line]
        if assignment_lines:
            first_line = assignment_lines[0]
            match = re.match(r"\s*([a-zA-Z_]\w*)\s*=", first_line)
            if match:
                variable = match.group(1)
                buggy_line = first_line.replace(variable, variable + "1", 1)
                buggy_code = base_code.replace(first_line, buggy_line, 1)
                return buggy_code, {
                    "bug_category": "wrong_variable_name",
                    "fix_text": f"Use the correct variable name '{variable}' consistently.",
                }

        misconception_text = self._safe_choice(
            misconceptions,
            default=f"{concept_name} is often misused because of small syntax mistakes."
        )
        buggy_code = base_code + "\nprint(result)"
        return buggy_code, {
            "bug_category": "undefined_variable",
            "fix_text": f"Define 'result' before printing it. Related misconception: {misconception_text}",
        }

    def _mask_definition(self, definition: str) -> Tuple[str, str]:
        words = definition.split()
        if not words:
            return "______", ""

        candidate_indexes = [i for i, w in enumerate(words) if len(w) > 4]
        if not candidate_indexes:
            candidate_indexes = [0]

        idx = self.rng.choice(candidate_indexes)
        answer = words[idx].strip(".,:;!?")
        words[idx] = "______"
        return " ".join(words), answer

    def _simple_trace_steps(self, code: str) -> List[str]:
        steps = []
        env: Dict[str, Any] = {}
        lines = [line.strip() for line in code.splitlines() if line.strip()]

        for line in lines:
            if line.startswith("print("):
                expr = line[6:-1].strip()
                try:
                    value = eval(expr, {"__builtins__": {}}, env)  # noqa: S307
                    steps.append(f"{line} -> prints {value}")
                except Exception:
                    steps.append(f"{line} -> evaluate expression")
            elif "=" in line and "==" not in line:
                lhs, rhs = line.split("=", 1)
                lhs = lhs.strip()
                rhs = rhs.strip()
                try:
                    value = eval(rhs, {"__builtins__": {}}, env)  # noqa: S307
                    env[lhs] = value
                    steps.append(f"{lhs} becomes {value}")
                except Exception:
                    steps.append(f"Execute assignment: {line}")
            else:
                steps.append(f"Execute line: {line}")

        return steps


# ============================================================
# OPTIONAL SIMPLE WRAPPER
# ============================================================

def generate_assessment_bundle(
    concept_resource: Dict[str, Any],
    learner_id: Optional[str] = None,
    difficulty: str = "medium",
    requested_types: Optional[List[str]] = None,
    recent_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if recent_history is None and learner_id is not None:
        recent_history = fetch_recent_history(
            learner_id=learner_id,
            item_type="question",
            limit=30
        )

    generator = AdaptiveQuestionGenerator(
        recent_history=recent_history,
        random_seed=None,
    )

    result = generator.generate_assessment_bundle(
        concept_resource=concept_resource,
        learner_id=learner_id,
        difficulty=difficulty,
        requested_types=requested_types,
    )

    if learner_id is not None:
        for q in result.get("questions", []):
            store_generated_item(
                learner_id=str(learner_id),
                concept_id=str(q.get("concept_id", "")),
                item_type="question",
                strategy=q.get("question_type"),
                question_hash=q.get("question_hash"),
            )

    return result
