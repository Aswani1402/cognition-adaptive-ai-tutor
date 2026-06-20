import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.answer_evaluator import evaluate_answer
from src.tutor_lm_service import TutorLMService
from src.rag_connector import RagConnector

ROOT_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ROOT_DIR / "outputs" / "doubt_handler"
OUTPUT_JSON = OUTPUT_DIR / "doubt_handler_demo.json"
OUTPUT_MD = OUTPUT_DIR / "doubt_handler_demo.md"


DOUBT_TYPES = {
    "next_step_doubt": [
        "next",
        "after this",
        "after",
        "what should i study",
        "what to study",
        "continue",
        "move next",
        "learn next",
    ],
    "debug_doubt": [
        "error",
        "bug",
        "wrong",
        "fix",
        "not working",
        "why error",
        "traceback",
        "invalid",
        "fails",
        "failed",
    ],
    "output_prediction_doubt": [
        "output",
        "print",
        "result",
        "what will happen",
        "why output",
    ],
    "code_doubt": [
        "code",
        "program",
        "syntax",
        "line",
        "write",
        "run",
        "=",
        "(",
        ")",
    ],
    "misconception_doubt": [
        "why not",
        "can i",
        "can't",
        "cannot",
        "is it true",
        "misunderstand",
        "why can't",
        "why cant",
    ],
    "revision_doubt": [
        "revise",
        "summary",
        "remember",
        "forgot",
        "again",
    ],
    "example_doubt": [
        "example",
        "show me",
        "give example",
        "sample",
    ],
    "definition_doubt": [
        "what is",
        "meaning",
        "define",
        "definition",
        "explain",
        "i don't understand",
        "i dont understand",
        "confused",
    ],
}


VIEW_BY_DOUBT_TYPE = {
    "definition_doubt": "definition_view",
    "example_doubt": "simple_example_view",
    "code_doubt": "code_view",
    "debug_doubt": "debug_view",
    "output_prediction_doubt": "output_prediction_view",
    "misconception_doubt": "misconception_view",
    "revision_doubt": "revision_summary_view",
    "next_step_doubt": "revision_summary_view",
}


QUESTION_TYPES_BY_DOUBT_TYPE = {
    "definition_doubt": ["mcq", "explanation_check"],
    "example_doubt": ["output_prediction", "mcq"],
    "code_doubt": ["output_prediction", "debug_task"],
    "debug_doubt": ["debug_task", "output_prediction"],
    "output_prediction_doubt": ["output_prediction", "mcq"],
    "misconception_doubt": ["mcq", "explanation_check"],
    "revision_doubt": ["mcq", "output_prediction"],
    "next_step_doubt": ["challenge_question", "transfer_question"],
}

DOUBT_PRIORITY = [
    "next_step_doubt",
    "debug_doubt",
    "output_prediction_doubt",
    "code_doubt",
    "misconception_doubt",
    "revision_doubt",
    "example_doubt",
    "definition_doubt",
]


def normalize_text(text: Any) -> str:
    text = str(text or "").lower()
    text = " ".join(text.split())
    return text.strip()


def short_text(text: Any, max_chars: int = 500) -> str:
    text = str(text or "").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].strip()
    last_period = cut.rfind(".")
    if last_period > 120:
        return cut[: last_period + 1]
    return cut + "..."


def looks_like_code(text: str) -> bool:
    """
    Stronger code detector.
    Prevents natural language like:
    'I don't understand why 2score = 10 is wrong'
    from becoming a full code block.
    """
    if not text:
        return False

    stripped = text.strip()

    natural_language_markers = [
        "i don't understand",
        "i dont understand",
        "why",
        "what",
        "can you",
        "please",
        "explain",
        "is wrong",
        "will be",
        "should i",
    ]

    lowered = stripped.lower()

    # If it is a long natural-language sentence, do not treat full line as code.
    if len(stripped.split()) > 6 and any(marker in lowered for marker in natural_language_markers):
        return False

    strong_patterns = [
        r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=",
        r"^\d+[a-zA-Z_][a-zA-Z0-9_]*\s*=",
        r"^print\s*\(",
        r"^for\s+.+\s+in\s+.+:?$",
        r"^while\s+.+:?$",
        r"^def\s+\w+\s*\(",
        r"^if\s+.+:?$",
        r"^SELECT\s+.+",
        r"^<\w+.*>$",
        r"^git\s+\w+",
    ]

    return any(re.search(pattern, stripped, flags=re.IGNORECASE) for pattern in strong_patterns)


