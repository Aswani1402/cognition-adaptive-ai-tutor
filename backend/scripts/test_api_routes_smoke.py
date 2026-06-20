from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


JSON_REPORT = Path("evaluation_outputs/json/api_routes_smoke_report.json")
MD_REPORT = Path("evaluation_outputs/reports/api_routes_smoke_report.md")


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# API Routes Smoke Report",
        "",
        f"- Status: {report['status']}",
        f"- Module: {report['module']}",
        f"- Passed checks: {report['passed_count']}",
        f"- Failed checks: {report['failed_count']}",
        f"- Warning checks: {report['warning_count']}",
        "",
        "## Route Checks",
    ]
    for item in report["checks"]:
        lines.append(f"- {item['name']}: {item['status']} ({item.get('http_status', 'n/a')})")
        if item.get("reason"):
            lines.append(f"  - Reason: {item['reason']}")
    lines.extend(
        [
            "",
            "## Limitations",
            "- Authentication uses local salted PBKDF2 password hashing and token-ready responses, but not full production OAuth.",
            "- API routes are thin backend wrappers; production deployment, CORS policy, refresh/logout flow, and API gateway hardening remain pending.",
            "- Optional modules return warning/fallback responses instead of crashing when report-time services are unavailable.",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record(checks: list[dict[str, Any]], name: str, response: Any = None, required_keys: list[str] | None = None) -> dict[str, Any]:
    required_keys = required_keys or []
    item: dict[str, Any] = {"name": name, "status": "success", "http_status": getattr(response, "status_code", None)}
    try:
        if response is None:
            raise AssertionError("No response object.")
        data = response.json()
        item["response_status"] = data.get("status")
        if response.status_code != 200:
            raise AssertionError(f"HTTP {response.status_code}")
        if data.get("status") not in {"success", "warning", "not_found"}:
            raise AssertionError(f"Unexpected status {data.get('status')}")
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise AssertionError(f"Missing response keys: {missing}")
        if data.get("status") == "warning":
            item["status"] = "warning"
            item["reason"] = data.get("reason", "Route returned explicit warning fallback.")
    except Exception as exc:
        item["status"] = "failed"
        item["reason"] = f"{type(exc).__name__}: {exc}"
    checks.append(item)
    return item


def run_smoke() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        from fastapi.testclient import TestClient
        from tutor.api.app import app
    except Exception as exc:
        report = {
            "status": "warning",
            "module": "api_routes_smoke_test",
            "passed_count": 0,
            "failed_count": 1,
            "warning_count": 0,
            "checks": [{"name": "app imports", "status": "failed", "reason": f"{type(exc).__name__}: {exc}"}],
        }
        _write_reports(report)
        return report

    client = TestClient(app)
    checks.append({"name": "app imports", "status": "success"})

    suffix = int(time.time() * 1000)
    email = f"api_smoke_{suffix}@example.com"
    password = "demo-pass-123"
    learner_id = ""

    health = client.get("/health")
    _record(checks, "GET /health", health, ["status"])

    register = client.post("/auth/register", json={"name": "API Smoke Learner", "email": email, "password": password})
    reg_item = _record(checks, "POST /auth/register", register, ["user_id", "learner_id", "app_learner_code", "name", "email", "active_subject", "current_concept", "current_difficulty"])
    if reg_item["status"] in {"success", "warning"}:
        learner_id = register.json().get("learner_id", "")
        if not str(learner_id).startswith("LNR-"):
            checks.append({"name": "registered learner uses app learner code", "status": "failed", "reason": f"Unexpected learner_id: {learner_id}"})

    login = client.post("/auth/login", json={"email": email, "password": password})
    login_item = _record(checks, "POST /auth/login", login, ["user_id", "learner_id", "app_learner_code", "name", "email", "active_subject", "current_concept", "current_difficulty"])
    if login_item["status"] in {"success", "warning"} and login.json().get("learner_id") != learner_id:
        checks.append({"name": "login returns same learner code", "status": "failed", "reason": "Login learner_id did not match register learner_id."})

    if learner_id:
        client.post(
            "/learner/session",
            json={
                "learner_id": learner_id,
                "subject": "Python",
                "concept_id": "variables",
                "concept_name": "Variables",
                "teaching_view": "revision_view",
                "difficulty": "easy",
                "active_session_packet": {"session_id": f"api_smoke_session_{suffix}"},
            },
        )
        _record(checks, f"GET /learner/context/{learner_id}", client.get(f"/learner/context/{learner_id}"), ["learner_id"])
        _record(checks, f"GET /learner/session/{learner_id}", client.get(f"/learner/session/{learner_id}"), ["learner_id"])

    adaptive_learner_id = learner_id
    _record(
        checks,
        f"GET /tutor/adaptive-session/{adaptive_learner_id}",
        client.get(f"/tutor/adaptive-session/{adaptive_learner_id}?reward_dry_run=true"),
        ["learner_id"],
    )

    _record(
        checks,
        "POST /answer/submit",
        client.post(
            "/answer/submit",
            json={
                "learner_id": learner_id or adaptive_learner_id,
                "concept_id": "variables",
                "concept_name": "Variables",
                "domain": "Python",
                "question_type": "mcq",
                "answer": "A",
                "question": {"question_id": "api_smoke_mcq", "expected_answer": "A", "prompt": "Which option is correct?"},
            },
        ),
        ["score", "label", "feedback"],
    )

    _record(
        checks,
        "POST /code/run",
        client.post("/code/run", json={"code": "print('hello')", "expected_output": "hello"}),
        ["stdout", "status", "score"],
    )

    _record(
        checks,
        "POST /doubt/ask",
        client.post(
            "/doubt/ask",
            json={
                "learner_id": learner_id or adaptive_learner_id,
                "doubt_text": "I do not understand Python variables",
                "concept_id": "variables",
                "concept_name": "Variables",
                "domain": "Python",
            },
        ),
        ["intent", "confidence"],
    )

    active_learner = learner_id or adaptive_learner_id
    _record(checks, f"GET /revision/{active_learner}", client.get(f"/revision/{active_learner}"), ["learner_id"])
    _record(checks, f"GET /reward/{active_learner}", client.get(f"/reward/{active_learner}"), ["learner_id"])
    _record(checks, f"GET /xai/{adaptive_learner_id}", client.get(f"/xai/{adaptive_learner_id}"), ["learner_id"])
    _record(checks, f"GET /path/{active_learner}", client.get(f"/path/{active_learner}"), ["learner_id"])

    failed_count = sum(1 for item in checks if item["status"] == "failed")
    warning_count = sum(1 for item in checks if item["status"] == "warning")
    passed_count = sum(1 for item in checks if item["status"] == "success")
    status = "success" if failed_count == 0 else "warning"
    report = {
        "status": status,
        "module": "api_routes_smoke_test",
        "passed_count": passed_count,
        "failed_count": failed_count,
        "warning_count": warning_count,
        "checks": checks,
    }
    _write_reports(report)
    return report


def main() -> None:
    report = run_smoke()
    print(f"STATUS: {report['status']}")
    print("MODULE: api_routes_smoke_test")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
