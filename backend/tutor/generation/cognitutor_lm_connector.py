"""
CogniTutorLM connector for the main Cognition-Adaptive AI Tutor project.

This file keeps the main tutor project and CogniTutor_LM_from_scratch separate.
It imports the external TutorLMService through a safe connector layer instead
of copying folders or merging src/scripts.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


CONNECTOR_SOURCE = "cognitutor_lm_connector"


def _find_cognitutor_project_root() -> Optional[Path]:
    """
    Expected layout:

    PythonProject/
    ├── cognition_adaptive_AI_tutor/
    └── CogniTutor_LM_from_scratch/
    """
    current_file = Path(__file__).resolve()

    # .../cognition_adaptive_AI_tutor/tutor/generation/cognitutor_lm_connector.py
    main_project_root = current_file.parents[2]

    # .../PythonProject/
    shared_parent = main_project_root.parent

    candidate = shared_parent / "CogniTutor_LM_from_scratch"

    if candidate.exists() and (candidate / "src" / "tutor_lm_service.py").exists():
        return candidate

    return None


def _safe_error(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "error",
        "source": CONNECTOR_SOURCE,
        "error": message,
        "details": details or {},
    }


def _public_response(raw: Dict[str, Any], output_key: str = "output") -> Dict[str, Any]:
    available = raw.get("status") == "success"
    return {
        "status": "success" if available else "warning",
        "service": "cognitutor_lm_from_scratch",
        "available": available,
        "model_generated": "unknown" if available else False,
        output_key: raw.get("data", raw),
        "fallback_used": not available,
        "limitations": [] if available else [raw.get("error") or raw.get("reason") or "CogniTutorLM service unavailable"],
    }


@lru_cache(maxsize=1)
def get_cognitutor_api_service():
    """
    Import and cache the guarded CogniTutorLM API service.

    This gives the main backend direct access to website-safe generated packets
    and all-89 outputs without training, external APIs, or pretrained models.
    """
    project_root = _find_cognitutor_project_root()

    if project_root is None:
        raise ImportError(
            "CogniTutor_LM_from_scratch not found beside cognition_adaptive_AI_tutor."
        )

    project_root_str = str(project_root)

    if project_root_str in sys.path:
        sys.path.remove(project_root_str)
    sys.path.insert(0, project_root_str)
    for package_name in ("src", "scripts"):
        module = sys.modules.get(package_name)
        module_file = str(getattr(module, "__file__", "") or "")
        if module and "CogniTutor_LM_from_scratch" not in module_file:
            sys.modules.pop(package_name, None)

    from src import cognitutor_lm_api_service

    return cognitutor_lm_api_service


def get_cognitutor_teaching_packet(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_learning_packet(
            domain=domain,
            concept_name=concept_name,
            concept_id=concept_id,
            difficulty=difficulty,
            teaching_view=teaching_view,
        )
    except Exception as exc:
        return _safe_error("CogniTutorLM teaching packet fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_assessment_packet(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
) -> Dict[str, Any]:
    packet = get_cognitutor_teaching_packet(domain, concept_name, concept_id, difficulty, teaching_view)
    if packet.get("status") != "success":
        return packet
    return {
        "status": "success",
        "domain": packet.get("domain"),
        "concept_id": packet.get("concept_id"),
        "concept_name": packet.get("concept_name"),
        "difficulty": packet.get("difficulty"),
        "source_level": packet.get("source_level"),
        "teaching_view": packet.get("teaching_view"),
        "aligned_assessments": packet.get("aligned_assessments", []),
    }


def get_cognitutor_doubt_answer(
    domain: str,
    concept: str,
    question: str,
    use_rag: bool = True,
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.ask_doubt_and_get_answer(domain=domain, concept=concept, question=question, use_rag=use_rag)
    except Exception as exc:
        return _safe_error("CogniTutorLM doubt answer fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_revision_packet(
    domain: str,
    concept: str,
    learner_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_revision_packet(domain=domain, concept=concept, learner_state=learner_state)
    except Exception as exc:
        return _safe_error("CogniTutorLM revision packet fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_session_packet(
    domain: str,
    concept: str,
    learner_id: Optional[str] = None,
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
    use_rag: bool = True,
    generation_mode: str = "guarded",
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        packet = api.get_website_session_packet(
            domain=domain,
            concept=concept,
            learner_id=learner_id,
            difficulty=difficulty,
            teaching_view=teaching_view,
            use_rag=use_rag,
            generation_mode=generation_mode,
        )
        if generation_mode == "rag_llm_live_guarded":
            packet["cognitutor_lm_live_guarded_output"] = packet.get("live_guarded_output")
        return packet
    except Exception as exc:
        return _safe_error("CogniTutorLM session packet fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_live_guarded_packet(
    domain: str,
    concept: str,
    learner_id: Optional[str] = None,
    difficulty: str = "easy",
    teaching_view: str = "definition_view",
    use_rag: bool = True,
) -> Dict[str, Any]:
    return get_cognitutor_session_packet(
        domain=domain,
        concept=concept,
        learner_id=learner_id,
        difficulty=difficulty,
        teaching_view=teaching_view,
        use_rag=use_rag,
        generation_mode="rag_llm_live_guarded",
    )


def get_cognitutor_all_task_outputs(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        rows = api.get_all_task_outputs(domain=domain, concept_name=concept_name, concept_id=concept_id)
        return {
            "status": "success" if rows else "not_found",
            "domain": domain,
            "concept_name": concept_name,
            "concept_id": concept_id,
            "task_count": len(rows),
            "tasks": rows,
        }
    except Exception as exc:
        return _safe_error("CogniTutorLM all-task output fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_flashcards(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    variant: str = "all",
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_flashcards(domain=domain, concept_name=concept_name, concept_id=concept_id, difficulty=difficulty, variant=variant)
    except Exception as exc:
        return _safe_error("CogniTutorLM flashcards fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_mindmap(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    variant: str = "concept_mindmap",
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_mindmap(domain=domain, concept_name=concept_name, concept_id=concept_id, variant=variant)
    except Exception as exc:
        return _safe_error("CogniTutorLM mindmap fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_notebook_packet(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    learner_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_notebook_packet(domain=domain, concept_name=concept_name, concept_id=concept_id, learner_state=learner_state)
    except Exception as exc:
        return _safe_error("CogniTutorLM notebook packet fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_audio_overview(
    domain: str,
    concept_name: Optional[str] = None,
    concept_id: Optional[str] = None,
    learner_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_audio_overview_packet(domain=domain, concept_name=concept_name, concept_id=concept_id, learner_state=learner_state)
    except Exception as exc:
        return _safe_error("CogniTutorLM audio overview fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


def get_cognitutor_similar_question(
    domain: str,
    concept: str,
    weakness: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: str = "medium",
) -> Dict[str, Any]:
    try:
        api = get_cognitutor_api_service()
        return api.get_similar_question(domain=domain, concept=concept, weakness=weakness, question_type=question_type, difficulty=difficulty)
    except Exception as exc:
        return _safe_error("CogniTutorLM similar question fetch failed", {"exception_type": type(exc).__name__, "exception_message": str(exc)})


@lru_cache(maxsize=1)
def get_cognitutor_service():
    """
    Import and cache TutorLMService.

    This intentionally returns the service object directly so wrapper functions
    can call methods without reloading artifacts/question bank each time.
    """
    project_root = _find_cognitutor_project_root()

    if project_root is None:
        raise ImportError(
            "CogniTutor_LM_from_scratch not found beside cognition_adaptive_AI_tutor."
        )

    project_root_str = str(project_root)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    from src.tutor_lm_service import TutorLMService

    return TutorLMService()


@lru_cache(maxsize=1)
def get_cognitutor_doubt_handler():
    """
    Import and cache DoubtHandlerService separately from TutorLMService.
    """
    project_root = _find_cognitutor_project_root()

    if project_root is None:
        raise ImportError(
            "CogniTutor_LM_from_scratch not found beside cognition_adaptive_AI_tutor."
        )

    project_root_str = str(project_root)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    from src.doubt_handler_service import DoubtHandlerService

    return DoubtHandlerService()


def _call_service(method_name: str, *args, **kwargs) -> Dict[str, Any]:
    try:
        service = get_cognitutor_service()
        method = getattr(service, method_name)

        result = method(*args, **kwargs)

        return {
            "status": "success",
            "source": CONNECTOR_SOURCE,
            "method": method_name,
            "data": result,
        }

    except Exception as exc:
        return _safe_error(
            message=f"CogniTutorLM service call failed: {method_name}",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )


def generate_cognitutor_session_packet(
    learner_id: str,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
    selected_view: Optional[str] = None,
    question_types: Optional[list[str]] = None,
    num_questions: int = 3,
) -> Dict[str, Any]:
    return _call_service(
        "generate_session_packet",
        learner_id=learner_id,
        concept_id=concept_id,
        concept_name=concept_name,
        domain=domain,
        selected_view=selected_view,
        question_types=question_types,
        num_questions=num_questions,
    )


def generate_cognitutor_adaptive_session(
    learner_id: str,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    return _call_service(
        "generate_adaptive_session_packet",
        learner_id=learner_id,
        concept_id=concept_id,
        concept_name=concept_name,
        domain=domain,
    )


def generate_cognitutor_returning_learner_packet(
    learner_id: str,
) -> Dict[str, Any]:
    return _call_service(
        "generate_returning_learner_packet",
        learner_id=learner_id,
    )


def submit_cognitutor_answer(
    learner_id: str,
    question_record: Dict[str, Any],
    learner_answer: str,
    teaching_view: Optional[str] = None,
) -> Dict[str, Any]:
    return _call_service(
        "submit_answer_and_update_progress",
        learner_id=learner_id,
        question_record=question_record,
        learner_answer=learner_answer,
        teaching_view=teaching_view,
    )


def ask_cognitutor_doubt(
    learner_id: str,
    learner_doubt: str,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    classifier_output: Dict[str, Any] = {}
    try:
        from tutor.doubt.doubt_intent_classifier import DoubtIntentClassifier

        classifier_output = DoubtIntentClassifier().predict(
            doubt_text=learner_doubt,
            concept_name=concept_name,
            domain=domain,
        )
    except Exception as exc:
        classifier_output = {
            "status": "error",
            "module": "DoubtIntentClassifier",
            "intent": "concept_doubt",
            "confidence": 0.0,
            "method": "classifier_unavailable",
            "fallback_used": True,
            "recommended_route": "rag_concept_explanation",
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        doubt_handler = get_cognitutor_doubt_handler()

        result = doubt_handler.handle_doubt(
            learner_id=learner_id,
            learner_doubt=learner_doubt,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
        )

        return {
            "status": "success",
            "source": CONNECTOR_SOURCE,
            "method": "handle_doubt",
            "intent": classifier_output.get("intent"),
            "intent_confidence": classifier_output.get("confidence"),
            "classifier_method": classifier_output.get("method"),
            "fallback_used": classifier_output.get("fallback_used"),
            "recommended_route": classifier_output.get("recommended_route"),
            "classifier_output": classifier_output,
            "data": result,
        }

    except Exception as exc:
        return _safe_error(
            message="CogniTutorLM doubt handler call failed",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "classifier_output": classifier_output,
            },
        )


def run_cognitutor_code(
    code: str,
    expected_output: Optional[str] = None,
) -> Dict[str, Any]:
    return _call_service(
        "run_code",
        code=code,
        expected_output=expected_output,
    )


def list_cognitutor_concepts() -> Dict[str, Any]:
    return _call_service("list_concepts")


def list_concepts() -> Dict[str, Any]:
    return _public_response(list_cognitutor_concepts())


def generate_teaching_artifact(
    learner_id: str = "",
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    return _public_response(
        generate_cognitutor_session_packet(
            learner_id=learner_id,
            concept_id=concept_id,
            concept_name=concept_name,
            domain=domain,
            num_questions=1,
        )
    )


def generate_adaptive_session_packet(
    learner_id: str,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    return _public_response(generate_cognitutor_adaptive_session(learner_id, concept_id, concept_name, domain))


def evaluate_answer(
    learner_id: str,
    question_record: Dict[str, Any],
    learner_answer: str,
    teaching_view: Optional[str] = None,
) -> Dict[str, Any]:
    return _public_response(submit_cognitutor_answer(learner_id, question_record, learner_answer, teaching_view))


def ask_doubt(
    learner_id: str,
    learner_doubt: str,
    concept_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    return _public_response(ask_cognitutor_doubt(learner_id, learner_doubt, concept_id, concept_name, domain))


def generate_returning_learner_packet(learner_id: str) -> Dict[str, Any]:
    return _public_response(generate_cognitutor_returning_learner_packet(learner_id))


def main() -> None:
    print("\nCogniTutorLM connector self-test")
    print("=" * 80)

    root = _find_cognitutor_project_root()
    print(f"CogniTutor project root: {root}")

    concepts_result = list_cognitutor_concepts()
    print("\nConcept list test")
    print("-" * 80)
    print(concepts_result)

    session_result = generate_cognitutor_adaptive_session(
        learner_id="main_connector_demo_001",
        concept_id="P1",
        concept_name="Variables",
        domain="Python",
    )
    print("\nAdaptive session test")
    print("-" * 80)
    print(session_result)

    doubt_result = ask_cognitutor_doubt(
        learner_id="main_connector_demo_001",
        learner_doubt="I don't understand why 2score = 10 is wrong.",
        concept_id="P1",
        concept_name="Variables",
        domain="Python",
    )
    print("\nDoubt test")
    print("-" * 80)
    print(doubt_result)

    code_result = run_cognitutor_code(
        code="x = 10\nprint(x * 2)",
        expected_output="20",
    )
    print("\nCode runner test")
    print("-" * 80)
    print(code_result)

    if (
        concepts_result.get("status") == "success"
        and session_result.get("status") == "success"
        and doubt_result.get("status") == "success"
        and code_result.get("status") == "success"
    ):
        print("\nSTATUS: PASS")
    else:
        print("\nSTATUS: CHECK")


if __name__ == "__main__":
    main()
