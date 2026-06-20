from __future__ import annotations

from fastapi import APIRouter

from tutor.api.dependencies import reward_state_packet
from tutor.api.schemas import api_response


router = APIRouter(prefix="/reward", tags=["reward"])


@router.get("/{learner_id}")
def reward(learner_id: str) -> dict:
    module = "RewardRoutes"
    try:
        packet = reward_state_packet(learner_id)
        try:
            from tutor.reward.badge_engine import BadgeEngine
            from tutor.reward.daily_goal_engine import DailyGoalEngine

            packet["badge_engine"] = BadgeEngine().evaluate_and_award(learner_id)
            packet["daily_goal_engine"] = DailyGoalEngine().update_goal(learner_id)
            packet = {**packet, **reward_state_packet(learner_id)}
        except Exception as exc:
            packet["engine_warning"] = f"{type(exc).__name__}: optional reward engines unavailable."
        xp = packet.get("xp") or {}
        streak = packet.get("streak") or {}
        reward_source = "backend_reward_state" if packet else "session_progress_preview"
        return api_response(module=module, fallback_used=bool(packet.get("engine_warning")), data={
            "auto_flow": True,
            "learner_id": learner_id,
            "reward_source": reward_source,
            "xp": xp.get("total_xp", 0),
            "streak": streak.get("current_streak", 0),
            "daily_goal_progress": xp.get("daily_xp", 0),
            "badge_status": packet.get("badge_engine", {}).get("status", "Not available") if isinstance(packet.get("badge_engine"), dict) else "Not available",
            "concept_progress": packet.get("concept_progress", "Not available"),
            "reward_gamification": packet,
            "current_activity": {"type": "reward", "frontend_component": "SessionCelebration", "payload": packet},
            "next_recommended_activity": {"type": "next_concept", "label": "Continue journey", "reason": "Reward state updated after learning activity."},
            "guide_message": "You're building a learning streak. Keep going!",
            "backend_connected": True,
        })
    except Exception as exc:
        return api_response(status="warning", module=module, fallback_used=True, reason=f"{type(exc).__name__}: {exc}")
