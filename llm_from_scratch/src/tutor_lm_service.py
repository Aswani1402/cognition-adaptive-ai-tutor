import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.answer_evaluator import evaluate_answer
from src.concept_resource_loader import load_concept_resources
from src.format_validator import validate_task_output
from src.safe_code_runner import run_python_code, run_python_test_cases
from src.learner_memory_service import LearnerMemoryService
from src.teaching_view_progression_service import TeachingViewProgressionService
from src.rag_connector import RagConnector


ROOT_DIR = Path(__file__).resolve().parents[1]

ARTIFACTS_PATH = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"
STRUCTURED_MODEL_CORE_PATH = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
STRUCTURED_MODEL_QUALITY_PATH = ROOT_DIR / "outputs" / "evaluation" / "structured_model_core_quality_eval.json"
STRUCTURED_MODEL_WEBSITE_PATH = ROOT_DIR / "outputs" / "evaluation" / "structured_model_website_readiness_eval.json"

FULL_TEACHING_VIEWS = [
    "explanation",
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "analogy_view",
    "code_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "comparison_view",
    "real_world_connection_view",
]

FULL_ASSESSMENT_TYPES = [
    "mcq",
    "fill_in_the_blank",
    "true_or_false",
    "output_prediction",
    "debug_task",
    "syntax_completion",
    "coding_prompt",
    "code_reasoning_task",
    "transfer_question",
    "challenge_question",
    "explanation_check",
    "real_world_application_question",
    "debug_challenge",
    "output_prediction_challenge",
    "multi_step_challenge",
]

TEACHING_TASK_TYPES = [
    "explanation", "definition_view", "simple_example_view", "step_by_step_view",
    "analogy_view", "code_view", "misconception_view", "debug_view",
    "output_prediction_view", "transfer_view", "challenge_view",
    "revision_summary_view", "comparison_view", "real_world_connection_view",
]

ASSESSMENT_TASK_TYPES = [
    "mcq", "debug_task", "output_prediction", "transfer_question",
    "challenge_question", "explanation_check", "syntax_completion",
    "coding_prompt", "code_reasoning_task", "fill_in_the_blank", "true_or_false",
]

REVISION_TASK_TYPES = [
    "revision_note", "revision_summary", "weakness_review", "daily_review",
    "personal_revision_plan", "recommended_revision_views", "spaced_repetition_card",
]

FLASHCARD_TASK_TYPES = [
    "flashcard", "concept_recall_flashcard", "misconception_flashcard",
    "example_flashcard", "debug_flashcard", "personal_flashcards",
    "syntax_flashcard",
]

MINDMAP_TASK_TYPES = ["mindmap", "concept_mindmap", "comparison_mindmap"]

FEEDBACK_TASK_TYPES = [
    "feedback", "correct_answer_feedback", "wrong_answer_feedback",
    "partial_answer_feedback", "debug_feedback", "output_prediction_feedback",
    "next_step_feedback", "encouragement_feedback",
]

HINT_TASK_TYPES = [
    "hint", "small_hint", "guided_hint", "worked_example_hint", "debug_hint",
    "syntax_hint", "output_prediction_hint", "misconception_hint",
    "next_step_hint", "analogy_hint",
]

DOUBT_TASK_TYPES = [
    "doubt_answer", "concept_doubt_answer", "syntax_doubt_answer",
    "debug_doubt_answer", "output_doubt_answer", "example_request_answer",
    "revision_doubt_answer", "next_step_doubt_answer", "comparison_doubt_answer",
]

NOTEBOOK_TASK_TYPES = [
    "notebook_summary", "mistake_summary", "revision_plan", "comeback_summary",
    "returning_learner_summary", "progress_insight",
]

PRACTICE_TASK_TYPES = [
    "practice_question", "transfer_task", "real_world_application_question",
    "debug_challenge", "output_prediction_challenge", "multi_step_challenge",
]

VOICE_TASK_TYPES = [
    "voice_script", "teaching_voice_script", "revision_voice_script",
    "mistake_feedback_voice_script", "doubt_explanation_voice_script",
    "encouragement_script", "next_step_guidance_script",
    "concept_intro_voice_script",
]

COGNITUTOR_FRONTEND_TASK_TYPES = (
    TEACHING_TASK_TYPES
    + ASSESSMENT_TASK_TYPES
    + REVISION_TASK_TYPES
    + FLASHCARD_TASK_TYPES
    + MINDMAP_TASK_TYPES
    + FEEDBACK_TASK_TYPES
    + HINT_TASK_TYPES
    + DOUBT_TASK_TYPES
    + NOTEBOOK_TASK_TYPES
    + PRACTICE_TASK_TYPES
    + VOICE_TASK_TYPES
)


