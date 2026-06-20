from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation_outputs" / "final_evaluation"
JSON_OUT = OUT / "json" / "integrated_tutor_cognitutor_final_evaluation.json"
MD_OUT = OUT / "reports" / "integrated_tutor_cognitutor_final_evaluation.md"


def extract_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    return json.loads(stdout[start:end + 1])


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def main() -> None:
    for directory in [OUT / "json", OUT / "reports"]:
        directory.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "tutor.system.run_integrated_tutor_once", "--learner_id", "demo_learner_001"]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
    output = extract_json(proc.stdout) if proc.returncode == 0 else {}
    product = output.get("cognitutor_lm_product_output") or nested(output, "cognitutor_lm_output", "cognitutor_lm_product_output") or {}
    lm = output.get("cognitutor_lm_output") or {}
    voice_bundle = output.get("voice_script_bundle") or {}
    assessment = output.get("assessment") or {}
    notebook = output.get("learner_notebook_memory_output") or {}
    reward = output.get("progression_reward_output") or output.get("reward_persistence_output") or {}
    xai = output.get("xai") or output.get("xai_output") or output.get("xai_reflection_output") or {}
    behaviour = output.get("module_outputs", {}).get("behaviour_state") or output.get("behaviour_state") or {}

    product_assessment_count = len(product.get("assessment_bank") or [])
    old_assessment_count = len(assessment.get("questions") or assessment.get("assessment_items") or [])
    checks = {
        "command_runs": proc.returncode == 0,
        "cognitutor_lm_status_success": lm.get("status") == "success" or product.get("status") == "success",
        "cognitutor_lm_assessment_count_ge_17": product_assessment_count >= 17,
        "voice_script_status_success": (voice_bundle.get("status") == "success") or bool(product.get("voice_script")),
        "voice_script_tts_ready_true": voice_bundle.get("tts_ready") is True or nested(product, "voice_script", "audio_ready") is True or nested(product, "audio_overview", "audio_ready") is True,
        "assessment_frontend_ready_true": assessment.get("frontend_ready") is True or product.get("frontend_ready") is True,
        "product_output_exists": bool(product),
        "notebook_summary_exists": bool(notebook.get("notebook_summary") or nested(product, "notebook", "notebook_summary")),
        "next_practice_queue_exists": isinstance(notebook.get("next_practice_queue"), list) or bool(product.get("next_practice_queue")),
        "reward_status_exists": bool(reward.get("status") or reward.get("reward_state") or reward.get("progression_result")),
        "xai_fields_exist": bool(xai.get("status") or xai.get("explanation_text") or xai.get("evidence") or xai.get("data")),
        "behaviour_state_exists": bool(behaviour),
    }
    warnings = {}
    if old_assessment_count and old_assessment_count < 17 and product_assessment_count >= 17:
        warnings["old_pipeline_assessment_types_limited"] = "WARN"
    status = "PASS" if all(checks.values()) else ("WARN" if checks["command_runs"] and checks["product_output_exists"] else "FAIL")
    report = {
        "evaluation_name": "integrated_tutor_cognitutor_final_evaluation",
        "status": status,
        "command": " ".join(command),
        "returncode": proc.returncode,
        "checks": checks,
        "warnings": warnings,
        "cognitutor_lm_status": lm.get("status") or product.get("status"),
        "cognitutor_lm_assessment_count": product_assessment_count,
        "old_pipeline_assessment_count": old_assessment_count,
        "product_output_assessment_count_status": "PASS" if product_assessment_count >= 17 else "FAIL",
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_OUT.write_text(
        "\n".join([
            "# Integrated Tutor CogniTutor Final Evaluation",
            "",
            f"- status: {status}",
            f"- command_runs: {checks['command_runs']}",
            f"- cognitutor_lm_status: {report['cognitutor_lm_status']}",
            f"- cognitutor_lm_assessment_count: {product_assessment_count}",
            f"- product_output_assessment_count_status: {report['product_output_assessment_count_status']}",
            f"- warnings: {warnings}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "json": str(JSON_OUT)}, indent=2))


if __name__ == "__main__":
    main()
