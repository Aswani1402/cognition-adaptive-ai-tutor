from __future__ import annotations

from scripts.production_readiness_checks import assert_db_persistence_after_answer


def main() -> None:
    assert_db_persistence_after_answer()
    print("behaviour state db persistence test success")


if __name__ == "__main__":
    main()
