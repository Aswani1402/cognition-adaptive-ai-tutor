from __future__ import annotations

from typing import Any, Dict, List

from tutor.assessment.structured_question_types import (
    make_syntax_completion_question,
    make_code_writing_question,
    make_arrange_steps_question,
    make_drag_order_question,
    make_match_pairs_question,
    make_fill_blank_question,
    make_code_puzzle_question,
    make_challenge_question,
    normalize_assessment_bundle_for_frontend,
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("|", "\n").splitlines()]
        return [part for part in parts if part]
    if value is None:
        return []
    return [str(value).strip()]


def _first_non_empty(*values: Any, default: str = "") -> str:
    for value in values:
        text = _safe_str(value).strip()
        if text:
            return text
    return default


def _get_concept_field(concept_resource: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = concept_resource.get(key)
        if value:
            return value
    return default


def _get_examples(concept_resource: Dict[str, Any]) -> List[str]:
    examples = _get_concept_field(
        concept_resource,
        "examples",
        "examples_base",
        "new_example",
        default=[],
    )
    return _safe_list(examples)


def _get_key_points(concept_resource: Dict[str, Any]) -> List[str]:
    key_points = _get_concept_field(
        concept_resource,
        "key_points",
        "key_points_base",
        default=[],
    )
    return _safe_list(key_points)


def _get_definition(concept_resource: Dict[str, Any]) -> str:
    return _first_non_empty(
        concept_resource.get("definition"),
        concept_resource.get("base_content"),
        concept_resource.get("expanded_definition"),
        default="",
    )


def _get_syntax(concept_resource: Dict[str, Any], concept_name: str) -> str:
    syntax = _first_non_empty(
        concept_resource.get("syntax"),
        concept_resource.get("basic_syntax"),
        default="",
    )

    if syntax:
        return syntax

    name = concept_name.lower()

    if "variable" in name:
        return "variable_name = value"
    if "loop" in name:
        return "for item in collection:"
    if "condition" in name or "if" in name:
        return "if condition:"
    if "function" in name:
        return "def function_name():"
    if "select" in name:
        return "SELECT column_name FROM table_name;"
    if "where" in name or "filter" in name:
        return "SELECT column_name FROM table_name WHERE condition;"
    if "join" in name:
        return "SELECT * FROM table_a JOIN table_b ON table_a.id = table_b.id;"
    if "html" in name or "tag" in name:
        return "<tag>content</tag>"
    if "git" in name or "commit" in name:
        return "git commit -m \"message\""

    return "concept_syntax_here"


def _make_example_code(concept_name: str, syntax: str, examples: List[str]) -> str:
    if examples:
        example = examples[0]
        if any(token in example for token in ["print(", "SELECT", "<", "git "]):
            return example

    name = concept_name.lower()

    if "variable" in name:
        return 'name = "Alice"\nprint(name)'
    if "data type" in name:
        return 'age = 20\nprint(type(age))'
    if "condition" in name:
        return 'age = 18\nif age >= 18:\n    print("adult")'
    if "loop" in name:
        return 'for i in range(3):\n    print(i)'
    if "function" in name:
        return 'def greet(name):\n    print("Hello", name)\n\ngreet("Alice")'
    if "select" in name:
        return "SELECT name FROM students;"
    if "where" in name or "filter" in name:
        return "SELECT name FROM students WHERE age > 18;"
    if "html" in name or "tag" in name:
        return "<p>Hello</p>"
    if "git" in name:
        return 'git commit -m "Add feature"'

    return syntax


def _make_incomplete_code(example_code: str, syntax: str, concept_name: str) -> tuple[str, str]:
    name = concept_name.lower()

    if "variable" in name:
        return "_____ = 10\nprint(x)", "x"

    if "loop" in name:
        return "for i in _____:\n    print(i)", "range(3)"

    if "condition" in name:
        return "if _____:\n    print('yes')", "condition"

    if "function" in name:
        return "def _____():\n    print('hello')", "function_name"

    if "select" in name:
        return "_____ name FROM students;", "SELECT"

    if "where" in name or "filter" in name:
        return "SELECT name FROM students _____ age > 18;", "WHERE"

    if "html" in name or "tag" in name:
        return "<_____>Hello</_____>", "p"

    if "git" in name:
        return "git _____ -m \"message\"", "commit"

    if syntax and " " in syntax:
        first_part = syntax.split()[0]
        return syntax.replace(first_part, "_____", 1), first_part

    return "Complete this syntax: _____", syntax or "missing_part"


def _build_drag_order_items(concept_name: str) -> tuple[List[str], List[int]]:
    name = concept_name.lower()

    if "variable" in name:
        return ["Use the variable", "Choose a valid name", "Assign a value"], [1, 2, 0]

    if "loop" in name:
        return ["Write loop body", "Choose iterable/range", "Write loop header"], [2, 1, 0]

    if "condition" in name:
        return ["Write action block", "Check condition", "Use if keyword"], [2, 1, 0]

    if "function" in name:
        return ["Call the function", "Define function body", "Write function header"], [2, 1, 0]

    if "select" in name:
        return ["Choose table", "Choose column", "Use SELECT query"], [2, 1, 0]

    if "html" in name or "tag" in name:
        return ["Close the tag", "Write content", "Open the tag"], [2, 1, 0]

    return ["Understand the concept", "Apply it in an example", "Check the result"], [0, 1, 2]


def _build_arrange_steps(concept_name: str) -> tuple[List[str], List[int]]:
    name = concept_name.lower()

    if "variable" in name:
        return ["Choose a valid variable name", "Assign a value", "Use the variable in code"], [0, 1, 2]

    if "loop" in name:
        return ["Write the loop header", "Indent the loop body", "Update or process the item"], [0, 1, 2]

    if "condition" in name:
        return ["Write the if keyword", "Add a condition", "Indent the block to run"], [0, 1, 2]

    if "function" in name:
        return ["Define the function header", "Write the function body", "Call the function"], [0, 1, 2]

    if "select" in name:
        return ["Choose the columns", "Choose the table", "Run the SELECT query"], [0, 1, 2]

    if "html" in name or "tag" in name:
        return ["Open the tag", "Add the content", "Close the tag"], [0, 1, 2]

    return ["Read the problem", "Apply the concept", "Check the result"], [0, 1, 2]


def _build_match_pairs(concept_name: str, key_points: List[str]) -> List[Dict[str, str]]:
    name = concept_name.lower()

    if "variable" in name:
        return [
            {"left": "variable", "right": "name linked to a value"},
            {"left": "assignment", "right": "giving a value to a name"},
            {"left": "dynamic typing", "right": "type is decided by assigned value"},
        ]

    if "loop" in name:
        return [
            {"left": "loop", "right": "repeats a block of code"},
            {"left": "iteration", "right": "one repetition of a loop"},
            {"left": "range", "right": "generates a sequence of numbers"},
        ]

    if "condition" in name:
        return [
            {"left": "if", "right": "runs code when condition is true"},
            {"left": "else", "right": "runs alternate code"},
            {"left": "boolean", "right": "true or false value"},
        ]

    if "select" in name:
        return [
            {"left": "SELECT", "right": "chooses columns"},
            {"left": "FROM", "right": "chooses table"},
            {"left": "result set", "right": "rows returned by query"},
        ]

    if "html" in name or "tag" in name:
        return [
            {"left": "tag", "right": "HTML marker"},
            {"left": "element", "right": "opening tag, content, closing tag"},
            {"left": "attribute", "right": "extra information inside tag"},
        ]

    pairs = []
    for idx, point in enumerate(key_points[:3], start=1):
        pairs.append(
            {
                "left": f"Key idea {idx}",
                "right": point,
            }
        )

    return pairs or [
        {"left": concept_name, "right": "main concept being learned"},
        {"left": "example", "right": "practical use of concept"},
    ]


def _build_fill_blank(concept_name: str, definition: str) -> tuple[str, List[str]]:
    name = concept_name.lower()

    if "variable" in name:
        return "A variable is a ____ linked to a value.", ["name"]

    if "loop" in name:
        return "A loop is used to ____ a block of code.", ["repeat"]

    if "condition" in name:
        return "A conditional runs code based on whether a condition is ____.", ["true"]

    if "function" in name:
        return "A function is a reusable ____ of code.", ["block"]

    if "select" in name:
        return "The SELECT statement is used to retrieve ____ from a table.", ["columns"]

    if "html" in name or "tag" in name:
        return "HTML tags are used to structure ____ on a web page.", ["content"]

    if definition:
        words = definition.split()
        if len(words) >= 5:
            blank = words[1].strip(".,")
            words[1] = "____"
            return " ".join(words), [blank]

    return f"{concept_name} helps organize and apply ____.", ["knowledge"]


def _build_code_puzzle(concept_name: str) -> tuple[str, str, str]:
    name = concept_name.lower()

    if "variable" in name:
        return 'name = "Alice"\n____', "print(name)", "Alice"

    if "loop" in name:
        return "numbers = [1, 2, 3]\nfor n in numbers:\n    ____", "print(n)", "1\n2\n3"

    if "condition" in name:
        return "age = 18\nif age >= 18:\n    ____", 'print("adult")', "adult"

    if "function" in name:
        return 'def greet(name):\n    ____\n\ngreet("Alice")', 'print("Hello", name)', "Hello Alice"

    if "select" in name:
        return "____ name FROM students;", "SELECT", "Query returns selected names"

    return "value = 3\n____", "print(value)", "3"


def generate_expanded_assessment_questions(
    concept_resource: Dict[str, Any],
    requested_types: List[str],
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    concept_resource = concept_resource if isinstance(concept_resource, dict) else {}

    concept_id = _safe_str(concept_resource.get("concept_id", ""))
    concept_name = _first_non_empty(
        concept_resource.get("concept_name"),
        concept_resource.get("topic"),
        default="Unknown Concept",
    )

    definition = _get_definition(concept_resource)
    examples = _get_examples(concept_resource)
    key_points = _get_key_points(concept_resource)
    syntax = _get_syntax(concept_resource, concept_name)
    example_code = _make_example_code(concept_name, syntax, examples)

    requested_types = [str(item).strip() for item in requested_types if str(item).strip()]

    questions: List[Dict[str, Any]] = []

    for question_type in requested_types:
        if question_type == "syntax_completion":
            incomplete_code, missing_part = _make_incomplete_code(
                example_code=example_code,
                syntax=syntax,
                concept_name=concept_name,
            )

            questions.append(
                make_syntax_completion_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    incomplete_code=incomplete_code,
                    missing_part=missing_part,
                )
            )

        elif question_type == "code_writing":
            questions.append(
                make_code_writing_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    task=f"Write a short example that uses {concept_name} correctly.",
                    expected_features=[
                        "uses correct syntax",
                        "shows the concept clearly",
                        "produces or explains a result",
                    ],
                )
            )

        elif question_type == "drag_order":
            items, correct_order = _build_drag_order_items(concept_name)

            questions.append(
                make_drag_order_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    prompt=f"Arrange the steps for using {concept_name} correctly.",
                    items=items,
                    correct_order=correct_order,
                )
            )

        elif question_type == "arrange_steps":
            steps, correct_order = _build_arrange_steps(concept_name)

            questions.append(
                make_arrange_steps_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    prompt="Arrange the steps in correct order.",
                    steps=steps,
                    correct_order=correct_order,
                )
            )

        elif question_type == "match_pairs":
            questions.append(
                make_match_pairs_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    prompt=f"Match each term related to {concept_name} with its meaning.",
                    pairs=_build_match_pairs(concept_name, key_points),
                )
            )

        elif question_type == "fill_blank":
            sentence, blanks = _build_fill_blank(concept_name, definition)

            questions.append(
                make_fill_blank_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    sentence=sentence,
                    blanks=blanks,
                )
            )

        elif question_type == "code_puzzle":
            starter_code, answer, expected_output = _build_code_puzzle(concept_name)

            questions.append(
                make_code_puzzle_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    starter_code=starter_code,
                    answer=answer,
                    expected_output=expected_output,
                )
            )

        elif question_type == "challenge":
            questions.append(
                make_challenge_question(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    difficulty=difficulty,
                    challenge_prompt=f"Create a practical mini-task using {concept_name}. Explain why your answer works.",
                    success_criteria=[
                        "uses the concept correctly",
                        "includes a relevant example",
                        "explains the result or reasoning",
                    ],
                )
            )

    return questions


