import sqlite3
from typing import Any, Dict, Optional

from tutor.long_term_personalization.feature_extractor import extract_features
from tutor.long_term_personalization.profile_rules import build_profile_from_features
from tutor.long_term_personalization.profile_store import load_profile, save_profile


def build_long_term_profile(
    conn: sqlite3.Connection, learner_id: str, save: bool = True
) -> Dict[str, Any]:
    features = extract_features(conn, learner_id=str(learner_id))
    profile = build_profile_from_features(features)
    if save:
        return save_profile(conn, learner_id=str(learner_id), profile=profile)
    return profile


def get_profile_for_learner(conn: sqlite3.Connection, learner_id: str) -> Optional[Dict[str, Any]]:
    return load_profile(conn, learner_id=str(learner_id))


def get_policy_teaching_bias(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    profile = load_profile(conn, learner_id=str(learner_id))
    if not profile:
        profile = build_long_term_profile(conn, learner_id=str(learner_id), save=True)
    return {
        "learner_id": str(learner_id),
        "preferred_difficulty": profile.get("preferred_difficulty", "medium"),
        "support_level": profile.get("support_level", "medium"),
        "challenge_readiness": profile.get("challenge_readiness", "medium"),
        "recommended_teaching_bias": profile.get("recommended_teaching_bias", "practice_first"),
        "explanation_need": profile.get("explanation_need", "medium"),
        "practice_need": profile.get("practice_need", "medium"),
    }

