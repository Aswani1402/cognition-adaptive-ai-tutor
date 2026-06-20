import ast
import json
import re
from typing import Any, Dict, List



def _as_text(value: Any) -> str:
    """Convert DB strings/lists safely into readable text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(x).strip() for x in value if str(x).strip())

    text = str(value).strip()

    # Some DB fields arrive as stringified Python lists: "['a', 'b']"
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return " ".join(str(x).strip() for x in parsed if str(x).strip())
        except Exception:
            pass

    return text



def _as_text(value: Any) -> str:
    """Convert DB strings/lists safely into readable text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(x).strip() for x in value if str(x).strip())

    text = str(value).strip()

    # Some DB fields arrive as stringified Python lists: "['a', 'b']"
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return " ".join(str(x).strip() for x in parsed if str(x).strip())
        except Exception:
            pass

    return text


def _clean(value: Any, max_len: int = 260) -> str:
    text = _as_text(value)
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace("?", " ").replace(" - ", " ")
    text = " ".join(text.split())
    text = text.replace("..", ".")

    # Remove obvious broken/truncated tail fragments.
    broken_tails = [" th", " becom", " st", " c", " elemen", " Progr", " API"]
    for tail in broken_tails:
        if text.endswith(tail):
            text = text[: -len(tail)].strip()

    if len(text) > max_len:
        cut = text[:max_len].strip()
        last = max(cut.rfind("."), cut.rfind("?"), cut.rfind("!"), cut.rfind(";"))
        if last > 55:
            text = cut[: last + 1].strip()
        else:
            # Prefer not to end mid-word.
            text = cut.rsplit(" ", 1)[0].strip()

    if text and text[-1] not in ".!?;:)\"'":
        text += "."
    return text


def _split_items(value: Any, max_items: int = 3, max_len: int = 180) -> List[str]:
    if isinstance(value, (list, tuple)):
        raw = [str(x) for x in value]
    else:
        text = _as_text(value)
        # If it was a list-like text, _as_text already flattened it.
        raw = re.split(r"[\n|?]", text)

    out = []
    for part in raw:
        cleaned = _clean(part.strip(" -*\t'\"[]"), max_len)
        if cleaned and cleaned not in out:
            out.append(cleaned)

    if not out:
        text = _as_text(value)
        out = [_clean(p, max_len) for p in text.split(". ") if len(p.strip()) > 8]

    return out[:max_items]


def _concept_name(c: Dict[str, Any]) -> str:
    return c.get("concept_name") or c.get("topic") or c.get("name") or "Concept"


def _domain(c: Dict[str, Any]) -> str:
    return c.get("domain") or "General"


def _definition(c: Dict[str, Any]) -> str:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Data Structures" and "tree" in name:
        return "A tree is a non-linear hierarchical data structure made of nodes and edges. It organizes data using parent-child relationships, starting from a root node and branching into child nodes."

    return _clean(c.get("base_content") or c.get("definition") or f"{_concept_name(c)} is an important concept.", 360)


def _key(c: Dict[str, Any]) -> str:
    items = _split_items(c.get("key_points"), 1, 180)
    if items:
        return items[0]
    return _clean(f"{_concept_name(c)} has a key rule learners should apply.", 180)


def _example(c: Dict[str, Any]) -> str:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Python" and "variable" in name:
        return "score = 10 stores the value 10 using the name score."
    if domain == "Python" and "loop" in name:
        return "for i in range(3): print(i) prints 0, 1, and 2."
    if domain == "Python" and "function" in name:
        return "def greet(name): return 'Hello ' + name creates a reusable function."

    if domain == "SQL" and "join" in name:
        return "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id returns matching customer-order rows."
    if domain == "SQL" and "select" in name:
        return "SELECT name FROM students returns the name column from the students table."
    if domain == "SQL" and "where" in name:
        return "SELECT name FROM students WHERE age > 18 returns only students older than 18."

    if domain == "HTML" and ("tag" in name or "element" in name):
        return "<p>Hello</p> creates a paragraph element."

    if domain == "Git" and "commit" in name:
        return 'git commit -m "Add login page" saves staged changes with a message.'

    if domain == "Data Structures" and "stack" in name:
        return "stack.append('A'); stack.append('B'); stack.pop() returns 'B' because a stack follows LIFO."
    if domain == "Data Structures" and "queue" in name:
        return "queue.append('A'); queue.append('B'); queue.pop(0) returns 'A' because a queue follows FIFO."
    if domain == "Data Structures" and "linked" in name:
        return "first.next = second connects the first node to the second node."
    if domain == "Data Structures" and "array" in name:
        return "numbers[0] reads the first element from an array-like list."
    if domain == "Data Structures" and "tree" in name:
        return "root.left stores the left child of a tree node."
    if domain == "Data Structures" and "set" in name:
        return "set([1, 1, 2]) stores only unique values: 1 and 2."
    if domain == "Data Structures" and "graph" in name:
        return "A graph can store cities as vertices and roads as edges."

    items = _split_items(c.get("examples"), 1, 220)
    return items[0] if items else f"Use {_concept_name(c)} in a small {_domain(c)} example."


