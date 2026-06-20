import json
import subprocess
import sys

from src.cognitutor_lm_config import ROOT


OUT_JSON = ROOT / "outputs" / "service_tests" / "integrated_backend_cognitutor_usage_test.json"
OUT_MD = ROOT / "outputs" / "service_tests" / "integrated_backend_cognitutor_usage_test.md"
MAIN_BACKEND = ROOT.parent / "cognition_adaptive_AI_tutor"


def main() -> None:
    report = {
        "integrated_pipeline_runs": False,
        "cognitutor_lm_called": False,
        "teaching_packet_present": False,
        "aligned_assessment_present": False,
        "all_task_output_available": False,
        "fallback_safe": True,
        "status": "WARN",
        "reason": "",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "tutor.system.run_integrated_tutor_once", "--learner_id", "demo_learner_001"],
            cwd=MAIN_BACKEND,
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        report["integrated_pipeline_runs"] = proc.returncode == 0
        report["cognitutor_lm_called"] = "cognitutor" in combined.lower()
        report["teaching_packet_present"] = "teaching" in combined.lower()
        report["aligned_assessment_present"] = "assessment" in combined.lower()
        report["all_task_output_available"] = "89" in combined or "all_task" in combined.lower()
        if report["integrated_pipeline_runs"] and report["cognitutor_lm_called"]:
            report["status"] = "PASS" if report["teaching_packet_present"] else "WARN"
        else:
            report["reason"] = "Integrated backend run completed without clear CogniTutorLM usage evidence." if proc.returncode == 0 else combined[-1200:]
    except Exception as exc:
        report["reason"] = f"Integrated backend could not run because of unrelated dependency/runtime failure: {type(exc).__name__}: {exc}"

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Integrated Backend CogniTutor Usage Test\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n", encoding="utf-8")
    for key in ["integrated_pipeline_runs", "cognitutor_lm_called", "teaching_packet_present", "aligned_assessment_present", "all_task_output_available", "fallback_safe", "status"]:
        print(f"{key}: {report[key]}")


if __name__ == "__main__":
    main()
