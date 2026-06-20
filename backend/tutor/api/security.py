from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


HASH_ALGORITHM = "pbkdf2_sha256"
AUTH_MODE = "pbkdf2_local"
PBKDF2_ITERATIONS = 120_000
TOKEN_VERSION = "local_v1"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _secret_key() -> bytes:
    configured = os.environ.get("COGNITUTOR_AUTH_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")
    return b"cognitutor-local-dev-auth-secret-change-before-deployment"


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{HASH_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_digest = str(password_hash or "").split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(_b64url_encode(actual), expected_digest)
    except Exception:
        return False


def create_session_token(user_id: str, learner_id: str) -> str:
    payload = {
        "version": TOKEN_VERSION,
        "user_id": str(user_id),
        "learner_id": str(learner_id),
        "issued_at": int(time.time()),
        "nonce": secrets.token_urlsafe(12),
    }
    payload_raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_raw)
    signature = hmac.new(_secret_key(), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def verify_session_token(token: str) -> dict[str, Any]:
    try:
        payload_part, signature_part = str(token or "").split(".", 1)
        expected_signature = hmac.new(
            _secret_key(),
            payload_part.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_b64url_encode(expected_signature), signature_part):
            return {"valid": False, "reason": "Invalid token signature."}
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
        if payload.get("version") != TOKEN_VERSION:
            return {"valid": False, "reason": "Unsupported token version."}
        return {
            "valid": True,
            "user_id": payload.get("user_id"),
            "learner_id": payload.get("learner_id"),
            "issued_at": payload.get("issued_at"),
            "version": payload.get("version"),
        }
    except Exception as exc:
        return {"valid": False, "reason": f"{type(exc).__name__}: invalid token."}


def is_secure_password_hash(password_hash: str | None) -> bool:
    return str(password_hash or "").startswith(f"{HASH_ALGORITHM}$")
