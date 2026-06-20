import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROFILES = ["strong", "average", "weak"]
RUNS_PER_PROFILE = 100
LEARNER_ID = "14"


def run_once(profile: str, run_no: int) -> bool:
    cmd = [
        sys.executable,
        "-m",
        "tutor.system.run_integrated_tutor_once",
        "--learner_id",
        LEARNER_ID,
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
        print(f"[ERROR] profile={profile} run={run_no}")
        print(result.stderr)
        return False

    print(f"[OK] profile={profile} run={run_no}")
    return True


def main():
    total = 0
    success = 0
    failed = 0

    for profile in PROFILES:
        for i in range(1, RUNS_PER_PROFILE + 1):
            total += 1
            if run_once(profile, i):
                success += 1
            else:
                failed += 1

    print("\nRL LOG GENERATION COMPLETE")
    print("Total runs:", total)
    print("Success:", success)
    print("Failed:", failed)


if __name__ == "__main__":
    main()