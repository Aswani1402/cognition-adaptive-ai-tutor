import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List

from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


OUTPUT_DIR = Path("evaluation_outputs/json")
OUTPUT_PATH = OUTPUT_DIR / "teaching_strategy_comparison_batch_run.json"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def compact_result(output: Dict[str, Any]) -> Dict[str, Any]:
    demo_summary = output.get("demo_summary", {})

    return {
        "learner_id": output.get("learner_id"),
        "status": output.get("status", "success"),
        "final_concept": demo_summary.get("final_concept"),
        "final_strategy": demo_summary.get("final_strategy"),
        "final_difficulty": demo_summary.get("final_difficulty"),

        "teaching_view": demo_summary.get("teaching_view"),
        "assessment_types": demo_summary.get("assessment_types"),
        "progression_action": demo_summary.get("progression_action"),

        "model_teaching_view": demo_summary.get("model_teaching_view"),
        "model_progression_action": demo_summary.get("model_progression_action"),
        "model_teaching_view_confidence": demo_summary.get("model_teaching_view_confidence"),
        "teaching_strategy_agreement": demo_summary.get("teaching_strategy_agreement"),
        "model_comparison_log_status": demo_summary.get("model_comparison_log_status"),

        "evaluation_score": demo_summary.get("evaluation_score"),
        "final_action": demo_summary.get("final_action"),
    }


def run_batch(start: int, end: int) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for learner_id in range(start, end + 1):
        learner_id_str = str(learner_id)

        print(f"\nRunning learner {learner_id_str}...")

        try:
            output = run_integrated_tutor_once(learner_id=learner_id_str)
            compact = compact_result(output)
            results.append(compact)

            print(
                "OK:",
                "learner=", learner_id_str,
                "view=", compact.get("teaching_view"),
                "model_view=", compact.get("model_teaching_view"),
                "agreement=", compact.get("teaching_strategy_agreement"),
            )

        except Exception as e:
            error = {
                "learner_id": learner_id_str,
                "status": "error",
                "error": str(e),
            }
            errors.append(error)
            print("ERROR:", error)

    success_count = len(results)
    error_count = len(errors)

    agreement_values = [
        item.get("teaching_strategy_agreement")
        for item in results
        if item.get("teaching_strategy_agreement") is not None
    ]

    agreement_rate = (
        sum(1 for value in agreement_values if value is True) / len(agreement_values)
        if agreement_values
        else 0.0
    )

    report = {
        "status": "success",
        "module": "TeachingStrategyComparisonBatchRunner",
        "generated_at": now_iso(),
        "start_learner_id": start,
        "end_learner_id": end,
        "success_count": success_count,
        "error_count": error_count,
        "agreement_rate_in_batch": round(agreement_rate, 4),
        "results": results,
        "errors": errors,
    }

    return report


def save_report(report: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=30)

    args = parser.parse_args()

    report = run_batch(start=args.start, end=args.end)
    save_report(report)

    print("\nBATCH RUN COMPLETE")
    print("Success count:", report["success_count"])
    print("Error count:", report["error_count"])
    print("Agreement rate in batch:", report["agreement_rate_in_batch"])
    print("Saved:", OUTPUT_PATH)


if __name__ == "__main__":
    main()