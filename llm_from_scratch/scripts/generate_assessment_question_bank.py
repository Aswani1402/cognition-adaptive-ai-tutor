import json
import random
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]

DB_CONFIGS = [
    {
        "path": ROOT_DIR / "data" / "raw" / "python_learning.db",
        "domain": "Python",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "database_sql.db",
        "domain": "SQL",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "html_web_basics.db",
        "domain": "HTML",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "git_version_control.db",
        "domain": "Git",
    },
    {
        "path": ROOT_DIR / "data" / "raw" / "data_structures.db",
        "domain": "Data Structures",
    },
]

OUTPUT_DIR = ROOT_DIR / "outputs" / "question_bank"
QUESTION_BANK_JSON = OUTPUT_DIR / "assessment_question_bank.json"
QUESTION_BANK_MD = OUTPUT_DIR / "assessment_question_bank.md"
QUALITY_JSON = OUTPUT_DIR / "question_bank_quality_report.json"
QUALITY_MD = OUTPUT_DIR / "question_bank_quality_report.md"


QUESTION_TYPES = [
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
]

MCQ_OPTION_MAX_CHARS = 160

BAD_DISTRACTOR_PHRASES = [
    "unrelated to",
    "should always be skipped",
    "cannot be practiced",
    "only matters in advanced topics",
    "can be ignored",
    "not useful in practical work",
    "only a memorized definition",
    "is unrelated",
    "should be skipped",
    "not related to",
    "has no connection",
    "has no practical use",
    "only for theory",
    "only memorization",
    "ignore the rule",
]


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()

def clean_cut_text(text: Any) -> str:
    text = safe_text(text)
    text = " ".join(text.split()).strip()

    bad_endings = [
        " it p",
        " it",
        " th",
        " t",
        " p",
        " a",
        " an",
        " the",
        " and",
        " or",
        " but",
        " to",
        " of",
        " in",
        " on",
        " for",
        " with",
        " is",
        " are",
        " does",
        " do",
    ]

    lowered = text.lower()

    for ending in bad_endings:
        if lowered.endswith(ending):
            text = text[: -len(ending)].strip()
            break

    # Remove dangling quote/dash artifacts.
    text = text.rstrip(" -—,:;")

    if text and text[-1].isalnum():
        text += "."

    # Normalize duplicate punctuation after cleanup.
    while ".." in text:
        text = text.replace("..", ".")

    while "??" in text:
        text = text.replace("??", "?")

    while "!!" in text:
        text = text.replace("!!", "!")

    text = text.replace(". ?", "?")
    text = text.replace(". .", ".")
    text = text.replace(" .", ".")
    text = text.replace(" ,", ",")

    return text

def clean_question_text(text: Any) -> str:
    text = clean_cut_text(text)

    text = text.replace(".?", "?")
    text = text.replace(". ?", "?")
    text = text.replace("?.", "?")
    text = text.replace("!.", "!")

    while ".." in text:
        text = text.replace("..", ".")

    return text.strip()


