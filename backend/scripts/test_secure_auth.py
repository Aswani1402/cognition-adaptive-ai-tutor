from __future__ import annotations

import sqlite3
import importlib
import time
from typing import Any

from fastapi.testclient import TestClient

from tutor.api.app import app
from tutor.api.dependencies import connect
from tutor.api.security import (
    AUTH_MODE,
    HASH_ALGORITHM,
    create_session_token,
    hash_password,
    is_secure_password_hash,
    verify_password,
    verify_session_token,
)


def run_secure_auth_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {}

    raw_password = "SecurePass123!"
    password_hash = hash_password(raw_password)
    checks["hash_password_not_plaintext"] = password_hash != raw_password
    checks["hash_algorithm"] = HASH_ALGORITHM
    checks["verify_password_correct"] = verify_password(raw_password, password_hash)
    checks["verify_password_wrong"] = not verify_password("WrongPass123!", password_hash)

    token = create_session_token("user_test", "learner_test")
    decoded = verify_session_token(token)
    checks["token_created"] = bool(token)
    checks["token_decoded"] = decoded.get("valid") is True and decoded.get("user_id") == "user_test"

    client = TestClient(app)
    suffix = int(time.time() * 1000)
    email = f"secure_auth_{suffix}@example.com"
    register_payload = {
        "name": "Secure Auth Learner",
        "email": email,
        "password": raw_password,
    }

    register_response = client.post("/auth/register", json=register_payload)
    register_json = register_response.json()
    checks["register_http_status"] = register_response.status_code
    checks["register_test_status"] = (
        register_response.status_code == 200
        and register_json.get("status") == "success"
        and register_json.get("access_token")
        and register_json.get("token_type") == "bearer"
        and register_json.get("auth_mode") == AUTH_MODE
    )

    stored_hash = ""
    conn = connect()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
        stored_hash = row["password_hash"] if row else ""
    finally:
        conn.close()

    checks["register_stored_password_hash"] = is_secure_password_hash(stored_hash)
    checks["password_plaintext_stored"] = stored_hash == raw_password

    login_response = client.post("/auth/login", json={"email": email, "password": raw_password})
    login_json = login_response.json()
    checks["login_http_status"] = login_response.status_code
    checks["login_test_status"] = (
        login_response.status_code == 200
        and login_json.get("status") == "success"
        and login_json.get("access_token")
        and login_json.get("token_type") == "bearer"
        and login_json.get("auth_mode") == AUTH_MODE
    )

    wrong_response = client.post("/auth/login", json={"email": email, "password": "WrongPass123!"})
    checks["wrong_password_blocked"] = wrong_response.status_code == 401

    duplicate_response = client.post("/auth/register", json=register_payload)
    duplicate_json = duplicate_response.json()
    checks["duplicate_email_handled"] = (
        duplicate_response.status_code == 200
        and duplicate_json.get("status") == "error"
        and duplicate_json.get("created") is False
    )

    try:
        api_app = importlib.import_module("tutor.api.app")

        checks["api_smoke_import"] = hasattr(api_app, "app")
    except Exception:
        checks["api_smoke_import"] = False

    checks["register_response"] = register_json
    checks["login_response"] = login_json
    return checks


def main() -> None:
    checks = run_secure_auth_checks()
    assert checks["hash_password_not_plaintext"]
    assert checks["verify_password_correct"]
    assert checks["verify_password_wrong"]
    assert checks["token_created"]
    assert checks["token_decoded"]
    assert checks["register_test_status"]
    assert checks["register_stored_password_hash"]
    assert checks["password_plaintext_stored"] is False
    assert checks["login_test_status"]
    assert checks["wrong_password_blocked"]
    assert checks["duplicate_email_handled"]
    assert checks["api_smoke_import"]

    print("STATUS: success")
    print("MODULE: secure_auth_test")


if __name__ == "__main__":
    main()
