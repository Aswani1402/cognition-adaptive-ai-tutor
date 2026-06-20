from __future__ import annotations

from scripts.production_readiness_checks import assert_assessment_coverage


def main() -> None:
    assert_assessment_coverage()
    print("assessment type coverage production test success")


if __name__ == "__main__":
    main()
