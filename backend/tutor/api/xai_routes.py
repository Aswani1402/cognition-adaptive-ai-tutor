from __future__ import annotations

from fastapi import APIRouter

from tutor.api.dependencies import connect, latest_session_state, table_exists
from tutor.api.schemas import api_response


router = APIRouter(prefix="/xai", tags=["xai"])


@router.get("/{learner_id}")
def xai_dashboard(learner_id: str) -> dict:
    module = "XAIRoutes"
    try:
        conn = connect()
        try:
            has_activity = False
            if table_exists(conn, "quiz_results"):
                row = conn.execute(
                    "SELECT 1 FROM quiz_results WHERE learner_id = ? LIMIT 1",
                    (learner_id,),
                ).fetchone()
                has_activity = row is not None
        finally:
            conn.close()
        if not has_activity:
            return api_response(
                module=module,
                fallback_used=True,
                data={
                    "learner_id": learner_id,
                    "xai_dashboard": {
                        "message": "No completed activity yet.",
                        "cards": {},
                        "top_factors": [],
                        "factor_contributions": {},
                        "counterfactuals": [],
                        "evidence_coverage": {"completed_activity_available": False},
                    },
                },
                reason="No completed activity yet.",
            )
        from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once
        from tutor.xai.xai_dashboard_builder import build_xai_dashboard

        integrated = run_integrated_tutor_once(learner_id=learner_id, reward_dry_run=True)
        dashboard = build_xai_dashboard(integrated, learner_id=learner_id)
        return api_response(module=module, data={"learner_id": learner_id, "xai_dashboard": dashboard})
    except Exception as exc:
        session = latest_session_state(learner_id)
        return api_response(
            status="warning",
            module=module,
            fallback_used=True,
            data={
                "learner_id": learner_id,
                "xai_dashboard": {
                    "cards": {},
                    "top_factors": [],
                    "factor_contributions": {},
                    "counterfactuals": [],
                    "evidence_coverage": {"saved_session_available": bool(session)},
                },
            },
            reason=f"{type(exc).__name__}: latest XAI build unavailable.",
        )