def clean_code_text(text: Any) -> str:
    """
    Preserve newlines/indentation for code fields.
    Do not use compact_text/clean_cut_text here because code must not become one line.
    """
    text = safe_text(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text


def clean_answer_text(value: Any) -> str:
    """
    Preserve raw answer/output formatting.

    Numeric/code/output answers should not receive sentence punctuation.
    """
    text = safe_text(value)

    if text.endswith("."):
        numeric_candidate = text[:-1].strip()
        if numeric_candidate:
            try:
                float(numeric_candidate)
                return numeric_candidate
            except ValueError:
                pass

    return text


def compact_text(value: Any, max_chars: int = 180) -> str:
    text = safe_text(value).replace("\r", "\n")
    text = " ".join(text.split())

    if len(text) <= max_chars:
        return clean_cut_text(text)

    cut = text[:max_chars].strip()

    # Prefer cutting at sentence boundary.
    sentence_end_positions = [
        cut.rfind("."),
        cut.rfind("?"),
        cut.rfind("!"),
    ]
    best_sentence_end = max(sentence_end_positions)

    if best_sentence_end >= 60:
        cut = cut[: best_sentence_end + 1].strip()
        return clean_cut_text(cut)

    # Otherwise cut at the last full word.
    last_space = cut.rfind(" ")
    if last_space >= 40:
        cut = cut[:last_space].strip()

    return clean_cut_text(cut)


def first_sentence(value: Any, max_chars: int = 160) -> str:
    text = safe_text(value).replace("\r", "\n").strip()
    if not text:
        return ""

    if "\n\n" in text:
        text = text.split("\n\n", 1)[0].strip()

    for sep in [". ", "\n"]:
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break

    if text and not text.endswith("."):
        text += "."

    return compact_text(text, max_chars)


def split_items(value: Any, max_items: int = 8) -> List[str]:
    text = safe_text(value)

    if not text:
        return []

    raw_parts = []

    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue

        line = line.lstrip("-•* ").strip()

        if "|" in line:
            raw_parts.extend([p.strip() for p in line.split("|") if p.strip()])
        else:
            raw_parts.append(line)

    if len(raw_parts) <= 1 and ". " in text:
        raw_parts = [p.strip() + "." for p in text.split(". ") if p.strip()]

    cleaned = []
    for item in raw_parts:
        item = compact_text(item, 160)
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned[:max_items]


def is_bad_distractor(text: str) -> bool:
    if not text:
        return True

    normalized = str(text).strip().lower()

    if len(normalized) < 8:
        return True

    return any(phrase in normalized for phrase in BAD_DISTRACTOR_PHRASES)


def get_domain_specific_distractors(domain: str, concept_name: str) -> List[str]:
    domain_key = (domain or "").strip().lower()
    concept_key = (concept_name or "").strip().lower()

    concept_fallback_map = {
        ("python", "variables"): [
            "A variable must declare its type before assignment.",
            "A variable name can start with a digit if it contains letters later.",
            "Reassigning a variable always changes the original object itself.",
            "A variable stores a value directly instead of referring to an object.",
        ],
        ("python", "loops"): [
            "A for loop only works with range() and not with lists or strings.",
            "A while loop runs exactly once for each item in a list.",
            "break skips only the current iteration and then continues.",
            "A for loop always requires a manual index variable.",
        ],
        ("python", "conditionals"): [
            "Every if statement must have both elif and else.",
            "Conditions are checked even after the first true branch runs.",
            "The assignment operator = is the same as comparison ==.",
            "An else block runs whenever any earlier condition is true.",
        ],
        ("python", "functions"): [
            "A function must always print instead of returning a value.",
            "Function parameters and arguments are always the same variable.",
            "A return statement does not stop function execution.",
            "A function can only be called once after it is defined.",
        ],
        ("sql", "sql select queries"): [
            "SELECT changes the data stored in the table.",
            "SELECT * is always the best choice for every query.",
            "ORDER BY filters rows before returning results.",
            "Column aliases change the original table column names.",
        ],
        ("sql", "where and filters"): [
            "WHERE filters columns instead of rows.",
            "WHERE is evaluated after ORDER BY.",
            "WHERE and HAVING always mean the same thing.",
            "A WHERE clause permanently removes rows from the table.",
        ],
        ("sql", "join operations"): [
            "INNER JOIN keeps rows that do not match in either table.",
            "A JOIN never needs a matching key.",
            "LEFT JOIN removes all rows from the left table.",
            "Joining tables always creates one row for every possible pair.",
        ],
        ("html", "html tags and elements"): [
            "Every HTML element must have a closing tag.",
            "A tag and an element mean exactly the same thing.",
            "Void elements should wrap text content.",
            "Nesting order does not matter if the browser displays the page.",
        ],
        ("html", "attributes and links"): [
            "Attribute values never need quotes.",
            "href is used to describe image alternative text.",
            "An anchor tag works without a destination.",
            "Attributes belong outside the opening tag.",
        ],
        ("git", "commits and history"): [
            "A commit automatically saves every file on the computer.",
            "git commit works the same as git push.",
            "A commit cannot be inspected later.",
            "git add saves changes into project history immediately.",
        ],
        ("git", "branches"): [
            "A branch is a separate copy that is disconnected forever.",
            "Switching branches always deletes uncommitted work.",
            "Merging branches always happens without conflicts.",
            "A branch stores files separately from the repository history.",
        ],
        ("data structures", "arrays"): [
            "Array indexing always starts at 1.",
            "Arrays do not preserve element order.",
            "Accessing any array element always requires scanning the whole array.",
            "Inserting into the middle of an array is always constant time.",
        ],
        ("data structures", "stack"): [
            "A stack removes the oldest item first.",
            "push removes an item from the stack.",
            "A stack works the same as a queue.",
            "A stack lets you directly remove any item by position.",
        ],
        ("data structures", "queue"): [
            "A queue removes the newest item first.",
            "enqueue removes an item from the queue.",
            "A queue follows LIFO order.",
            "A queue allows every item to be removed before the front item.",
        ],
    }

    if (domain_key, concept_key) in concept_fallback_map:
        return concept_fallback_map[(domain_key, concept_key)]

    fallback_map = {
        "python": [
            "Python applies this idea the same way to every value type.",
            "A program is correct as long as it runs once without a syntax error.",
            "Python can usually infer the intended name or block when syntax is incomplete.",
            "Changing one value automatically updates every related value in the program.",
            "The same Python pattern should be used even when the input data changes shape.",
            "Readable Python code depends mostly on comments, not on clear structure.",
            "Runtime behavior is the same whether values are reassigned or kept unchanged.",
            "Python code should choose the shortest syntax even when it hides the logic.",
            "A name, value, and operation can usually be rearranged without changing behavior.",
            "This idea works best when every step is written as a separate statement.",
            "Python treats similar-looking expressions as equivalent in most beginner programs.",
            "The result matters more than whether the code follows Python's data model.",
        ],
        "sql": [
            "A SELECT-style query permanently changes the stored table data.",
            "Column names are only labels and do not affect query logic.",
            "Adding a WHERE clause changes the table instead of the returned rows.",
            "Tables can be combined correctly without matching related columns.",
            "Rows are always returned in the order they were inserted.",
            "A query is correct as long as it mentions the expected table.",
            "Filtering and grouping happen at the same stage of query execution.",
            "Missing rows and unmatched rows should be handled the same way.",
            "Selecting more columns always makes a query more accurate.",
            "The database can infer relationships from similar column names.",
            "The order of clauses can be changed freely if the words are valid SQL.",
            "Every query returns one row for each row in the main table.",
        ],
        "html": [
            "HTML elements control program logic instead of page structure.",
            "A page is valid as long as the visible text appears in the browser.",
            "Tags should be chosen mainly by how large the text should look.",
            "Opening tags, closing tags, and attributes can be used interchangeably.",
            "Browsers interpret page meaning the same way even with vague elements.",
            "Content behaves the same inside the head and body sections.",
            "Every nested element automatically has the same meaning as its parent.",
            "Browser error correction means element choice has little practical effect.",
            "Attributes describe styling only and do not change element behavior.",
            "Semantic elements matter only after CSS has been added.",
            "The browser can infer accessibility meaning from visual layout alone.",
            "A closing tag can usually be placed wherever the layout looks right.",
        ],
        "git": [
            "Git saves edited files to history as soon as they are changed.",
            "Staged and unstaged changes are treated the same during a commit.",
            "A clean terminal prompt means the repository has no pending changes.",
            "A command run on one branch automatically updates every branch.",
            "Local history and remote history are always identical after a commit.",
            "Commit messages are optional because Git records the file names.",
            "Conflicts are resolved automatically when both branches contain useful work.",
            "Checking repository status is only needed after a command fails.",
            "A branch name points to a folder instead of a line of commit history.",
            "Pushing changes is the same operation as recording a local commit.",
            "Git can recover intent even when unrelated changes are grouped together.",
            "Repository history is mainly a backup, not a record of project decisions.",
        ],
        "data structures": [
            "Every data structure stores and accesses data in the same basic way.",
            "A structure should be chosen before considering insertion, deletion, or search behavior.",
            "Lookup, insertion, deletion, and traversal always have the same cost.",
            "A structure is correct whenever it can hold all required values.",
            "Memory layout and access patterns matter only for very large programs.",
            "Ordered and unordered data can usually use the same structure.",
            "The most advanced structure is usually the best choice for a project.",
            "A structure should be chosen based only on the stored values, not the operations needed.",
            "Constant-time access applies to every operation when the structure is implemented correctly.",
            "Removing data has the same cost no matter where the data is stored.",
            "Traversal order is a display detail and does not affect algorithm behavior.",
            "Using a familiar structure is usually more important than matching the required operations.",
        ],
    }

    return fallback_map.get(
        domain_key,
        [
            "The same approach works well in every situation.",
            "The approach should be selected before considering the problem requirements.",
            "The most familiar approach always gives the most efficient solution.",
            "The approach is applied the same way before and after requirements change.",
            "Changing the input or goal does not affect which rule should be used.",
            "An approach is correct whenever the final result looks reasonable.",
            "Once an approach works once, there is no need to compare alternatives.",
            "Small examples always predict how the approach behaves at larger scale.",
        ],
    )


def _misconception_items(misconceptions: Any) -> List[str]:
    if isinstance(misconceptions, list):
        return [safe_text(item) for item in misconceptions if safe_text(item)]

    return split_items(misconceptions, max_items=8)


def misconception_to_distractor(value: Any) -> str:
    text = clean_question_text(compact_text(value, MCQ_OPTION_MAX_CHARS))

    if "—" in text:
        text = text.split("—", 1)[0].strip()
    elif " - " in text:
        text = text.split(" - ", 1)[0].strip()

    text = text.strip("\"'“”‘’ ")

    if text and text[-1].isalnum():
        text += "."

    return clean_question_text(text)


def clean_distractors(
    options: List[str],
    correct_answer: str,
    concept: str,
    domain: str,
    misconceptions: Any,
    start_index: int = 0,
) -> List[str]:
    correct = clean_question_text(compact_text(correct_answer, MCQ_OPTION_MAX_CHARS))
    cleaned_options = []
    seen_normalized = set()

    def add_option(value: Any) -> None:
        text = clean_question_text(compact_text(value, MCQ_OPTION_MAX_CHARS))
        normalized = text.lower()

        if not text or normalized in seen_normalized:
            return

        if normalized != correct.lower() and is_bad_distractor(text):
            return

        cleaned_options.append(text)
        seen_normalized.add(normalized)

    add_option(correct)

    for option in options:
        if len(cleaned_options) >= 4:
            break
        add_option(option)

    misconception_candidates = _misconception_items(misconceptions)
    if misconception_candidates:
        offset = start_index % len(misconception_candidates)
        misconception_candidates = misconception_candidates[offset:] + misconception_candidates[:offset]

    misconception_count = 0
    max_misconceptions_per_question = 2

    for misconception in misconception_candidates:
        if len(cleaned_options) >= 4:
            break

        before_count = len(cleaned_options)
        add_option(misconception_to_distractor(misconception))

        if len(cleaned_options) > before_count:
            misconception_count += 1

        if misconception_count >= max_misconceptions_per_question:
            break

    fallback_candidates = get_domain_specific_distractors(domain, concept)
    if fallback_candidates:
        offset = start_index % len(fallback_candidates)
        fallback_candidates = fallback_candidates[offset:] + fallback_candidates[:offset]

    for fallback in fallback_candidates:
        if len(cleaned_options) >= 4:
            break
        add_option(fallback)

    if len(cleaned_options) < 4:
        generic_fallbacks = [
            "The same approach works well in every situation.",
            "The approach should be selected before considering the problem requirements.",
            "The most familiar approach always gives the most efficient solution.",
            "Small examples always predict how the approach behaves at larger scale.",
        ]

        for fallback in generic_fallbacks:
            if len(cleaned_options) >= 4:
                break
            add_option(fallback)

    cleaned_options = cleaned_options[:4]

    if cleaned_options.count(correct) != 1:
        cleaned_options = [option for option in cleaned_options if option.lower() != correct.lower()]
        cleaned_options.insert(0, correct)
        cleaned_options = cleaned_options[:4]

    if len(cleaned_options) == 4 and correct in cleaned_options:
        rng = random.Random(f"{domain}|{concept}|{correct}")
        rng.shuffle(cleaned_options)

    return cleaned_options


def build_plausible_mcq_options(
    correct_answer: str,
    concept_name: str,
    domain: str,
    misconceptions: Any,
    start_index: int = 0,
) -> List[str]:
    return clean_distractors(
        options=[],
        correct_answer=correct_answer,
        concept=concept_name,
        domain=domain,
        misconceptions=misconceptions,
        start_index=start_index,
    )


def primary_key_point(concept: Dict[str, Any], index: int = 0) -> str:
    items = split_items(concept.get("key_points", ""), max_items=8)
    if items:
        return items[index % len(items)]
    return first_sentence(concept.get("base_content", ""), 160)


def primary_misconception(concept: Dict[str, Any], index: int = 0) -> str:
    items = split_items(concept.get("misconceptions", ""), max_items=8)
    if items:
        return items[index % len(items)]
    return f"A common mistake is misunderstanding {concept['concept_name']}."


def primary_example(concept: Dict[str, Any], index: int = 0) -> str:
    items = split_items(concept.get("examples", ""), max_items=8)
    if items:
        return items[index % len(items)]
    return ""


def primary_real_use(concept: Dict[str, Any], index: int = 0) -> str:
    items = split_items(concept.get("real_world_use", ""), max_items=8)
    if items:
        return items[index % len(items)]
    return f"{concept['concept_name']} is used in real-world problem solving."


def normalize_for_duplicate(value: Any) -> str:
    if isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    else:
        text = str(value)

    text = text.lower()
    text = " ".join(text.split())

    keep = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            keep.append(ch)

    return "".join(keep).strip()


def load_concepts() -> List[Dict[str, Any]]:
    concepts = []

    for config in DB_CONFIGS:
        db_path = config["path"]
        domain = config["domain"]

        if not db_path.exists():
            print(f"WARNING: Missing DB: {db_path}")
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT concept_id, topic, base_content, examples, key_points,
                   misconceptions, real_world_use, next_concept_link
            FROM concept_resources
            ORDER BY concept_id
            """
        ).fetchall()

        conn.close()

        print(f"{domain}: {len(rows)} concepts loaded")

        for row in rows:
            concepts.append(
                {
                    "concept_id": safe_text(row["concept_id"]),
                    "concept_name": safe_text(row["topic"]),
                    "domain": domain,
                    "base_content": safe_text(row["base_content"]),
                    "examples": safe_text(row["examples"]),
                    "key_points": safe_text(row["key_points"]),
                    "misconceptions": safe_text(row["misconceptions"]),
                    "real_world_use": safe_text(row["real_world_use"]),
                    "next_concept_link": safe_text(row["next_concept_link"]),
                }
            )

    return concepts


def make_mcq_variants(concept: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = concept["concept_name"]
    domain = concept["domain"]
    misconceptions = concept.get("misconceptions", "")

    key1 = primary_key_point(concept, 0)
    key2 = primary_key_point(concept, 1)
    key3 = primary_key_point(concept, 2)

    variants = [
        {
            "question": f"Which statement best describes {name}?",
            "answer": key1,
            "explanation": f"The correct option states the main idea of {name}.",
        },
        {
            "question": f"Which idea about {name} is correct?",
            "answer": key2,
            "explanation": f"This option matches an important rule about {name}.",
        },
        {
            "question": f"Which option avoids a common mistake in {name}?",
            "answer": key1,
            "explanation": f"The correct answer avoids the common misconception about {name}.",
        },
        {
            "question": f"What should a learner remember first about {name}?",
            "answer": key3,
            "explanation": f"The first thing to remember is the practical rule behind {name}.",
        },
        {
            "question": f"Which statement is most useful when applying {name}?",
            "answer": key1,
            "explanation": f"Applying {name} requires understanding the core rule.",
        },
    ]

    # Clean and shorten all MCQ options so the website does not show truncated text.
    cleaned_variants = []

    for option_start_index, variant in enumerate(variants):
        answer = clean_question_text(compact_text(variant["answer"], MCQ_OPTION_MAX_CHARS))
        cleaned_options = build_plausible_mcq_options(
            correct_answer=answer,
            concept_name=name,
            domain=domain,
            misconceptions=misconceptions,
            start_index=option_start_index,
        )

        cleaned_variants.append(
            {
                "question": clean_question_text(variant["question"]),
                "options": cleaned_options,
                "answer": answer,
                "explanation": clean_question_text(variant["explanation"]),
            }
        )

    return cleaned_variants




def make_debug_variants(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    name = concept["concept_name"]
    domain = concept["domain"]

    lower_name = name.lower()

    if domain == "Python":
        if "variable" in lower_name:
            return [
                {
                    "buggy_code": "name = Alice\nprint(name)",
                    "expected_fix": "name = \"Alice\"\nprint(name)",
                    "hint": "String values need quotation marks.",
                },
                {
                    "buggy_code": "print(score)\nscore = 10",
                    "expected_fix": "score = 10\nprint(score)",
                    "hint": "Assign the variable before using it.",
                },
                {
                    "buggy_code": "2score = 10\nprint(2score)",
                    "expected_fix": "score2 = 10\nprint(score2)",
                    "hint": "Variable names cannot start with a digit.",
                },
            ]

        if "loop" in lower_name:
            return [
                {
                    "buggy_code": "for i in range(3)\n    print(i)",
                    "expected_fix": "for i in range(3):\n    print(i)",
                    "hint": "A Python loop header needs a colon.",
                },
                {
                    "buggy_code": "count = 0\nwhile count < 3:\n    print(count)",
                    "expected_fix": "count = 0\nwhile count < 3:\n    print(count)\n    count += 1",
                    "hint": "Update the loop variable so the while loop can stop.",
                },
                {
                    "buggy_code": "numbers = [1, 2, 3]\nfor n in numbers:\nprint(n * 2)",
                    "expected_fix": "numbers = [1, 2, 3]\nfor n in numbers:\n    print(n * 2)",
                    "hint": "The loop body should be indented.",
                },
            ]

        if "function" in lower_name:
            return [
                {
                    "buggy_code": "def add(a, b):\n    a + b\n\nresult = add(2, 3)",
                    "expected_fix": "def add(a, b):\n    return a + b\n\nresult = add(2, 3)",
                    "hint": "Fix the Functions bug by returning the computed value.",
                },
                {
                    "buggy_code": "def add(a, b):\nprint(a + b)",
                    "expected_fix": "def add(a, b):\n    print(a + b)",
                    "hint": "Fix the Functions indentation bug in the function body.",
                },
                {
                    "buggy_code": "result = add(2, 3)\ndef add(a, b):\n    return a + b",
                    "expected_fix": "def add(a, b):\n    return a + b\nresult = add(2, 3)",
                    "hint": "Fix the Functions call order by defining the function before calling it.",
                },
            ]

        if "data type" in lower_name:
            return [
                {
                    "buggy_code": "age = \"20\"\nprint(age + 1)",
                    "expected_fix": "age = \"20\"\nprint(int(age) + 1)",
                    "hint": "Fix the Data Types bug by converting text before numeric addition.",
                },
                {
                    "buggy_code": "price = \"9.99\"\ntotal = price * 2",
                    "expected_fix": "price = \"9.99\"\ntotal = float(price) * 2",
                    "hint": "Fix the Data Types bug by converting the string to a number first.",
                },
                {
                    "buggy_code": "items = [\"1\", \"2\", \"3\"]\nprint(sum(items))",
                    "expected_fix": "items = [\"1\", \"2\", \"3\"]\nprint(sum(int(item) for item in items))",
                    "hint": "Fix the Data Types bug by converting each string item before summing.",
                },
            ]

        if "conditional" in lower_name:
            return [
                {
                    "buggy_code": "score = 80\nif score = 80:\n    print(\"pass\")",
                    "expected_fix": "score = 80\nif score == 80:\n    print(\"pass\")",
                    "hint": "Fix the Conditionals bug by using comparison in the condition.",
                },
                {
                    "buggy_code": "age = 17\nif age >= 18:\nprint(\"adult\")",
                    "expected_fix": "age = 17\nif age >= 18:\n    print(\"adult\")",
                    "hint": "Fix the Conditionals bug by indenting the branch body.",
                },
                {
                    "buggy_code": "status = \"paid\"\nif status == \"paid\":\n    print(\"ship\")\nif status != \"paid\":\n    print(\"hold\")",
                    "expected_fix": "status = \"paid\"\nif status == \"paid\":\n    print(\"ship\")\nelse:\n    print(\"hold\")",
                    "hint": "Fix the Conditionals logic by using else for the opposite branch.",
                },
            ]

        if "object-oriented" in lower_name or "oop" in lower_name:
            return [
                {
                    "buggy_code": "class User:\n    def set_name(name):\n        self.name = name",
                    "expected_fix": "class User:\n    def set_name(self, name):\n        self.name = name",
                    "hint": "Fix the OOP method by including self as the first parameter.",
                },
                {
                    "buggy_code": "class User:\n    def __init__(self, name):\n        name = name",
                    "expected_fix": "class User:\n    def __init__(self, name):\n        self.name = name",
                    "hint": "Fix the OOP attribute bug by assigning to self.name.",
                },
                {
                    "buggy_code": "class Counter:\n    count = 0\n\nc = Counter()\nc.count += 1",
                    "expected_fix": "class Counter:\n    def __init__(self):\n        self.count = 0\n\nc = Counter()\nc.count += 1",
                    "hint": "Fix the OOP state bug by storing per-instance data on self.",
                },
            ]

        if "decorator" in lower_name or "generator" in lower_name:
            return [
                {
                    "buggy_code": "def numbers():\n    return 1\n    return 2",
                    "expected_fix": "def numbers():\n    yield 1\n    yield 2",
                    "hint": "Fix the Generators bug by yielding multiple values.",
                },
                {
                    "buggy_code": "def log_calls(fn):\n    def wrapper(*args, **kwargs):\n        print(\"calling\")\n        fn(*args, **kwargs)\n    return wrapper",
                    "expected_fix": "def log_calls(fn):\n    def wrapper(*args, **kwargs):\n        print(\"calling\")\n        return fn(*args, **kwargs)\n    return wrapper",
                    "hint": "Fix the Decorators bug by returning the wrapped function result.",
                },
                {
                    "buggy_code": "def repeat_twice(fn):\n    fn()\n    fn()",
                    "expected_fix": "def repeat_twice(fn):\n    def wrapper():\n        fn()\n        fn()\n    return wrapper",
                    "hint": "Fix the Decorators bug by returning a wrapper function.",
                },
            ]

        if "file" in lower_name:
            return [
                {
                    "buggy_code": "file = open(\"notes.txt\")\nfile.write(\"hello\")",
                    "expected_fix": "with open(\"notes.txt\", \"w\") as file:\n    file.write(\"hello\")",
                    "hint": "Fix the File Handling bug by opening in write mode and closing safely.",
                },
                {
                    "buggy_code": "file = open(\"data.txt\")\ncontent = file.read()",
                    "expected_fix": "with open(\"data.txt\", \"r\") as file:\n    content = file.read()",
                    "hint": "Fix the File Handling bug by using with for automatic close.",
                },
                {
                    "buggy_code": "with open(\"log.txt\", \"w\") as file:\n    old = file.read()",
                    "expected_fix": "with open(\"log.txt\", \"r\") as file:\n    old = file.read()",
                    "hint": "Fix the File Handling bug by using read mode when reading.",
                },
            ]

        return [
            {
                "buggy_code": "value = Example\nprint(value)",
                "expected_fix": "value = \"Example\"\nprint(value)",
                "hint": f"Fix the {name} bug by quoting text values.",
            },
            {
                "buggy_code": "print(value)\nvalue = 5",
                "expected_fix": "value = 5\nprint(value)",
                "hint": f"Fix the {name} bug by defining the value before using it.",
            },
            {
                "buggy_code": "if True\n    print(\"yes\")",
                "expected_fix": "if True:\n    print(\"yes\")",
                "hint": f"Fix the {name} bug by adding the colon to the block header.",
            },
        ]

    if domain == "SQL":
        if "select" in lower_name:
            return [
                {
                    "buggy_code": "SELECT name students;",
                    "expected_fix": "SELECT name FROM students;",
                    "hint": "Fix the SQL SELECT bug by adding FROM before the table name.",
                },
                {
                    "buggy_code": "SELECT FROM students;",
                    "expected_fix": "SELECT name FROM students;",
                    "hint": "Fix the SQL SELECT bug by naming at least one selected column.",
                },
                {
                    "buggy_code": "SELECT name, FROM students;",
                    "expected_fix": "SELECT name FROM students;",
                    "hint": "Fix the SQL SELECT bug by removing the trailing comma.",
                },
            ]
        if "where" in lower_name or "filter" in lower_name:
            return [
                {
                    "buggy_code": "SELECT * FROM students WHERE grade;",
                    "expected_fix": "SELECT * FROM students WHERE grade = 'A';",
                    "hint": "Fix the WHERE bug by writing a complete condition.",
                },
                {
                    "buggy_code": "SELECT * FROM students WHERE age => 18;",
                    "expected_fix": "SELECT * FROM students WHERE age >= 18;",
                    "hint": "Fix the WHERE bug by using the correct comparison operator.",
                },
                {
                    "buggy_code": "SELECT * FROM students WHERE 'A';",
                    "expected_fix": "SELECT * FROM students WHERE grade = 'A';",
                    "hint": "Fix the WHERE bug by filtering a column, not a bare value.",
                },
            ]
        if "join" in lower_name:
            return [
                {
                    "buggy_code": "SELECT students.name, courses.title\nFROM students\nJOIN courses;",
                    "expected_fix": "SELECT students.name, courses.title\nFROM students\nJOIN enrollments ON enrollments.student_id = students.student_id\nJOIN courses ON courses.course_id = enrollments.course_id;",
                    "hint": "Fix the JOIN bug by adding ON conditions with matching keys.",
                },
                {
                    "buggy_code": "SELECT * FROM orders JOIN customers ON orders.order_id = customers.customer_id;",
                    "expected_fix": "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.customer_id;",
                    "hint": "Fix the JOIN bug by joining on the customer key.",
                },
                {
                    "buggy_code": "SELECT customers.name FROM customers INNER JOIN orders;",
                    "expected_fix": "SELECT customers.name FROM customers INNER JOIN orders ON orders.customer_id = customers.customer_id;",
                    "hint": "Fix the JOIN bug by specifying how rows match.",
                },
            ]
        if "index" in lower_name:
            return [
                {
                    "buggy_code": "CREATE INDEX idx_students_name ON students(age);\nSELECT * FROM students WHERE name = 'Alice';",
                    "expected_fix": "CREATE INDEX idx_students_name ON students(name);\nSELECT * FROM students WHERE name = 'Alice';",
                    "hint": "Fix the Indexes bug by indexing the filtered column.",
                },
                {
                    "buggy_code": "CREATE INDEX idx_orders_total ON orders(total);\n-- Expect: SELECT results change order automatically",
                    "expected_fix": "CREATE INDEX idx_orders_total ON orders(total);\n-- Use ORDER BY total when result order matters",
                    "hint": "Fix the Indexes misconception: an index can speed lookup but does not define output order.",
                },
                {
                    "buggy_code": "CREATE INDEX idx_users_email ON users(name);\nSELECT * FROM users WHERE email = 'a@example.com';",
                    "expected_fix": "CREATE INDEX idx_users_email ON users(email);\nSELECT * FROM users WHERE email = 'a@example.com';",
                    "hint": "Fix the Indexes bug by matching the index to the lookup column.",
                },
            ]
        if "window" in lower_name:
            return [
                {
                    "buggy_code": "SELECT name, salary, RANK() ORDER BY salary DESC FROM employees;",
                    "expected_fix": "SELECT name, salary, RANK() OVER (ORDER BY salary DESC) FROM employees;",
                    "hint": "Fix the Window Functions bug by adding OVER.",
                },
                {
                    "buggy_code": "SELECT department, name, SUM(salary) FROM employees;",
                    "expected_fix": "SELECT department, name, SUM(salary) OVER (PARTITION BY department) FROM employees;",
                    "hint": "Fix the Window Functions bug by using OVER with PARTITION BY for per-row totals.",
                },
                {
                    "buggy_code": "SELECT name, ROW_NUMBER() OVER salary FROM employees;",
                    "expected_fix": "SELECT name, ROW_NUMBER() OVER (ORDER BY salary) FROM employees;",
                    "hint": "Fix the Window Functions bug by putting ORDER BY inside OVER(...).",
                },
            ]
        if "cte" in lower_name or "common table" in lower_name:
            return [
                {
                    "buggy_code": "recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;",
                    "expected_fix": "WITH recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;",
                    "hint": "Fix the CTE bug by starting the temporary result with WITH.",
                },
                {
                    "buggy_code": "WITH top_customers AS (SELECT customer_id FROM orders)\nSELECT * FROM customers;\nSELECT * FROM top_customers;",
                    "expected_fix": "WITH top_customers AS (SELECT customer_id FROM orders)\nSELECT * FROM top_customers;",
                    "hint": "Fix the CTE bug by using the CTE in the statement where it is defined.",
                },
                {
                    "buggy_code": "WITH totals AS SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id\nSELECT * FROM totals;",
                    "expected_fix": "WITH totals AS (SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id)\nSELECT * FROM totals;",
                    "hint": "Fix the CTE bug by wrapping the CTE query in parentheses.",
                },
            ]
        return [
            {
                "buggy_code": "SELECT * students;",
                "expected_fix": "SELECT * FROM students;",
                "hint": f"Fix the {name} SQL bug by using complete query syntax.",
            },
            {
                "buggy_code": "SELECT id, name FROM records WHERE;",
                "expected_fix": "SELECT id, name FROM records WHERE id IS NOT NULL;",
                "hint": f"Fix the {name} SQL bug by completing the condition.",
            },
            {
                "buggy_code": "SELECT name FROM records ORDER name;",
                "expected_fix": "SELECT name FROM records ORDER BY name;",
                "hint": f"Fix the {name} SQL bug by using ORDER BY.",
            },
        ]

    if domain == "HTML":
        if "accessibility" in lower_name:
            return [
                {
                    "buggy_code": "<label>Email</label>\n<input id=\"email\" type=\"email\">",
                    "expected_fix": "<label for=\"email\">Email</label>\n<input id=\"email\" name=\"email\" type=\"email\">",
                    "hint": "Fix the Accessibility bug by connecting the label to the input.",
                },
                {
                    "buggy_code": "<img src=\"chart.png\">",
                    "expected_fix": "<img src=\"chart.png\" alt=\"Sales chart for April\">",
                    "hint": "Fix the Accessibility bug by adding meaningful alt text.",
                },
                {
                    "buggy_code": "<h1>Profile</h1>\n<h3>Settings</h3>",
                    "expected_fix": "<h1>Profile</h1>\n<h2>Settings</h2>",
                    "hint": "Fix the Accessibility bug by keeping heading levels in order.",
                },
            ]
        if "component" in lower_name:
            return [
                {
                    "buggy_code": "class UserCard extends HTMLElement {}\n<user-card></user-card>",
                    "expected_fix": "class UserCard extends HTMLElement {}\ncustomElements.define(\"user-card\", UserCard);\n<user-card></user-card>",
                    "hint": "Fix the Web Components bug by registering the custom element.",
                },
                {
                    "buggy_code": "class UserCard extends HTMLElement {\n    connectedCallback() {\n        shadowRoot.innerHTML = \"<p>User</p>\";\n    }\n}",
                    "expected_fix": "class UserCard extends HTMLElement {\n    connectedCallback() {\n        const shadow = this.attachShadow({mode: \"open\"});\n        shadow.innerHTML = \"<p>User</p>\";\n    }\n}",
                    "hint": "Fix the Web Components bug by creating and using the component shadow root.",
                },
                {
                    "buggy_code": "customElements.define(\"UserCard\", UserCard);",
                    "expected_fix": "customElements.define(\"user-card\", UserCard);",
                    "hint": "Fix the Web Components bug by using a hyphenated custom element name.",
                },
            ]
        if "form" in lower_name or "input" in lower_name:
            return [
                {
                    "buggy_code": "<form><input id=\"email\"><button>Send</button></form>",
                    "expected_fix": "<form><label for=\"email\">Email</label><input id=\"email\" name=\"email\"><button type=\"submit\">Send</button></form>",
                    "hint": "Fix the Forms bug by adding a label and input name.",
                },
                {
                    "buggy_code": "<input type=\"email\" value=\"email\">",
                    "expected_fix": "<input type=\"email\" name=\"email\" placeholder=\"email@example.com\">",
                    "hint": "Fix the Forms bug by using name for submitted data and placeholder for hints.",
                },
                {
                    "buggy_code": "<button>Cancel</button>",
                    "expected_fix": "<button type=\"button\">Cancel</button>",
                    "hint": "Fix the Forms bug by setting button type when it should not submit.",
                },
            ]
        if "attribute" in lower_name or "link" in lower_name:
            return [
                {
                    "buggy_code": "<a src=\"about.html\">About</a>",
                    "expected_fix": "<a href=\"about.html\">About</a>",
                    "hint": "Fix the Attributes and Links bug by using href for links.",
                },
                {
                    "buggy_code": "<img href=\"logo.png\" alt=\"Logo\">",
                    "expected_fix": "<img src=\"logo.png\" alt=\"Logo\">",
                    "hint": "Fix the Attributes bug by using src for image files.",
                },
                {
                    "buggy_code": "<a href=>Read more</a>",
                    "expected_fix": "<a href=\"article.html\">Read more</a>",
                    "hint": "Fix the Links bug by providing a real href value.",
                },
            ]
        if "image" in lower_name or "list" in lower_name:
            return [
                {
                    "buggy_code": "<img src=\"photo.png\"></img>",
                    "expected_fix": "<img src=\"photo.png\" alt=\"Profile photo\">",
                    "hint": "Fix the Images bug because img is void and needs alt text.",
                },
                {
                    "buggy_code": "<ul><li>One<li>Two</ul>",
                    "expected_fix": "<ul><li>One</li><li>Two</li></ul>",
                    "hint": "Fix the Lists bug by closing each list item clearly.",
                },
                {
                    "buggy_code": "<ol><div>Step 1</div></ol>",
                    "expected_fix": "<ol><li>Step 1</li></ol>",
                    "hint": "Fix the Lists bug by using li elements inside ordered lists.",
                },
            ]
        if "service worker" in lower_name:
            return [
                {
                    "buggy_code": "navigator.serviceWorker.register();",
                    "expected_fix": "navigator.serviceWorker.register(\"/service-worker.js\");",
                    "hint": "Fix the Service Workers bug by passing the worker file path.",
                },
                {
                    "buggy_code": "self.addEventListener(\"install\", event => {\n    caches.open(\"v1\");\n});",
                    "expected_fix": "self.addEventListener(\"install\", event => {\n    event.waitUntil(caches.open(\"v1\"));\n});",
                    "hint": "Fix the Service Workers bug by waiting for cache setup.",
                },
                {
                    "buggy_code": "caches.match(request).then(response => fetch(request));",
                    "expected_fix": "caches.match(request).then(response => response || fetch(request));",
                    "hint": "Fix the Service Workers cache bug by returning cached responses when present.",
                },
            ]
        return [
            {
                "buggy_code": "<p>Hello",
                "expected_fix": "<p>Hello</p>",
                "hint": f"Fix the {name} markup bug by closing the paragraph tag.",
            },
            {
                "buggy_code": "<a href=page.html>Open</a>",
                "expected_fix": "<a href=\"page.html\">Open</a>",
                "hint": f"Fix the {name} attribute bug by quoting the value.",
            },
            {
                "buggy_code": "<strong><em>Hello</strong></em>",
                "expected_fix": "<strong><em>Hello</em></strong>",
                "hint": f"Fix the {name} nesting bug by closing tags in reverse order.",
            },
        ]

    if domain == "Git":
        if "repository" in lower_name:
            return [
                {
                    "buggy_code": "git remote add origin\ngit status",
                    "expected_fix": "git remote add origin https://github.com/user/project.git\ngit status",
                    "hint": "Fix the Git Repositories bug by giving the remote a URL.",
                },
                {
                    "buggy_code": "mkdir app\ncd app\ngit status",
                    "expected_fix": "mkdir app\ncd app\ngit init\ngit status",
                    "hint": "Fix the Git Repositories bug by initializing the repository first.",
                },
                {
                    "buggy_code": "git clone\ngit status",
                    "expected_fix": "git clone https://github.com/user/project.git\ncd project\ngit status",
                    "hint": "Fix the Git Repositories bug by cloning from a remote URL.",
                },
            ]
        if "commit" in lower_name or "history" in lower_name:
            return [
                {
                    "buggy_code": "git commit -m \"save login fix\"",
                    "expected_fix": "git add app.py\ngit commit -m \"save login fix\"",
                    "hint": "Fix the Commits bug by staging the file before committing.",
                },
                {
                    "buggy_code": "git add app.py\ngit push",
                    "expected_fix": "git add app.py\ngit commit -m \"Update app\"\ngit push",
                    "hint": "Fix the Commits bug by creating a commit before pushing.",
                },
                {
                    "buggy_code": "git log app.py",
                    "expected_fix": "git log -- app.py",
                    "hint": "Fix the History command by separating the file path with --.",
                },
            ]
        if "branch" in lower_name:
            return [
                {
                    "buggy_code": "git checkout feature/login\ngit commit -m \"fix login\"",
                    "expected_fix": "git checkout -b feature/login\ngit add .\ngit commit -m \"fix login\"",
                    "hint": "Fix the Branches bug by creating or switching to the feature branch first.",
                },
                {
                    "buggy_code": "git branch feature/login\ngit commit -m \"work\"",
                    "expected_fix": "git branch feature/login\ngit checkout feature/login\ngit add .\ngit commit -m \"work\"",
                    "hint": "Fix the Branches bug by checking out the branch before committing there.",
                },
                {
                    "buggy_code": "git merge feature/login\n# still on feature/login",
                    "expected_fix": "git checkout main\ngit merge feature/login",
                    "hint": "Fix the Branches bug by merging into the target branch.",
                },
            ]
        if "merge" in lower_name or "conflict" in lower_name:
            return [
                {
                    "buggy_code": "<<<<<<< HEAD\nold title\n=======\nnew title\n>>>>>>> feature",
                    "expected_fix": "new title",
                    "hint": "Fix the Merge Conflict bug by removing conflict markers after choosing content.",
                },
                {
                    "buggy_code": "git merge feature\n# conflict fixed in editor\ngit status",
                    "expected_fix": "git merge feature\n# conflict fixed in editor\ngit add conflicted-file.txt\ngit commit",
                    "hint": "Fix the Merge Conflict flow by staging the resolved file and completing the merge.",
                },
                {
                    "buggy_code": "git merge feature\nrm conflicted-file.txt\ngit commit",
                    "expected_fix": "git merge feature\n# edit conflicted-file.txt to keep intended content\ngit add conflicted-file.txt\ngit commit",
                    "hint": "Fix the Merge Conflict bug by resolving content instead of deleting blindly.",
                },
            ]
        if "rebase" in lower_name:
            return [
                {
                    "buggy_code": "git rebase main\n# conflict fixed\ngit commit -m \"fix conflict\"",
                    "expected_fix": "git rebase main\n# conflict fixed\ngit add .\ngit rebase --continue",
                    "hint": "Fix the Rebase bug by continuing the rebase after staging the resolution.",
                },
                {
                    "buggy_code": "git rebase main\ngit push",
                    "expected_fix": "git rebase main\ngit push --force-with-lease",
                    "hint": "Fix the Rebase workflow by updating the rewritten remote branch safely.",
                },
                {
                    "buggy_code": "git rebase --continue\n# conflict still unresolved",
                    "expected_fix": "# resolve conflict markers first\ngit add .\ngit rebase --continue",
                    "hint": "Fix the Rebase flow by resolving conflicts before continuing.",
                },
            ]
        if "submodule" in lower_name:
            return [
                {
                    "buggy_code": "git clone https://github.com/user/app.git\ncd app\nls vendor/library",
                    "expected_fix": "git clone https://github.com/user/app.git\ncd app\ngit submodule update --init --recursive",
                    "hint": "Fix the Submodules bug by initializing and updating submodules.",
                },
                {
                    "buggy_code": "git pull\n# submodule code still old",
                    "expected_fix": "git pull\ngit submodule update --recursive",
                    "hint": "Fix the Submodules bug by updating nested repositories after pulling.",
                },
                {
                    "buggy_code": "rm -rf vendor/library\ngit status",
                    "expected_fix": "git submodule deinit vendor/library\ngit rm vendor/library",
                    "hint": "Fix the Submodules removal flow by deinitializing and removing through Git.",
                },
            ]
        return [
            {
                "buggy_code": "git comit -m \"save\"",
                "expected_fix": "git commit -m \"save\"",
                "hint": f"Fix the {name} Git command typo.",
            },
            {
                "buggy_code": "git add\n git commit -m \"save\"",
                "expected_fix": "git add .\ngit commit -m \"save\"",
                "hint": f"Fix the {name} Git flow by specifying what to stage.",
            },
            {
                "buggy_code": "git checkout new-feature",
                "expected_fix": "git checkout -b new-feature",
                "hint": f"Fix the {name} Git branch command by using -b when creating a branch.",
            },
        ]

    if "array" in lower_name:
        return [
            {
                "buggy_code": "items = [10, 20, 30]\nlast = items[len(items)]",
                "expected_fix": "items = [10, 20, 30]\nlast = items[len(items) - 1]",
                "hint": "Fix the Arrays bug by using the last valid zero-based index.",
            },
            {
                "buggy_code": "items = [10, 20, 30]\nfor i in range(1, len(items)):\n    print(items[i])",
                "expected_fix": "items = [10, 20, 30]\nfor i in range(0, len(items)):\n    print(items[i])",
                "hint": "Fix the Arrays bug by starting at index 0 when every item is needed.",
            },
            {
                "buggy_code": "items = [10, 20, 30]\nitems[3] = 40",
                "expected_fix": "items = [10, 20, 30]\nitems.append(40)",
                "hint": "Fix the Arrays bug by appending instead of writing past the last index.",
            },
        ]
    if "linked" in lower_name:
        return [
            {
                "buggy_code": "new_node.next = head.next\nhead = new_node",
                "expected_fix": "new_node.next = head\nhead = new_node",
                "hint": "Fix the Linked List bug by preserving the old head pointer.",
            },
            {
                "buggy_code": "current.next = new_node\nnew_node.next = current.next",
                "expected_fix": "new_node.next = current.next\ncurrent.next = new_node",
                "hint": "Fix the Linked List insertion order so the rest of the list is not lost.",
            },
            {
                "buggy_code": "while current:\n    current = current.next\ncurrent.next = new_node",
                "expected_fix": "while current.next:\n    current = current.next\ncurrent.next = new_node",
                "hint": "Fix the Linked List traversal by stopping at the last node before appending.",
            },
        ]
    if "stack" in lower_name:
        return [
            {
                "buggy_code": "stack = [\"first\", \"second\"]\nremoved = stack.pop(0)",
                "expected_fix": "stack = [\"first\", \"second\"]\nremoved = stack.pop()",
                "hint": "Fix the Stack bug by removing the most recent item.",
            },
            {
                "buggy_code": "stack = []\nitem = stack.pop()",
                "expected_fix": "stack = []\nif stack:\n    item = stack.pop()",
                "hint": "Fix the Stack bug by checking for empty stack before pop.",
            },
            {
                "buggy_code": "stack = []\nstack.pop(\"page\")",
                "expected_fix": "stack = []\nstack.append(\"page\")",
                "hint": "Fix the Stack bug by using push/append to add an item.",
            },
        ]
    if "queue" in lower_name:
        return [
            {
                "buggy_code": "queue = [\"first\", \"second\"]\nremoved = queue.pop()",
                "expected_fix": "queue = [\"first\", \"second\"]\nremoved = queue.pop(0)",
                "hint": "Fix the Queue bug by removing the oldest item first.",
            },
            {
                "buggy_code": "queue = []\nnext_item = queue.pop(0)",
                "expected_fix": "queue = []\nif queue:\n    next_item = queue.pop(0)",
                "hint": "Fix the Queue bug by checking for empty queue before dequeue.",
            },
            {
                "buggy_code": "queue = []\nqueue.pop(0, \"job\")",
                "expected_fix": "queue = []\nqueue.append(\"job\")",
                "hint": "Fix the Queue bug by enqueueing with append before removing.",
            },
        ]
    if "tree" in lower_name:
        return [
            {
                "buggy_code": "def inorder(node):\n    visit(node)\n    inorder(node.left)\n    inorder(node.right)",
                "expected_fix": "def inorder(node):\n    inorder(node.left)\n    visit(node)\n    inorder(node.right)",
                "hint": "Fix the Trees bug so inorder traversal visits left, root, then right.",
            },
            {
                "buggy_code": "def height(node):\n    return 1 + height(node.left)",
                "expected_fix": "def height(node):\n    return 1 + max(height(node.left), height(node.right))",
                "hint": "Fix the Trees bug by considering both child branches.",
            },
            {
                "buggy_code": "def search(node, target):\n    return node.value == target",
                "expected_fix": "def search(node, target):\n    return node.value == target or search(node.left, target) or search(node.right, target)",
                "hint": "Fix the Trees bug by searching child nodes, not only the root.",
            },
        ]
    if "set" in lower_name:
        return [
            {
                "buggy_code": "seen = set([\"A\", \"A\", \"B\"])\nprint(len(seen) == 3)",
                "expected_fix": "seen = set([\"A\", \"A\", \"B\"])\nprint(len(seen) == 2)",
                "hint": "Fix the Sets bug because duplicate values are removed.",
            },
            {
                "buggy_code": "allowed = {\"read\", \"write\"}\nallowed.append(\"admin\")",
                "expected_fix": "allowed = {\"read\", \"write\"}\nallowed.add(\"admin\")",
                "hint": "Fix the Sets bug by using add for set insertion.",
            },
            {
                "buggy_code": "common = a + b",
                "expected_fix": "common = a & b",
                "hint": "Fix the Sets bug by using intersection for shared values.",
            },
        ]
    if "graph" in lower_name:
        return [
            {
                "buggy_code": "def dfs(node):\n    for neighbor in graph[node]:\n        dfs(neighbor)",
                "expected_fix": "def dfs(node):\n    if node in visited:\n        return\n    visited.add(node)\n    for neighbor in graph[node]:\n        dfs(neighbor)",
                "hint": "Fix the Graphs bug by tracking visited nodes.",
            },
            {
                "buggy_code": "queue = [start]\nwhile queue:\n    node = queue.pop()\n    queue.extend(graph[node])",
                "expected_fix": "queue = [start]\nwhile queue:\n    node = queue.pop(0)\n    queue.extend(graph[node])",
                "hint": "Fix the Graphs BFS bug by dequeuing from the front.",
            },
            {
                "buggy_code": "graph[a].append(b)",
                "expected_fix": "graph[a].append(b)\ngraph[b].append(a)",
                "hint": "Fix the Graphs bug by adding both directions for an undirected edge.",
            },
        ]

    return [
        {
            "buggy_code": "remove_item()  # used before checking if item exists",
            "expected_fix": "if item_exists:\n    remove_item()",
            "hint": f"Fix the {name} bug by checking the condition before applying the operation.",
        },
        {
            "buggy_code": "push(item)\npop()\npop()",
            "expected_fix": "push(item)\nif not empty:\n    pop()",
            "hint": f"Fix the {name} bug by checking whether the structure is empty before removing.",
        },
        {
            "buggy_code": "visit(node)\nvisit(node)",
            "expected_fix": "if node not in visited:\n    visit(node)",
            "hint": f"Fix the {name} bug by avoiding duplicate processing.",
        },
    ]


def make_output_prediction_variants(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    name = concept["concept_name"]
    domain = concept["domain"]
    lower_name = name.lower()

    if domain == "Python":
        if "variable" in lower_name:
            return [
                {
                    "question": "What is the output of this code?",
                    "code": "x = 5\nprint(x)",
                    "answer": "5",
                    "explanation": "x stores 5, so print(x) displays 5.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "x = 10\nx = 20\nprint(x)",
                    "answer": "20",
                    "explanation": "The second assignment changes what x refers to.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "name = \"Alice\"\nprint(name)",
                    "answer": "Alice",
                    "explanation": "name refers to the string Alice.",
                },
            ]

        if "loop" in lower_name:
            return [
                {
                    "question": "What is the output of this code?",
                    "code": "for i in range(3):\n    print(i)",
                    "answer": "0\n1\n2",
                    "explanation": "range(3) produces 0, 1, and 2.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "total = 0\nfor x in [1, 2, 3]:\n    total += x\nprint(total)",
                    "answer": "6",
                    "explanation": "The loop adds 1, 2, and 3.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "for letter in \"ab\":\n    print(letter)",
                    "answer": "a\nb",
                    "explanation": "The loop visits each character in the string.",
                },
            ]

        if "data type" in lower_name:
            return [
                {
                    "question": "What is the output of this code?",
                    "code": "age = \"20\"\nprint(int(age) + 1)",
                    "answer": "21",
                    "explanation": "int(age) converts the string before addition.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "price = \"9.5\"\nprint(float(price) * 2)",
                    "answer": "19.0",
                    "explanation": "float(price) converts text to a decimal number.",
                },
                {
                    "question": "What is the output of this code?",
                    "code": "items = [\"1\", \"2\"]\nprint(\"\".join(items))",
                    "answer": "12",
                    "explanation": "The list contains strings, so join concatenates them.",
                },
            ]

        if "conditional" in lower_name:
            return [
                {
                    "question": "What is the output of this conditional?",
                    "code": "score = 82\nif score >= 80:\n    print(\"pass\")\nelse:\n    print(\"retry\")",
                    "answer": "pass",
                    "explanation": "The condition is true, so the if branch runs.",
                },
                {
                    "question": "What is the output of this conditional?",
                    "code": "role = \"guest\"\nif role == \"admin\":\n    print(\"full\")\nelif role == \"guest\":\n    print(\"limited\")",
                    "answer": "limited",
                    "explanation": "The elif branch matches the value guest.",
                },
                {
                    "question": "What is the output of this conditional?",
                    "code": "logged_in = False\nprint(\"home\" if logged_in else \"login\")",
                    "answer": "login",
                    "explanation": "The conditional expression chooses the else value.",
                },
            ]

        if "function" in lower_name:
            return [
                {
                    "question": "What is the output of this function call?",
                    "code": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))",
                    "answer": "5",
                    "explanation": "The function returns 2 + 3.",
                },
                {
                    "question": "What is the output of this function call?",
                    "code": "def greet(name):\n    return \"Hi \" + name\n\nprint(greet(\"Asha\"))",
                    "answer": "Hi Asha",
                    "explanation": "The argument is combined with the greeting string.",
                },
                {
                    "question": "What is the output of this function call?",
                    "code": "def double(x):\n    return x * 2\n\nprint(double(double(3)))",
                    "answer": "12",
                    "explanation": "The inner call returns 6, then the outer call doubles it.",
                },
            ]

        if "object-oriented" in lower_name or "oop" in lower_name:
            return [
                {
                    "question": "What is the output of this OOP code?",
                    "code": "class Counter:\n    def __init__(self):\n        self.count = 0\n\nc = Counter()\nc.count += 1\nprint(c.count)",
                    "answer": "1",
                    "explanation": "The instance attribute is incremented once.",
                },
                {
                    "question": "What is the output of this OOP code?",
                    "code": "class User:\n    def __init__(self, name):\n        self.name = name\n\nprint(User(\"Maya\").name)",
                    "answer": "Maya",
                    "explanation": "The constructor stores the name on the instance.",
                },
                {
                    "question": "What is the output of this OOP code?",
                    "code": "class Box:\n    def label(self):\n        return \"box\"\n\nprint(Box().label())",
                    "answer": "box",
                    "explanation": "The method returns the string box.",
                },
            ]

        if "decorator" in lower_name or "generator" in lower_name:
            return [
                {
                    "question": "What is the output of this decorator example?",
                    "code": "def deco(fn):\n    def wrapper():\n        print(\"before\")\n        fn()\n    return wrapper\n\n@deco\ndef greet():\n    print(\"hello\")\n\ngreet()",
                    "answer": "before\nhello",
                    "explanation": "The wrapper prints first, then calls greet.",
                },
                {
                    "question": "What is the output of this generator example?",
                    "code": "def nums():\n    yield 1\n    yield 2\n\nfor n in nums():\n    print(n)",
                    "answer": "1\n2",
                    "explanation": "The generator yields one value at a time.",
                },
                {
                    "question": "What is the output of this decorator example?",
                    "code": "def shout(fn):\n    def wrapper():\n        print(fn().upper())\n    return wrapper\n\n@shout\ndef word():\n    return \"hello\"\n\nword()",
                    "answer": "HELLO",
                    "explanation": "The wrapper uppercases the decorated function result.",
                },
            ]

        if "file" in lower_name:
            return [
                {
                    "question": "What does this file-handling code print after writing and reading?",
                    "code": "with open(\"note.txt\", \"w\") as f:\n    f.write(\"done\")\nwith open(\"note.txt\", \"r\") as f:\n    print(f.read())",
                    "answer": "done",
                    "explanation": "The first block writes text, and the second reads it.",
                },
                {
                    "question": "What does this file-handling code print?",
                    "code": "line = \"alpha\\n\".strip()\nprint(line)",
                    "answer": "alpha",
                    "explanation": "strip removes the newline from the text.",
                },
                {
                    "question": "What does this file path example print?",
                    "code": "filename = \"report.txt\"\nprint(filename.endswith(\".txt\"))",
                    "answer": "True",
                    "explanation": "The filename string ends with the .txt suffix.",
                },
            ]

        return [
            {
                "question": "What is the output of this code?",
                "code": "value = 3\nprint(value)",
                "answer": "3",
                "explanation": "value stores 3.",
            },
            {
                "question": "What is the output of this code?",
                "code": "print(\"Python\")",
                "answer": "Python",
                "explanation": "print displays the text.",
            },
            {
                "question": "What is the output of this code?",
                "code": "x = 2 + 3\nprint(x)",
                "answer": "5",
                "explanation": "2 + 3 evaluates to 5.",
            },
        ]

    if domain == "SQL":
        if "where" in lower_name or "filter" in lower_name:
            return [
                {
                    "question": "What does this filtered query return?",
                    "code": "SELECT name FROM students WHERE grade = 'A';",
                    "answer": "It returns names for students whose grade is A.",
                    "explanation": "WHERE keeps only rows matching the grade condition.",
                },
                {
                    "question": "What does this filtered query return?",
                    "code": "SELECT product FROM orders WHERE amount >= 100;",
                    "answer": "It returns products from orders with amount at least 100.",
                    "explanation": "The comparison filters rows by amount.",
                },
                {
                    "question": "What does this filtered query return?",
                    "code": "SELECT email FROM users WHERE active = 1;",
                    "answer": "It returns emails for active users.",
                    "explanation": "The condition keeps active rows.",
                },
            ]
        if "join" in lower_name:
            return [
                {
                    "question": "What does this JOIN query return?",
                    "code": "SELECT students.name, courses.title\nFROM students\nJOIN enrollments ON enrollments.student_id = students.student_id\nJOIN courses ON courses.course_id = enrollments.course_id;",
                    "answer": "It returns matched student names with course titles.",
                    "explanation": "The JOINs connect students to courses through enrollments.",
                },
                {
                    "question": "What does this JOIN query return?",
                    "code": "SELECT orders.id, customers.name\nFROM orders\nJOIN customers ON orders.customer_id = customers.customer_id;",
                    "answer": "It returns order ids with matching customer names.",
                    "explanation": "The customer key connects the two tables.",
                },
                {
                    "question": "What does this LEFT JOIN preserve?",
                    "code": "SELECT customers.name, orders.id\nFROM customers\nLEFT JOIN orders ON orders.customer_id = customers.customer_id;",
                    "answer": "It keeps all customers, even customers without orders.",
                    "explanation": "LEFT JOIN preserves rows from the left table.",
                },
            ]
        if "index" in lower_name:
            return [
                {
                    "question": "What changes after this index is added?",
                    "code": "CREATE INDEX idx_students_name ON students(name);\nSELECT * FROM students WHERE name = 'Alice';",
                    "answer": "The result stays the same, but lookup may be faster.",
                    "explanation": "Indexes improve retrieval without changing query meaning.",
                },
                {
                    "question": "What does this index support?",
                    "code": "CREATE INDEX idx_orders_customer ON orders(customer_id);",
                    "answer": "It supports faster lookups or joins by customer_id.",
                    "explanation": "The indexed column matches common filtering/joining work.",
                },
                {
                    "question": "What should you expect from this indexed ORDER BY query?",
                    "code": "CREATE INDEX idx_products_price ON products(price);\nSELECT * FROM products ORDER BY price;",
                    "answer": "The query returns rows ordered by price.",
                    "explanation": "ORDER BY controls result order; the index may help performance.",
                },
            ]
        if "window" in lower_name:
            return [
                {
                    "question": "What does this window query compute?",
                    "code": "SELECT department, name, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank\nFROM employees;",
                    "answer": "It ranks employees inside each department by salary.",
                    "explanation": "PARTITION BY creates one ranking window per department.",
                },
                {
                    "question": "What does this running total compute?",
                    "code": "SELECT day, amount, SUM(amount) OVER (ORDER BY day) AS running_total\nFROM sales;",
                    "answer": "It computes a cumulative sales total by day.",
                    "explanation": "The window keeps rows visible while adding an ordered aggregate.",
                },
                {
                    "question": "What does ROW_NUMBER assign here?",
                    "code": "SELECT name, ROW_NUMBER() OVER (ORDER BY name) AS row_num\nFROM students;",
                    "answer": "It assigns sequential numbers ordered by name.",
                    "explanation": "ROW_NUMBER numbers rows in the specified order.",
                },
            ]
        if "cte" in lower_name or "common table" in lower_name:
            return [
                {
                    "question": "What does this CTE query return?",
                    "code": "WITH recent_orders AS (SELECT * FROM orders WHERE order_date >= '2026-01-01')\nSELECT * FROM recent_orders;",
                    "answer": "It returns rows from the named recent_orders result.",
                    "explanation": "The CTE names a temporary result for the following SELECT.",
                },
                {
                    "question": "What does this CTE summarize?",
                    "code": "WITH totals AS (SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id)\nSELECT * FROM totals WHERE total > 1000;",
                    "answer": "It returns customers whose order total is greater than 1000.",
                    "explanation": "The CTE computes totals, then the outer query filters them.",
                },
                {
                    "question": "What role does active_users play here?",
                    "code": "WITH active_users AS (SELECT * FROM users WHERE active = 1)\nSELECT email FROM active_users;",
                    "answer": "It acts as a named temporary set of active users.",
                    "explanation": "The outer query reads from the CTE name.",
                },
            ]
        return [
            {
                "question": "What does this query return?",
                "code": "SELECT name FROM students;",
                "answer": "It returns values from the name column.",
                "explanation": "SELECT chooses which column to display.",
            },
            {
                "question": "What does this query return?",
                "code": "SELECT * FROM students;",
                "answer": "It returns all columns from the students table.",
                "explanation": "The star means all columns.",
            },
            {
                "question": "What does this query return?",
                "code": "SELECT age FROM students WHERE age > 18;",
                "answer": "It returns ages greater than 18 from students.",
                "explanation": "WHERE filters rows.",
            },
        ]

    if domain == "HTML":
        if "accessibility" in lower_name:
            return [
                {
                    "question": "What accessibility relationship does this create?",
                    "code": "<label for=\"email\">Email</label>\n<input id=\"email\" name=\"email\">",
                    "answer": "The label is associated with the email input.",
                    "explanation": "The for and id values match.",
                },
                {
                    "question": "What useful information does this image provide?",
                    "code": "<img src=\"chart.png\" alt=\"April sales chart\">",
                    "answer": "It provides alternative text for the chart image.",
                    "explanation": "The alt attribute gives non-visual context.",
                },
                {
                    "question": "What heading order is shown?",
                    "code": "<h1>Account</h1>\n<h2>Security</h2>",
                    "answer": "A top-level heading followed by a second-level section heading.",
                    "explanation": "Clear heading order helps navigation.",
                },
            ]
        if "service worker" in lower_name:
            return [
                {
                    "question": "What does this service worker call attempt?",
                    "code": "navigator.serviceWorker.register(\"/sw.js\")",
                    "answer": "It attempts to register the service worker script.",
                    "explanation": "register receives the service worker file path.",
                },
                {
                    "question": "What does waitUntil protect here?",
                    "code": "self.addEventListener(\"install\", event => {\n  event.waitUntil(caches.open(\"v1\"));\n});",
                    "answer": "It keeps the install event alive until the cache opens.",
                    "explanation": "Service worker setup should finish before install completes.",
                },
                {
                    "question": "What is returned when the cache has a match?",
                    "code": "caches.match(request).then(response => response || fetch(request));",
                    "answer": "The cached response is returned.",
                    "explanation": "The network is used only when no cached response exists.",
                },
            ]
        if "component" in lower_name:
            return [
                {
                    "question": "Why is this custom element name valid?",
                    "code": "customElements.define(\"user-card\", UserCard)",
                    "answer": "It is valid because user-card contains a hyphen.",
                    "explanation": "Custom element names must include a hyphen.",
                },
                {
                    "question": "What does attachShadow create?",
                    "code": "const shadow = this.attachShadow({mode: \"open\"});",
                    "answer": "It creates a shadow root for the component.",
                    "explanation": "The shadow root scopes component markup and styles.",
                },
                {
                    "question": "What lifecycle method runs when the element is added?",
                    "code": "connectedCallback() {\n  this.textContent = \"Ready\";\n}",
                    "answer": "connectedCallback runs and sets the text to Ready.",
                    "explanation": "connectedCallback is called when the custom element connects to the document.",
                },
            ]
        if "attribute" in lower_name or "link" in lower_name:
            return [
                {
                    "question": "What link text appears?",
                    "code": "<a href=\"about.html\">About</a>",
                    "answer": "About",
                    "explanation": "The anchor text is displayed and href stores the destination.",
                },
                {
                    "question": "What image source is referenced?",
                    "code": "<img src=\"logo.png\" alt=\"Logo\">",
                    "answer": "logo.png",
                    "explanation": "src points to the image file.",
                },
                {
                    "question": "What target page does this link use?",
                    "code": "<a href=\"docs.html\">Docs</a>",
                    "answer": "docs.html",
                    "explanation": "href stores the link destination.",
                },
            ]
        if "form" in lower_name or "input" in lower_name:
            return [
                {
                    "question": "What field name would be submitted?",
                    "code": "<input name=\"email\" type=\"email\">",
                    "answer": "email",
                    "explanation": "The name attribute identifies submitted form data.",
                },
                {
                    "question": "What button behavior is specified?",
                    "code": "<button type=\"submit\">Send</button>",
                    "answer": "The button submits the form.",
                    "explanation": "type=\"submit\" gives submit behavior.",
                },
                {
                    "question": "Which input is connected to the label?",
                    "code": "<label for=\"username\">User</label><input id=\"username\" name=\"username\">",
                    "answer": "The input with id username.",
                    "explanation": "The label for value matches the input id.",
                },
            ]
        return [
            {
                "question": "What appears on the page?",
                "code": "<p>Hello</p>",
                "answer": "Hello",
                "explanation": "The paragraph element displays Hello.",
            },
            {
                "question": "What does this link text show?",
                "code": "<a href=\"page.html\">Open page</a>",
                "answer": "Open page",
                "explanation": "The text between the anchor tags is displayed.",
            },
            {
                "question": "What list items appear?",
                "code": "<ul><li>A</li><li>B</li></ul>",
                "answer": "A and B",
                "explanation": "The list has two list items.",
            },
        ]

    if domain == "Git":
        if "commit" in lower_name or "history" in lower_name:
            return [
                {
                    "question": "What does this Git flow do?",
                    "code": "git add app.py\ngit commit -m \"Fix login\"\ngit log --oneline",
                    "answer": "It stages a file, creates a commit, and shows compact history.",
                    "explanation": "The commands follow the commit workflow.",
                },
                {
                    "question": "What does this history command show?",
                    "code": "git log --oneline -- app.py",
                    "answer": "It shows compact commit history for app.py.",
                    "explanation": "The path after -- limits history to that file.",
                },
                {
                    "question": "What state does this command inspect?",
                    "code": "git show --stat HEAD",
                    "answer": "It shows summary changes from the latest commit.",
                    "explanation": "HEAD points to the current latest commit.",
                },
            ]
        if "branch" in lower_name:
            return [
                {
                    "question": "What does this branch command do?",
                    "code": "git checkout -b feature/login",
                    "answer": "It creates and switches to feature/login.",
                    "explanation": "-b creates the branch during checkout.",
                },
                {
                    "question": "What does this branch listing show?",
                    "code": "git branch",
                    "answer": "It lists local branches and marks the current one.",
                    "explanation": "git branch reports branch state.",
                },
                {
                    "question": "What does this switch do?",
                    "code": "git switch main",
                    "answer": "It switches the working tree to main.",
                    "explanation": "git switch changes the active branch.",
                },
            ]
        if "merge" in lower_name or "conflict" in lower_name:
            return [
                {
                    "question": "What does this merge command attempt?",
                    "code": "git checkout main\ngit merge feature/login",
                    "answer": "It attempts to merge feature/login into main.",
                    "explanation": "The current branch receives the merged changes.",
                },
                {
                    "question": "What do these markers mean?",
                    "code": "<<<<<<< HEAD\nold\n=======\nnew\n>>>>>>> feature",
                    "answer": "They mark a merge conflict that must be resolved.",
                    "explanation": "Git shows both versions around the conflicting lines.",
                },
                {
                    "question": "What completes this resolved merge?",
                    "code": "git add conflicted.txt\ngit commit",
                    "answer": "It stages the resolution and creates the merge commit.",
                    "explanation": "Resolved conflicts must be staged before finishing.",
                },
            ]
        if "rebase" in lower_name:
            return [
                {
                    "question": "What does this interactive rebase command open?",
                    "code": "git log --oneline\ngit rebase -i HEAD~3",
                    "answer": "It opens the last three commits for interactive editing.",
                    "explanation": "Interactive rebase can reorder, squash, or edit recent commits.",
                },
                {
                    "question": "What continues this rebase after a conflict fix?",
                    "code": "git add .\ngit rebase --continue",
                    "answer": "It stages the resolution and continues the rebase.",
                    "explanation": "Rebase uses --continue after conflicts are resolved.",
                },
                {
                    "question": "What does this rebase do?",
                    "code": "git rebase main",
                    "answer": "It replays current branch commits on top of main.",
                    "explanation": "Rebase changes the base commit of the branch.",
                },
            ]
        if "submodule" in lower_name:
            return [
                {
                    "question": "What does this submodule command do?",
                    "code": "git submodule update --init --recursive",
                    "answer": "It initializes and updates nested submodule repositories.",
                    "explanation": "Submodules need their own checkout/update step.",
                },
                {
                    "question": "What does this command add?",
                    "code": "git submodule add https://github.com/user/lib.git vendor/lib",
                    "answer": "It adds an external repository as a submodule at vendor/lib.",
                    "explanation": "The parent stores a reference to the external repo.",
                },
                {
                    "question": "What should happen after pulling submodule pointer changes?",
                    "code": "git pull\ngit submodule update --recursive",
                    "answer": "The parent and nested submodule checkout are updated.",
                    "explanation": "Submodule pointers and contents are updated separately.",
                },
            ]
        if "repository" in lower_name:
            return [
                {
                    "question": "What does this repository setup do?",
                    "code": "git init\ngit status",
                    "answer": "It creates a repository and shows its working tree state.",
                    "explanation": "git init creates the .git history directory.",
                },
                {
                    "question": "What does this remote command connect?",
                    "code": "git remote add origin https://github.com/user/project.git",
                    "answer": "It connects the local repository to a remote named origin.",
                    "explanation": "Remotes let Git push and pull with hosted repositories.",
                },
                {
                    "question": "What does this clone command create?",
                    "code": "git clone https://github.com/user/project.git",
                    "answer": "It creates a local copy of the remote repository.",
                    "explanation": "Clone copies files and repository history.",
                },
            ]
        return [
            {
                "question": "What does this command show?",
                "code": "git status",
                "answer": "It shows the working tree status.",
                "explanation": "git status shows changed, staged, and untracked files.",
            },
            {
                "question": "What does this command do?",
                "code": "git add .",
                "answer": "It stages current changes.",
                "explanation": "git add prepares changes for commit.",
            },
            {
                "question": "What does this command do?",
                "code": "git log --oneline",
                "answer": "It shows commit history in short form.",
                "explanation": "git log displays previous commits.",
            },
        ]

    if "array" in lower_name:
        return [
            {
                "question": "What is printed from this array access?",
                "code": "arr = [10, 20, 30]\nprint(arr[1])",
                "answer": "20",
                "explanation": "Index 1 reads the second element.",
            },
            {
                "question": "What is the array after append?",
                "code": "arr = [10, 20]\narr.append(30)",
                "answer": "[10, 20, 30]",
                "explanation": "append adds the new value at the end.",
            },
            {
                "question": "Which element is last?",
                "code": "arr = [10, 20, 30]\nlast = arr[len(arr) - 1]",
                "answer": "30",
                "explanation": "The final valid index is length minus one.",
            },
        ]
    if "linked" in lower_name:
        return [
            {
                "question": "What link changes when C is inserted after A?",
                "code": "A -> B -> None\ninsert C after A",
                "answer": "A -> C -> B -> None",
                "explanation": "C points to B, and A points to C.",
            },
            {
                "question": "What does head point to after inserting at the front?",
                "code": "head -> B -> None\ninsert A at head",
                "answer": "A",
                "explanation": "The new node becomes the head.",
            },
            {
                "question": "Which pointer is followed to move forward?",
                "code": "current = current.next",
                "answer": "next",
                "explanation": "A linked list node points to the next node.",
            },
        ]
    if "stack" in lower_name:
        return [
            {
                "question": "What is popped from this stack?",
                "code": "stack = []\nstack.append('A')\nstack.append('B')\nprint(stack.pop())",
                "answer": "B",
                "explanation": "A stack removes the last pushed item.",
            },
            {
                "question": "What remains after one pop?",
                "code": "stack = ['A', 'B']\nstack.pop()",
                "answer": "['A']",
                "explanation": "The top item B is removed.",
            },
            {
                "question": "Which item is on top?",
                "code": "stack = ['home', 'settings', 'profile']",
                "answer": "profile",
                "explanation": "The top is the most recently added item.",
            },
        ]
    if "queue" in lower_name:
        return [
            {
                "question": "What is dequeued from this queue?",
                "code": "queue = ['A', 'B']\nprint(queue.pop(0))",
                "answer": "A",
                "explanation": "A queue removes the oldest item first.",
            },
            {
                "question": "What remains after one dequeue?",
                "code": "queue = ['A', 'B']\nqueue.pop(0)",
                "answer": "['B']",
                "explanation": "The front item A is removed.",
            },
            {
                "question": "Which job runs first?",
                "code": "queue = ['email', 'backup', 'report']",
                "answer": "email",
                "explanation": "FIFO order serves the first enqueued job first.",
            },
        ]
    if "tree" in lower_name:
        return [
            {
                "question": "What is the inorder traversal?",
                "code": "root B with left A and right C",
                "answer": "A, B, C",
                "explanation": "Inorder visits left, root, then right.",
            },
            {
                "question": "Which node is the parent of A?",
                "code": "B\n└── A",
                "answer": "B",
                "explanation": "A is connected below B as a child.",
            },
            {
                "question": "What is the root?",
                "code": "root = 'CEO'; children = ['Manager']",
                "answer": "CEO",
                "explanation": "The root is the top node.",
            },
        ]
    if "set" in lower_name:
        return [
            {
                "question": "What is printed from this set length?",
                "code": "items = {1, 1, 2}\nprint(len(items))",
                "answer": "2",
                "explanation": "Duplicate 1 is stored only once.",
            },
            {
                "question": "What is in the set after add?",
                "code": "items = {'read'}\nitems.add('write')",
                "answer": "{'read', 'write'}",
                "explanation": "add inserts a unique item.",
            },
            {
                "question": "What is the intersection?",
                "code": "{1, 2, 3} & {2, 3, 4}",
                "answer": "{2, 3}",
                "explanation": "Intersection keeps values present in both sets.",
            },
        ]
    if "graph" in lower_name:
        return [
            {
                "question": "Why is visited used in this graph traversal?",
                "code": "if node in visited: return\nvisited.add(node)",
                "answer": "It prevents visiting the same node repeatedly.",
                "explanation": "Graphs can contain cycles.",
            },
            {
                "question": "What edge is represented?",
                "code": "roads['A'].append('B')",
                "answer": "A connection from A to B.",
                "explanation": "An adjacency list stores neighbors for each node.",
            },
            {
                "question": "What does BFS visit first from the queue?",
                "code": "queue = ['A', 'B']\nnode = queue.pop(0)",
                "answer": "A",
                "explanation": "BFS uses queue order.",
            },
        ]

    return [
        {
            "question": f"What happens when {name} is used correctly?",
            "code": primary_example(concept, 0),
            "answer": f"It applies the main idea of {name}.",
            "explanation": primary_key_point(concept, 0),
        },
        {
            "question": f"What should you observe in this {name} example?",
            "code": primary_example(concept, 1),
            "answer": primary_key_point(concept, 0),
            "explanation": f"The example demonstrates the key idea of {name}.",
        },
        {
            "question": f"What is the main result of applying {name}?",
            "code": primary_example(concept, 2),
            "answer": f"The structure behaves according to the rule of {name}.",
            "explanation": primary_key_point(concept, 1),
        },
    ]


def make_transfer_variants(concept: Dict[str, Any]) -> List[str]:
    name = concept["concept_name"]
    real1 = clean_question_text(primary_real_use(concept, 0))
    real2 = clean_question_text(primary_real_use(concept, 1))
    key = clean_question_text(primary_key_point(concept, 0)).rstrip(".")

    return [
        clean_question_text(f"How would you apply {name} in this real-world situation: {real1}?"),
        clean_question_text(f"Apply {name} in one new example where it solves a practical problem."),
        clean_question_text(f"Apply this rule in a different scenario and explain the result: {key}."),
        clean_question_text(f"Imagine you are building a small project. Where would you apply {name}, and why?"),
        clean_question_text(f"How would you apply {name} in this situation: {real2}?"),
    ]


def make_challenge_variants(concept: Dict[str, Any]) -> List[str]:
    name = concept["concept_name"]
    domain = concept["domain"]
    key1 = primary_key_point(concept, 0)
    key2 = primary_key_point(concept, 1)

    return [
        f"Design a non-trivial {domain} example using {name}, then explain why it follows this rule: {key1}",
        f"Compare two possible {domain} uses of {name} and justify which one better fits a realistic project.",
        f"Identify the mistake in this {domain} misconception, explain why it is wrong, and justify the fix: {primary_misconception(concept, 0)}",
        f"Modify a {domain} example so that it demonstrates {key2}, then explain what would break if the rule were ignored.",
        f"Design a small {domain} practice task where another learner must apply {name} and reason about an edge case.",
    ]


def make_explanation_check_variants(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    name = concept["concept_name"]
    key = clean_cut_text(primary_key_point(concept, 0))
    misconception = clean_cut_text(primary_misconception(concept, 0))

    common_mistake_text = clean_cut_text(
        f"Common mistake: {misconception} Correct idea: {key}"
    )

    return [
        {
            "question": clean_cut_text(f"Explain {name} in one or two sentences and give one concrete example."),
            "expected_key_points": key,
            "rubric": "Award full credit if the learner explains the main idea clearly.",
        },
        {
            "question": clean_cut_text(f"Explain one common mistake about {name}, and describe how to correct it."),
            "expected_key_points": common_mistake_text,
            "rubric": "Award full credit if the learner identifies the mistake and gives the correct rule.",
        },
        {
            "question": clean_cut_text(f"Explain why one example of {name} works and what rule it demonstrates."),
            "expected_key_points": key,
            "rubric": "Award full credit if the example matches the rule.",
        },
    ]

def validate_question(question_type: str, output: Any) -> List[str]:
    errors = []

    if output is None:
        return ["Output is None"]

    if question_type == "mcq":
        if not isinstance(output, dict):
            return ["MCQ output must be dict"]

        for field in ["question", "options", "answer", "explanation"]:
            if field not in output or not output[field]:
                errors.append(f"MCQ missing {field}")

        options = output.get("options", [])
        if not isinstance(options, list):
            errors.append("MCQ options must be list")
        elif len(options) != 4:
            errors.append(f"MCQ must have exactly 4 options, got {len(options)}")
        elif len(set(options)) != 4:
            errors.append("MCQ options must be unique")

        if output.get("answer") not in options:
            errors.append("MCQ answer must match one option")

    elif question_type == "debug_task":
        if not isinstance(output, dict):
            return ["debug_task output must be dict"]
        for field in ["buggy_code", "expected_fix", "hint"]:
            if field not in output or not output[field]:
                errors.append(f"debug_task missing {field}")

    elif question_type == "output_prediction":
        if not isinstance(output, dict):
            return ["output_prediction output must be dict"]
        for field in ["question", "code", "answer", "explanation"]:
            if field not in output or not output[field]:
                errors.append(f"output_prediction missing {field}")

    elif question_type in {"transfer_question", "challenge_question"}:
        if not isinstance(output, str) or len(output.strip()) < 30:
            errors.append(f"{question_type} must be non-empty text")

    elif question_type == "explanation_check":
        if not isinstance(output, dict):
            return ["explanation_check output must be dict"]
        for field in ["question", "expected_key_points", "rubric"]:
            if field not in output or not output[field]:
                errors.append(f"explanation_check missing {field}")

    return errors


def question_to_record(
    concept: Dict[str, Any],
    question_type: str,
    output: Any,
    variant_id: int,
    difficulty: str = "easy",
) -> Dict[str, Any]:


    # Final cleanup for generated text/dict fields before saving.
    if isinstance(output, str):
        output = clean_question_text(output)

    elif isinstance(output, dict):
        cleaned_output = {}

        raw_answer_fields = {"answer", "expected_output", "expected_fix", "code", "buggy_code"}

        for k, v in output.items():
            # Preserve code formatting.
            if k in {"buggy_code", "expected_fix", "code"} and isinstance(v, str):
                cleaned_output[k] = clean_code_text(v)

            elif k in {"answer", "expected_output"} and isinstance(v, str):
                cleaned_output[k] = clean_answer_text(v)

            elif isinstance(v, str):
                cleaned_output[k] = clean_question_text(v)

            elif isinstance(v, list):
                cleaned_output[k] = [
                    clean_answer_text(x) if k in raw_answer_fields and isinstance(x, str)
                    else clean_question_text(x) if isinstance(x, str)
                    else x
                    for x in v
                ]

            else:
                cleaned_output[k] = v

        output = cleaned_output

    errors = validate_question(question_type, output)
    valid = len(errors) == 0

    answer_key = {}
    rubric = {}

    if isinstance(output, dict):
        if question_type == "mcq":
            answer_key = {"answer": output.get("answer")}
            rubric = {"type": "exact_match", "field": "answer"}

        elif question_type == "debug_task":
            answer_key = {"expected_fix": output.get("expected_fix")}
            rubric = {"type": "code_fix", "hint": output.get("hint")}

        elif question_type == "output_prediction":
            answer_key = {"answer": output.get("answer")}
            rubric = {"type": "output_match"}

        elif question_type == "explanation_check":
            answer_key = {"expected_key_points": output.get("expected_key_points")}
            rubric = {"type": "rubric", "criteria": output.get("rubric")}

    else:
        answer_key = {"expected_key_points": primary_key_point(concept, 0)}
        rubric = {"type": "rubric", "criteria": "Answer should apply the concept correctly."}

    duplicate_group = normalize_for_duplicate(output)

    return {
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "question_type": question_type,
        "difficulty": difficulty,
        "variant_id": variant_id,
        "question_json": output if isinstance(output, dict) else None,
        "question_text": output if isinstance(output, str) else None,
        "answer_key_json": answer_key,
        "rubric_json": rubric,
        "valid": valid,
        "errors": errors,
        "duplicate_group": duplicate_group,
        "source": "variant_template_from_concept_resources",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_questions_for_concept(concept: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = []

    # 5 MCQs
    for idx, item in enumerate(make_mcq_variants(concept), start=1):
        records.append(question_to_record(concept, "mcq", item, idx))

    # 3 debug tasks
    for idx, item in enumerate(make_debug_variants(concept), start=1):
        records.append(question_to_record(concept, "debug_task", item, idx))

    # 3 output prediction questions
    for idx, item in enumerate(make_output_prediction_variants(concept), start=1):
        records.append(question_to_record(concept, "output_prediction", item, idx))

    # 3 transfer questions
    for idx, item in enumerate(make_transfer_variants(concept)[:3], start=1):
        records.append(question_to_record(concept, "transfer_question", item, idx))

    # 3 challenge questions
    for idx, item in enumerate(make_challenge_variants(concept)[:3], start=1):
        records.append(question_to_record(concept, "challenge_question", item, idx))

    # 3 explanation checks
    for idx, item in enumerate(make_explanation_check_variants(concept), start=1):
        records.append(question_to_record(concept, "explanation_check", item, idx))

    return records


def generate_question_bank(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    question_bank = []

    for concept in concepts:
        question_bank.extend(generate_questions_for_concept(concept))

    return question_bank


def inspect_question_bank(question_bank: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    by_concept = defaultdict(list)
    by_type = Counter()
    duplicates_global = defaultdict(list)

    for item in question_bank:
        key = (item["domain"], item["concept_id"], item["concept_name"])
        by_concept[key].append(item)
        by_type[item["question_type"]] += 1
        duplicates_global[item["duplicate_group"]].append(item)

        if not item["valid"]:
            issues.append(
                {
                    "concept_id": item["concept_id"],
                    "concept_name": item["concept_name"],
                    "question_type": item["question_type"],
                    "variant_id": item["variant_id"],
                    "errors": item["errors"],
                }
            )

    duplicate_groups = []
    for duplicate_key, group in duplicates_global.items():
        if len(group) > 1 and len(duplicate_key) > 40:
            duplicate_groups.append(
                {
                    "count": len(group),
                    "preview": duplicate_key[:180],
                    "items": [
                        {
                            "domain": item["domain"],
                            "concept_id": item["concept_id"],
                            "concept_name": item["concept_name"],
                            "question_type": item["question_type"],
                            "variant_id": item["variant_id"],
                        }
                        for item in group[:10]
                    ],
                }
            )

    concept_counts = {
        f"{key[0]}::{key[1]}::{key[2]}": len(items)
        for key, items in by_concept.items()
    }

    concepts_with_low_count = {
        key: count for key, count in concept_counts.items() if count < 15
    }

    return {
        "total_questions": len(question_bank),
        "total_concepts": len(by_concept),
        "valid_questions": sum(1 for item in question_bank if item["valid"]),
        "question_type_counts": dict(by_type),
        "issue_count": len(issues),
        "issues": issues,
        "concept_counts": concept_counts,
        "concepts_with_low_count": concepts_with_low_count,
        "global_duplicate_group_count": len(duplicate_groups),
        "global_duplicate_groups": duplicate_groups[:30],
    }


def build_question_bank_markdown(question_bank: List[Dict[str, Any]]) -> str:
    lines = []

    lines.append("# Assessment Question Bank")
    lines.append("")
    lines.append(f"Total questions: **{len(question_bank)}**")
    lines.append("")

    grouped = defaultdict(list)
    for item in question_bank:
        grouped[(item["domain"], item["concept_id"], item["concept_name"])].append(item)

    for (domain, concept_id, concept_name), items in grouped.items():
        lines.append(f"## {domain} — {concept_id}: {concept_name}")
        lines.append("")

        for item in items:
            lines.append(
                f"### {item['question_type']} — Variant {item['variant_id']}"
            )
            lines.append("")
            lines.append(f"- Valid: `{item['valid']}`")
            lines.append(f"- Difficulty: `{item['difficulty']}`")
            lines.append(f"- Source: `{item['source']}`")
            lines.append("")

            if item["question_json"] is not None:
                lines.append("```json")
                lines.append(json.dumps(item["question_json"], indent=2, ensure_ascii=False))
                lines.append("```")
            else:
                lines.append(str(item["question_text"]))

            lines.append("")
            lines.append("Answer key:")
            lines.append("```json")
            lines.append(json.dumps(item["answer_key_json"], indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def build_quality_markdown(report: Dict[str, Any]) -> str:
    lines = []

    lines.append("# Assessment Question Bank Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total questions: **{report['total_questions']}**")
    lines.append(f"- Total concepts: **{report['total_concepts']}**")
    lines.append(f"- Valid questions: **{report['valid_questions']} / {report['total_questions']}**")
    lines.append(f"- Issue count: **{report['issue_count']}**")
    lines.append(f"- Global duplicate groups: **{report['global_duplicate_group_count']}**")
    lines.append("")

    lines.append("## Question Type Counts")
    lines.append("")
    for qtype, count in sorted(report["question_type_counts"].items()):
        lines.append(f"- {qtype}: {count}")
    lines.append("")

    lines.append("## Concepts With Low Count")
    lines.append("")
    if not report["concepts_with_low_count"]:
        lines.append("No concepts with low question count.")
    else:
        for concept, count in report["concepts_with_low_count"].items():
            lines.append(f"- {concept}: {count}")
    lines.append("")

    lines.append("## Issues")
    lines.append("")
    if not report["issues"]:
        lines.append("No validation issues found.")
    else:
        for issue in report["issues"][:50]:
            lines.append(
                f"- {issue['concept_id']} | {issue['concept_name']} | "
                f"{issue['question_type']} v{issue['variant_id']} | {issue['errors']}"
            )
    lines.append("")

    lines.append("## Duplicate Groups")
    lines.append("")
    if not report["global_duplicate_groups"]:
        lines.append("No meaningful global duplicate groups found.")
    else:
        for group in report["global_duplicate_groups"][:20]:
            lines.append(f"### Duplicate group count: {group['count']}")
            lines.append(f"Preview: `{group['preview']}`")
            for item in group["items"]:
                lines.append(
                    f"- {item['domain']} | {item['concept_id']} | "
                    f"{item['concept_name']} | {item['question_type']} | v{item['variant_id']}"
                )
            lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nGenerating assessment question bank...")
    print("=" * 80)

    concepts = load_concepts()
    question_bank = generate_question_bank(concepts)
    quality_report = inspect_question_bank(question_bank)

    with QUESTION_BANK_JSON.open("w", encoding="utf-8") as f:
        json.dump(question_bank, f, indent=2, ensure_ascii=False)

    with QUESTION_BANK_MD.open("w", encoding="utf-8") as f:
        f.write(build_question_bank_markdown(question_bank))

    with QUALITY_JSON.open("w", encoding="utf-8") as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)

    with QUALITY_MD.open("w", encoding="utf-8") as f:
        f.write(build_quality_markdown(quality_report))

    print("\nQuestion bank generation complete.")
    print(f"Concepts processed: {len(concepts)}")
    print(f"Total questions: {quality_report['total_questions']}")
    print(f"Valid questions: {quality_report['valid_questions']}/{quality_report['total_questions']}")
    print(f"Issue count: {quality_report['issue_count']}")
    print(f"Global duplicate groups: {quality_report['global_duplicate_group_count']}")
    print(f"Question type counts: {quality_report['question_type_counts']}")
    print(f"Output JSON: {QUESTION_BANK_JSON}")
    print(f"Output Markdown: {QUESTION_BANK_MD}")
    print(f"Quality JSON: {QUALITY_JSON}")
    print(f"Quality Markdown: {QUALITY_MD}")

    expected_min_questions = len(concepts) * 15

    if (
        quality_report["total_questions"] >= expected_min_questions
        and quality_report["valid_questions"] == quality_report["total_questions"]
        and quality_report["issue_count"] == 0
    ):
        print("STATUS: PASS")
    else:
        print("STATUS: CHECK")


if __name__ == "__main__":
    main()
