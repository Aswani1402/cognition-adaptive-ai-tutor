from __future__ import annotations

import random
import re
from typing import Any, Dict, List


class ConceptExpansionEngine:
    """
    Expands one concept resource into richer learning material.

    Goal:
    - not copy DB text directly
    - add missing useful parts like syntax/example/use-case
    - generate different formats: summary, flashcards, mindmap, challenges
    - support easy/medium/advanced levels
    """

    def expand(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str = "easy",
    ) -> Dict[str, Any]:

        topic = self._get_topic(concept_resource)
        definition = self._get_definition(concept_resource)
        examples = self._as_list(concept_resource.get("examples", []))
        key_points = self._as_list(concept_resource.get("key_points", []))
        misconceptions = self._as_list(concept_resource.get("misconceptions", []))
        real_world_use = str(concept_resource.get("real_world_use", "") or "")

        concept_type = self._detect_concept_type(topic, definition)

        syntax = self._generate_syntax(topic, concept_type)
        new_example = self._generate_new_example(topic, concept_type, difficulty)
        analogy = self._generate_analogy(topic, concept_type)
        expanded_definition = self._generate_rephrased_definition(topic, definition)

        mode = random.choice([
            "analogy",
            "code_first",
            "definition_first",
            "question_based",
        ])

        if mode == "analogy":
            explanation_style = f"Think of it like this:\n{analogy}"
        elif mode == "code_first":
            explanation_style = f"Start with this code:\n```python\n{new_example}\n```"
        elif mode == "question_based":
            explanation_style = (
                f"What happens if you change one value in this example?\n\n"
                f"```python\n{new_example}\n```\n\n"
                f"Now connect that behavior to this idea: {expanded_definition}"
            )
        else:
            explanation_style = expanded_definition

        return {
            "status": "success",
            "engine": "ConceptExpansionEngine",
            "topic": topic,
            "difficulty": difficulty,
            "concept_type": concept_type,
            "expanded_definition": expanded_definition,
            "syntax": syntax,
            "new_example": new_example,
            "analogy": analogy,

            "generation_mode": mode,
            "explanation_style": explanation_style,
            
            "level_content": self._generate_level_content(
                topic=topic,
                definition=expanded_definition,
                syntax=syntax,
                example=new_example,
                key_points=key_points,
                misconceptions=misconceptions,
                difficulty=difficulty,
            ),
            "summary": self._generate_summary(
                topic=topic,
                definition=expanded_definition,
                key_points=key_points,
                difficulty=difficulty,
            ),
            "flashcards": self._generate_flashcards(
                topic=topic,
                definition=expanded_definition,
                syntax=syntax,
                key_points=key_points,
                misconceptions=misconceptions,
            ),
            "mindmap": self._generate_mindmap(
                topic=topic,
                definition=expanded_definition,
                syntax=syntax,
                key_points=key_points,
                misconceptions=misconceptions,
                real_world_use=real_world_use,
            ),
            "challenge": self._generate_challenge(
                topic=topic,
                concept_type=concept_type,
                difficulty=difficulty,
            ),
            "debug_task": self._generate_debug_task(
                topic=topic,
                concept_type=concept_type,
            ),
            "transfer_task": self._generate_transfer_task(
                topic=topic,
                real_world_use=real_world_use,
            ),
            "source_note": "Generated from expanded concept understanding, not direct copy.",
        }

    def _get_topic(self, resource: Dict[str, Any]) -> str:
        return str(
            resource.get("topic")
            or resource.get("concept_name")
            or "this concept"
        )

    def _get_definition(self, resource: Dict[str, Any]) -> str:
        return str(
            resource.get("definition")
            or resource.get("content")
            or resource.get("base_content")
            or ""
        )

    def _as_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            lines = []
            for line in value.splitlines():
                clean = line.strip()
                if clean.startswith("-"):
                    clean = clean[1:].strip()
                if clean:
                    lines.append(clean)
            return lines
        return []

    def _detect_concept_type(self, topic: str, definition: str) -> str:
        text = f"{topic} {definition}".lower()

        if any(word in text for word in ["variable", "assignment", "value"]):
            return "programming_variable"
        if any(word in text for word in ["loop", "iteration", "repeat"]):
            return "programming_loop"
        if any(word in text for word in ["function", "parameter", "return"]):
            return "programming_function"
        if any(word in text for word in ["html", "tag", "element"]):
            return "html_concept"
        if any(word in text for word in ["sql", "database", "table", "query"]):
            return "sql_concept"
        if any(word in text for word in ["git", "commit", "repository", "branch"]):
            return "git_concept"
        if any(word in text for word in ["array", "stack", "queue", "tree", "graph"]):
            return "data_structure"

        return "general_concept"

    def _generate_rephrased_definition(self, topic: str, definition: str) -> str:
        topic_clean = topic.replace("Python ", "").strip()

        if "variable" in topic_clean.lower():
            variants = [
                "A variable is a named reference that lets a program store, access, and reuse data.",
                "A variable works like a label attached to a value, so the program can use that value later.",
                "In programming, a variable gives a meaningful name to data stored during execution.",
            ]
            return random.choice(variants)

        if definition:
            return (
                f"{topic_clean} is a concept that helps solve a specific kind of problem. "
                f"In simple terms, it gives a structured way to understand and apply the idea in practice."
            )

        return f"{topic_clean} is an important concept that should be understood through meaning, use, and examples."

    def _generate_syntax(self, topic: str, concept_type: str) -> str:
        if concept_type == "programming_variable":
            return "variable_name = value"

        if concept_type == "programming_loop":
            return "for item in collection:\n    # repeat action"

        if concept_type == "programming_function":
            return "def function_name(parameters):\n    return result"

        if concept_type == "html_concept":
            return "<tagname>content</tagname>"

        if concept_type == "sql_concept":
            return "SELECT column_name FROM table_name;"

        if concept_type == "git_concept":
            return "git command_name"

        if concept_type == "data_structure":
            return "structure_name = [elements]"

        return "No fixed syntax; understand the concept and apply it."

    def _generate_new_example(
        self,
        topic: str,
        concept_type: str,
        difficulty: str,
    ) -> str:

        if concept_type == "programming_variable":
            if difficulty == "easy":
                return "score = 95\nprint(score)"
            if difficulty == "medium":
                return "price = 50\nquantity = 3\ntotal = price * quantity\nprint(total)"
            return "items = [10, 20]\nbackup = items.copy()\nitems.append(30)\nprint(items)\nprint(backup)"

        if concept_type == "programming_loop":
            return "for number in [1, 2, 3]:\n    print(number)"

        if concept_type == "programming_function":
            return "def add(a, b):\n    return a + b\n\nprint(add(3, 4))"

        if concept_type == "html_concept":
            return "<p>This is a paragraph.</p>"

        if concept_type == "sql_concept":
            return "SELECT name FROM students WHERE grade = 'A';"

        if concept_type == "git_concept":
            return "git status\ngit add file.py\ngit commit -m \"save changes\""

        if concept_type == "data_structure":
            return "numbers = [10, 20, 30]\nprint(numbers[0])"

        return f"Create a small example where {topic} is used to solve a real task."

    def _generate_analogy(self, topic: str, concept_type: str) -> str:
        if concept_type == "programming_variable":
            return "Think of a variable like a label on a box. The label helps you find and reuse what is inside."

        if concept_type == "programming_loop":
            return "Think of a loop like repeating the same instruction for every item in a checklist."

        if concept_type == "programming_function":
            return "Think of a function like a machine: you give input, it processes it, and returns output."

        if concept_type == "html_concept":
            return "Think of HTML tags like labels that tell the browser what each part of a webpage means."

        if concept_type == "sql_concept":
            return "Think of SQL like asking questions to a well-organized table of information."

        if concept_type == "git_concept":
            return "Think of Git like a timeline that saves versions of your project."

        if concept_type == "data_structure":
            return "Think of a data structure like a specific container chosen based on how you want to store and access items."

        return f"Think of {topic} as a tool that helps organize and solve a specific kind of problem."

    def _generate_level_content(
        self,
        topic: str,
        definition: str,
        syntax: str,
        example: str,
        key_points: List[str],
        misconceptions: List[str],
        difficulty: str,
    ) -> str:

        if difficulty == "easy":
            return (
                f"{topic} in simple words:\n"
                f"{definition}\n\n"
                f"Simple example:\n```python\n{example}\n```\n\n"
                f"Remember:\n- {key_points[0] if key_points else 'Focus on what it means and where it is used.'}"
            )

        if difficulty == "medium":
            return (
                f"{topic} at medium level:\n"
                f"{definition}\n\n"
                f"Syntax:\n```python\n{syntax}\n```\n\n"
                f"Example:\n```python\n{example}\n```\n\n"
                f"Important ideas:\n"
                f"{self._bullet_lines(key_points[:3])}"
            )

        return (
            f"{topic} at advanced level:\n"
            f"{definition}\n\n"
            f"Syntax / structure:\n```python\n{syntax}\n```\n\n"
            f"Advanced example:\n```python\n{example}\n```\n\n"
            f"Deeper points:\n"
            f"{self._bullet_lines(key_points[:5])}\n\n"
            f"Common mistake:\n"
            f"{misconceptions[0] if misconceptions else 'Do not memorize only the definition; understand behavior and limitations.'}"
        )

    def _generate_summary(
        self,
        topic: str,
        definition: str,
        key_points: List[str],
        difficulty: str,
    ) -> str:

        if difficulty == "easy":
            return (
                f"{topic} means giving a clear name to an idea or value so it can be used again. "
                f"It helps the learner understand what the concept does before focusing on details."
            )

        if difficulty == "medium":
            return (
                f"{topic} is useful because it connects the concept meaning with practical use. "
                f"It should be understood through its purpose, syntax, example, and common mistakes."
            )

        return (
            f"{topic} should be understood not only by definition, but also by behavior, edge cases, "
            f"and how it affects problem solving in larger programs or systems."
        )

    def _generate_flashcards(
        self,
        topic: str,
        definition: str,
        syntax: str,
        key_points: List[str],
        misconceptions: List[str],
    ) -> List[Dict[str, str]]:

        cards = [
            {
                "question": f"What is {topic}?",
                "answer": definition,
            },
            {
                "question": f"Why do we use {topic}?",
                "answer": f"We use {topic} to make a task easier to organize, understand, and reuse.",
            },
            {
                "question": f"What is the basic syntax or structure of {topic}?",
                "answer": syntax,
            },
        ]

        for point in key_points[:3]:
            cards.append(
                {
                    "question": f"What is one important point about {topic}?",
                    "answer": point,
                }
            )

        if misconceptions:
            cards.append(
                {
                    "question": f"What mistake should be avoided in {topic}?",
                    "answer": misconceptions[0],
                }
            )

        return cards

    def _generate_mindmap(
        self,
        topic: str,
        definition: str,
        syntax: str,
        key_points: List[str],
        misconceptions: List[str],
        real_world_use: str,
    ) -> Dict[str, Any]:

        return {
            "center": topic,
            "branches": [
                {
                    "title": "Meaning",
                    "points": [definition],
                },
                {
                    "title": "Syntax / Structure",
                    "points": [syntax],
                },
                {
                    "title": "Key Ideas",
                    "points": key_points[:4],
                },
                {
                    "title": "Common Mistakes",
                    "points": misconceptions[:3],
                },
                {
                    "title": "Use Cases",
                    "points": [real_world_use] if real_world_use else [],
                },
            ],
        }

    def _generate_challenge(
        self,
        topic: str,
        concept_type: str,
        difficulty: str,
    ) -> str:

        if difficulty == "easy":
            return f"Create one simple example that uses {topic} and explain what each part means."

        if difficulty == "medium":
            return f"Create two different examples using {topic}, then compare how they behave."

        return f"Use {topic} in a small real-world scenario and explain one edge case or limitation."

    def _generate_debug_task(
        self,
        topic: str,
        concept_type: str,
    ) -> Dict[str, str]:

        if concept_type == "programming_variable":
            return {
                "buggy_code": 'name = Alice"\nprint(name)',
                "expected_fix": 'name = "Alice"\nprint(name)',
                "bug_type": "string_syntax",
            }

        return {
            "buggy_code": f"# Buggy use of {topic}\n",
            "expected_fix": f"Explain and correct the mistake in how {topic} is used.",
            "bug_type": "concept_usage",
        }

    def _generate_transfer_task(
        self,
        topic: str,
        real_world_use: str,
    ) -> str:

        if real_world_use:
            return (
                f"Apply {topic} in a real situation. "
                f"Use this context: {real_world_use}"
            )

        return f"Describe one real-world situation where {topic} would be useful."

    def _bullet_lines(self, points: List[str]) -> str:
        if not points:
            return "- Understand the meaning\n- Apply it in an example"
        return "\n".join(f"- {p}" for p in points)


if __name__ == "__main__":
    sample = {
        "topic": "Variables",
        "definition": "Variables are names used to store values in memory.",
        "examples": ["x = 10", "name = 'Aswani'"],
        "key_points": [
            "Variables store data.",
            "Variable values can change.",
            "Names should be meaningful.",
        ],
        "misconceptions": [
            "A variable is not the value itself; it is a name pointing to a value."
        ],
        "real_world_use": "Variables can store names, scores, prices, and settings.",
    }

    engine = ConceptExpansionEngine()
    output = engine.expand(sample, difficulty="medium")

    import json
    print(json.dumps(output, indent=2))