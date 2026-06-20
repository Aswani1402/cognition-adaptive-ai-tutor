from __future__ import annotations

from fastapi import APIRouter

from tutor.api.schemas import AskDoubtRequest, api_response
from tutor.api.concept_content_resolver import build_doubt_answer
from tutor.system.user_persistence_store import save_doubt_log


router = APIRouter(prefix="/doubt", tags=["doubt"])


@router.post("/ask")
def ask_doubt(payload: AskDoubtRequest) -> dict:
    module = "DoubtRoutes"
    try:
        classifier_result = {}
        try:
            from tutor.doubt.doubt_intent_classifier import DoubtIntentClassifier

            classifier_result = DoubtIntentClassifier().classify(
                doubt_text=payload.doubt_text,
                concept_name=payload.concept_name,
                domain=payload.domain,
                code_context=payload.code_context,
            )
        except Exception as exc:
            classifier_result = {
                "status": "warning",
                "intent": "low_confidence_doubt",
                "confidence": 0.0,
                "method": "classifier_unavailable",
                "fallback_used": True,
                "recommended_route": "supportive_reteach",
                "reason": f"{type(exc).__name__}: {exc}",
            }

        answer_packet = {}
        try:
            from tutor.generation.cognitutor_lm_connector import ask_cognitutor_doubt

            raw = ask_cognitutor_doubt(
                learner_id=payload.learner_id,
                learner_doubt=payload.doubt_text,
                concept_id=payload.concept_id,
                concept_name=payload.concept_name,
                domain=payload.domain,
            )
            answer_packet = raw.get("data") if isinstance(raw, dict) and isinstance(raw.get("data"), dict) else raw
        except Exception as exc:
            answer_packet = build_doubt_answer(payload.subject or payload.domain, payload.concept_id, payload.doubt_text)
            answer_packet["status"] = "warning"
            answer_packet["reason"] = f"{type(exc).__name__}: {exc}"

        save_doubt_log(
            payload.learner_id,
            "api_session",
            {
                "domain": payload.subject or payload.domain,
                "concept_id": payload.concept_id,
                "concept_name": payload.concept_name,
                "doubt_text": payload.doubt_text,
                "doubt_type": classifier_result.get("intent"),
                "answer_summary": answer_packet.get("answer") or answer_packet.get("doubt_answer"),
                "rag_grounded": answer_packet.get("rag_grounded") or answer_packet.get("rag_success"),
                "grounding_score": answer_packet.get("grounding_score"),
                "follow_up_questions": answer_packet.get("follow_up_check") or answer_packet.get("followup_check"),
                "memory_updated": True,
            },
        )
        frontend_doubt_type = answer_packet.get("doubt_type") or answer_packet.get("intent") or classifier_result.get("intent")
        if not str(frontend_doubt_type or "").endswith("_doubt_answer"):
            frontend_doubt_type = build_doubt_answer(payload.subject or payload.domain, payload.concept_id, payload.doubt_text).get("doubt_type")
        return api_response(
            module=module,
            fallback_used=bool(classifier_result.get("fallback_used") or answer_packet.get("status") == "warning"),
            data={
                "intent": classifier_result.get("intent"),
                "confidence": classifier_result.get("confidence"),
                "classifier_method": classifier_result.get("method"),
                "recommended_route": classifier_result.get("recommended_route"),
                "subject": payload.subject or payload.domain or answer_packet.get("subject"),
                "concept_id": answer_packet.get("concept_id") or payload.concept_id,
                "concept_name": answer_packet.get("concept_name") or payload.concept_name,
                "intent": frontend_doubt_type,
                "doubt_type": frontend_doubt_type,
                "answer": answer_packet.get("answer") or answer_packet.get("doubt_answer"),
                "source": answer_packet.get("source") or answer_packet.get("method") or "concept_context_rag_or_artifact",
                "topic": answer_packet.get("concept_name") or payload.concept_name,
                "example": answer_packet.get("example"),
                "available_doubt_types": answer_packet.get("available_doubt_types", []),
                "voice_script": answer_packet.get("voice_script"),
                "llm_generation": answer_packet.get("llm_generation"),
                "rag_grounding": {
                    "rag_grounded": True if answer_packet.get("base_content") else bool(answer_packet.get("rag_grounded") or answer_packet.get("rag_success")),
                    "grounding_score": answer_packet.get("grounding_score"),
                    "grounding_source_label": answer_packet.get("grounding_source_label") or answer_packet.get("source") or "concept_resources",
                    "source_sections": answer_packet.get("source_sections_used") or answer_packet.get("retrieved_sections", ["concept_resources"]),
                },
                "follow_up_check": answer_packet.get("follow_up_check") or answer_packet.get("followup_check"),
                "classifier_output": classifier_result,
                "doubt_handler_output": answer_packet,
            },
        )
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")
