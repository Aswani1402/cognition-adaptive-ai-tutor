from __future__ import annotations

from scripts.audit_full_system_module_connections import GENERATION_TASKS, build_generation_coverage, run_audit


def main() -> None:
    report = run_audit()
    rows = build_generation_coverage()
    expected_count = sum(len(items) for items in GENERATION_TASKS.values())
    assert len(rows) == expected_count, (len(rows), expected_count)
    assert report["generation_task_coverage"], "Generation coverage missing from report."
    assert any(row["Task category"] == "Voice-ready scripts" and "text only" in row["Missing/limitation"] for row in rows)
    print("STATUS: success")
    print("MODULE: test_generation_task_coverage")


if __name__ == "__main__":
    main()
