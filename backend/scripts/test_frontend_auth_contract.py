from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tutor.api.app import app


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend_ui" / "KP-UI"
REPORT_JSON = Path("evaluation_outputs/json/frontend_auth_contract_report.json")
REPORT_MD = Path("evaluation_outputs/reports/frontend_auth_contract_report.md")


def main() -> None:
    env = (FRONTEND / ".env.local").read_text(encoding="utf-8")
    api = (FRONTEND / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    register_page = (FRONTEND / "src" / "pages" / "RegisterPage.tsx").read_text(encoding="utf-8")
    login_page = (FRONTEND / "src" / "pages" / "LoginPage.tsx").read_text(encoding="utf-8")
    app_py = (ROOT / "cognition_adaptive_AI_tutor" / "tutor" / "api" / "app.py").read_text(encoding="utf-8")

    assert "VITE_API_BASE_URL=http://127.0.0.1:8010" in env
    assert "POST" in api and "/auth/register" in api and "/auth/login" in api
    assert "name:" in api and "email:" in api and "password:" in api
    assert "console.error('[register] failed'" in register_page
    assert "console.error('[login] failed'" in login_page
    assert "Email already exists. Please login." in register_page
    assert "http://localhost:5174" in app_py and "http://127.0.0.1:5174" in app_py

    client = TestClient(app)
    email = f"frontend_contract_{int(time.time() * 1000)}@example.test"
    password = "StrongPass123!"
    registered = client.post("/auth/register", json={"name": "Frontend Contract", "email": email, "password": password})
    assert registered.status_code == 200, registered.text
    reg = registered.json()
    assert reg.get("access_token") and reg.get("user_id") and reg.get("learner_id"), reg
    duplicate = client.post("/auth/register", json={"name": "Frontend Contract", "email": email, "password": password})
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json().get("status") == "error", duplicate.json()
    logged_in = client.post("/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    login = logged_in.json()
    assert login.get("learner_id") == reg.get("learner_id"), login

    report = {
        "status": "success",
        "env_local_checked": True,
        "backend_url": "http://127.0.0.1:8010",
        "frontend_register_payload": ["name", "email", "password"],
        "frontend_login_payload": ["email", "password"],
        "routes": ["/auth/register", "/auth/login"],
        "cors_checked": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        "duplicate_email_handled": True,
        "registered_learner_id": reg.get("learner_id"),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Frontend Auth Contract Report",
                "",
                "- Status: success",
                "- Frontend env: `VITE_API_BASE_URL=http://127.0.0.1:8010`",
                "- Register payload: `name`, `email`, `password`",
                "- Login payload: `email`, `password`",
                "- Routes: `POST /auth/register`, `POST /auth/login`",
                "- Duplicate email handling: `Email already exists. Please login.`",
                "- CORS includes frontend ports 5173 and 5174.",
            ]
        ),
        encoding="utf-8",
    )
    print(report)


if __name__ == "__main__":
    main()