def _mistake(c: Dict[str, Any]) -> str:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Data Structures" and "stack" in name:
        return "A common mistake is treating a stack like a queue; stack removes the last inserted item first."
    if domain == "Data Structures" and "queue" in name:
        return "A common mistake is treating a queue like a stack; queue removes the first inserted item first."
    if domain == "SQL" and "join" in name:
        return "A common mistake is writing JOIN without an ON condition."
    if domain == "Python" and "loop" in name:
        return "A common mistake is forgetting the colon after the loop header."

    items = _split_items(c.get("misconceptions"), 1, 220)
    return items[0] if items else f"A common mistake is misunderstanding {_concept_name(c)}."


def _real_world(c: Dict[str, Any]) -> str:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Data Structures" and "tree" in name:
        return "File systems, database indexes, and browser DOM structures use trees to organize hierarchical data."

    items = _split_items(c.get("real_world_use"), 1, 180)
    return items[0] if items else f"{_concept_name(c)} is useful in practical {_domain(c)} work."


def _debug_payload(c: Dict[str, Any]) -> Dict[str, str]:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Python" and "variable" in name:
        return {
            "buggy_code": "2score = 10\nprint(2score)",
            "expected_fix": "score2 = 10\nprint(score2)",
            "hint": "Variable names cannot start with a digit.",
            "explanation": "Python variable names must start with a letter or underscore.",
        }
    if domain == "Python" and "loop" in name:
        return {
            "buggy_code": "for i in range(3)\n    print(i)",
            "expected_fix": "for i in range(3):\n    print(i)",
            "hint": "A loop header needs a colon.",
            "explanation": "Python uses a colon to start the loop block.",
        }
    if domain == "Python" and "function" in name:
        return {
            "buggy_code": "def greet(name)\n    return 'Hello ' + name",
            "expected_fix": "def greet(name):\n    return 'Hello ' + name",
            "hint": "A function definition needs a colon.",
            "explanation": "A def statement must end with a colon before the function body.",
        }

    if domain == "SQL" and "select" in name:
        return {
            "buggy_code": "SELEC name FROM students;",
            "expected_fix": "SELECT name FROM students;",
            "hint": "Check the SELECT keyword spelling.",
            "explanation": "SELECT retrieves columns from a table.",
        }
    if domain == "SQL" and "where" in name:
        return {
            "buggy_code": "SELECT name FROM students WHERE age = NULL;",
            "expected_fix": "SELECT name FROM students WHERE age IS NULL;",
            "hint": "NULL must be checked using IS NULL.",
            "explanation": "SQL does not compare NULL using =.",
        }
    if domain == "SQL" and "join" in name:
        return {
            "buggy_code": "SELECT customers.name, orders.amount FROM customers JOIN orders;",
            "expected_fix": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;",
            "hint": "A JOIN needs an ON condition linking related columns.",
            "explanation": "JOIN combines matching rows using a related column.",
        }
    if domain == "SQL" and "index" in name:
        return {
            "buggy_code": "SELECT * FROM users WHERE email = 'a@test.com'; -- repeated slow lookup",
            "expected_fix": "CREATE INDEX idx_users_email ON users(email);\nSELECT * FROM users WHERE email = 'a@test.com';",
            "hint": "Use an index for repeated lookup columns.",
            "explanation": "Indexes help the database find matching rows faster for repeated lookup columns such as email.",
        }
    if domain == "SQL" and "window" in name:
        return {
            "buggy_code": "SELECT department, MAX(salary) FROM employees;",
            "expected_fix": "SELECT name, department, salary, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank FROM employees;",
            "hint": "Use a window function when you need row-level output with group-based calculation.",
            "explanation": "Window functions compute across related rows without collapsing each group into one row.",
        }
    if domain == "SQL" and ("cte" in name or "common table" in name):
        return {
            "buggy_code": "high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
            "expected_fix": "WITH high_earners AS (SELECT * FROM employees WHERE salary > 50000) SELECT * FROM high_earners;",
            "hint": "A CTE starts with WITH.",
            "explanation": "A Common Table Expression defines a temporary named result for one query.",
        }

    if domain == "HTML" and ("tag" in name or "element" in name):
        return {
            "buggy_code": "<p>Hello",
            "expected_fix": "<p>Hello</p>",
            "hint": "Most HTML elements need closing tags.",
            "explanation": "The paragraph element should be closed with </p>.",
        }

    if domain == "Git" and "commit" in name:
        return {
            "buggy_code": "git commit -m",
            "expected_fix": 'git commit -m "Describe the change"',
            "hint": "A commit message is required after -m.",
            "explanation": "Git commits should include a meaningful message.",
        }

    if domain == "Data Structures" and "stack" in name:
        return {
            "buggy_code": "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop(0))",
            "expected_fix": "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop())",
            "hint": "A stack removes the last inserted item.",
            "explanation": "Stack follows LIFO, so pop() removes the last pushed value.",
        }
    if domain == "Data Structures" and "queue" in name:
        return {
            "buggy_code": "queue = []\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop())",
            "expected_fix": "queue = []\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop(0))",
            "hint": "A queue removes the first inserted item.",
            "explanation": "Queue follows FIFO, so dequeue removes from the front.",
        }
    if domain == "Data Structures" and "linked" in name:
        return {
            "buggy_code": "first = Node(10)\nsecond = Node(20)\nfirst.next = None",
            "expected_fix": "first = Node(10)\nsecond = Node(20)\nfirst.next = second",
            "hint": "A linked list connects nodes using next references.",
            "explanation": "Each node should point to the next node in the list.",
        }
    if domain == "Data Structures" and "array" in name:
        return {
            "buggy_code": "numbers = [10, 20, 30]\nprint(numbers[3])",
            "expected_fix": "numbers = [10, 20, 30]\nprint(numbers[2])",
            "hint": "Array/list indexes start at 0.",
            "explanation": "The last item in a 3-item list is at index 2.",
        }
    if domain == "Data Structures" and "tree" in name:
        return {
            "buggy_code": "root.left.value = 10  # root.left was never created",
            "expected_fix": "root.left = Node(10)",
            "hint": "Create a child node before accessing its value.",
            "explanation": "Tree nodes must be linked before their child values are used.",
        }
    if domain == "Data Structures" and "set" in name:
        return {
            "buggy_code": "values = {1, 2}\nprint(values[0])",
            "expected_fix": "values = {1, 2}\nprint(1 in values)",
            "hint": "Sets are unordered and do not support index access.",
            "explanation": "Use membership checks with sets instead of positional indexing.",
        }
    if domain == "Data Structures" and "graph" in name:
        return {
            "buggy_code": "graph['A'].append('B')  # graph['A'] was not initialized",
            "expected_fix": "graph = {'A': []}\ngraph['A'].append('B')",
            "hint": "Initialize an adjacency list before adding neighbors.",
            "explanation": "Graph adjacency lists need a list for each vertex before appending edges.",
        }

    return {
        "buggy_code": f"answer = None  # incomplete use of {_concept_name(c)}",
        "expected_fix": f"Use {_concept_name(c)} according to this rule: {_key(c)}",
        "hint": f"Start from the key rule for {_concept_name(c)}.",
        "explanation": f"The correction should follow this idea: {_key(c)}",
    }


