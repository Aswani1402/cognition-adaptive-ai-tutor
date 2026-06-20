from __future__ import annotations

import time
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tutor.api.app import app


def main() -> None:
    client = TestClient(app)
    email = f"auth_fix_{int(time.time())}@example.com"
    password = "StrongPass123"

    register_payload = {
        "name": "Auth Fix Learner",
        "email": email,
        "password": password,
        "goal": "Python",
        "level": "Beginner",
        "preferred_subject": "Python",
    }

    registered = client.post("/auth/register", json=register_payload)
    assert registered.status_code == 200, registered.text
    register_json = registered.json()
    assert register_json["success"] is True, register_json
    assert register_json["user_id"], register_json
    assert register_json["learner_id"], register_json
    assert register_json["access_token"], register_json

    duplicate = client.post("/auth/register", json=register_payload)
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"] == "Account already exists. Please sign in."

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    login_json = login.json()
    assert login_json["success"] is True, login_json
    assert login_json["user_id"] == register_json["user_id"], login_json
    assert login_json["learner_id"] == register_json["learner_id"], login_json
    assert login_json["access_token"], login_json

    wrong_password = client.post("/auth/login", json={"email": email, "password": "WrongPass123"})
    assert wrong_password.status_code == 401, wrong_password.text
    assert wrong_password.json()["detail"] == "Invalid email or password."

    learner_id = login_json["learner_id"]
    context = client.get(f"/learner/context/{learner_id}")
    assert context.status_code == 200, context.text
    context_json = context.json()
    assert context_json["learner_id"] == learner_id, context_json
    assert "learner_profile" in context_json, context_json

    subject = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "Python"})
    assert subject.status_code == 200, subject.text
    subject_json = subject.json()
    assert subject_json["active_subject"] == "Python", subject_json
    assert subject_json["current_concept_id"], subject_json
    assert subject_json["next_route"].startswith("/lesson/"), subject_json

    print("auth register/login fix smoke test success")
    print(f"email={email}")
    print(f"user_id={login_json['user_id']}")
    print(f"learner_id={learner_id}")


if __name__ == "__main__":
    main()
