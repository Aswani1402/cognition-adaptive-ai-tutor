from __future__ import annotations

from scripts.production_readiness_checks import submit_answer


def main() -> None:
    payload = submit_answer("explanation_check")["answer_response"]
    kt = payload.get("kt_update") or {}
    for key in ["mastery_before", "mastery_after", "mastery_label", "model_used", "fallback_used"]:
        assert key in kt, kt
    print("kt production connection test success")


if __name__ == "__main__":
    main()
