from __future__ import annotations

from scripts.production_readiness_checks import assert_auth_db_secure, register_only


def main() -> None:
    setup = register_only()
    auth = setup["auth"]
    assert_auth_db_secure(str(auth["user_id"]), str(auth["learner_id"]))
    print("auth user profile production test success")


if __name__ == "__main__":
    main()