def _output_prediction_payload(c: Dict[str, Any]) -> Dict[str, str]:
    name = _concept_name(c).lower()
    domain = _domain(c)

    if domain == "Data Structures" and "stack" in name:
        return {
            "code": "stack=[]\nstack.append('A')\nstack.append('B')\nprint(stack.pop())",
            "question": "What is printed?",
            "answer": "B",
            "explanation": "A stack removes the last pushed item first.",
        }
    if domain == "Data Structures" and "queue" in name:
        return {
            "code": "queue=[]\nqueue.append('A')\nqueue.append('B')\nprint(queue.pop(0))",
            "question": "What is printed?",
            "answer": "A",
            "explanation": "A queue removes the first inserted item first.",
        }
    if domain == "Python" and "loop" in name:
        return {
            "code": "for i in range(3):\n    print(i)",
            "question": "What is printed?",
            "answer": "0\n1\n2",
            "explanation": "This Loops example repeats the print statement for each value produced by range(3): 0, 1, and 2.",
        }
    if domain == "Python" and "variable" in name:
        return {
            "code": "value = 10\nvalue = 20\nprint(value)",
            "question": "What is printed?",
            "answer": "20",
            "explanation": "This Variables example shows that reassignment updates the stored value, so value becomes 20.",
        }
    if domain == "SQL" and "join" in name:
        return {
            "code": "SELECT customers.name, orders.amount FROM customers JOIN orders ON customers.id = orders.customer_id;",
            "question": "What does this query return?",
            "answer": "Customer names with matching order amounts.",
            "explanation": "The JOIN connects rows where the customer id matches the order customer_id.",
        }

    return {
        "code": _example(c),
        "question": f"What key idea does this example show about {_concept_name(c)}?",
        "answer": _key(c),
        "explanation": f"The example demonstrates the main rule of {_concept_name(c)}.",
    }


