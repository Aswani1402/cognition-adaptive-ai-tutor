from __future__ import annotations


def main() -> None:
    from tutor.system.agentic_orchestrator import SafeTutorOrchestrator, write_agentic_orchestrator_upgrade_report

    output = SafeTutorOrchestrator().run(
        {
            "learner_id": "agentic_test_learner",
            "subject": "Python",
            "concept_id": "P1",
            "concept_name": "Variables",
            "difficulty": "easy",
            "activity_type": "lesson",
            "behaviour_payload": {"confidence": 0.7, "time_taken_sec": 20},
        }
    )
    assert output["orchestrator_type"] == "safe_tutor_orchestrator"
    assert output["is_fully_autonomous"] is False
    assert output["safety_controlled"] is True
    assert len(output["trace"]) >= 12
    assert output["agentic_trace"]["stage_count"] == len(output["trace"])
    report = write_agentic_orchestrator_upgrade_report(output)
    assert report["status"] == "success"
    print("agentic orchestrator test success")
    print("stage_count:", len(output["trace"]))
    print("report:", report["md_report"])


if __name__ == "__main__":
    main()
