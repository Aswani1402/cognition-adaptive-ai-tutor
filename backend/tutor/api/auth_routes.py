from __future__ import annotations

import sqlite3
import uuid
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from tutor.api.dependencies import connect, now_iso, row_to_dict, column_exists
from tutor.api.security import (
    AUTH_MODE,
    create_session_token,
    hash_password,
    is_secure_password_hash,
    verify_password,
)
from tutor.api.schemas import LoginRequest, RegisterRequest, api_response


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _ensure_auth_schema(conn: sqlite3.Connection) -> None:
    if not column_exists(conn, "users", "password_hash"):
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if not column_exists(conn, "users", "last_login_at"):
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    if not column_exists(conn, "users", "updated_at"):
        conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
    profile_columns = {
        "active_subject": "TEXT",
        "current_difficulty": "TEXT",
        "preferred_subject": "TEXT",
        "preferred_difficulty": "TEXT",
        "skill_level": "TEXT",
        "learning_goal": "TEXT",
    }
    for column_name, column_type in profile_columns.items():
        if not column_exists(conn, "learner_profile", column_name):
            conn.execute(f"ALTER TABLE learner_profile ADD COLUMN {column_name} {column_type}")
    conn.commit()


def _validate_email(email: str) -> None:
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required.")


def _generate_app_learner_id(conn: sqlite3.Connection) -> str:
    year = datetime.now(timezone.utc).year
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        suffix = "".join(alphabet[uuid.uuid4().int % len(alphabet)] for _ in range(6))
        learner_id = f"LNR-{year}-{suffix}"
        exists = conn.execute(
            "SELECT 1 FROM learner_profile WHERE learner_id = ? LIMIT 1",
            (learner_id,),
        ).fetchone()
        if not exists:
            return learner_id
    raise HTTPException(status_code=500, detail="Unable to allocate a unique learner ID.")


def _profile_identity(profile_data: dict) -> dict:
    learner_id = str(profile_data.get("learner_id") or "")
    return {
        "learner_id": learner_id,
        "app_learner_code": learner_id if learner_id.startswith("LNR-") else "",
        "name": profile_data.get("display_name") or "Learner",
        "active_subject": profile_data.get("active_subject") or profile_data.get("current_domain") or "",
        "preferred_subject": profile_data.get("preferred_subject") or "",
        "current_concept_id": profile_data.get("current_concept_id") or "",
        "current_concept_name": profile_data.get("current_concept_name") or "",
        "current_concept": profile_data.get("current_concept_name") or profile_data.get("current_concept_id") or "",
        "current_difficulty": profile_data.get("current_difficulty") or profile_data.get("preferred_difficulty") or "easy",
    }