def build_guarded_fallback(concept: Dict[str, Any], task_type: str) -> str:
    name = _concept_name(concept)
    domain = _domain(concept)
    d = _definition(concept)
    k = _key(concept)
    ex = _example(concept)
    mis = _mistake(concept)
    use = _real_world(concept)

    if task_type == "explanation":
        return f"Concept: {name}\nDefinition: {d}\nExample: {ex}\nWhy it matters: {k}"

    if task_type == "flashcard":
        return json.dumps({"front": f"What is {name}?", "back": k}, ensure_ascii=False)

    if task_type == "mcq":
        distractors = {
            "Python": [f"{name} requires declaring every Python type manually", f"{name} only works inside print statements", f"{name} ignores Python program flow rules"],
            "SQL": [f"{name} permanently edits SQL table rows", f"{name} works without related database tables", f"{name} replaces every SQL query clause"],
            "HTML": [f"{name} directly edits database rows", f"{name} trains a machine learning model", f"{name} replaces browser rendering"],
            "Git": [f"{name} changes Python syntax", f"{name} removes the need for version history", f"{name} stores SQL rows"],
            "Data Structures": [f"{name} ignores insertion and removal rules", f"{name} is always identical to every other structure", f"{name} behaves like a database table"],
        }.get(domain, [f"{name} is unrelated to examples", f"{name} removes the need for practice", f"{name} always changes stored data permanently"])
        correct = f"{name}: {k.rstrip('.')}"
        return json.dumps({
            "question": f"Which statement best describes {name} in {domain}?",
            "options": [correct] + distractors[:3],
            "answer": correct,
            "explanation": f"The correct option matches the key idea for {name}: {k.rstrip('.')}.",
        }, ensure_ascii=False)

    if task_type == "debug_task":
        return json.dumps(_debug_payload(concept), ensure_ascii=False)

    if task_type == "output_prediction":
        return json.dumps(_output_prediction_payload(concept), ensure_ascii=False)

    if task_type == "challenge_question":
        return json.dumps({
            "challenge": f"Create a small {domain} example that uses {name}.",
            "solution_outline": f"Use this key idea: {k} Then explain the example: {ex}",
        }, ensure_ascii=False)

    if task_type == "revision_summary":
        return f"Summary: {name} means {d}\nRemember: {k}\nAvoid this mistake: {mis}"

    if task_type == "hint":
        return f"Hint: Focus on {name}: {k}"

    if task_type == "feedback":
        return f"What was correct: You worked on {name} in {domain}.\nWhat to improve: Connect your answer to this key idea: {k}\nNext step: Try this example: {ex}"

    if task_type == "mindmap":
        return json.dumps({
            "center": name,
            "branches": [
                f"Definition: {d}",
                f"Key point: {k}",
                f"Example: {ex}",
                f"Common mistake: {mis}",
                f"Real-world use: {use}",
            ],
        }, ensure_ascii=False)

    if task_type == "doubt_answer":
        return f"Answer: {name} is mainly about {k}\nReason: {d}\nExample: {ex}\nTry this: Explain why this mistake is wrong: {mis}"

    if task_type == "voice_script":
        return f"Voice Script: Today we learn {name}. The main idea is {k} For example, {ex} One mistake to avoid is this: {mis}"

    return f"Concept: {name}\nDefinition: {d}\nExample: {ex}\nWhy it matters: {k}"
