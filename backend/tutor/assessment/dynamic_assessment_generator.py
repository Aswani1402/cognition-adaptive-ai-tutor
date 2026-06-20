from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List


def _hash_text(text: str) -> str:
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _get_topic(concept_resource: Dict[str, Any]) -> str:
    return (
        concept_resource.get("concept_name")
        or concept_resource.get("topic")
        or concept_resource.get("name")
        or "Concept"
    )


def _get_definition(concept_resource: Dict[str, Any]) -> str:
    return (
        concept_resource.get("definition")
        or concept_resource.get("base_content")
        or concept_resource.get("content")
        or ""
    )


def _short_code_example(examples: Any) -> str:
    examples_list = _as_list(examples)

    if examples_list:
        text = examples_list[0]
    else:
        text = ""

    if "Example 2" in text:
        text = text.split("Example 2")[0]

    text = text.replace("```python", "").replace("```", "").strip()

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:6])


def _remove_text_noise(text: str) -> str:
    text = str(text or "")
    text = text.replace("Basic assignment and printing:", "")
    return text.strip()


def _remove_inline_comments(code: str) -> str:
    cleaned_lines = []

    for line in str(code or "").splitlines():
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if line.strip():
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def _expected_output_for_code(code: str) -> str:
    code_clean = _remove_inline_comments(code)

    if "print(name)" in code_clean and "name" in code_clean:
        return "Alice"

    if "print(age)" in code_clean and "age" in code_clean:
        return "30"

    if "print(x)" in code_clean and "x = 5" in code_clean:
        return "5"

    if "print(y)" in code_clean and "y = x + 2" in code_clean:
        return "7"

    if "print(total)" in code_clean and "price" in code_clean:
        return "150"

    return "Expected output depends on correct line-by-line tracing."


def _make_mcq(
    concept_id: str,
    topic: str,
    definition: str,
    key_points: List[str],
    misconceptions: List[str],
    difficulty: str,
) -> Dict[str, Any]:

    correct = definition or f"{topic} is an important programming concept."

    distractors = []

    for m in misconceptions[:2]:
        if isinstance(m, str) and m.strip():
            distractors.append(m.strip())

    distractors.extend([
        "Variables can have any names without following naming rules.",
        "Variables can be used without assigning values.",
        "Python reserved keywords can be used as variable names.",
        "Variables are not case-sensitive.",
    ])

    options = [correct] + distractors[:3]
    random.shuffle(options)

    return {
        "question_id": f"{concept_id}_mcq_{random.randint(100000, 999999)}",
        "concept_id": concept_id,
        "concept_name": topic,
        "question_type": "mcq",
        "difficulty": difficulty,
        "prompt": f"What is true about {topic}?",
        "expected_answer": correct,
        "options": options,
        "correct_option_index": options.index(correct),
        "explanation": f"The correct choice matches the concept definition or key idea of {topic}.",
        "metadata": {
            "source_used": "definition/key_points/misconceptions"
        },
        "question_hash": _hash_text(f"{concept_id}|mcq|{correct}"),
    }


def _make_output_prediction(
    concept_id: str,
    topic: str,
    examples: List[str],
    difficulty: str,
) -> Dict[str, Any]:

    code = _short_code_example(examples)

    if not code:
        code = 'name = "Alice"\nprint(name)'

    if "Basic assignment" in code:
        code = code.split("Basic assignment")[-1].strip()

    code = _remove_text_noise(code)
    code = _remove_inline_comments(code)

    lines = [line for line in code.splitlines() if line.strip()]
    print_lines = [line for line in lines if line.strip().startswith("print(")]
    assign_lines = [line for line in lines if "=" in line and not line.strip().startswith("print(")]

    if assign_lines and print_lines:
        code = assign_lines[0] + "\n" + print_lines[0]
    else:
        code = "\n".join(lines[:2])

    expected = _expected_output_for_code(code)

    return {
        "question_id": f"{concept_id}_output_prediction_{random.randint(100000, 999999)}",
        "concept_id": concept_id,
        "concept_name": topic,
        "question_type": "output_prediction",
        "difficulty": difficulty,
        "prompt": f"What is the output of the following code?\n\n{code}",
        "expected_answer": expected,
        "options": None,
        "correct_option_index": None,
        "explanation": "Evaluate exact output or normalized equivalent output.",
        "metadata": {
            "code": code
        },
        "question_hash": _hash_text(f"{concept_id}|output|{code}|{expected}"),
    }


