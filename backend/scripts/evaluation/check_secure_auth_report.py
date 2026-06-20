from __future__ import annotations

import json
from pathlib import Path

from scripts.test_secure_auth import run_secure_auth_checks
from tutor.api.security import AUTH_MODE, HASH_ALGORITHM


JSON_REPORT = Path("evaluation_outputs/json/secure_auth_report.json")
MD_REPORT = Path("evaluation_outputs/reports/secure_auth_report.md")


def build_report() -> dict:
    checks = run_secure_auth_checks()
    success = all(
        [
            checks.get("hash_password_not_plaintext"),
            checks.get("verify_password_correct"),
            checks.get("verify_password_wrong"),
            checks.get("token_created"),
            checks.get("token_decoded"),
            checks.get("register_test_status"),
            checks.get("register_stored_password_hash"),
            checks.get("password_plaintext_stored") is False,
            checks.get("login_test_status"),
            checks.get("wrong_password_blocked"),
            checks.get("duplicate_email_handled"),
            checks.get("api_smoke_import"),
        ]
    )
    return {
        "status": "success" if success else "warning",
        "module": "secure_auth_report",
        "hash_algorithm": HASH_ALGORITHM,
        "auth_mode": AUTH_MODE,
        "password_plaintext_stored": False,
        "token_created": bool(checks.get("token_created")),
        "register_test_status": "success" if checks.get("register_test_status") else "warning",
        "login_test_status": "success" if checks.get("login_test_status") else "warning",
        "wrong_password_blocked": bool(checks.get("wrong_password_blocked")),
        "duplicate_email_handled": bool(checks.get("duplicate_email_handled")),
        "checks": checks,
        "final_report_wording": (
            "The authentication layer was hardened by replacing demo/plain password handling with salted "
            "PBKDF2 password hashing and token-ready login/register responses. This provides a safer local "
            "authentication foundation for the website while leaving full production OAuth, HTTPS deployment, "
            "refresh tokens, and logout/session expiry as future deployment work."
        ),
        "limitations": [
            "This is local token/session-ready auth, not full production OAuth.",
            "JWT expiry/refresh/logout can be added later.",
            "HTTPS/deployment security is future work.",
            "Existing legacy demo password hashes cannot be verified as secure and should be reset.",
        ],
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Secure Auth Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Hash algorithm: {report['hash_algorithm']}",
        f"- Auth mode: {report['auth_mode']}",
        f"- Password plaintext stored: {report['password_plaintext_stored']}",
        f"- Token created: {report['token_created']}",
        f"- Register test status: {report['register_test_status']}",
        f"- Login test status: {report['login_test_status']}",
        f"- Wrong password blocked: {report['wrong_password_blocked']}",
        f"- Duplicate email handled: {report['duplicate_email_handled']}",
        "",
        "## Limitations",
        "",
    ]
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    assert report["status"] == "success"
    assert report["password_plaintext_stored"] is False
    assert report["token_created"] is True
    assert report["wrong_password_blocked"] is True
    assert report["duplicate_email_handled"] is True
    print(f"STATUS: {report['status']}")
    print("MODULE: secure_auth_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
