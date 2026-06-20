from __future__ import annotations

from scripts.production_readiness_checks import assert_long_term_routes


def main() -> None:
    assert_long_term_routes()
    print("long term personalization production test success")


if __name__ == "__main__":
    main()
