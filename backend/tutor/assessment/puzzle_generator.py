from __future__ import annotations

from typing import Any

from tutor.assessment.puzzle_schema import make_puzzle


def _concept_key(concept_name: str, domain: str) -> str:
    text = f"{domain} {concept_name}".lower()
    if "loop" in text:
        return "python_loops"
    if "sql" in text or "select" in text:
        return "sql_select"
    if "html" in text or "tag" in text:
        return "html_tags"
    if "git" in text or "commit" in text:
        return "git_commits"
    if "array" in text or "data structure" in text:
        return "arrays"
    return "python_variables"


def _templates(key: str) -> dict[str, Any]:
    templates = {
        "python_variables": {
            "fill_sentence": "A Python variable stores a ____.",
            "blank": "value",
            "steps": ["Choose a variable name", "Assign a value with =", "Use the variable later"],
            "pairs": [
                {"left": "name", "right": "variable identifier"},
                {"left": "=", "right": "assignment operator"},
                {"left": "42", "right": "stored value"},
            ],
            "items": ["score = 10", "score = score + 5", "print(score)"],
            "code_snippet": "score = ____\nprint(score)",
            "code_answer": "10",
            "expected_output": "10",
            "syntax_snippet": "name ____ 'Ada'",
            "syntax_answer": "=",
        },
        "python_loops": {
            "fill_sentence": "A for loop repeats code for each ____ in a sequence.",
            "blank": "item",
            "steps": ["Write the loop header", "Indent the loop body", "Process each item"],
            "pairs": [
                {"left": "for", "right": "loop keyword"},
                {"left": "in", "right": "iterates over"},
                {"left": "indentation", "right": "loop body"},
            ],
            "items": ["for n in numbers:", "    total = total + n", "print(total)"],
            "code_snippet": "for n in [1, 2, 3]:\n    ____",
            "code_answer": "print(n)",
            "expected_output": "1\n2\n3",
            "syntax_snippet": "for n ____ numbers:",
            "syntax_answer": "in",
        },
        "sql_select": {
            "fill_sentence": "SQL SELECT retrieves columns from a ____.",
            "blank": "table",
            "steps": ["Write SELECT", "Choose columns", "Add FROM table"],
            "pairs": [
                {"left": "SELECT", "right": "choose columns"},
                {"left": "FROM", "right": "choose table"},
                {"left": "*", "right": "all columns"},
            ],
            "items": ["SELECT name", "FROM students", "WHERE grade = 'A'"],
            "code_snippet": "SELECT ____ FROM students;",
            "code_answer": "name",
            "expected_output": None,
            "syntax_snippet": "SELECT name ____ students;",
            "syntax_answer": "FROM",
        },
        "html_tags": {
            "fill_sentence": "Most HTML elements use an opening and closing ____.",
            "blank": "tag",
            "steps": ["Open the tag", "Add content", "Close the tag"],
            "pairs": [
                {"left": "<p>", "right": "paragraph start"},
                {"left": "</p>", "right": "paragraph end"},
                {"left": "<h1>", "right": "main heading"},
            ],
            "items": ["<ul>", "<li>Item</li>", "</ul>"],
            "code_snippet": "<h1>____</h1>",
            "code_answer": "Title",
            "expected_output": None,
            "syntax_snippet": "<p>Hello____",
            "syntax_answer": "</p>",
        },
        "git_commits": {
            "fill_sentence": "A Git commit records a project ____.",
            "blank": "snapshot",
            "steps": ["Edit files", "Stage changes", "Create commit"],
            "pairs": [
                {"left": "git add", "right": "stage changes"},
                {"left": "git commit", "right": "save snapshot"},
                {"left": "message", "right": "describe change"},
            ],
            "items": ["git status", "git add app.py", "git commit -m init"],
            "code_snippet": "git ____ app.py",
            "code_answer": "add",
            "expected_output": None,
            "syntax_snippet": "git commit ____ \"message\"",
            "syntax_answer": "-m",
        },
        "arrays": {
            "fill_sentence": "An array stores items in an ordered ____.",
            "blank": "sequence",
            "steps": ["Create the array", "Use an index", "Read or update an item"],
            "pairs": [
                {"left": "index", "right": "position"},
                {"left": "append", "right": "add item"},
                {"left": "length", "right": "item count"},
            ],
            "items": ["numbers = [1, 2, 3]", "first = numbers[0]", "print(first)"],
            "code_snippet": "numbers = [1, 2, 3]\nprint(numbers[____])",
            "code_answer": "0",
            "expected_output": "1",
            "syntax_snippet": "numbers____0]",
            "syntax_answer": "[",
        },
    }
    return templates[key]


def generate_puzzle_bundle(
    concept_id: str,
    concept_name: str,
    domain: str,
    difficulty: str = "easy",
) -> dict[str, Any]:
    key = _concept_key(concept_name, domain)
    template = _templates(key)
    steps = template["steps"]
    pairs = template["pairs"]
    drag_items = template["items"]
    puzzles = [
        make_puzzle(
            "fill_blank",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt=template["fill_sentence"],
            instructions="Fill the blank with the most accurate term.",
            blanks=[template["blank"]],
            correct_answer=[template["blank"]],
            hints=["Use the key concept definition."],
        ),
        make_puzzle(
            "arrange_steps",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt=f"Arrange the {concept_name} steps in the correct order.",
            instructions="Place each step from first to last.",
            options=[{"id": f"s{idx + 1}", "text": text} for idx, text in enumerate(steps)],
            correct_order=[f"s{idx + 1}" for idx in range(len(steps))],
            hints=["Start with the setup step."],
        ),
        make_puzzle(
            "match_pairs",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt=f"Match each {concept_name} term to its meaning.",
            instructions="Pair every left-side item with the correct right-side item.",
            pairs=[
                {
                    "left_id": f"l{idx + 1}",
                    "left": pair["left"],
                    "right_id": f"r{idx + 1}",
                    "right": pair["right"],
                }
                for idx, pair in enumerate(pairs)
            ],
            correct_answer=[
                {"left_id": f"l{idx + 1}", "right_id": f"r{idx + 1}"}
                for idx in range(len(pairs))
            ],
            hints=["Match by role, not by position."],
        ),
        make_puzzle(
            "drag_order",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt="Drag the statements into a sensible order.",
            instructions="Order the items to form a valid progression.",
            options=[{"id": f"i{idx + 1}", "text": text} for idx, text in enumerate(drag_items)],
            correct_order=[f"i{idx + 1}" for idx in range(len(drag_items))],
            hints=["Look for the line that must happen first."],
        ),
        make_puzzle(
            "code_puzzle",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt="Complete the missing code fragment.",
            instructions="Replace the blank with code that satisfies the expected result.",
            code_snippet=template["code_snippet"],
            correct_answer=template["code_answer"],
            expected_output=template["expected_output"],
            hints=["Use the smallest valid completion."],
        ),
        make_puzzle(
            "syntax_completion",
            concept_id,
            concept_name,
            domain,
            difficulty,
            prompt="Complete the missing syntax.",
            instructions="Enter only the missing syntax token or fragment.",
            code_snippet=template["syntax_snippet"],
            correct_answer=template["syntax_answer"],
            hints=["Focus on syntax, not explanation."],
        ),
    ]
    return {
        "status": "success",
        "module": "puzzle_generator",
        "concept_id": concept_id,
        "concept_name": concept_name,
        "domain": domain,
        "difficulty": difficulty,
        "puzzles": puzzles,
    }
