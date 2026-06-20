import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_profile(profile: str) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "tutor.system.run_integrated_tutor_once",
        "--learner_id",
        "14",
        "--learner_profile",
        profile,
    ]

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        return {
            "profile": profile,
            "status": "error",
            "error": result.stderr,
        }

    output = result.stdout

    json_start = output.find("{")
    json_end = output.rfind("}") + 1

    if json_start == -1 or json_end == -1:
        return {
            "profile": profile,
            "status": "error",
            "error": "No JSON found in output",
        }

    data = json.loads(output[json_start:json_end])

    evaluation = data.get("evaluation", {})
    multi = data.get("multi_evidence_output", {})
    policy = data.get("policy_output", {}).get("data", {})
    rl = data.get("rl_log_output", {})

    return {
        "profile": profile,
        "status": data.get("status"),
        "score": evaluation.get("overall_score"),
        "learning_signal": data.get("learning_signal"),
        "final_action": multi.get("final_action"),
        "next_concept_id": policy.get("next_concept_id"),
        "strategy": policy.get("strategy"),
        "difficulty": policy.get("difficulty"),
        "decision_type": policy.get("decision_type"),
        "reward": rl.get("reward"),
    }


def print_table(rows: list[dict]) -> None:
    headers = [
        "profile",
        "status",
        "score",
        "learning_signal",
        "final_action",
        "next_concept_id",
        "strategy",
        "difficulty",
        "decision_type",
        "reward",
    ]

    widths = {
        h: max(len(h), max(len(str(row.get(h, ""))) for row in rows))
        for h in headers
    }

    line = " | ".join(h.ljust(widths[h]) for h in headers)
    sep = "-+-".join("-" * widths[h] for h in headers)

    print("\nPROFILE TEST REPORT")
    print(line)
    print(sep)

    for row in rows:
        print(" | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers))


def main() -> None:
    profiles = ["strong", "average", "weak"]
    rows = [run_profile(profile) for profile in profiles]
    print_table(rows)


if __name__ == "__main__":
    main()