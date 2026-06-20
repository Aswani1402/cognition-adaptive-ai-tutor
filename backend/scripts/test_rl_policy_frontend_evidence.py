from __future__ import annotations

from scripts.production_readiness_checks import assert_policy_and_xai


def main() -> None:
    assert_policy_and_xai()
    print("rl policy frontend evidence test success")


if __name__ == "__main__":
    main()