def clean_inline_code_fragment(fragment: str) -> str:
    """
    Clean small inline code fragments extracted from natural language.
    """
    if not fragment:
        return ""

    fragment = fragment.strip()

    # Remove common natural-language endings.
    bad_suffixes = [
        " is wrong",
        " is correct",
        " is not working",
        " not working",
        " wrong",
        " correct",
        " error",
        " fails",
        " failed",
    ]

    lowered = fragment.lower()

    for suffix in bad_suffixes:
        if lowered.endswith(suffix):
            fragment = fragment[: -len(suffix)].strip()
            lowered = fragment.lower()
            break

    # Convert simple pseudo-code wording into line-separated code.
    # Example: x = 10 then x = 20 print x
    if " then " in lowered:
        parts = re.split(r"\bthen\b", fragment, flags=re.IGNORECASE)
        cleaned_parts = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Convert "x = 20 print x" to:
            # x = 20
            # print(x)
            print_match = re.search(r"\bprint\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", part)
            if print_match:
                before_print = part[: print_match.start()].strip()
                var_name = print_match.group(1)

                if before_print:
                    cleaned_parts.append(before_print)

                cleaned_parts.append(f"print({var_name})")
            else:
                cleaned_parts.append(part)

        return "\n".join(cleaned_parts).strip()

    # Convert "print x" to "print(x)".
    print_match = re.fullmatch(r"print\s+([a-zA-Z_][a-zA-Z0-9_]*)", fragment.strip(), flags=re.IGNORECASE)
    if print_match:
        return f"print({print_match.group(1)})"

    return fragment.strip()


def extract_code_block(text: str) -> Optional[str]:
    """
    Extract actual code only.
    Avoid treating a full natural-language sentence as a code block.
    """
    if not text:
        return None

    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        code = fenced.group(1).strip()
        return code if looks_like_code(code) else None

    lines = text.splitlines()

    # Only accept line-based code if at least one line strongly looks like code.
    code_like_lines = []

    for line in lines:
        stripped = line.strip()
        if looks_like_code(stripped):
            code_like_lines.append(stripped)

    if code_like_lines:
        return "\n".join(code_like_lines).strip()

    # Extract tiny inline assignment/code fragments like: 2score = 10
    inline_patterns = [
        # invalid identifier assignment like 2score = 10
        r"\b\d+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[A-Za-z0-9_\"']+",

        # normal assignment or pseudo-code chain like x = 10 then x = 20 print x
        r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^,.;?]+",

        r"print\s*\([^)]*\)",
        r"SELECT\s+.+?\s+FROM\s+\w+",
        r"git\s+\w+(?:\s+[\w\-.\"']+)*",
    ]

    for pattern in inline_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_inline_code_fragment(match.group(0).strip())

    return None