def _profile_for_user(conn: sqlite3.Connection, user_id: str, name: str | None = None) -> dict:
    profile = conn.execute(
        "SELECT * FROM learner_profile WHERE user_id = ? ORDER BY created_at LIMIT 1",
        (user_id,),
    ).fetchone()
    profile_data = row_to_dict(profile)
    if profile_data:
        return profile_data
    now = now_iso()
    learner_id = _generate_app_learner_id(conn)
    conn.execute(
        """
        INSERT INTO learner_profile (
            learner_id, user_id, display_name, profile_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (learner_id, user_id, name or "Learner", '{"source":"api_auth_profile_backfill"}', now, now),
    )
    conn.commit()
    return {"learner_id": learner_id, "user_id": user_id, "display_name": name or "Learner"}


def _auth_payload(user_id: str, learner_id: str, **extra: object) -> dict:
    email = str(extra.get("email") or "")
    name = str(extra.get("name") or "Learner")
    active_subject = str(extra.get("active_subject") or "")
    token = create_session_token(user_id=user_id, learner_id=learner_id)
    return {
        "success": True,
        "user_id": user_id,
        "learner_id": learner_id,
        "app_learner_code": learner_id if str(learner_id).startswith("LNR-") else "",
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "auth_mode": AUTH_MODE,
        "email": email,
        "user": {"id": user_id, "name": name, "email": email, "role": "learner"},
        "next_route": "/dashboard" if active_subject else "/subjects",
        **extra,
    }


def _payload_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _normalize_register(payload: RegisterRequest) -> dict[str, str]:
    email = _payload_text(payload.email or payload.username).lower()
    name = _payload_text(payload.name or payload.username or email.split("@")[0], "Learner")
    goal = _payload_text(payload.goal or payload.learning_goal or payload.preferred_subject)
    level = _payload_text(payload.level or payload.skill_level, "beginner").lower()
    return {
        "email": email,
        "name": name,
        "goal": goal,
        "level": level,
        "preferred_subject": _payload_text(payload.preferred_subject or payload.goal),
    }


def _normalize_login(payload: LoginRequest) -> dict[str, str]:
    return {"email": _payload_text(payload.email or payload.username).lower()}


@router.post("/register")
def register(payload: RegisterRequest) -> dict:
    module = "AuthRoutes"
    normalized = _normalize_register(payload)
    email = normalized["email"]
    name = normalized["name"]
    _validate_email(email)
    logger.info("Register attempted for email=%s", email)
    now = now_iso()
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    conn = connect()
    try:
        _ensure_auth_schema(conn)
        learner_id = _generate_app_learner_id(conn)
        existing = conn.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
        if existing:
            logger.info("Register duplicate email=%s", email)
            raise HTTPException(status_code=409, detail="Account already exists. Please sign in.")

        conn.execute(
            """
            INSERT INTO users (
                user_id, username, email, password_hash, role,
                created_at, updated_at, last_login_at, is_active
            )
            VALUES (?, ?, ?, ?, 'learner', ?, ?, ?, 1)
            """,
            (user_id, email, email, hash_password(payload.password), now, now, now),
        )
        conn.execute(
            """
            INSERT INTO learner_profile (
                learner_id, user_id, display_name, active_subject, current_difficulty,
                preferred_subject, preferred_difficulty, skill_level, learning_goal,
                profile_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                user_id,
                name,
                "",
                "easy",
                normalized["preferred_subject"],
                "easy",
                normalized["level"],
                normalized["goal"],
                json.dumps({"source": "api_register", "goal": normalized["goal"], "level": normalized["level"]}),
                now,
                now,
            ),
        )
        conn.commit()
        logger.info("Register DB write success email=%s user_id=%s learner_id=%s", email, user_id, learner_id)
        return api_response(
            module=module,
            data={
                **_auth_payload(
                    user_id=user_id,
                    learner_id=learner_id,
                    name=name,
                    email=email,
                    active_subject="",
                    current_difficulty="easy",
                ),
                "created": True,
                "name": name,
                "email": email,
                "goal": normalized["goal"],
                "level": normalized["level"],
                "preferred_subject": normalized["preferred_subject"],
                "active_subject": "",
                "selected_subject": "",
                "current_concept": "",
                "current_concept_id": "",
                "current_concept_name": "",
                "current_difficulty": "easy",
                "learner_type": "Real-time App Learner",
            },
        )
    except HTTPException:
        raise
    except sqlite3.Error as exc:
        logger.exception("Register DB write failure email=%s", email)
        raise HTTPException(status_code=500, detail=f"Unable to create account. Please try again. {exc}") from exc
    finally:
        conn.close()


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    module = "AuthRoutes"
    email = _normalize_login(payload)["email"]
    _validate_email(email)
    logger.info("Login attempted for email=%s", email)
    conn = connect()
    try:
        _ensure_auth_schema(conn)
        user = conn.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
        if not user:
            logger.info("Login failed invalid email=%s", email)
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        user_data = row_to_dict(user)
        password_hash = user_data.get("password_hash")
        if not is_secure_password_hash(password_hash):
            logger.info("Login failed legacy password hash email=%s", email)
            raise HTTPException(status_code=401, detail="Legacy demo credential cannot be used until password is reset.")
        if not verify_password(payload.password, password_hash):
            logger.info("Login failed wrong password email=%s", email)
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        now = now_iso()
        if column_exists(conn, "users", "last_login_at"):
            conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?", (now, now, user_data["user_id"]))
            conn.commit()
        profile_data = _profile_for_user(conn, user_data["user_id"])
        profile_identity = _profile_identity(profile_data)
        logger.info("Login DB read success email=%s user_id=%s learner_id=%s", email, user_data.get("user_id"), profile_identity["learner_id"])
        return api_response(
            module=module,
            data=_auth_payload(
                user_id=user_data.get("user_id"),
                learner_id=profile_identity["learner_id"],
                last_login_at=now,
                name=profile_identity["name"],
                email=user_data.get("email") or email,
                app_learner_code=profile_identity["app_learner_code"],
                active_subject=profile_identity["active_subject"],
                selected_subject=profile_identity["active_subject"],
                preferred_subject=profile_identity["preferred_subject"],
                current_concept=profile_identity["current_concept"],
                current_subject=profile_identity["active_subject"],
                current_concept_id=profile_identity["current_concept_id"],
                current_concept_name=profile_identity["current_concept_name"],
                current_difficulty=profile_identity["current_difficulty"],
                learner_context=profile_data,
                learner_type="Real-time App Learner" if str(profile_identity["learner_id"]).startswith("LNR-") else "Dataset / Evaluation Learner",
            ),
        )
    except HTTPException:
        raise
    except sqlite3.Error as exc:
        logger.exception("Login DB failure email=%s", email)
        raise HTTPException(status_code=500, detail="Unable to sign in. Please try again.") from exc
    finally:
        conn.close()
