from __future__ import annotations

from scripts.production_readiness_checks import assert_auth_db_secure, assert_teaching_coverage, register_only, write_final_reports


def main() -> None:
    setup = register_only()
    assert_auth_db_secure(setup["auth"]["user_id"], setup["learner_id"])
    assert_teaching_coverage()
    write_final_reports()
    print("final production readiness test success")


if __name__ == "__main__":
    main()