def attach_expanded_questions_to_bundle(
    assessment_bundle: Dict[str, Any],
    concept_resource: Dict[str, Any],
    requested_types: List[str],
    difficulty: str = "medium",
    max_extra_questions: int = 4,
) -> Dict[str, Any]:
    assessment_bundle = dict(assessment_bundle) if isinstance(assessment_bundle, dict) else {}

    existing_questions = assessment_bundle.get("questions", [])
    if not isinstance(existing_questions, list):
        existing_questions = []

    existing_types = {
        q.get("question_type") or q.get("assessment_type")
        for q in existing_questions
        if isinstance(q, dict)
    }

    extra_types = [
        q_type
        for q_type in requested_types
        if q_type not in existing_types
    ]

    expanded_questions = generate_expanded_assessment_questions(
        concept_resource=concept_resource,
        requested_types=extra_types,
        difficulty=difficulty,
    )

    if max_extra_questions is not None:
        expanded_questions = expanded_questions[:max_extra_questions]

    assessment_bundle["questions"] = existing_questions + expanded_questions
    assessment_bundle["domain"] = assessment_bundle.get("domain") or concept_resource.get("domain")
    assessment_bundle["question_count"] = len(assessment_bundle["questions"])
    assessment_bundle["expanded_question_types_added"] = [
        q.get("question_type")
        for q in expanded_questions
    ]

    assessment_bundle = normalize_assessment_bundle_for_frontend(assessment_bundle)

    return assessment_bundle
