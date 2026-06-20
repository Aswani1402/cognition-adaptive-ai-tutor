from __future__ import annotations

from scripts.production_readiness_checks import assert_code_runner


def main() -> None:
    assert_code_runner()
    print("safe code runner frontend backend connection test success")


if __name__ == "__main__":
    main()
