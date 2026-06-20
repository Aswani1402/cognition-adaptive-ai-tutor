from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.test_learner_answer_simulator import SAMPLE_QUESTIONS
from tutor.simulation.learner_answer_simulator import PROFILE_PARAMETERS, LearnerAnswerSimulator


JSON_REPORT = Path("evaluation_outputs/json/learner_simulator_report.json")
MD_REPORT = Path("evaluation_outputs/reports/learner_simulator_report.md")


def build_report() -> dict:
    simulator = LearnerAnswerSimulator()
    sessions = simulator.simulate_profiles(SAMPLE_QUESTIONS, seed=2026)["sessions"]
    average_score_by_profile = {}
    average_confidence_by_profile = {}
    average_time_by_profile = {}
    hint_usage_rate_by_profile = {}
    option_change_rate_by_profile = {}
    mistake_counts = Counter()
    simulated_case_count = 0

    for profile, session in sessions.items():
        summary = session["summary"]
        average_score_by_profile[profile] = summary["average_score"]
        average_confidence_by_profile[profile] = summary["average_confidence"]
        average_time_by_profile[profile] = summary["average_time_taken_sec"]
        hint_usage_rate_by_profile[profile] = summary["hint_usage_rate"]
        option_change_rate_by_profile[profile] = summary["option_change_rate"]
        simulated_case_count += len(session["answers"])
        for answer in session["answers"]:
            mistake_counts[answer["mistake_type"]] += 1

    return {
        "status": "success",
        "module": "learner_simulator_report",
        "profile_list": list(PROFILE_PARAMETERS),
        "simulated_case_count": simulated_case_count,
        "average_score_by_profile": average_score_by_profile,
        "average_confidence_by_profile": average_confidence_by_profile,
        "average_time_by_profile": average_time_by_profile,
        "hint_usage_rate_by_profile": hint_usage_rate_by_profile,
        "option_change_rate_by_profile": option_change_rate_by_profile,
        "mistake_type_distribution": dict(mistake_counts),
        "sessions": sessions,
        "final_report_wording": (
            "The learner answer simulator creates controlled learner profiles such as strong, average, weak, "
            "guessing, careless, and low-confidence learners. It generates simulated responses, confidence, "
            "timing, hint usage, and mistake patterns for backend testing. This supports multi-profile "
            "evaluation of the adaptive tutor before collecting large-scale live frontend data."
        ),
        "limitations": [
            "Simulated answers do not replace real learner data.",
            "Profile probabilities are hand-configured and should be calibrated with real usage logs later.",
            "The simulator is intended for testing, evaluation, demos, and report evidence.",
        ],
    }


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Learner Simulator Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Profiles: {', '.join(report['profile_list'])}",
        f"- Simulated case count: {report['simulated_case_count']}",
        "",
        "## Average Score by Profile",
        "",
    ]
    for profile, value in report["average_score_by_profile"].items():
        lines.append(f"- {profile}: {value}")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)

    assert report["status"] == "success"
    assert report["module"] == "learner_simulator_report"
    assert set(report["profile_list"]) == set(PROFILE_PARAMETERS)
    assert report["simulated_case_count"] == len(PROFILE_PARAMETERS) * len(SAMPLE_QUESTIONS)
    assert report["average_score_by_profile"]["strong"] > report["average_score_by_profile"]["weak"]
    assert report["limitations"]

    print(f"STATUS: {report['status']}")
    print("MODULE: learner_simulator_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
