from __future__ import annotations

from fastapi import APIRouter

from tutor.api.dependencies import latest_concept_from_logs, revision_due_packet
from tutor.api.schemas import api_response


router = APIRouter(prefix="/revision", tags=["revision"])


@router.get("/{learner_id}")
def revision(learner_id: str) -> dict:
    module = "RevisionRoutes"
    try:
        due = revision_due_packet(learner_id)
        latest = latest_concept_from_logs(learner_id)
        scheduler_output = {}
        try:
            from tutor.memory.revision_scheduler import RevisionScheduler

            scheduler_output = RevisionScheduler().build_revision_plan(
                {
                    "learner_id": learner_id,
                    "concept_id": latest.get("concept_id"),
                    "concept_name": latest.get("concept_name") or "current concept",
                    "domain": latest.get("domain"),
                    "mastery_score": latest.get("mastery") or latest.get("mastery_score") or 0.0,
                    "review_due": bool(due),
                    "fused_score": latest.get("last_score") or 0.5,
                }
            )
        except Exception as exc:
            scheduler_output = {"status": "warning", "reason": f"{type(exc).__name__}: optional scheduler unavailable."}
        return api_response(
            module=module,
            fallback_used=scheduler_output.get("status") == "warning",
            data={
                "auto_flow": True,
                "learner_id": learner_id,
                "concept_id": latest.get("concept_id"),
                "concept_name": latest.get("concept_name"),
                "revision_needed": bool(due),
                "retention_risk": "high" if due else "low",
                "due_cards": due,
                "recommended_revision_activity": {
                    "type": "flashcard_revision" if due else "assessment",
                    "label": "Review due cards" if due else "Try a quick check",
                    "reason": "Due cards indicate retention risk." if due else "No due cards found.",
                },
                "due_revision_cards": due,
                "revision_packet": scheduler_output.get("frontend_revision_packet", {}),
                "scheduler_output": scheduler_output,
                "current_activity": {
                    "type": "flashcard_revision" if due else "revision_summary",
                    "frontend_component": "FlashcardDeck" if due else "SelectedTeachingViewRenderer",
                    "payload": {"due_count": len(due)},
                },
                "next_recommended_activity": {
                    "type": "assessment",
                    "label": "Try a quick check",
                    "reason": "Confirm revision before continuing.",
                },
                "guide_message": "Welcome back! It's been a while, so let's revise before continuing." if due else "Nice revision! Now you're ready to continue.",
                "backend_connected": True,
            },
        )
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")