def _make_debug_question(
    concept_id: str,
    topic: str,
    concept_resource: Dict[str, Any],
    difficulty: str,
) -> Dict[str, Any]:

    buggy_code = 'name = Alice"\nprint(name)'
    expected_fix = 'name = "Alice"\nprint(name)'
    bug_type = "string_syntax"

    return {
        "question_id": f"{concept_id}_debug_{random.randint(100000, 999999)}",
        "concept_id": concept_id,
        "concept_name": topic,
        "question_type": "debug",
        "difficulty": difficulty,
        "prompt": f"Find the mistake in the code below and say how to fix it:\n\n{buggy_code}",
        "expected_answer": {
            "bug_category": bug_type,
            "fix_text": "Fix the string quotes so the syntax becomes valid.",
            "expected_fix": expected_fix,
        },
        "options": None,
        "correct_option_index": None,
        "explanation": "Check whether learner identifies the actual bug and provides a valid correction.",
        "metadata": {
            "buggy_code": buggy_code,
            "bug_category": bug_type,
        },
        "question_hash": _hash_text(f"{concept_id}|debug|{buggy_code}|{expected_fix}"),
    }


def _make_short_explanation(
    concept_id: str,
    topic: str,
    definition: str,
    difficulty: str,
) -> Dict[str, Any]:

    return {
        "question_id": f"{concept_id}_short_explanation_{random.randint(100000, 999999)}",
        "concept_id": concept_id,
        "concept_name": topic,
        "question_type": "short_explanation",
        "difficulty": difficulty,
        "prompt": f"Write a short explanation of {topic}.",
        "expected_answer": definition or f"Explain the meaning and purpose of {topic}.",
        "options": None,
        "correct_option_index": None,
        "explanation": "Check semantic similarity, concept coverage, and misconception absence.",
        "metadata": {
            "evaluation_hint": "semantic"
        },
        "question_hash": _hash_text(f"{concept_id}|explanation|{definition}"),
    }


def _make_transfer_question(
    concept_id: str,
    topic: str,
    real_world_use: str,
    difficulty: str,
) -> Dict[str, Any]:

    context = real_world_use or f"Use {topic} in a practical programming task."

    return {
        "question_id": f"{concept_id}_transfer_{random.randint(100000, 999999)}",
        "concept_id": concept_id,
        "concept_name": topic,
        "question_type": "transfer",
        "difficulty": difficulty,
        "prompt": f"How would you apply {topic} in a real situation?\nYou may use this as context: {context}",
        "expected_answer": context,
        "options": None,
        "correct_option_index": None,
        "explanation": "Check whether learner transfers concept understanding into a practical context.",
        "metadata": {
            "evaluation_hint": "semantic_transfer"
        },
        "question_hash": _hash_text(f"{concept_id}|transfer|{context}"),
    }


def generate_assessment_bundle(
    concept_resource: Dict[str, Any],
    learner_id: str | None = None,
    difficulty: str = "easy",
    requested_types: List[str] | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:

    concept_id = str(
        concept_resource.get("concept_id")
        or concept_resource.get("system_concept_id")
        or "unknown"
    )

    topic = _get_topic(concept_resource)
    definition = _get_definition(concept_resource)

    examples = _as_list(concept_resource.get("examples", []))
    key_points = _as_list(concept_resource.get("key_points", []))
    misconceptions = _as_list(concept_resource.get("misconceptions", []))
    real_world_use = str(concept_resource.get("real_world_use", "") or "")

    requested_types = requested_types or [
        "mcq",
        "output_prediction",
        "debug",
        "short_explanation",
        "transfer",
    ]

    questions: List[Dict[str, Any]] = []

    for qtype in requested_types:
        if qtype == "mcq":
            questions.append(
                _make_mcq(
                    concept_id=concept_id,
                    topic=topic,
                    definition=definition,
                    key_points=key_points,
                    misconceptions=misconceptions,
                    difficulty=difficulty,
                )
            )

        elif qtype == "output_prediction":
            questions.append(
                _make_output_prediction(
                    concept_id=concept_id,
                    topic=topic,
                    examples=examples,
                    difficulty=difficulty,
                )
            )

        elif qtype == "debug":
            questions.append(
                _make_debug_question(
                    concept_id=concept_id,
                    topic=topic,
                    concept_resource=concept_resource,
                    difficulty=difficulty,
                )
            )

        elif qtype in {"short_explanation", "explanation"}:
            questions.append(
                _make_short_explanation(
                    concept_id=concept_id,
                    topic=topic,
                    definition=definition,
                    difficulty=difficulty,
                )
            )

        elif qtype == "transfer":
            questions.append(
                _make_transfer_question(
                    concept_id=concept_id,
                    topic=topic,
                    real_world_use=real_world_use,
                    difficulty=difficulty,
                )
            )

    return {
        "status": "success",
        "concept_id": concept_id,
        "concept_name": topic,
        "difficulty": difficulty,
        "question_count": len(questions),
        "questions": questions,
    }