class TutorLMService:
    """
    Service wrapper for CogniTutorLM-related assets.

    This is the layer the backend/website should call.

    It provides:
    - teaching view retrieval
    - assessment question selection
    - learner answer evaluation
    - safe code execution
    - session packet generation
    """

    def __init__(
        self,
        artifacts_path: Optional[Path] = None,
        question_bank_path: Optional[Path] = None,
    ):
        self.artifacts_path = artifacts_path or ARTIFACTS_PATH
        self.question_bank_path = question_bank_path or QUESTION_BANK_PATH
        self.content_mode = os.environ.get("TUTOR_CONTENT_MODE", "template_baseline")
        self.structured_model_core_path = STRUCTURED_MODEL_CORE_PATH
        self.structured_model_quality_path = STRUCTURED_MODEL_QUALITY_PATH
        self.structured_model_website_path = STRUCTURED_MODEL_WEBSITE_PATH

        self.artifacts = self._load_json(self.artifacts_path)
        self.question_bank = self._load_json(self.question_bank_path)
        self.concept_resources = self._load_concept_resources()
        self.structured_model_items = self._load_structured_model_items()
        self.learner_memory_service = LearnerMemoryService()
        self.teaching_progression_service = TeachingViewProgressionService()
        self.rag_connector = None

    def _load_json(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_json_if_exists(self, path: Path) -> Any:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _structured_model_gates_pass(self) -> bool:
        quality = self._load_json_if_exists(self.structured_model_quality_path) or {}
        website = self._load_json_if_exists(self.structured_model_website_path) or {}
        return (
            quality.get("status") == "PASS"
            and quality.get("valid_rate", 0.0) >= 0.85
            and quality.get("avg_quality_score", 0.0) >= 0.85
            and quality.get("website_ready_rate", 0.0) >= 0.85
            and quality.get("mcq_quality_score", 0.0) >= 0.85
            and quality.get("option_quality_score", 0.0) >= 0.85
            and website.get("website_readiness_status") == "PASS"
            and website.get("critical_schema_failures", 1) == 0
        )

    def _structured_not_ready(self) -> Dict[str, Any]:
        return {
            "status": "warning",
            "reason": "structured_model_generated_content_not_ready",
        }

    def _load_structured_model_items(self) -> List[Dict[str, Any]]:
        if self.content_mode != "structured_model_generated":
            return []
        if not self.structured_model_core_path.exists() or not self._structured_model_gates_pass():
            return []
        data = self._load_json_if_exists(self.structured_model_core_path)
        return data if isinstance(data, list) else []

    def get_structured_model_output(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.content_mode != "structured_model_generated":
            return self._structured_not_ready()
        if not self.structured_model_items:
            return self._structured_not_ready()

        matches = []
        for item in self.structured_model_items:
            if concept_id and self._normalize(item.get("concept_id")) != self._normalize(concept_id):
                continue
            if concept_name and self._normalize(item.get("concept_name")) != self._normalize(concept_name):
                continue
            if domain and self._normalize(item.get("domain")) != self._normalize(domain):
                continue
            if task_type and self._normalize(item.get("task_type")) != self._normalize(task_type):
                continue
            matches.append(item)

        valid_matches = [item for item in matches if item.get("valid") is True]
        valid_matches = sorted(
            valid_matches,
            key=lambda item: (item.get("valid") is not True, -float(item.get("quality_score", 0.0) or 0.0)),
        )

        if valid_matches:
            item = valid_matches[0]
            return {
                "status": "success",
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": item.get("task_type"),
                "generation_source": item.get("generation_source"),
                "model_used": item.get("model_used"),
                "output": item.get("output"),
                "valid": item.get("valid"),
                "quality_score": item.get("quality_score"),
                "issues": item.get("issues", []),
            }

        return {
            **self._structured_not_ready(),
            "reason": "structured_model_generated_item_not_found_or_not_valid",
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
            "task_type": task_type,
        }

    def list_structured_model_outputs(self) -> List[Dict[str, Any]]:
        if self.content_mode != "structured_model_generated" or not self.structured_model_items:
            return []
        return [
            {
                "status": "success",
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
                "task_type": item.get("task_type"),
                "generation_source": item.get("generation_source"),
                "model_used": item.get("model_used"),
                "output": item.get("output"),
                "valid": item.get("valid"),
                "quality_score": item.get("quality_score"),
                "issues": item.get("issues", []),
            }
            for item in self.structured_model_items
        ]

    def _normalize(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _load_concept_resources(self) -> Dict[tuple, Dict[str, Any]]:
        resources = {}
        for concept in load_concept_resources():
            resources[(self._normalize(concept["domain"]), self._normalize(concept["concept_id"]))] = concept
            resources[(self._normalize(concept["domain"]), self._normalize(concept["concept_name"]))] = concept
        return resources

    def _concept_resource(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if domain and concept_id:
            found = self.concept_resources.get((self._normalize(domain), self._normalize(concept_id)))
            if found:
                return found
        if domain and concept_name:
            return self.concept_resources.get((self._normalize(domain), self._normalize(concept_name)))
        return None

    def _clean(self, value: Any, max_chars: int = 420) -> str:
        text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
        text = text[:max_chars].strip()
        if text and text[-1] not in ".!?;:})]\"'":
            text += "."
        return text

    def _points(self, value: Any, limit: int = 3) -> List[str]:
        if isinstance(value, list):
            raw = value
        else:
            raw = re.split(r"\n|\||•", str(value or ""))
        points = []
        for item in raw:
            item = self._clean(str(item).lstrip("-* ").strip(), 220)
            if item and item not in points:
                points.append(item)
        return points[:limit]

    def _rich_teaching_text(self, concept: Dict[str, Any], artifact_type: str) -> str:
        name = concept["concept_name"]
        definition = self._clean(concept.get("base_content"), 520)
        key_points = self._points(concept.get("key_points"), 3)
        examples = self._points(concept.get("examples"), 2)
        mistakes = self._points(concept.get("misconceptions"), 2)
        use_case = self._clean(concept.get("real_world_use"), 260)
        key_block = "\n".join(f"- {point}" for point in key_points)
        example = examples[0] if examples else f"Try a small example that uses {name}."
        mistake = mistakes[0] if mistakes else f"A common mistake is using {name} without checking its main rule."

        if artifact_type == "flashcard_view":
            return json.dumps(
                {
                    "front": f"What should you remember about {name}?",
                    "back": f"{key_points[0] if key_points else definition} Example: {example}",
                },
                ensure_ascii=False,
            )
        if artifact_type == "mindmap_view":
            return json.dumps(
                {
                    "center": name,
                    "branches": [
                        f"Definition: {definition}",
                        f"Key point: {key_points[0] if key_points else definition}",
                        f"Example: {example}",
                        f"Common mistake: {mistake}",
                        f"Real-world use: {use_case}",
                    ],
                },
                ensure_ascii=False,
            )
        if artifact_type in {"code_view", "debug_view", "output_prediction_view"}:
            focus = "Code/example focus"
        elif artifact_type == "misconception_view":
            focus = "Misconception focus"
        elif artifact_type in {"transfer_view", "challenge_view"}:
            focus = "Apply it in a new situation"
        elif artifact_type == "revision_summary_view":
            focus = "Revision summary"
        else:
            focus = "Teaching view"
        return (
            f"{name} - {focus}\n\n"
            f"Definition: {definition}\n\n"
            f"Key points:\n{key_block}\n\n"
            f"Example: {example}\n\n"
            f"Common mistake: {mistake}\n\n"
            f"Real-world use: {use_case}"
        )

    def _enrich_teaching_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        concept = self._concept_resource(response.get("concept_id"), response.get("concept_name"), response.get("domain"))
        if not concept:
            return response
        artifact_type = response.get("artifact_type", "definition_view")
        enriched = self._rich_teaching_text(concept, artifact_type)
        response = dict(response)
        response["teaching"] = enriched
        response["quality_enriched"] = True
        response["source_fields_used"] = [
            "base_content",
            "examples",
            "key_points",
            "misconceptions",
            "real_world_use",
        ]
        return response

    def _question_signature(self, question: Dict[str, Any]) -> str:
        payload = question.get("question")
        if isinstance(payload, dict):
            if payload.get("question"):
                text = payload.get("question")
            elif payload.get("buggy_code"):
                text = payload.get("buggy_code")
            else:
                text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        else:
            text = str(payload or "")
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _synthetic_question(self, concept: Dict[str, Any], qtype: str, variant_id: int) -> Dict[str, Any]:
        name = concept["concept_name"]
        domain = concept["domain"]
        key = (self._points(concept.get("key_points"), 1) or [self._clean(concept.get("base_content"), 180)])[0]
        example = (self._points(concept.get("examples"), 1) or [f"Apply {name} in {domain}."])[0]
        mistake = (self._points(concept.get("misconceptions"), 1) or [f"Do not confuse {name} with an unrelated idea."])[0]
        base = {
            "session_question_id": "",
            "concept_id": concept["concept_id"],
            "concept_name": name,
            "domain": domain,
            "question_type": qtype,
            "difficulty": "adaptive",
            "variant_id": variant_id,
            "source": "concept_resources_service_enrichment",
        }
        if qtype == "mcq":
            correct = key
            q = {"question": f"Which statement best matches {name}?", "options": [correct, f"{name} is unrelated to {domain}.", f"{name} only works in advanced cases.", f"{name} can be ignored in practice."], "answer": correct, "explanation": f"The correct answer matches the main rule of {name}."}
            return {**base, "question": q, "answer_key": {"answer": correct}, "rubric": {"type": "exact_match", "field": "answer"}}
        if qtype == "fill_in_the_blank":
            q = {"question": f"Fill in the blank: {name} mainly means ____.", "answer": key, "explanation": key}
            return {**base, "question": q, "answer_key": {"answer": key}, "rubric": {"type": "contains_key_point"}}
        if qtype == "true_or_false":
            q = {"statement": f"{name} is about this idea: {key}", "answer": True, "explanation": key}
            return {**base, "question": q, "answer_key": {"answer": True}, "rubric": {"type": "boolean"}}
        if qtype == "debug_task":
            q = {"buggy_code": f"# Buggy {domain} example for {name}\nwrong_step = 'misapplied concept'", "expected_fix": f"Apply this rule correctly: {key}", "hint": f"Check the exact rule for {name}.", "explanation": f"The fix is related to {name}: {key}"}
            return {**base, "question": q, "answer_key": {"expected_fix": q["expected_fix"]}, "rubric": {"type": "code_fix"}}
        if qtype == "output_prediction":
            q = {"code": example, "question": f"What idea does this example demonstrate about {name}?", "answer": key, "explanation": f"The example demonstrates: {key}"}
            return {**base, "question": q, "answer_key": {"answer": key}, "rubric": {"type": "expected_output"}}
        if qtype == "syntax_completion":
            q = {"incomplete_code": example.split("\\n")[0], "completion": example, "explanation": f"Complete it to show {name}: {key}"}
            return {**base, "question": q, "answer_key": {"completion": example}, "rubric": {"type": "syntax_completion"}}
        if qtype == "coding_prompt":
            text = f"Write a small {domain} example that demonstrates {name}. Use this key idea: {key}"
            return {**base, "question": text, "answer_key": {"expected_key_points": key}, "rubric": {"type": "rubric"}}
        if qtype == "transfer_question":
            text = f"How would you apply {name} in a new {domain} problem? Use this example as a clue: {example}"
            return {**base, "question": text, "answer_key": {"expected_key_points": key}, "rubric": {"type": "rubric"}}
        if qtype == "challenge_question":
            text = f"Challenge: solve a small problem using {name}, then explain why the solution follows this rule: {key}"
            return {**base, "question": text, "answer_key": {"expected_key_points": key}, "rubric": {"type": "rubric"}}
        text = f"Explain {name} using the taught definition, one example, and this mistake to avoid: {mistake}"
        return {**base, "question": {"question": text, "expected_key_points": key, "rubric": "Use the concept rule and one example."}, "answer_key": {"expected_key_points": key}, "rubric": {"type": "rubric"}}

    def _support_outputs(self, concept_id: str, concept_name: str, domain: str, selected_view: str) -> Dict[str, Any]:
        concept = self._concept_resource(concept_id, concept_name, domain)
        if not concept:
            return {}
        key = (self._points(concept.get("key_points"), 1) or [self._clean(concept.get("base_content"), 180)])[0]
        example = (self._points(concept.get("examples"), 1) or [f"Apply {concept_name} in {domain}."])[0]
        mistake = (self._points(concept.get("misconceptions"), 1) or [f"Avoid mixing {concept_name} with unrelated ideas."])[0]
        hint_kind = "debug" if "debug" in selected_view else "output" if "output" in selected_view else "misconception" if "misconception" in selected_view else "guided"
        return {
            "hint": {
                "type": f"{hint_kind}_hint",
                "text": f"Hint: Focus on {concept_name}. Use this rule first: {key}",
                "example_clue": example,
            },
            "feedback_template": {
                "correct": f"Correct. Your answer used the main rule of {concept_name}: {key}",
                "partial": f"Partly correct. Add the exact rule and connect it to this example: {example}",
                "wrong": f"Not yet. The likely mistake is: {mistake}. Review the rule, then try again.",
                "next_step": "Answer one aligned assessment question before moving to the next view.",
            },
            "revision_summary": f"Remember {concept_name}: {key} Example: {example} Avoid: {mistake}",
        }

    def build_rag_grounding_metadata(
        self,
        query: str,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Build optional RAG grounding metadata for teaching/revision packets.

        Packet generation must remain available even when the main tutor RAG is
        missing, unavailable, or returns no chunks, so this method never raises.
        """

        try:
            if self.rag_connector is None:
                self.rag_connector = RagConnector()

            rag_result = self.rag_connector.get_rag_context(
                query=query,
                concept_id=concept_id,
                domain=domain,
                top_k=top_k,
            )
        except Exception as exc:
            return {
                "rag_context_used": False,
                "context_source": "rag_unavailable",
                "rag_connected": False,
                "rag_success": False,
                "fallback_used": True,
                "retrieved_sections": [],
                "source_chunks_preview": [],
                "grounding_score": None,
                "safe_to_generate": None,
                "query": query,
                "error": str(exc),
            }

        chunks = rag_result.get("chunks", []) if isinstance(rag_result, dict) else []
        chunks = chunks or []
        retrieved_sections = []
        source_chunks_preview = []

        for chunk in chunks[:3]:
            section = chunk.get("section")
            if section and section not in retrieved_sections:
                retrieved_sections.append(section)

            preview_text = (
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("chunk_text")
                or ""
            )

            source_chunks_preview.append(
                {
                    "concept_id": chunk.get("concept_id") or concept_id,
                    "concept_name": chunk.get("concept_name") or concept_name,
                    "domain": chunk.get("domain") or domain,
                    "section": section,
                    "preview": str(preview_text)[:250],
                }
            )

        rag_success = (
            isinstance(rag_result, dict)
            and rag_result.get("status") == "success"
            and bool(chunks)
        )

        return {
            "rag_context_used": bool(chunks),
            "context_source": rag_result.get("source", "option_c_plus_rag")
            if isinstance(rag_result, dict)
            else "rag_unavailable",
            "rag_connected": bool(rag_result.get("rag_connected"))
            if isinstance(rag_result, dict)
            else False,
            "rag_success": rag_success,
            "fallback_used": not rag_success,
            "retrieved_sections": retrieved_sections,
            "source_chunks_preview": source_chunks_preview,
            "grounding_score": rag_result.get("grounding_score")
            if isinstance(rag_result, dict)
            else None,
            "safe_to_generate": rag_result.get("safe_to_generate")
            if isinstance(rag_result, dict)
            else None,
            "query": query,
        }

    def _resolve_concept(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolve concept_id/name/domain using loaded generated artifacts.
        """

        for item in self.artifacts:
            if concept_id and self._normalize(item.get("concept_id")) != self._normalize(concept_id):
                continue

            if concept_name and self._normalize(item.get("concept_name")) != self._normalize(concept_name):
                continue

            if domain and self._normalize(item.get("domain")) != self._normalize(domain):
                continue

            return {
                "status": "success",
                "concept_id": item.get("concept_id"),
                "concept_name": item.get("concept_name"),
                "domain": item.get("domain"),
            }

        return {
            "status": "not_found",
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
        }

    def list_concepts(self) -> List[Dict[str, str]]:
        seen = {}

        for item in self.artifacts:
            key = (item["domain"], item["concept_id"], item["concept_name"])
            seen[key] = {
                "domain": item["domain"],
                "concept_id": item["concept_id"],
                "concept_name": item["concept_name"],
            }

        return sorted(
            seen.values(),
            key=lambda x: (x["domain"], x["concept_id"]),
        )

    def get_teaching_view(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
        artifact_type: str = "definition_view",
    ) -> Dict[str, Any]:
        """
        Return one teaching artifact/view.

        Example:
        get_teaching_view(concept_id="P1", artifact_type="code_view")
        """

        matches = []

        for item in self.artifacts:
            if concept_id and self._normalize(item.get("concept_id")) != self._normalize(concept_id):
                continue

            if concept_name and self._normalize(item.get("concept_name")) != self._normalize(concept_name):
                continue

            if domain and self._normalize(item.get("domain")) != self._normalize(domain):
                continue

            if self._normalize(item.get("artifact_type")) != self._normalize(artifact_type):
                continue

            matches.append(item)

        if not matches:
            return {
                "status": "not_found",
                "message": "No matching teaching view found.",
                "concept_id": concept_id,
                "concept_name": concept_name,
                "domain": domain,
                "artifact_type": artifact_type,
                "teaching": None,
            }

        item = matches[0]

        response = {
            "status": "success",
            "source": "generated_tutor_artifacts",
            "concept_id": item["concept_id"],
            "concept_name": item["concept_name"],
            "domain": item["domain"],
            "artifact_type": item["artifact_type"],
            "difficulty": item.get("difficulty", "adaptive"),
            "teaching_style": item.get("teaching_style"),
            "teaching": item.get("output"),
            "valid": item.get("valid", True),
        }
        return self._enrich_teaching_response(response)

    def get_available_views(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[str]:
        views = set()

        for item in self.artifacts:
            if concept_id and self._normalize(item.get("concept_id")) != self._normalize(concept_id):
                continue

            if concept_name and self._normalize(item.get("concept_name")) != self._normalize(concept_name):
                continue

            if domain and self._normalize(item.get("domain")) != self._normalize(domain):
                continue

            views.add(item.get("artifact_type"))

        return sorted(v for v in views if v)

    def get_assessment_questions(
        self,
        concept_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        domain: Optional[str] = None,
        question_types: Optional[List[str]] = None,
        num_questions: int = 10,
        difficulty: Optional[str] = None,
        shuffle: bool = True,
    ) -> Dict[str, Any]:
        """
        Select validated questions from assessment_question_bank.

        This should be used by the website to show Question 1 of N.
        """

        matches = []

        question_type_set = set(question_types or [])

        for item in self.question_bank:
            if concept_id and self._normalize(item.get("concept_id")) != self._normalize(concept_id):
                continue

            if concept_name and self._normalize(item.get("concept_name")) != self._normalize(concept_name):
                continue

            if domain and self._normalize(item.get("domain")) != self._normalize(domain):
                continue

            if difficulty and self._normalize(item.get("difficulty")) != self._normalize(difficulty):
                continue

            if question_type_set and item.get("question_type") not in question_type_set:
                continue

            if item.get("valid") is not True:
                continue

            matches.append(item)

        if shuffle:
            rng = random.Random(f"{domain}:{concept_id}:{concept_name}:{difficulty}")
            rng.shuffle(matches)

        preferred_order = [
            "mcq",
            "fill_in_the_blank",
            "true_or_false",
            "debug_task",
            "output_prediction",
            "syntax_completion",
            "coding_prompt",
            "transfer_question",
            "challenge_question",
            "explanation_check",
        ]
        required_types = list(question_types or preferred_order)
        selected = []
        seen_signatures = set()

        for qtype in required_types:
            candidate = next((item for item in matches if item.get("question_type") == qtype and (item.get("duplicate_group") or "") not in seen_signatures), None)
            if candidate:
                selected.append(candidate)
                seen_signatures.add(candidate.get("duplicate_group") or self._normalize(candidate.get("question_json") or candidate.get("question_text")))

        resolved_for_synthetic = None
        if selected:
            resolved_for_synthetic = self._concept_resource(selected[0].get("concept_id"), selected[0].get("concept_name"), selected[0].get("domain"))
        if resolved_for_synthetic is None:
            resolved_for_synthetic = self._concept_resource(concept_id, concept_name, domain)

        synthetic_variant = 9000
        if resolved_for_synthetic:
            existing_types = {item.get("question_type") for item in selected}
            for qtype in required_types:
                if len(selected) >= num_questions:
                    break
                if qtype in existing_types:
                    continue
                selected.append(self._synthetic_question(resolved_for_synthetic, qtype, synthetic_variant))
                synthetic_variant += 1
                existing_types.add(qtype)

        for item in matches:
            if len(selected) >= num_questions:
                break
            signature = item.get("duplicate_group") or self._normalize(item.get("question_json") or item.get("question_text"))
            if signature in seen_signatures:
                continue
            selected.append(item)
            seen_signatures.add(signature)

        selected = selected[:num_questions]

        frontend_questions = []

        for idx, item in enumerate(selected, start=1):
            frontend_questions.append(
                {
                    "session_question_id": f"Q{idx}",
                    "concept_id": item.get("concept_id"),
                    "concept_name": item.get("concept_name"),
                    "domain": item.get("domain"),
                    "question_type": item.get("question_type"),
                    "difficulty": item.get("difficulty"),
                    "variant_id": item.get("variant_id"),
                    "question": item.get("question_json") or item.get("question_text") or item.get("question"),
                    "answer_key": item.get("answer_key_json") or item.get("answer_key"),
                    "rubric": item.get("rubric_json") or item.get("rubric"),
                    "source": item.get("source"),
                }
            )

        resolved_concept_id = concept_id
        resolved_concept_name = concept_name
        resolved_domain = domain

        if selected:
            resolved_concept_id = selected[0].get("concept_id")
            resolved_concept_name = selected[0].get("concept_name")
            resolved_domain = selected[0].get("domain")

        return {
            "status": "success",
            "source": "assessment_question_bank",
            "num_requested": num_questions,
            "num_available": len(matches),
            "num_returned": len(frontend_questions),
            "question_type_coverage": sorted({q.get("question_type") for q in frontend_questions}),
            "deduplicated": True,
            "concept_id": resolved_concept_id,
            "concept_name": resolved_concept_name,
            "domain": resolved_domain,
            "questions": frontend_questions,
        }

    def find_question(
        self,
        concept_id: str,
        question_type: str,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:
        for item in self.question_bank:
            if (
                str(item.get("concept_id")) == str(concept_id)
                and str(item.get("question_type")) == str(question_type)
                and int(item.get("variant_id", -1)) == int(variant_id)
            ):
                return item

        return None

    def evaluate_learner_answer(
        self,
        concept_id: str,
        question_type: str,
        variant_id: int,
        learner_answer: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate learner answer using src.answer_evaluator.
        """

        question = self.find_question(
            concept_id=concept_id,
            question_type=question_type,
            variant_id=variant_id,
        )

        if question is None:
            return {
                "status": "not_found",
                "message": "Question not found in assessment question bank.",
                "concept_id": concept_id,
                "question_type": question_type,
                "variant_id": variant_id,
            }

        result = evaluate_answer(question, learner_answer)
        concept = self._concept_resource(question.get("concept_id"), question.get("concept_name"), question.get("domain"))
        key = ""
        if concept:
            key = (self._points(concept.get("key_points"), 1) or [self._clean(concept.get("base_content"), 180)])[0]
        score = float(result.get("score", result.get("overall_score", 0.0)) or 0.0)
        label = result.get("label") or result.get("verdict") or ("correct" if score >= 0.8 else "partial" if score >= 0.4 else "wrong")
        feedback = {
            "correct_answer": question.get("answer_key_json") or question.get("answer_key"),
            "explanation": key or "Review the concept rule and compare it with the expected answer.",
            "mistake_type": result.get("mistake_type") or ("none" if label == "correct" else f"{question_type}_needs_review"),
            "next_step": (
                "Move to a related challenge."
                if label == "correct"
                else "Review the teaching view, use the hint, then retry one aligned question."
            ),
        }

        return {
            "status": "success",
            "source": "answer_evaluator",
            "evaluation": result,
            "feedback": feedback,
        }

    def run_code(
        self,
        code: str,
        expected_output: Optional[str] = None,
        timeout_seconds: int = 3,
    ) -> Dict[str, Any]:
        """
        Run Python code safely.

        Used for website Run button / console.
        """

        if expected_output is None:
            return {
                "status": "success",
                "mode": "run_only",
                "result": run_python_code(code, timeout_seconds=timeout_seconds),
            }

        test_result = run_python_test_cases(
            code=code,
            test_cases=[
                {
                    "test_id": "T1",
                    "expected_output": expected_output,
                }
            ],
            timeout_seconds=timeout_seconds,
        )

        return {
            "status": "success",
            "mode": "test_case",
            "result": test_result,
        }

    def generate_session_packet(
        self,
        concept_id: str,
        domain: Optional[str] = None,
        selected_view: str = "definition_view",
        num_questions: int = 10,
        question_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create one website-ready learning session packet.

        This combines:
        - one teaching view
        - question set
        - available views

        Later this can receive policy_output / learner_state / teaching_strategy_output.
        """

        teaching = self.get_teaching_view(
            concept_id=concept_id,
            domain=domain,
            artifact_type=selected_view,
        )

        if teaching["status"] != "success":
            return {
                "status": "not_found",
                "message": "Cannot create session packet because teaching view was not found.",
                "teaching": teaching,
                "assessment": None,
            }

        assessment = self.get_assessment_questions(
            concept_id=concept_id,
            domain=domain,
            question_types=question_types,
            num_questions=num_questions,
        )

        available_views = self.get_available_views(
            concept_id=concept_id,
            domain=domain,
        )

        rag_metadata = self.build_rag_grounding_metadata(
            query=f"Teach {teaching['concept_name']} in {teaching['domain']} using {selected_view}",
            concept_id=teaching["concept_id"],
            concept_name=teaching["concept_name"],
            domain=teaching["domain"],
            top_k=5,
        )
        support_outputs = self._support_outputs(teaching["concept_id"], teaching["concept_name"], teaching["domain"], selected_view)

        return {
            "status": "success",
            "model": "CogniTutorLM-S",
            "concept_id": teaching["concept_id"],
            "concept_name": teaching["concept_name"],
            "domain": teaching["domain"],
            "selected_view": selected_view,
            "available_views": available_views,
            "teaching": teaching,
            "assessment": assessment,
            **support_outputs,
            "rag_grounding": rag_metadata,
            "frontend_contract": {
                "show_teaching_card": True,
                "show_question_one_at_a_time": True,
                "show_code_runner_for": ["debug_task", "coding_question", "output_prediction"],
                "next_action": "answer_question",
            },
        }

    def generate_full_task_bundle(
        self,
        concept_id: str,
        domain: Optional[str] = None,
        concept_name: Optional[str] = None,
        difficulty: str = "easy",
    ) -> Dict[str, Any]:
        """
        Return a website-ready coverage bundle for all major tutor task groups.

        This remains artifact/concept-resource based. It does not claim live model
        generation when the local generated artifact is missing.
        """

        concept = self._concept_resource(concept_id, concept_name, domain) or {
            "concept_id": concept_id,
            "concept_name": concept_name or concept_id,
            "domain": domain or "Python",
            "base_content": f"{concept_name or concept_id} is the selected concept.",
            "examples": f"Example for {concept_name or concept_id}.",
            "key_points": [f"Understand {concept_name or concept_id}."],
            "misconceptions": [f"Do not mix {concept_name or concept_id} with unrelated concepts."],
            "real_world_use": f"{concept_name or concept_id} appears in practical tasks.",
        }
        cid = concept["concept_id"]
        cname = concept["concept_name"]
        cdomain = concept.get("domain") or domain or "Python"

        content_by_view: Dict[str, Any] = {}
        for view in FULL_TEACHING_VIEWS:
            teaching = self.get_teaching_view(concept_id=cid, concept_name=cname, domain=cdomain, artifact_type=view)
            if teaching.get("status") == "success":
                source = "generated_tutor_artifacts"
                text = teaching.get("teaching")
            else:
                source = "concept_resources_fallback"
                text = self._rich_teaching_text(concept, view)
            content_by_view[view] = {
                "view": view,
                "source": source,
                "teaching": text,
                "format_valid": bool(text),
            }

        assessment = self.get_assessment_questions(
            concept_id=cid,
            concept_name=cname,
            domain=cdomain,
            difficulty=difficulty,
            question_types=FULL_ASSESSMENT_TYPES,
            num_questions=12,
        )
        support_outputs = self._support_outputs(cid, cname, cdomain, "explanation")
        scripts = {
            "voice_script": f"Let's stay with {cname}.",
            "teaching_voice_script": f"We are learning {cname}. First understand the idea, then use the example.",
            "revision_voice_script": f"Quick revision for {cname}: {self._clean(concept.get('base_content'), 180)}",
            "mistake_feedback_voice_script": f"Review {cname} and compare your answer with the key point.",
            "doubt_explanation_voice_script": f"Your doubt is about {cname}; I will answer with this concept context.",
            "encouragement_script": f"Keep going with {cname}; use the next hint before retrying.",
            "next_step_guidance_script": f"Next, answer one mixed question on {cname}.",
            "concept_intro_voice_script": f"Welcome to {cname} in {cdomain}.",
        }

        return {
            "status": "success",
            "model": "CogniTutorLM-S",
            "service": "artifact_or_concept_resource_bundle",
            "concept_id": cid,
            "concept_name": cname,
            "domain": cdomain,
            "difficulty": difficulty,
            "selected_view": "explanation",
            "available_views": FULL_TEACHING_VIEWS,
            "content_by_view": content_by_view,
            "assessment": assessment,
            "flashcards": support_outputs.get("flashcards"),
            "mindmap": support_outputs.get("mindmap"),
            "hints": support_outputs.get("hint"),
            "feedback": support_outputs.get("feedback_template"),
            "revision": support_outputs.get("revision_summary"),
            "voice_scripts": scripts,
            "task_coverage": {
                "teaching_views": FULL_TEACHING_VIEWS,
                "assessment_types": FULL_ASSESSMENT_TYPES,
                "flashcard_types": ["concept_recall_flashcard", "misconception_flashcard", "example_flashcard", "debug_flashcard", "syntax_flashcard", "personal_flashcards", "spaced_repetition_card"],
                "mindmap_types": ["concept_mindmap", "comparison_mindmap", "revision_mindmap"],
                "hint_types": ["hint", "small_hint", "guided_hint", "worked_example_hint", "debug_hint", "syntax_hint", "output_prediction_hint", "misconception_hint", "next_step_hint", "analogy_hint"],
                "feedback_types": ["feedback", "correct_answer_feedback", "wrong_answer_feedback", "partial_answer_feedback", "debug_feedback", "output_prediction_feedback", "next_step_feedback", "encouragement_feedback"],
                "doubt_types": ["doubt_answer", "concept_doubt_answer", "syntax_doubt_answer", "debug_doubt_answer", "output_doubt_answer", "example_request_answer", "revision_doubt_answer", "next_step_doubt_answer", "comparison_doubt_answer"],
            },
            "llm_generation": {
                "service": "CogniTutorLM|artifact|concept_resources_fallback",
                "task_type": "full_task_bundle",
                "model_generated": "unknown",
                "fallback_used": any(v["source"] == "concept_resources_fallback" for v in content_by_view.values()),
                "format_valid": True,
            },
        }

    def supported_frontend_task_types(self) -> List[str]:
        return list(COGNITUTOR_FRONTEND_TASK_TYPES)

    def _coerce_concept_resource(self, concept_resource: Dict[str, Any]) -> Dict[str, Any]:
        concept = dict(concept_resource or {})
        concept.setdefault("concept_id", concept.get("id") or "unknown")
        concept.setdefault("concept_name", concept.get("concept_name") or concept.get("topic") or concept.get("name") or str(concept["concept_id"]))
        concept.setdefault("topic", concept.get("concept_name"))
        concept.setdefault("domain", concept.get("domain") or "Unknown")
        concept.setdefault("base_content", concept.get("definition") or "")
        concept.setdefault("examples", concept.get("example") or [])
        concept.setdefault("key_points", concept.get("key_point") or [])
        concept.setdefault("misconceptions", concept.get("misconception") or [])
        concept.setdefault("real_world_use", concept.get("real_world") or "")
        concept.setdefault("next_concept_link", concept.get("next_concept") or "")
        return concept

    def _resource_parts(self, concept_resource: Dict[str, Any]) -> Dict[str, Any]:
        concept = self._coerce_concept_resource(concept_resource)
        definition = self._clean(concept.get("base_content") or concept.get("definition"), 1400)
        examples = self._points(concept.get("examples"), 6) or [f"Use {concept['concept_name']} in a small {concept['domain']} task."]
        key_points = self._points(concept.get("key_points"), 6) or [definition]
        misconceptions = self._points(concept.get("misconceptions"), 6) or [f"Do not treat {concept['concept_name']} as unrelated to its definition."]
        real_world = self._clean(concept.get("real_world_use"), 900) or f"{concept['concept_name']} is used in practical {concept['domain']} work."
        next_link = self._clean(concept.get("next_concept_link"), 700) or f"After {concept['concept_name']}, continue to the next related concept."
        return {
            "concept": concept,
            "definition": definition,
            "examples": examples,
            "key_points": key_points,
            "misconceptions": misconceptions,
            "real_world_use": real_world,
            "next_concept_link": next_link,
            "primary_example": examples[0],
            "primary_key": key_points[0],
            "primary_misconception": misconceptions[0],
        }

    def _base_assessment_item(self, parts: Dict[str, Any], task_type: str, difficulty: str, index: int = 1) -> Dict[str, Any]:
        concept = parts["concept"]
        name = concept["concept_name"]
        key = parts["primary_key"]
        example = parts["primary_example"]
        mistake = parts["primary_misconception"]
        base = {
            "question_id": f"{concept['concept_id']}_{task_type}_{index}",
            "task_type": task_type,
            "question_type": task_type,
            "difficulty": difficulty,
            "hint": f"Use the definition and key point for {name}: {key}",
            "expected_points": [key, example, mistake],
        }
        if task_type == "mcq":
            return {
                **base,
                "prompt": f"Which statement best matches {name}?",
                "options": [key, mistake, f"{name} is unrelated to {concept['domain']} practice.", f"The example is not needed to understand {name}."],
                "correct_answer": key,
                "explanation": f"The correct answer uses the key point from concept_resources for {name}. The misconception option is wrong because it states: {mistake}",
                "questions": [
                    {
                        "question_id": f"{concept['concept_id']}_mcq_1",
                        "task_type": "mcq",
                        "question_type": "mcq",
                        "difficulty": difficulty,
                        "prompt": f"Which statement best defines {name}?",
                        "options": [key, mistake, f"{name} only matters in rare cases.", f"{name} has no practical use."],
                        "correct_answer": key,
                        "explanation": f"This answer is grounded in the key_points field: {key}",
                        "hint": f"Look for the definition-like statement about {name}.",
                        "expected_points": [key],
                    },
                    {
                        "question_id": f"{concept['concept_id']}_mcq_2",
                        "task_type": "mcq",
                        "question_type": "mcq",
                        "difficulty": difficulty,
                        "prompt": f"Which choice avoids a common mistake about {name}?",
                        "options": [f"Use the rule: {key}", mistake, "Ignore the example.", "Skip the definition."],
                        "correct_answer": f"Use the rule: {key}",
                        "explanation": f"The correct choice directly corrects the misconception: {mistake}",
                        "hint": f"Compare each option with the misconception for {name}.",
                        "expected_points": [key, mistake],
                    },
                ],
            }
        if task_type == "fill_in_the_blank":
            return {**base, "prompt": f"Fill in the blank: {name} is best remembered as ____.", "correct_answer": key, "explanation": f"The blank is filled by the key point: {key}"}
        if task_type == "true_or_false":
            return {**base, "prompt": f"True or False: {mistake}", "correct_answer": False, "explanation": f"False. The concept resource correction is: {key}"}
        if task_type in {"output_prediction", "output_prediction_challenge"}:
            return {**base, "prompt": f"Trace the example and predict what it demonstrates about {name}.", "code": example, "expected_output": key, "correct_answer": key, "explanation": f"The trace should lead to the key idea: {key}"}
        if task_type in {"debug_task", "debug_challenge"}:
            return {**base, "prompt": f"Fix the mistake in this {name} example.", "buggy_code": f"BUGGY OR MISTAKEN VERSION:\n{example}\n# Mistake: {mistake}", "expected_fix": f"Apply this rule: {key}", "correct_answer": f"Apply this rule: {key}", "explanation": f"The bug comes from this misconception: {mistake}"}
        if task_type == "syntax_completion":
            return {**base, "prompt": f"Complete the syntax/example for {name}: ____", "code": example, "correct_answer": example, "explanation": f"The completion is grounded in the examples field and shows: {key}"}
        if task_type in {"coding_prompt", "multi_step_challenge"}:
            return {**base, "prompt": f"Create a small {concept['domain']} task that demonstrates {name} and explain how it uses {key}.", "code": example, "test_cases": [{"input": "concept example", "expected": key}], "correct_answer": key, "explanation": f"A good solution must include the key point and a concrete example for {name}."}
        if task_type == "code_reasoning_task":
            return {**base, "prompt": f"Read this example and explain why it demonstrates {name}: {example}", "code": example, "correct_answer": key, "explanation": f"The reasoning should connect the example to: {key}"}
        return {**base, "prompt": f"{task_type.replace('_', ' ').title()}: explain or apply {name} using the definition, example, and real-world use.", "correct_answer": key, "explanation": f"A complete answer should include: {key}. Example: {example}. Real-world use: {parts['real_world_use']}"}

    def _build_teaching_output(self, task_type: str, parts: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
        concept = parts["concept"]
        name = concept["concept_name"]
        key_points = parts["key_points"]
        examples = parts["examples"]
        misconceptions = parts["misconceptions"]
        emphasis = task_type.replace("_", " ")
        output = {
            "view_type": task_type,
            "title": f"{name} - {emphasis.title()}",
            "definition": parts["definition"],
            "explanation": (
                f"{name} in {concept['domain']} should be understood from its definition, examples, key points, and common mistakes. "
                f"The central idea is: {parts['primary_key']} The main example is: {parts['primary_example']} "
                f"A common mistake to avoid is: {parts['primary_misconception']} In practice, {parts['real_world_use']}"
            ),
            "example": parts["primary_example"],
            "key_points": key_points,
            "common_mistake": parts["primary_misconception"],
            "mini_check": f"Can you explain {name} using the key point '{parts['primary_key']}' and one example?",
            "next_step": parts["next_concept_link"],
            "source_fields_used": ["concept_id", "topic", "base_content", "examples", "key_points", "misconceptions", "real_world_use", "next_concept_link"],
        }
        if task_type == "code_view":
            output.update({
                "syntax": examples[0],
                "simple_code": examples[0],
                "multiple_assignment_example": "Use the resource example as the syntax pattern; if the concept supports assignment, compare one name/value with multiple names/values.",
                "output_explanation": f"The code or task example demonstrates this key point: {parts['primary_key']}",
            })
        if task_type == "misconception_view":
            output.update({"wrong_idea": misconceptions[0], "correction": parts["primary_key"], "corrected_example": examples[0]})
        if task_type == "output_prediction_view":
            output.update({"code": examples[0], "line_by_line_trace": [f"Read the example: {examples[0]}", f"Apply the key point: {parts['primary_key']}", f"Check against the misconception: {misconceptions[0]}"], "final_output": parts["primary_key"]})
        if task_type == "debug_view":
            output.update({"buggy_code": f"BUGGY OR MISTAKEN VERSION:\n{examples[0]}\n# Mistake: {misconceptions[0]}", "fixed_code": f"FIXED IDEA:\n{parts['primary_key']}", "debug_explanation": f"The fix is to replace the misconception with the key point for {name}."})
        return output

    def _build_flashcard_output(self, task_type: str, parts: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
        name = parts["concept"]["concept_name"]
        cards = [
            {"card_type": "concept_recall", "front": f"What is {name}?", "back": parts["primary_key"], "explanation": parts["definition"], "difficulty": "easy"},
            {"card_type": "misconception", "front": f"What mistake should you avoid with {name}?", "back": parts["primary_misconception"], "explanation": f"Correct it with: {parts['primary_key']}", "difficulty": "medium"},
            {"card_type": "example", "front": f"What example demonstrates {name}?", "back": parts["primary_example"], "explanation": f"The example shows: {parts['primary_key']}", "difficulty": "easy"},
            {"card_type": "debug", "front": f"How do you debug a mistake about {name}?", "back": f"Compare the attempt with: {parts['primary_key']}", "explanation": f"The common mistake is: {parts['primary_misconception']}", "difficulty": "medium"},
            {"card_type": "syntax", "front": f"What syntax/example pattern belongs to {name}?", "back": parts["primary_example"], "explanation": "This comes from the concept_resources examples field.", "difficulty": "medium"},
            {"card_type": "personal_revision", "front": f"What should you revise next for {name}?", "back": parts["next_concept_link"], "explanation": "This follows the next_concept_link field.", "difficulty": difficulty},
        ]
        return {"flashcard_type": task_type, "cards": cards}

    def _build_mindmap_output(self, task_type: str, parts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mindmap_type": "comparison_mindmap" if task_type == "comparison_mindmap" else "concept_mindmap",
            "center": parts["concept"]["concept_name"],
            "branches": [
                {"label": "Definition", "items": [parts["definition"], parts["primary_key"]]},
                {"label": "Examples", "items": parts["examples"][:4]},
                {"label": "Key Points", "items": parts["key_points"][:4]},
                {"label": "Common Mistakes", "items": parts["misconceptions"][:4]},
                {"label": "Real-world Use", "items": [parts["real_world_use"]]},
                {"label": "Related Concept", "items": [parts["next_concept_link"]]},
            ],
        }

    def _build_hint_output(self, task_type: str, parts: Dict[str, Any], question_type: Optional[str]) -> Dict[str, Any]:
        hint_type = task_type if task_type != "hint" else (question_type + "_hint" if question_type else "guided_hint")
        return {
            "hint_type": hint_type,
            "hint": f"Start from {parts['concept']['concept_name']}'s key point: {parts['primary_key']}. Then compare your answer with the example: {parts['primary_example']}",
            "why_this_helps": f"This keeps the learner inside concept_resources instead of guessing from unrelated facts.",
            "next_step": "Try answering once before reading the full explanation.",
        }

    def _build_feedback_output(self, task_type: str, parts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "feedback_type": task_type,
            "message": f"Your answer should be checked against {parts['concept']['concept_name']}'s key point: {parts['primary_key']}",
            "correction": f"If your answer followed the misconception '{parts['primary_misconception']}', replace it with the resource rule.",
            "next_step": parts["next_concept_link"],
            "correct_answer_feedback": f"Correct: you used {parts['primary_key']}.",
            "wrong_answer_feedback": f"Not quite: review {parts['primary_misconception']}.",
            "partial_answer_feedback": f"Partly right: add the example {parts['primary_example']}.",
        }

    def _build_doubt_output(self, task_type: str, parts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "answer": f"This doubt is about {parts['concept']['concept_name']}. The grounded answer is: {parts['primary_key']} Use the definition and example together before moving on.",
            "example": parts["primary_example"],
            "source_context_summary": f"Used concept_resources fields: definition, examples, key_points, misconceptions, real_world_use, next_concept_link. Main misconception: {parts['primary_misconception']}",
            "follow_up_check": f"Can you explain why '{parts['primary_misconception']}' is not the correct rule for {parts['concept']['concept_name']}?",
            "next_step": parts["next_concept_link"],
            "doubt_type": task_type,
        }

    def _build_notebook_revision_output(self, task_type: str, parts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "summary_type": task_type,
            "notebook_summary": f"{parts['concept']['concept_name']}: {parts['primary_key']} Example: {parts['primary_example']}",
            "mistake_summary": f"Watch for this mistake: {parts['primary_misconception']}",
            "revision_plan": ["Review the definition.", "Study the example.", "Answer one assessment question.", f"Move next: {parts['next_concept_link']}"],
            "comeback_summary": f"Welcome back to {parts['concept']['concept_name']}. Start with the key point, then retry the example.",
            "returning_learner_summary": f"You last need to reconnect {parts['concept']['concept_name']} with its example and misconception.",
            "progress_insight": f"Mastery should improve when the learner can explain {parts['primary_key']} and avoid {parts['primary_misconception']}.",
        }

    def _build_voice_output(self, task_type: str, parts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "script_type": task_type,
            "voice_ready": True,
            "script": (
                f"Today we are learning {parts['concept']['concept_name']} in {parts['concept']['domain']}. "
                f"The main idea is {parts['primary_key']}. Here is the example: {parts['primary_example']}. "
                f"One mistake learners make is this: {parts['primary_misconception']}. "
                f"Now pause and answer this check: can you explain the example using the key idea?"
            ),
        }

    def _guarded_output_for_task(self, task_type: str, parts: Dict[str, Any], difficulty: str, question_type: Optional[str]) -> Dict[str, Any]:
        if task_type in TEACHING_TASK_TYPES:
            return self._build_teaching_output(task_type, parts, difficulty)
        if task_type in ASSESSMENT_TASK_TYPES or task_type in PRACTICE_TASK_TYPES:
            return self._base_assessment_item(parts, task_type, difficulty)
        if task_type == "spaced_repetition_card":
            return self._build_flashcard_output(task_type, parts, difficulty)
        if task_type in FLASHCARD_TASK_TYPES:
            return self._build_flashcard_output(task_type, parts, difficulty)
        if task_type in MINDMAP_TASK_TYPES:
            return self._build_mindmap_output(task_type, parts)
        if task_type in HINT_TASK_TYPES:
            return self._build_hint_output(task_type, parts, question_type)
        if task_type in FEEDBACK_TASK_TYPES:
            return self._build_feedback_output(task_type, parts)
        if task_type in DOUBT_TASK_TYPES:
            return self._build_doubt_output(task_type, parts)
        if task_type in NOTEBOOK_TASK_TYPES or task_type in REVISION_TASK_TYPES:
            return self._build_notebook_revision_output(task_type, parts)
        if task_type in VOICE_TASK_TYPES:
            return self._build_voice_output(task_type, parts)
        return self._build_teaching_output("explanation", parts, difficulty)

    def generate_task(
        self,
        task_type: str,
        concept_resource: Dict[str, Any],
        difficulty: str = "easy",
        teaching_style: Optional[str] = None,
        learner_state: Optional[Dict[str, Any]] = None,
        question_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        parts = self._resource_parts(concept_resource)
        concept = parts["concept"]
        raw_model_output = ""
        output = self._guarded_output_for_task(task_type, parts, difficulty, question_type)
        validation = validate_task_output(
            task_type=task_type,
            output=output,
            concept_name=concept.get("concept_name"),
            key_points=parts.get("key_points"),
        )
        source = "concept_resource_fallback"
        if task_type in DOUBT_TASK_TYPES:
            source = "rag_grounded" if self.build_rag_grounding_metadata(
                query=f"{task_type} {concept['concept_name']}",
                concept_id=concept.get("concept_id"),
                concept_name=concept.get("concept_name"),
                domain=concept.get("domain"),
                top_k=3,
            ).get("rag_connected") else "concept_resource_fallback"
        return {
            "status": "success" if validation["valid"] else "warning",
            "task_type": task_type,
            "concept_id": concept.get("concept_id"),
            "concept_name": concept.get("concept_name"),
            "difficulty": difficulty,
            "teaching_style": teaching_style,
            "learner_state_used": bool(learner_state),
            "source": source,
            "model_generated": False,
            "fallback_used": True,
            "format_valid": validation["valid"],
            "quality_score": validation["quality_score"],
            "output": output,
            "raw_model_output": raw_model_output,
            "validation": validation,
            "fallback_reason": "raw_from_scratch_model_generation_not_used_for_service_contract; guarded concept_resources output used",
            "source_fields_used": ["concept_id", "topic", "base_content", "examples", "key_points", "misconceptions", "real_world_use", "next_concept_link"],
        }

    def generate_assessment_question_set(
        self,
        concept_resource: Dict[str, Any],
        difficulty: str = "easy",
    ) -> Dict[str, Any]:
        parts = self._resource_parts(concept_resource)
        items = []
        for task_type in ASSESSMENT_TASK_TYPES:
            if task_type == "mcq":
                mcq = self._base_assessment_item(parts, "mcq", difficulty)
                items.extend(mcq.pop("questions"))
                items.append(mcq)
            else:
                items.append(self._base_assessment_item(parts, task_type, difficulty))
        prompts = [item.get("prompt", "") for item in items]
        return {
            "status": "success",
            "source": "concept_resource_fallback",
            "model_generated": False,
            "fallback_used": True,
            "concept_id": parts["concept"]["concept_id"],
            "concept_name": parts["concept"]["concept_name"],
            "questions": items,
            "duplicate_prompt_count": len(prompts) - len(set(prompts)),
        }

    def generate_adaptive_session_packet(
        self,
        learner_id: str,
        concept_id: str,
        domain: Optional[str] = None,
        concept_name: Optional[str] = None,
        learner_profile: str = "average",
        returning_mode: Optional[str] = None,
        weak_question_types: Optional[List[str]] = None,
        num_questions: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate a session packet where the teaching view is automatically selected
        using TeachingViewProgressionService.

        This is better than manually passing selected_view every time.
        """

        resolved_concept = self._resolve_concept(
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )

        if resolved_concept.get("status") != "success":
            return {
                "status": "not_found",
                "message": "Concept could not be resolved.",
                "input": {
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "domain": domain,
                },
            }

        resolved_concept_id = resolved_concept["concept_id"]
        resolved_concept_name = resolved_concept["concept_name"]
        resolved_domain = resolved_concept["domain"]

        learning_plan = self.teaching_progression_service.build_concept_learning_plan(
            learner_id=learner_id,
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
            learner_profile=learner_profile,
            returning_mode=returning_mode,
            weak_question_types=weak_question_types,
        )

        selected_view = learning_plan["next_recommended_view"]
        question_types = learning_plan["next_assessment_types"]

        teaching = self.get_teaching_view(
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
            artifact_type=selected_view,
        )

        # If selected view is unavailable, fall back safely.
        if teaching.get("status") != "success":
            fallback_views = [
                "definition_view",
                "simple_example_view",
                "code_view",
                "revision_summary_view",
            ]

            for fallback_view in fallback_views:
                teaching = self.get_teaching_view(
                    concept_id=resolved_concept_id,
                    concept_name=resolved_concept_name,
                    domain=resolved_domain,
                    artifact_type=fallback_view,
                )

                if teaching.get("status") == "success":
                    selected_view = fallback_view
                    question_types = learning_plan.get("next_assessment_types") or ["mcq"]
                    break

        assessment = self.get_assessment_questions(
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
            question_types=question_types,
            num_questions=num_questions,
        )

        rag_metadata = self.build_rag_grounding_metadata(
            query=f"Teach {resolved_concept_name} in {resolved_domain} using {selected_view}",
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
            top_k=5,
        )
        support_outputs = self._support_outputs(resolved_concept_id, resolved_concept_name, resolved_domain, selected_view)

        return {
            "status": "success",
            "mode": "adaptive_teaching_session",
            "model": "CogniTutorLM-S",
            "learner_id": learner_id,
            "concept_id": resolved_concept_id,
            "concept_name": resolved_concept_name,
            "domain": resolved_domain,
            "selected_view": selected_view,
            "question_types": question_types,
            "teaching": teaching,
            "assessment": assessment,
            **support_outputs,
            "rag_grounding": rag_metadata,
            "progression": {
                "coverage_status": learning_plan.get("coverage_status"),
                "current_view": learning_plan.get("current_view"),
                "covered_views": learning_plan.get("covered_views"),
                "successful_views": learning_plan.get("successful_views"),
                "weak_views": learning_plan.get("weak_views"),
                "next_recommended_view": learning_plan.get("next_recommended_view"),
                "next_assessment_types": learning_plan.get("next_assessment_types"),
                "full_learning_sequence": learning_plan.get("full_learning_sequence"),
                "fast_forward_map": learning_plan.get("fast_forward_map"),
                "rule": learning_plan.get("rule"),
            },
            "frontend_contract": {
                "show_teaching_card": True,
                "show_question_one_at_a_time": True,
                "show_progression_reason": True,
                "show_code_runner_for": [
                    "debug_task",
                    "coding_question",
                    "output_prediction",
                ],
                "next_action": "answer_question",
            },
        }

    def submit_answer_and_update_progress(
        self,
        learner_id: str,
        concept_id: str,
        question_type: str,
        variant_id: int,
        learner_answer: Any,
        teaching_view: Optional[str] = None,
        domain: Optional[str] = None,
        concept_name: Optional[str] = None,
        difficulty: str = "easy",
    ) -> Dict[str, Any]:
        """
        Evaluate one submitted answer, then update learner memory and one-view
        teaching progression.
        """

        resolved_concept = self._resolve_concept(
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )

        if resolved_concept.get("status") != "success":
            return {
                "status": "not_found",
                "mode": "answer_submission_update",
                "message": "Concept could not be resolved.",
                "input": {
                    "learner_id": learner_id,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "domain": domain,
                    "question_type": question_type,
                    "variant_id": variant_id,
                },
            }

        resolved_concept_id = resolved_concept["concept_id"]
        resolved_concept_name = resolved_concept["concept_name"]
        resolved_domain = resolved_concept["domain"]

        evaluation_response = self.evaluate_learner_answer(
            concept_id=resolved_concept_id,
            question_type=question_type,
            variant_id=variant_id,
            learner_answer=learner_answer,
        )

        if evaluation_response.get("status") != "success":
            return {
                "status": evaluation_response.get("status", "error"),
                "mode": "answer_submission_update",
                "learner_id": learner_id,
                "concept_id": resolved_concept_id,
                "concept_name": resolved_concept_name,
                "domain": resolved_domain,
                "question_type": question_type,
                "variant_id": variant_id,
                "evaluation": evaluation_response,
                "next_action": "check_question_reference",
            }

        evaluation = evaluation_response["evaluation"]
        score = float(evaluation.get("score", 0.0))
        next_signal = evaluation.get("next_signal") or {}

        current_plan = self.teaching_progression_service.build_concept_learning_plan(
            learner_id=learner_id,
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
        )

        resolved_view = (
            teaching_view
            or current_plan.get("current_view")
            or current_plan.get("next_recommended_view")
            or "definition_view"
        )

        memory_update = self.learner_memory_service.update_memory_from_evaluation(
            learner_id=learner_id,
            evaluation_result=evaluation,
            teaching_view=resolved_view,
            difficulty=difficulty,
        )

        progression_update = self.teaching_progression_service.update_after_view_result(
            learner_id=learner_id,
            concept_id=resolved_concept_id,
            concept_name=resolved_concept_name,
            domain=resolved_domain,
            view=resolved_view,
            score=score,
            question_type=question_type,
        )

        recommendation = progression_update.get("recommendation") or {}

        return {
            "status": "success",
            "mode": "answer_submission_update",
            "learner_id": learner_id,
            "concept_id": resolved_concept_id,
            "concept_name": resolved_concept_name,
            "domain": resolved_domain,
            "question_type": question_type,
            "variant_id": variant_id,
            "teaching_view": resolved_view,
            "evaluation": evaluation,
            "memory_update": memory_update,
            "progression_update": progression_update,
            "next_recommended_view": recommendation.get("next_view"),
            "next_assessment_types": recommendation.get("assessment_types", []),
            "next_action": next_signal.get("recommended_next_action") or "continue_learning",
        }

    def generate_returning_learner_packet(
        self,
        learner_id: str,
        force_time_gap_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete returning-learner packet.

        This combines:
        - learner memory
        - comeback summary
        - recommended teaching view
        - actual teaching artifact
        - recommended assessment questions

        Used when a learner comes back after minutes/hours/days/long gap.
        """

        memory_packet = self.learner_memory_service.recommend_revision_packet(
            learner_id=learner_id
        )

        # Allow test/demo forcing: minutes, hours, days, long_gap.
        if force_time_gap_category:
            memory_packet = self.learner_memory_service.build_comeback_summary(
                learner_id=learner_id,
                force_category=force_time_gap_category,
            )

            if memory_packet.get("mode") != "new_learner":
                memory_packet = {
                    "status": "success",
                    "mode": memory_packet["mode"],
                    "learner_id": learner_id,
                    "time_gap_category": memory_packet["time_gap_category"],
                    "last_concept": memory_packet["last_concept"],
                    "comeback_summary": memory_packet["comeback_summary"],
                    "recommended_views": memory_packet["recommended_views"],
                    "recommended_question_types": memory_packet["recommended_question_types"],
                    "num_questions": memory_packet["num_questions"],
                    "next_action": memory_packet["next_action"],
                    "weak_concepts": memory_packet["weak_concepts"],
                    "weak_question_types": memory_packet["weak_question_types"],
                    "strong_question_types": memory_packet["strong_question_types"],
                    "mistake_summary": memory_packet["mistake_summary"],
                }

        if memory_packet.get("mode") == "new_learner":
            return {
                "status": "success",
                "mode": "new_learner",
                "learner_id": learner_id,
                "message": memory_packet.get("comeback_summary"),
                "recommended_views": memory_packet.get("recommended_views", []),
                "recommended_question_types": memory_packet.get("recommended_question_types", []),
                "rag_grounding": self.build_rag_grounding_metadata(
                    query="Start learning with CogniTutorLM recommendations for a new learner",
                    top_k=5,
                ),
                "next_action": "start_learning",
            }

        last_concept = memory_packet.get("last_concept") or {}

        concept_id = last_concept.get("concept_id")
        concept_name = last_concept.get("concept_name")
        domain = last_concept.get("domain")

        recommended_views = memory_packet.get("recommended_views") or [
            "revision_summary_view"
        ]

        selected_view = recommended_views[0]

        teaching = self.get_teaching_view(
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            artifact_type=selected_view,
        )

        # If the first recommended view is not found, try fallback views.
        if teaching.get("status") != "success":
            for view in [
                "revision_summary_view",
                "misconception_view",
                "definition_view",
                "code_view",
            ]:
                teaching = self.get_teaching_view(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    domain=domain,
                    artifact_type=view,
                )
                if teaching.get("status") == "success":
                    selected_view = view
                    break

        question_types = memory_packet.get("recommended_question_types") or [
            "mcq",
            "output_prediction",
        ]

        num_questions = int(memory_packet.get("num_questions") or 2)

        assessment = self.get_assessment_questions(
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            question_types=question_types,
            num_questions=num_questions,
        )

        weak_question_types = memory_packet.get("weak_question_types", [])
        rag_metadata = self.build_rag_grounding_metadata(
            query=(
                f"Revise {concept_name} in {domain} for weak areas: "
                f"{', '.join(weak_question_types) if weak_question_types else 'general revision'}"
            ),
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            top_k=5,
        )
        support_outputs = self._support_outputs(concept_id, concept_name, domain, selected_view)

        return {
            "status": "success",
            "mode": "returning_learner",
            "model": "CogniTutorLM-S",
            "learner_id": learner_id,
            "time_gap_category": memory_packet.get("time_gap_category"),
            "last_concept": last_concept,
            "comeback_summary": memory_packet.get("comeback_summary"),
            "weak_concepts": memory_packet.get("weak_concepts", []),
            "weak_question_types": memory_packet.get("weak_question_types", []),
            "strong_question_types": memory_packet.get("strong_question_types", []),
            "mistake_summary": memory_packet.get("mistake_summary", []),
            "recommended_views": recommended_views,
            "selected_view": selected_view,
            "recommended_question_types": question_types,
            "teaching": teaching,
            "assessment": assessment,
            **support_outputs,
            "rag_grounding": rag_metadata,
            "next_action": memory_packet.get("next_action"),
            "frontend_contract": {
                "show_comeback_summary": True,
                "show_teaching_card": True,
                "show_question_one_at_a_time": True,
                "show_code_runner_for": [
                    "debug_task",
                    "coding_question",
                    "output_prediction",
                ],
                "next_action": memory_packet.get("next_action"),
            },
        }


def run_self_test() -> None:
    print("\nTutorLMService self-test")
    print("=" * 80)

    service = TutorLMService()

    if service.content_mode == "structured_model_generated":
        structured_items = service.list_structured_model_outputs()
        status = "ready_for_structured_model_generated_mode" if structured_items else "structured_model_generated_content_not_ready"
        print(f"\nStructured model mode status: {status}")
        print(f"Structured model items loaded: {len(structured_items)}")
        sample = service.get_structured_model_output(task_type="explanation")
        print(json.dumps(sample, indent=2, ensure_ascii=False)[:1600])
        return

    concepts = service.list_concepts()

    print(f"\nConcepts loaded: {len(concepts)}")
    print("First 5 concepts:")
    for item in concepts[:5]:
        print(item)

    print("\nTeaching view test")
    print("-" * 80)
    teaching = service.get_teaching_view(
        concept_id="P1",
        domain="Python",
        artifact_type="definition_view",
    )
    print(json.dumps(teaching, indent=2, ensure_ascii=False)[:1200])

    print("\nAssessment question selection test")
    print("-" * 80)
    assessment = service.get_assessment_questions(
        concept_id="P1",
        domain="Python",
        num_questions=5,
    )
    print(json.dumps(assessment, indent=2, ensure_ascii=False)[:1600])

    print("\nEvaluate learner answer test")
    print("-" * 80)

    if assessment["questions"]:
        first_question = assessment["questions"][0]

        qtype = first_question["question_type"]
        variant_id = first_question["variant_id"]

        if qtype == "mcq":
            learner_answer = first_question["answer_key"]["answer"]
        elif qtype == "output_prediction":
            learner_answer = first_question["answer_key"]["answer"]
        elif qtype == "debug_task":
            learner_answer = first_question["answer_key"]["expected_fix"]
        else:
            learner_answer = "I would explain and apply the concept with one clear example."

        evaluation = service.evaluate_learner_answer(
            concept_id="P1",
            question_type=qtype,
            variant_id=variant_id,
            learner_answer=learner_answer,
        )

        print(json.dumps(evaluation, indent=2, ensure_ascii=False)[:1600])

    print("\nRun code test")
    print("-" * 80)
    run_result = service.run_code(
        code="x = 10\nx = 20\nprint(x)",
        expected_output="20",
    )
    print(json.dumps(run_result, indent=2, ensure_ascii=False))

    print("\nSession packet test")
    print("-" * 80)
    packet = service.generate_session_packet(
        concept_id="P1",
        domain="Python",
        selected_view="code_view",
        num_questions=5,
    )
    print(json.dumps(packet, indent=2, ensure_ascii=False)[:2200])

    print("\nReturning learner packet test")
    print("-" * 80)

    returning_packet = service.generate_returning_learner_packet(
        learner_id="demo_learner_001",
        force_time_gap_category="days",
    )

    print(json.dumps(returning_packet, indent=2, ensure_ascii=False)[:2600])
    print("\nAdaptive session packet test")
    print("-" * 80)

    adaptive_packet = service.generate_adaptive_session_packet(
        learner_id="demo_progress_learner_001",
        concept_id="P1",
        domain="Python",
        learner_profile="weak",
        num_questions=3,
    )

    print(json.dumps(adaptive_packet, indent=2, ensure_ascii=False)[:3200])

    print("\nClean new learner adaptive session packet test")
    print("-" * 80)

    clean_learner_id = "new_adaptive_demo_001"
    service.teaching_progression_service.reset_progress(
        learner_id=clean_learner_id,
        concept_id="P1",
        domain="Python",
    )

    clean_adaptive_packet = service.generate_adaptive_session_packet(
        learner_id=clean_learner_id,
        concept_id="P1",
        domain="Python",
        learner_profile="weak",
        num_questions=3,
    )

    print(json.dumps(clean_adaptive_packet, indent=2, ensure_ascii=False)[:3200])

    print("\nSubmit answer and update progress test")
    print("-" * 80)

    answer_update_learner_id = "answer_update_demo_001"
    service.teaching_progression_service.reset_progress(
        learner_id=answer_update_learner_id,
        concept_id="P1",
        domain="Python",
    )

    answer_update_packet = service.generate_adaptive_session_packet(
        learner_id=answer_update_learner_id,
        concept_id="P1",
        domain="Python",
        learner_profile="weak",
        num_questions=3,
    )

    answer_update_questions = (answer_update_packet.get("assessment") or {}).get("questions") or []

    if answer_update_questions:
        first_question = answer_update_questions[0]
        answer_key = first_question.get("answer_key") or {}
        qtype = first_question.get("question_type")

        if qtype == "mcq":
            learner_answer = answer_key.get("answer", "")
        elif qtype == "output_prediction":
            learner_answer = answer_key.get("answer", "")
        elif qtype == "debug_task":
            learner_answer = answer_key.get("expected_fix", "")
        else:
            learner_answer = (
                f"I can explain {first_question.get('concept_name')} with the main rule "
                "and one simple example."
            )

        submission_result = service.submit_answer_and_update_progress(
            learner_id=answer_update_learner_id,
            concept_id=first_question["concept_id"],
            concept_name=first_question.get("concept_name"),
            domain=first_question.get("domain"),
            question_type=qtype,
            variant_id=first_question["variant_id"],
            learner_answer=learner_answer,
            teaching_view=answer_update_packet.get("selected_view"),
            difficulty=first_question.get("difficulty", "easy"),
        )

        print(json.dumps(submission_result, indent=2, ensure_ascii=False)[:2500])

    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()
