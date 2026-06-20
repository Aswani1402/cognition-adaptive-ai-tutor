from tutor.adaptation.view_performance_tracker import ViewPerformanceTracker


def main():
    tracker = ViewPerformanceTracker()

    result = tracker.log_view_result(
        learner_id=14,
        concept_id="P3",
        teaching_view="step_by_step_view",
        difficulty="easy",
        assessment_score=0.82,
        time_taken=120,
        hint_usage=1,
        engagement_score=0.78,
        mastery_before=0.35,
        mastery_after=0.52,
        metadata={
            "source": "test_run",
            "note": "Testing view performance tracking after MultiViewGenerator",
        },
    )

    print("\nLOG STATUS:", result["status"])
    print("MODULE:", result["module"])
    print("VIEW:", result["logged"]["teaching_view"])
    print("REWARD:", result["logged"]["reward"])
    print("OUTCOME:", result["logged"]["outcome_label"])

    best = tracker.get_best_view_for_learner(
        learner_id=14,
        concept_id="P3",
    )

    print("\nBEST VIEW RESULT")
    print(best)

    summary = tracker.get_view_summary(learner_id=14)

    print("\nVIEW SUMMARY")
    print(summary)


if __name__ == "__main__":
    main()