def build_concept_specific_tip(
    concept_name: Optional[str],
    domain: Optional[str],
    doubt_type: Optional[str],
    rag_chunks: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Build a short concept/domain-aware tip.
    Uses RAG chunks first when available, then domain-level fallback.
    """

    concept_name = str(concept_name or "").strip()
    domain = str(domain or "").strip()
    concept_lower = concept_name.lower()
    domain_lower = domain.lower()
    rag_chunks = rag_chunks or []

    if domain_lower == "python" and "variable" in concept_lower and doubt_type == "debug_doubt":
        return "Tip: In Python, variable names can contain letters, numbers, and underscores, but they cannot start with a number."

    # Prefer misconception/key-point chunks from RAG.
    for preferred_section in ["misconceptions", "key_points", "definition"]:
        for chunk in rag_chunks:
            section = str(chunk.get("section") or "").lower()
            text = str(chunk.get("text") or "").strip()

            if preferred_section == section and text:
                first_line = text.splitlines()[0].strip("- ").strip()
                if first_line:
                    if section == "misconceptions":
                        return f"Tip: Watch this common misconception about {concept_name}: {first_line}"
                    if section == "key_points":
                        return f"Tip: For {concept_name}, keep this key point in mind: {first_line}"
                    return f"Tip: For {concept_name}, connect your doubt back to this definition: {first_line}"

    # Domain/concept fallback tips.
    if domain_lower == "python":
        if "variable" in concept_lower:
            return "Tip: For Python variables, assign the name before using it, and use a valid identifier name."
        if "loop" in concept_lower:
            return "Tip: For Python loops, trace each iteration carefully and check the loop condition or iterable."
        if "condition" in concept_lower:
            return "Tip: For Python conditionals, check which Boolean condition becomes True first."
        if "function" in concept_lower:
            return "Tip: For Python functions, check the parameters, return value, and where the function is called."
        return f"Tip: For Python {concept_name}, check the syntax rule and trace the code step by step."

    if domain_lower == "sql":
        if "select" in concept_lower:
            return "Tip: For SELECT queries, identify the table, selected columns, filters, and ordering separately."
        if "where" in concept_lower:
            return "Tip: For WHERE filters, check which rows satisfy the condition before reading the output."
        if "join" in concept_lower:
            return "Tip: For JOINs, check the matching key columns and the join type."
        return f"Tip: For SQL {concept_name}, check the query clause order and what each clause changes."

    if domain_lower == "html":
        if "tag" in concept_lower or "element" in concept_lower:
            return "Tip: For HTML tags/elements, check the opening tag, content, closing tag, and nesting."
        if "attribute" in concept_lower or "link" in concept_lower:
            return "Tip: For HTML attributes/links, check the attribute name, quoted value, and where the link points."
        if "form" in concept_lower:
            return "Tip: For HTML forms, check input names, labels, and the form submission behavior."
        return f"Tip: For HTML {concept_name}, check structure, nesting, and required attributes."

    if domain_lower == "git":
        if "commit" in concept_lower:
            return "Tip: For Git commits, check what is staged first, then what snapshot is saved."
        if "branch" in concept_lower:
            return "Tip: For Git branches, check which branch you are on before committing or merging."
        if "merge" in concept_lower:
            return "Tip: For Git merges, compare both branches and resolve conflicting lines carefully."
        return f"Tip: For Git {concept_name}, check repository state, command order, and history."

    if domain_lower == "data structures":
        if "array" in concept_lower:
            return "Tip: For arrays, check the index, order, and how elements are accessed."
        if "stack" in concept_lower:
            return "Tip: For stacks, remember LIFO: last in, first out."
        if "queue" in concept_lower:
            return "Tip: For queues, remember FIFO: first in, first out."
        if "tree" in concept_lower:
            return "Tip: For trees, check parent-child relationships and traversal order."
        if "graph" in concept_lower:
            return "Tip: For graphs, check nodes, edges, and whether traversal revisits nodes."
        return f"Tip: For {concept_name}, check how data is stored, accessed, and updated."

    if concept_name:
        return f"Tip: For {concept_name}, focus on the key rule, one example, and one common mistake."

    return None


def build_rag_query_for_doubt(
    learner_doubt: str,
    concept: Dict[str, Any],
    doubt_type: str,
) -> str:
    """
    Build a stronger RAG query so retrieval stays inside the resolved concept.
    """

    concept_id = concept.get("concept_id", "")
    concept_name = concept.get("concept_name", "")
    domain = concept.get("domain", "")

    query_parts = [
        str(domain),
        str(concept_id),
        str(concept_name),
        str(learner_doubt),
    ]

    concept_lower = str(concept_name or "").lower()
    domain_lower = str(domain or "").lower()
    doubt_lower = str(learner_doubt or "").lower()

    if domain_lower == "python" and "variable" in concept_lower:
        query_parts.append(
            "variable naming rules assignment identifier cannot start with digit invalid name"
        )

    if "2score" in doubt_lower:
        query_parts.append(
            "2score invalid variable name cannot start with number"
        )

    if doubt_type == "debug_doubt":
        query_parts.append("misconceptions common mistake debug fix rule")

    elif doubt_type == "output_prediction_doubt":
        query_parts.append("examples output prediction trace code result")

    elif doubt_type == "revision_doubt":
        query_parts.append("definition key_points misconceptions revision summary")

    elif doubt_type == "next_step_doubt":
        query_parts.append("next_concept_link next topic prerequisite continue after")

    return " ".join(part for part in query_parts if part).strip()


class DoubtHandlerService:
    """
    Handles learner doubts using current TutorLMService assets.

    Current version:
    - rule-based doubt classification
    - artifact/question-bank grounded response
    - RAG-ready context field
    - returns follow-up check

    Later:
    - replace generated answer text with CogniTutorLM trained doubt task
    - connect RAG for retrieved chunks
    - update learner memory after follow-up evaluation
    """

    def __init__(self):
        self.tutor_service = TutorLMService()
        self.rag_connector = RagConnector()

    def classify_doubt(self, learner_doubt: str) -> Dict[str, Any]:
        text = normalize_text(learner_doubt)

        scores = {}

        for doubt_type, keywords in DOUBT_TYPES.items():
            score = 0
            matched = []

            for keyword in keywords:
                if keyword in text:
                    score += 1
                    matched.append(keyword)

            if score:
                scores[doubt_type] = {
                    "score": score,
                    "matched_keywords": matched,
                }

        # Strong special cases.
        if re.search(r"\b\d+[a-zA-Z_][a-zA-Z0-9_]*\s*=", learner_doubt):
            scores["debug_doubt"] = {
                "score": scores.get("debug_doubt", {}).get("score", 0) + 3,
                "matched_keywords": scores.get("debug_doubt", {}).get("matched_keywords", []) + [
                    "invalid_identifier_assignment"],
            }

        if "what should i study" in text or "study after" in text or "after select" in text:
            scores["next_step_doubt"] = {
                "score": scores.get("next_step_doubt", {}).get("score", 0) + 3,
                "matched_keywords": scores.get("next_step_doubt", {}).get("matched_keywords", []) + ["study_after"],
            }

        if "output" in text or "what will be" in text:
            scores["output_prediction_doubt"] = {
                "score": scores.get("output_prediction_doubt", {}).get("score", 0) + 2,
                "matched_keywords": scores.get("output_prediction_doubt", {}).get("matched_keywords", []) + [
                    "output_intent"],
            }

        if not scores:
            return {
                "doubt_type": "definition_doubt",
                "confidence": 0.3,
                "matched_keywords": [],
                "reason": "No strong keyword match; defaulting to definition_doubt.",
            }

        # Choose highest score; if tie, use priority order.
        best_type = None
        best_score = -1

        for doubt_type in DOUBT_PRIORITY:
            if doubt_type not in scores:
                continue

            score = scores[doubt_type]["score"]

            if score > best_score:
                best_score = score
                best_type = doubt_type

        best = scores[best_type]
        confidence = min(1.0, 0.4 + (best["score"] * 0.15))

        return {
            "doubt_type": best_type,
            "confidence": round(confidence, 2),
            "matched_keywords": best["matched_keywords"],
            "reason": f"Matched priority-adjusted keywords for {best_type}.",
        }

    def infer_concept(
        self,
        learner_doubt: str,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Infer concept from explicit inputs or by matching concept names in the doubt.
        """

        if concept_id or concept_name:
            candidates = self.tutor_service.list_concepts()

            for item in candidates:
                if concept_id and str(item.get("concept_id")).lower() == str(concept_id).lower():
                    return {
                        "status": "success",
                        "source": "explicit_concept_id",
                        **item,
                    }

                if concept_name and str(item.get("concept_name")).lower() == str(concept_name).lower():
                    if domain and str(item.get("domain")).lower() != str(domain).lower():
                        continue
                    return {
                        "status": "success",
                        "source": "explicit_concept_name",
                        **item,
                    }

        text = normalize_text(learner_doubt)
        candidates = self.tutor_service.list_concepts()

        best_match = None
        best_score = 0

        for item in candidates:
            cname = normalize_text(item.get("concept_name"))
            cid = normalize_text(item.get("concept_id"))
            cdomain = normalize_text(item.get("domain"))

            score = 0

            if cname and cname in text:
                score += 3

            if cid and cid in text:
                score += 2

            if domain and cdomain == normalize_text(domain):
                score += 1

            if score > best_score:
                best_score = score
                best_match = item

        if best_match:
            return {
                "status": "success",
                "source": "matched_from_doubt_text",
                "match_score": best_score,
                **best_match,
            }

        # Fallback: keep the service usable when the doubt text has no concept clue.
        # Prefer the requested domain if supplied; otherwise use the first loaded concept.
        fallback_candidates = candidates
        if domain:
            fallback_candidates = [
                item for item in candidates
                if normalize_text(item.get("domain")) == normalize_text(domain)
            ] or candidates

        fallback = fallback_candidates[0] if fallback_candidates else {
            "domain": domain,
            "concept_id": concept_id,
            "concept_name": concept_name,
        }

        return {
            "status": "fallback",
            "source": "default_available_concept",
            "domain": fallback.get("domain") or domain,
            "concept_id": fallback.get("concept_id") or concept_id,
            "concept_name": fallback.get("concept_name") or concept_name,
        }

    def retrieve_grounding_context(
                self,
                concept_id: str,
                domain: str,
                doubt_type: str,
                learner_doubt: Optional[str] = None,
                concept_name: Optional[str] = None,
        ) -> Dict[str, Any]:
        """
        Grounding order:
        1. Try main project RAG through RagConnector.
        2. If RAG succeeds, use RAG chunks/context_text as primary grounding.
        3. Always attach generated artifact/question-bank context as fallback/support.
        """

        preferred_view = VIEW_BY_DOUBT_TYPE.get(doubt_type, "definition_view")

        rag_result = None
        rag_success = False

        rag_query = None

        if learner_doubt:
            rag_query = build_rag_query_for_doubt(
                learner_doubt=learner_doubt,
                concept={
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "domain": domain,
                },
                doubt_type=doubt_type,
            )

            rag_result = self.rag_connector.get_rag_context(
                query=rag_query,
                concept_id=concept_id,
                domain=domain,
                top_k=5,
            )

            rag_success = (
                    isinstance(rag_result, dict)
                    and rag_result.get("status") == "success"
                    and bool(rag_result.get("chunks"))
                    and bool(str(rag_result.get("context_text") or "").strip())
            )

        teaching = self.tutor_service.get_teaching_view(
            concept_id=concept_id,
            domain=domain,
            artifact_type=preferred_view,
        )

        fallback_used = False

        if teaching.get("status") != "success":
            fallback_used = True
            for view in [
                "definition_view",
                "simple_example_view",
                "misconception_view",
                "debug_view",
                "revision_summary_view",
            ]:
                teaching = self.tutor_service.get_teaching_view(
                    concept_id=concept_id,
                    domain=domain,
                    artifact_type=view,
                )

                if teaching.get("status") == "success":
                    preferred_view = view
                    break

        question_types = QUESTION_TYPES_BY_DOUBT_TYPE.get(doubt_type, ["mcq"])

        questions = self.tutor_service.get_assessment_questions(
            concept_id=concept_id,
            domain=domain,
            question_types=question_types,
            num_questions=2,
            shuffle=False,
        )

        return {
            "status": "success",
            "context_source": "rag_primary" if rag_success else "generated_artifacts_and_question_bank",
            "rag_connected": bool(rag_result and rag_result.get("rag_connected")),
            "rag_success": rag_success,
            "rag_query": rag_query,
            "rag_context": rag_result,
            "selected_view": preferred_view,
            "fallback_used": fallback_used or not rag_success,
            "teaching_context": teaching,
            "question_context": questions,
            "grounding_priority": [
                "main_project_rag",
                "generated_tutor_artifacts",
                "assessment_question_bank",
            ],
        }

    def generate_grounded_doubt_answer(
        self,
        learner_doubt: str,
        concept: Dict[str, Any],
        classification: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Current version generates deterministic grounded answer.

        Later this can call CogniTutorLM with:
        <task_doubt_answer>
        <task_misconception_clarification>
        <task_code_doubt_explanation>
        """

        concept_name = concept.get("concept_name")
        domain = concept.get("domain")
        doubt_type = classification.get("doubt_type")

        teaching = context.get("teaching_context") or {}
        teaching_text = teaching.get("teaching") or ""

        rag_context = context.get("rag_context") or {}
        rag_text = rag_context.get("context_text") or ""
        rag_chunks = rag_context.get("chunks") or []

        code_snippet = extract_code_block(learner_doubt)

        if context.get("rag_success") and rag_text:
            base_summary = short_text(rag_text, 700)
            grounding_label = "RAG-grounded explanation"
        elif context.get("rag_success") and rag_chunks:
            chunk_summaries = []
            for chunk in rag_chunks[:3]:
                section = str(chunk.get("section") or "retrieved_context").strip()
                text = short_text(chunk.get("text") or "", 220)
                if text:
                    chunk_summaries.append(f"{section}: {text}")
            base_summary = "\n".join(chunk_summaries)
            grounding_label = "RAG-grounded explanation"
        else:
            base_summary = short_text(teaching_text, 420)
            grounding_label = "Grounded explanation"

        answer_parts = []

        answer_parts.append(f"You are asking about {concept_name} in {domain}.")

        if doubt_type == "debug_doubt":
            answer_parts.append(
                "This looks like a debugging doubt. First, identify what rule is being broken, then fix the smallest line causing the error."
            )

        elif doubt_type == "output_prediction_doubt":
            answer_parts.append(
                "This is an output-prediction doubt. Trace the code line by line and update the value after each assignment or operation."
            )

        elif doubt_type == "misconception_doubt":
            answer_parts.append(
                "This looks like a misconception. The important step is to separate the wrong assumption from the correct rule."
            )

        elif doubt_type == "code_doubt":
            answer_parts.append(
                "This is a code-related doubt. Focus on the syntax rule and then test with a small example."
            )

        elif doubt_type == "revision_doubt":
            answer_parts.append(
                "This is a revision doubt. Start with the shortest rule, then try one simple practice question."
            )

        elif doubt_type == "next_step_doubt":
            answer_parts.append(
                "This is a next-step doubt. You should continue only after a small check confirms the current concept is understood."
            )

        else:
            answer_parts.append(
                "Here is the core idea in a simpler form."
            )

        if base_summary:
            answer_parts.append(f"{grounding_label}:\n{base_summary}")

        if context.get("rag_success") and rag_chunks:
            useful_sections = []
            for chunk in rag_chunks[:3]:
                section = chunk.get("section")
                if section and section not in useful_sections:
                    useful_sections.append(section)

            if useful_sections:
                answer_parts.append(
                    "Retrieved source sections used: " + ", ".join(useful_sections)
                )

        if code_snippet:
            answer_parts.append(
                f"Code or code-like part you asked about:\n```python\n{code_snippet}\n```"
            )

        concept_tip = build_concept_specific_tip(
            concept_name=concept_name,
            domain=domain,
            doubt_type=doubt_type,
            rag_chunks=rag_chunks,
        )

        if concept_tip:
            answer_parts.append(concept_tip)

        example = self._build_example(concept_name, domain, doubt_type)

        follow_up_check = self._build_follow_up_check(context, concept, doubt_type)

        answer_text = "\n\n".join(answer_parts)

        return {
            "doubt_answer": answer_text,
            "example": example,
            "follow_up_check": follow_up_check,
        }

    def _build_example(
        self,
        concept_name: str,
        domain: str,
        doubt_type: str,
    ) -> str:
        cname = normalize_text(concept_name)
        domain_norm = normalize_text(domain)

        if domain_norm == "python" and "variable" in cname:
            return 'Example:\nname = "Alice"\nprint(name)\n\nThe variable name is assigned first, then printed.'

        if domain_norm == "python" and "loop" in cname:
            return "Example:\nfor i in range(3):\n    print(i)\n\nThe loop repeats the indented body for each value."

        if domain_norm == "sql":
            return "Example:\nSELECT name FROM students;\n\nThis selects the name column from the students table."

        if domain_norm == "html":
            return "Example:\n<p>Hello</p>\n\nThe tag marks the text as a paragraph."

        if domain_norm == "git":
            return 'Example:\ngit add .\ngit commit -m "save work"\n\nThis stages changes and creates a commit.'

        if domain_norm == "data structures":
            return f"Example:\nUse {concept_name} to organize data so operations become easier to reason about."

        return f"Example:\nUse {concept_name} in a small practice task and explain the result."

    def _build_follow_up_check(
        self,
        context: Dict[str, Any],
        concept: Dict[str, Any],
        doubt_type: str,
    ) -> Dict[str, Any]:
        questions = ((context.get("question_context") or {}).get("questions") or [])

        if questions:
            q = questions[0]
            return {
                "source": "assessment_question_bank",
                "concept_id": q.get("concept_id"),
                "concept_name": q.get("concept_name"),
                "domain": q.get("domain"),
                "question_type": q.get("question_type"),
                "variant_id": q.get("variant_id"),
                "question": q.get("question"),
                "answer_key": q.get("answer_key"),
                "rubric": q.get("rubric"),
            }

        concept_name = concept.get("concept_name")

        return {
            "source": "generated_fallback",
            "concept_id": concept.get("concept_id"),
            "concept_name": concept_name,
            "domain": concept.get("domain"),
            "question_type": "explanation_check",
            "variant_id": None,
            "question": f"Explain {concept_name} in one sentence using your own example.",
            "answer_key": {
                "expected_key_points": concept_name,
            },
            "rubric": {
                "type": "rubric",
                "criteria": "Learner should explain the concept with a relevant example.",
            },
        }

    def handle_doubt(
        self,
        learner_id: str,
        learner_doubt: str,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        classification = self.classify_doubt(learner_doubt)

        concept = self.infer_concept(
            learner_doubt=learner_doubt,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )

        context = self.retrieve_grounding_context(
            concept_id=concept["concept_id"],
            domain=concept["domain"],
            doubt_type=classification["doubt_type"],
            learner_doubt=learner_doubt,
            concept_name=concept.get("concept_name"),
        )


        generated = self.generate_grounded_doubt_answer(
            learner_doubt=learner_doubt,
            concept=concept,
            classification=classification,
            context=context,
        )

        return {
            "status": "success",
            "mode": "doubt_handling",
            "model": "CogniTutorLM-S",
            "learner_id": learner_id,
            "learner_doubt": learner_doubt,
            "classification": classification,
            "concept": concept,
            "grounding": {
                "context_source": context.get("context_source"),
                "rag_connected": context.get("rag_connected"),
                "rag_success": context.get("rag_success"),
                "selected_view": context.get("selected_view"),
                "fallback_used": context.get("fallback_used"),
                "rag_context_preview": short_text(
                    ((context.get("rag_context") or {}).get("context_text")),
                    300,
                ),
                "rag_chunk_count": len(((context.get("rag_context") or {}).get("chunks") or [])),
                "teaching_context_preview": short_text(
                    (context.get("teaching_context") or {}).get("teaching"),
                    300,
                ),
            },
            "doubt_answer": generated["doubt_answer"],
            "example": generated["example"],
            "follow_up_check": generated["follow_up_check"],
            "next_action": "answer_follow_up_check",
            "logging": {
                "should_log_doubt": True,
                "should_update_memory_after_followup": True,
                "memory_signal_if_followup_wrong": "doubt_revealed_weakness",
            },
            "future_upgrade": {
                "rag": "Connect retrieve_grounding_context() to RAG chunks.",
                "llm": "Replace deterministic response with <task_doubt_answer> generation.",
                "evaluator": "Evaluate follow-up answer and update learner memory.",
            },
        }

    def submit_doubt_followup_answer(
        self,
        learner_id: str,
        follow_up_check: Dict[str, Any],
        learner_answer: Any,
        teaching_view: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a doubt follow-up check and update learner memory/progression.
        """

        concept_id = follow_up_check.get("concept_id")
        concept_name = follow_up_check.get("concept_name")
        domain = follow_up_check.get("domain")
        question_type = follow_up_check.get("question_type") or "explanation_check"
        variant_id = follow_up_check.get("variant_id")

        evaluation_response = None

        if variant_id is not None:
            evaluation_response = self.tutor_service.evaluate_learner_answer(
                concept_id=concept_id,
                question_type=question_type,
                variant_id=variant_id,
                learner_answer=learner_answer,
            )

        if evaluation_response and evaluation_response.get("status") == "success":
            evaluation = evaluation_response["evaluation"]
        else:
            fallback_question = {
                "concept_id": concept_id,
                "concept_name": concept_name,
                "domain": domain,
                "question_type": question_type,
                "variant_id": variant_id,
                "question_json": {
                    "question": follow_up_check.get("question"),
                    "expected_key_points": (follow_up_check.get("answer_key") or {}).get(
                        "expected_key_points"
                    ),
                    "rubric": follow_up_check.get("rubric"),
                },
                "answer_key_json": follow_up_check.get("answer_key") or {},
                "rubric_json": follow_up_check.get("rubric") or {},
            }

            evaluation = evaluate_answer(fallback_question, learner_answer)

            if evaluation_response and evaluation_response.get("status") != "success":
                evaluation["evaluation_fallback_reason"] = evaluation_response.get("message")

        score = float(evaluation.get("score", 0.0))
        resolved_view = teaching_view or "definition_view"

        try:
            current_plan = self.tutor_service.teaching_progression_service.build_concept_learning_plan(
                learner_id=learner_id,
                concept_id=concept_id,
                concept_name=concept_name,
                domain=domain,
            )
            resolved_view = (
                teaching_view
                or current_plan.get("current_view")
                or current_plan.get("next_recommended_view")
                or "definition_view"
            )
        except Exception:
            current_plan = None

        memory_update = self.tutor_service.learner_memory_service.update_memory_from_evaluation(
            learner_id=learner_id,
            evaluation_result=evaluation,
            teaching_view=resolved_view,
            difficulty="easy",
        )

        progression_update = None
        if concept_id and concept_name and domain:
            progression_update = self.tutor_service.teaching_progression_service.update_after_view_result(
                learner_id=learner_id,
                concept_id=concept_id,
                concept_name=concept_name,
                domain=domain,
                view=resolved_view,
                score=score,
                question_type=question_type,
            )

        next_signal = evaluation.get("next_signal") or {}

        return {
            "status": "success",
            "mode": "doubt_followup_submission",
            "learner_id": learner_id,
            "teaching_view": resolved_view,
            "evaluation": evaluation,
            "memory_update": memory_update,
            "progression_update": progression_update,
            "next_action": next_signal.get("recommended_next_action") or "continue_learning",
        }


def build_markdown_demo(results: List[Dict[str, Any]]) -> str:
    lines = []

    lines.append("# Doubt Handler Demo Report")
    lines.append("")
    lines.append("This report shows how learner doubts are routed, grounded, answered, and followed by a check question.")
    lines.append("")

    for idx, result in enumerate(results, start=1):
        lines.append(f"## Doubt Case {idx}")
        lines.append("")
        lines.append(f"**Learner doubt:** {result['learner_doubt']}")
        lines.append("")
        lines.append(f"**Doubt type:** `{result['classification']['doubt_type']}`")
        lines.append(f"**Concept:** `{result['concept']['domain']} / {result['concept']['concept_id']} / {result['concept']['concept_name']}`")
        lines.append(f"**Grounding source:** `{result['grounding']['context_source']}`")
        lines.append(f"**Selected view:** `{result['grounding']['selected_view']}`")
        lines.append("")
        lines.append("### Doubt Answer")
        lines.append("")
        lines.append(result["doubt_answer"])
        lines.append("")
        lines.append("### Example")
        lines.append("")
        lines.append(result["example"])
        lines.append("")
        lines.append("### Follow-up Check")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result["follow_up_check"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def run_self_test() -> None:
    print("\nDoubtHandlerService self-test")
    print("=" * 80)

    service = DoubtHandlerService()

    demo_cases = [
        {
            "learner_id": "demo_learner_001",
            "learner_doubt": "I don't understand why 2score = 10 is wrong.",
            "concept_id": "P1",
            "domain": "Python",
        },
        {
            "learner_id": "demo_learner_001",
            "learner_doubt": "What will be the output of x = 10 then x = 20 print x?",
            "concept_id": "P1",
            "domain": "Python",
        },
        {
            "learner_id": "demo_learner_001",
            "learner_doubt": "Can you revise loops again with one example?",
            "concept_id": "P4",
            "domain": "Python",
        },
        {
            "learner_id": "demo_learner_001",
            "learner_doubt": "What should I study after SELECT?",
            "concept_id": "S2",
            "domain": "SQL",
        },
    ]

    results = []

    for case in demo_cases:
        result = service.handle_doubt(**case)
        results.append(result)

        print("\nDoubt case")
        print("-" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2500])

    print("\nDoubt follow-up submission test")
    print("-" * 80)

    follow_up_check = results[0]["follow_up_check"]
    answer_key = follow_up_check.get("answer_key") or {}
    qtype = follow_up_check.get("question_type")

    if qtype == "mcq":
        learner_answer = answer_key.get("answer", "")
    elif qtype == "output_prediction":
        learner_answer = answer_key.get("answer", "")
    elif qtype == "debug_task":
        learner_answer = answer_key.get("expected_fix", "")
    else:
        learner_answer = (
            f"I can explain {follow_up_check.get('concept_name')} using the main rule "
            "and one clear example."
        )

    follow_up_result = service.submit_doubt_followup_answer(
        learner_id="doubt_followup_demo_001",
        follow_up_check=follow_up_check,
        learner_answer=learner_answer,
        teaching_view=results[0]["grounding"].get("selected_view"),
    )

    print(json.dumps(follow_up_result, indent=2, ensure_ascii=False)[:2500])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown_demo(results))

    print("\nDoubt handler demo saved.")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Markdown: {OUTPUT_MD}")
    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()
