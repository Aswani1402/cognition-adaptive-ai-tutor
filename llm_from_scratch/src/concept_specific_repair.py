import json
from typing import Any, Dict, List


def _clean(value: Any, max_chars: int = 260) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    text = text.replace("...", " example ")
    text = " ".join(text.split())
    if len(text) > max_chars:
        text = text[:max_chars].strip()
        last_end = max(text.rfind("."), text.rfind("?"), text.rfind("!"), text.rfind(";"))
        if last_end > 45:
            text = text[: last_end + 1].strip()
    if text and text[-1] not in ".!?;:})]\"'":
        text += "."
    return text


def _items(value: Any, max_items: int = 3) -> List[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").replace("|", "\n").splitlines()
    items: List[str] = []
    for item in raw:
        cleaned = _clean(str(item).lstrip("-* ").strip(), 220)
        if cleaned and cleaned not in items:
            items.append(cleaned)
    return items[:max_items]


def _definition(concept: Dict[str, Any]) -> str:
    return _clean(concept.get("base_content") or concept.get("definition"), 340) or (
        f"{concept['concept_name']} is an important concept in {concept['domain']}."
    )


def _key(concept: Dict[str, Any]) -> str:
    points = _items(concept.get("key_points"), 1)
    return points[0] if points else _definition(concept)


def _example(concept: Dict[str, Any]) -> str:
    examples = _items(concept.get("examples"), 2)
    if len(examples) > 1 and examples[0].lower().startswith("example"):
        return examples[1]
    return examples[0] if examples else f"Apply {concept['concept_name']} in a small {concept['domain']} example."


def _mistake(concept: Dict[str, Any]) -> str:
    mistakes = _items(concept.get("misconceptions"), 1)
    return mistakes[0] if mistakes else f"A common mistake is misunderstanding {concept['concept_name']}."


def _use_case(concept: Dict[str, Any]) -> str:
    return _clean(concept.get("real_world_use"), 240) or f"{concept['concept_name']} is used in practical {concept['domain']} work."


def _domain_distractors(concept: Dict[str, Any]) -> List[str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lowered = name.lower()
    if domain == "Python":
        return [
            f"{name} requires declaring every Python type manually",
            f"{name} only works inside print statements",
            f"{name} ignores Python program flow rules",
        ]
    if domain == "SQL":
        return [
            f"{name} permanently edits SQL table rows",
            f"{name} works without related database tables",
            f"{name} replaces every SQL query clause",
        ]
    if domain == "HTML":
        return [
            f"{name} only changes HTML page colors",
            f"{name} cannot affect page structure",
            f"{name} works only inside script tags",
        ]
    if domain == "Git":
        return [
            f"{name} automatically uploads every Git change",
            f"{name} deletes previous Git project history",
            f"{name} works without a Git repository",
        ]
    if "stack" in lowered:
        return [
            "Stack removes the first inserted data item",
            "Stack allows only sorted data values",
            "Stack behaves like a database table",
        ]
    if "queue" in lowered:
        return [
            "Queue removes the newest data item first",
            "Queue requires tree-shaped node links",
            "Queue stores only unique set values",
        ]
    return [
        f"{name} ignores the main Data Structures rule",
        f"{name} stores unrelated database table rows",
        f"{name} only changes visual page markup",
    ]


def _mcq_payload(concept: Dict[str, Any]) -> Dict[str, Any]:
    name = concept["concept_name"]
    key = _clean(_key(concept), 130).rstrip(" .")
    correct = f"{name}: {key}"
    options = [correct]
    for option in _domain_distractors(concept):
        if option not in options:
            options.append(option)
    while len(options) < 4:
        options.append(f"{name} incorrect option {len(options)} for {concept['domain']}")
    return {
        "question": f"Which statement best describes {name} in {concept['domain']}?",
        "options": options[:4],
        "answer": correct,
        "explanation": f"The correct option matches the key idea for {name}: {key}.",
    }


def _debug_payload(concept: Dict[str, Any]) -> Dict[str, str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lowered = name.lower()
    key = _key(concept)
    if domain == "Python" and "loop" in lowered:
        return {
            "buggy_code": "for i in range(3)\n    print(i)",
            "expected_fix": "for i in range(3):\n    print(i)",
            "hint": "A Python loop header needs a colon.",
            "explanation": f"{name} depends on correct Python loop syntax.",
        }
    if domain == "Python":
        return {
            "buggy_code": "value = example\nprint(value)",
            "expected_fix": "value = 'example'\nprint(value)",
            "hint": "Put text values in quotes.",
            "explanation": f"{name} should follow this Python idea: {key}.",
        }
    if domain == "SQL":
        if "join" in lowered:
            return {
                "buggy_code": "SELECT customers.name, orders.amount FROM customers JOIN orders;",
                "expected_fix": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;",
                "hint": "A SQL JOIN needs an ON condition that links related columns.",
                "explanation": f"{name} should follow this SQL idea: {key}.",
            }
        if "index" in lowered:
            return {
                "buggy_code": "SELECT * FROM users WHERE email = 'a@test.com'; -- repeated slow lookup",
                "expected_fix": "CREATE INDEX idx_users_email ON users(email);\nSELECT * FROM users WHERE email = 'a@test.com';",
                "hint": "Create an index on the column used for repeated lookup.",
                "explanation": f"{name} should follow this SQL idea: {key}.",
            }
        if "window" in lowered:
            return {
                "buggy_code": "SELECT department, MAX(salary) FROM employees;",
                "expected_fix": "SELECT name, department, salary, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank FROM employees;",
                "hint": "Use a window function when each row should keep row-level detail.",
                "explanation": f"{name} should follow this SQL idea: {key}.",
            }
        if "cte" in lowered or "common table" in lowered:
            return {
                "buggy_code": "high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
                "expected_fix": "WITH high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
                "hint": "Start a Common Table Expression with WITH.",
                "explanation": f"{name} should follow this SQL idea: {key}.",
            }
        return {
            "buggy_code": "SELECT name FROM students WHERE age = NULL;",
            "expected_fix": "SELECT name FROM students WHERE age IS NULL;",
            "hint": "Use SQL syntax that matches the concept rule.",
            "explanation": f"{name} should follow this SQL idea: {key}.",
        }
    if domain == "HTML":
        return {
            "buggy_code": "<p>Hello",
            "expected_fix": "<p>Hello</p>",
            "hint": "Close the HTML element when it needs an end tag.",
            "explanation": f"{name} should follow this HTML idea: {key}.",
        }
    if domain == "Git":
        return {
            "buggy_code": "git comit -m \"save\"",
            "expected_fix": "git commit -m \"save\"",
            "hint": "Use the correct Git command spelling.",
            "explanation": f"{name} should follow this Git idea: {key}.",
        }
    return {
        "buggy_code": f"{name.lower().replace(' ', '_')}.remove_wrong_item()",
        "expected_fix": f"Use the valid {name} operation that follows: {key}.",
        "hint": f"Check the main rule for {name}.",
        "explanation": f"The fix must follow this Data Structures idea: {key}.",
    }


def _prediction_payload(concept: Dict[str, Any]) -> Dict[str, str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lowered = name.lower()
    key = _key(concept)
    if domain == "Python" and "loop" in lowered:
        return {"code": "for i in range(3):\n    print(i)", "question": f"What output demonstrates {name}?", "answer": "0\n1\n2", "explanation": f"The loop repeats according to this idea: {key}."}
    if domain == "Python":
        return {"code": "value = 10\nvalue = 20\nprint(value)", "question": f"What output demonstrates {name}?", "answer": "20", "explanation": f"The code follows this Python idea: {key}."}
    if domain == "SQL":
        if "join" in lowered:
            return {"code": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;", "question": f"What result demonstrates {name}?", "answer": "The SQL query combines matching customer and order rows.", "explanation": f"The query follows this SQL idea: {key}."}
        if "index" in lowered:
            return {"code": "CREATE INDEX idx_users_email ON users(email);", "question": f"What result demonstrates {name}?", "answer": "The database can find repeated email lookups faster.", "explanation": f"The statement follows this SQL idea: {key}."}
        if "window" in lowered:
            return {"code": "SELECT name, salary, RANK() OVER (ORDER BY salary DESC) AS salary_rank FROM employees;", "question": f"What result demonstrates {name}?", "answer": "Each employee row keeps its detail and receives a salary rank.", "explanation": f"The query follows this SQL idea: {key}."}
        if "cte" in lowered or "common table" in lowered:
            return {"code": "WITH high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;", "question": f"What result demonstrates {name}?", "answer": "The named temporary result is queried in the final SELECT.", "explanation": f"The query follows this SQL idea: {key}."}
        return {"code": "SELECT name FROM students WHERE age > 18;", "question": f"What result demonstrates {name}?", "answer": f"The SQL query returns rows that follow {name}.", "explanation": f"The query follows this SQL idea: {key}."}
    if domain == "HTML":
        return {"code": "<p>Hello</p>", "question": f"What page output demonstrates {name}?", "answer": "Hello appears as paragraph text.", "explanation": f"The markup follows this HTML idea: {key}."}
    if domain == "Git":
        return {"code": "git status", "question": f"What result demonstrates {name}?", "answer": "Git shows the repository working tree status.", "explanation": f"The command supports this Git idea: {key}."}
    if "queue" in lowered:
        return {"code": "queue.enqueue('A')\nqueue.enqueue('B')\nqueue.dequeue()", "question": f"What result demonstrates {name}?", "answer": "A", "explanation": f"The operation follows this Data Structures idea: {key}."}
    return {"code": "stack.append('A')\nstack.append('B')\nstack.pop()", "question": f"What result demonstrates {name}?", "answer": "B", "explanation": f"The operation follows this Data Structures idea: {key}."}


def repair_output(concept: Dict[str, Any], task_type: str) -> str:
    name = concept["concept_name"]
    domain = concept["domain"]
    definition = _definition(concept)
    key = _key(concept)
    ex = _example(concept)
    mistake = _mistake(concept)
    use_case = _use_case(concept)

    if task_type == "explanation":
        return f"Concept: {name}\nDefinition: {definition}\nExample: {ex}\nWhy it matters: {key}"
    if task_type == "flashcard":
        return json.dumps({"front": f"What is {name}?", "back": key}, ensure_ascii=False)
    if task_type == "mcq":
        return json.dumps(_mcq_payload(concept), ensure_ascii=False)
    if task_type == "debug_task":
        return json.dumps(_debug_payload(concept), ensure_ascii=False)
    if task_type == "output_prediction":
        return json.dumps(_prediction_payload(concept), ensure_ascii=False)
    if task_type == "challenge_question":
        return json.dumps(
            {
                "challenge": f"Create a small {domain} example that uses {name}.",
                "solution_outline": f"Use this key idea: {key}. Then explain the example: {ex}.",
            },
            ensure_ascii=False,
        )
    if task_type == "revision_summary":
        return f"Summary: {name} means {definition}\nRemember: {key}\nAvoid this mistake: {mistake}"
    if task_type == "hint":
        return f"Hint: Focus on {name}: {key}"
    if task_type == "feedback":
        return f"What was correct: You worked on {name} in {domain}.\nWhat to improve: Connect your answer to this key idea: {key}\nNext step: Try this example: {ex}"
    if task_type == "mindmap":
        return json.dumps(
            {
                "center": name,
                "branches": [
                    f"Definition: {definition}",
                    f"Key point: {key}",
                    f"Example: {ex}",
                    f"Common mistake: {mistake}",
                    f"Real-world use: {use_case}",
                ],
            },
            ensure_ascii=False,
        )
    if task_type == "doubt_answer":
        return f"Answer: {name} is mainly about {key}\nReason: {definition}\nExample: {ex}\nTry this: Explain why this mistake is wrong: {mistake}"
    if task_type == "voice_script":
        return f"Voice Script: Today we learn {name}. The main idea is {key}. For example, {ex}. One mistake to avoid is this: {mistake}."
    raise ValueError(f"Unsupported repair task_type: {task_type}")
