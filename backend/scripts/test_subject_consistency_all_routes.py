from __future__ import annotations

from scripts.production_readiness_checks import assert_subject_consistency


def main() -> None:
    for subject in ["SQL / Database", "Python", "HTML/Web Basics", "Git", "Data Structures"]:
        assert_subject_consistency(subject)
    print("subject consistency all routes test success")


if __name__ == "__main__":
    main()
