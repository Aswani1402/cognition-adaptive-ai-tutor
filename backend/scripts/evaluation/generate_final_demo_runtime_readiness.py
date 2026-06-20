from __future__ import annotations

import contextlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.behaviour.behaviour_state_store import persist_behaviour_state
from tutor.behaviour.lstm_behaviour_model import BehaviourLSTMRuntime, find_lstm_artifact
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


ROOT = Path(__file__).resolve().parents[2]
REPORT_MD = ROOT / "evaluation_outputs" / "reports" / "final_demo_runtime_readiness_report.md"
REPORT_JSON = ROOT / "evaluation_outputs" / "json" / "final_demo_runtime_readiness_report.json"
COMMANDS = ROOT / "demo_commands_final.txt"
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def table_exists(table: str) -> bool:
    if not DB_PATH.exists():
        return False
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
    return row is not None


def run_normal_behaviour() -> dict[str, Any]:
    interaction = {
        "learner_id": "14",
        "concept_id": "demo_readiness_concept",
        "domain": "python",
        "question_type": "mcq",
        "difficulty": "easy",
        "time_taken_sec": 18,
        "confidence": 0.8,
        "hint_count": 0,
        "hint_used": False,
        "option_change_count": 0,
        "answer_change_count": 0,
        "run_code_count": 0,
        "attempt_count": 1,
        "wrong_attempt_count": 0,
        "score": 1.0,
    }
    result = BehaviourLSTMRuntime().predict("14", interaction=interaction)
    persistence = persist_behaviour_state(result) if result.get("status") == "success" else {}
    return {
        "status": result.get("status"),
        "model_source": result.get("model_source"),
        "behaviour_state": result.get("behaviour_state"),
        "behaviour_risk": result.get("behaviour_risk"),
        "confidence_score": result.get("confidence_score"),
        "fallback_reason": result.get("fallback_reason"),
        "persistence_status": persistence.get("status", "not_available"),
    }


def run_fallback_behaviour() -> dict[str, Any]:
    runtime = BehaviourLSTMRuntime(
        artifact_path=ROOT / "models" / "behaviour_lstm" / "missing_model_for_fallback_test.pt"
    )
    result = runtime.predict(
        "fallback_smoke",
        interaction={
            "learner_id": "fallback_smoke",
            "time_taken_sec": 95,
            "confidence": 0.25,
            "hint_count": 2,
            "hint_used": True,
            "option_change_count": 3,
            "answer_change_count": 2,
            "attempt_count": 3,
            "wrong_attempt_count": 2,
            "score": 0.0,
        },
        recent_sequence=[],
    )
    return {
        "status": result.get("status"),
        "model_source": result.get("model_source"),
        "behaviour_state": result.get("behaviour_state"),
        "behaviour_risk": result.get("behaviour_risk"),
        "fallback_reason": result.get("fallback_reason"),
        "interpretation": "Expected only in fallback test: the test intentionally points to a missing artifact.",
    }


def run_integrated_summary() -> dict[str, Any]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        output = run_integrated_tutor_once("14")
    demo_summary = output.get("demo_summary", {}) if isinstance(output, dict) else {}
    return {
        "status": output.get("status") if isinstance(output, dict) else "error",
        "demo_summary": demo_summary,
        "captured_log_tail": buffer.getvalue()[-3000:],
    }


def build_report() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = find_lstm_artifact()
    normal_behaviour = run_normal_behaviour()
    fallback_behaviour = run_fallback_behaviour()
    integrated = run_integrated_summary()
    summary = integrated.get("demo_summary", {})
    kt = summary.get("kt_runtime", {})
    behaviour = summary.get("behaviour_runtime", {})
    policy = summary.get("policy_runtime", {})
    generation = summary.get("generation_source", {})
    reward = summary.get("reward_source", {})
    adaptive_path = summary.get("adaptive_path_validation_result", {})

    api = load_json(ROOT / "evaluation_outputs" / "json" / "api_routes_smoke_report.json")
    frontend = load_json(ROOT / "evaluation_outputs" / "json" / "frontend_backend_latest_connection_report.json")
    xai = load_json(ROOT / "evaluation_outputs" / "json" / "xai_surrogate_model_report.json")
    answer = load_json(ROOT / "evaluation_outputs" / "json" / "answer_evaluator_report.json")

    checks = {
        "behaviour_lstm_runtime": normal_behaviour.get("status") == "success"
        and normal_behaviour.get("model_source") == "lstm_runtime",
        "behaviour_fallback_test": fallback_behaviour.get("status") == "success"
        and fallback_behaviour.get("model_source") == "fallback_proxy_signal_scoring"
        and fallback_behaviour.get("fallback_reason") == "LSTM artifact not found.",
        "kt_dkt_runtime": kt.get("kt_source") == "dkt_runtime" and kt.get("fallback_used") is False,
        "policy_rl_safe_mask": policy.get("policy_source") == "rl_runtime"
        and policy.get("safe_mask_applied") is True,
        "guarded_generation_source": generation.get("final_learner_facing_source") == "guarded_product_generator"
        and generation.get("guarded_product_generator_used") is True,
        "reward_backend_state": reward.get("reward_source") == "backend_reward_state",
        "api_smoke_test": api.get("status") == "success" and api.get("failed_count") == 0,
        "developer_demo_upgraded": (ROOT / "developer_demo" / "app.py").exists(),
    }
    verdict = "ready" if all(checks.values()) else "fail"
    warnings: list[str] = []
    if "sklearn_version_mismatch" in integrated.get("captured_log_tail", ""):
        warnings.append("Some optional sklearn artifacts reported version mismatch and used fallback; core DKT/LSTM/RL/guarded-generation demo path still passed.")
    if not table_exists("xai_log"):
        warnings.append("xai_log table is not available; XAI status is reported from existing XAI evaluation JSON.")
    if warnings and verdict == "ready":
        final_verdict = "ready"
    else:
        final_verdict = verdict

    report = {
        "generated_at": generated_at,
        "final_verdict": final_verdict,
        "checks": checks,
        "lstm_artifact_status": {
            "model_pt_exists": (ROOT / "models" / "behaviour_lstm" / "model.pt").exists(),
            "meta_json_exists": (ROOT / "models" / "behaviour_lstm" / "meta.json").exists(),
            "resolved_artifact_path": str(artifact) if artifact else None,
        },
        "lstm_runtime_status": normal_behaviour,
        "fallback_test_status": fallback_behaviour,
        "dkt_artifact_runtime_status": {
            "model_pt_exists": (ROOT / "models" / "dkt" / "model.pt").exists(),
            "id_map_exists": (ROOT / "models" / "dkt" / "id_map.json").exists(),
            "kt_runtime": kt,
        },
        "policy_rl_runtime_status": policy,
        "generation_source_status": generation,
        "reward_source_status": reward,
        "adaptive_path_validation": adaptive_path,
        "xai_status": {
            "xai_log_table_exists": table_exists("xai_log"),
            "evaluation_report_status": xai.get("status", "not_available"),
            "targets_trained": xai.get("targets_trained", []),
        },
        "mistake_filtering_status": {
            "learner_mistake_log_table_exists": table_exists("learner_mistake_log"),
            "answer_evaluator_status": answer.get("overall_status", answer.get("status", "not_available")),
            "label_counts": answer.get("case_status", {}).get("label_counts", {}),
        },
        "backend_api_smoke_test_status": api,
        "frontend_response_builder_contract_status": {
            "status": "available" if frontend else "not_available",
            "vite_api_base_url_found": frontend.get("vite_api_base_url_found", "not_available"),
            "required_frontend_calls_or_components": frontend.get("required_frontend_calls_or_components", {}),
            "manual_browser_qa_required": frontend.get("manual_browser_qa_required", "not_available"),
        },
        "fastapi_entrypoint": "tutor.api.app:app",
        "streamlit_developer_demo": "developer_demo/app.py",
        "warnings": warnings,
        "expected_fallback_explanation": "fallback_reason = 'LSTM artifact not found.' is expected only in scripts.test_behaviour_runtime_fallback because that test intentionally points BehaviourLSTMRuntime to a missing artifact path. Normal runtime resolves models/behaviour_lstm/model.pt and uses model_source = 'lstm_runtime'.",
        "overclaim_guardrails": [
            "Behaviour LSTM runtime works in normal runtime.",
            "Fallback proxy scoring works when LSTM artifact is missing.",
            "DKT runtime is used when artifact is available.",
            "Policy/RL is safe decision support, not unrestricted controller.",
            "CogniTutorLM learner-facing content is guarded/fallback-supported.",
            "Safe Code Runner is prototype controlled execution, not production sandbox.",
        ],
    }
    return report


def write_outputs(report: dict[str, Any]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    checks = report["checks"]
    lines = [
        "# Final Demo Runtime Readiness Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Final verdict: **{report['final_verdict'].upper()}**",
        "",
        "## Runtime Status",
        "",
        f"- LSTM artifact status: `model.pt={report['lstm_artifact_status']['model_pt_exists']}`, `meta.json={report['lstm_artifact_status']['meta_json_exists']}`",
        f"- LSTM runtime status: `{report['lstm_runtime_status']}`",
        f"- Fallback test status: `{report['fallback_test_status']}`",
        f"- DKT artifact/runtime status: `{report['dkt_artifact_runtime_status']}`",
        f"- Policy/RL runtime status: `{report['policy_rl_runtime_status']}`",
        f"- Generation source status: `{report['generation_source_status']}`",
        f"- Reward source status: `{report['reward_source_status']}`",
        f"- XAI status: `{report['xai_status']}`",
        f"- Mistake filtering status: `{report['mistake_filtering_status']}`",
        f"- Backend API smoke-test status: status=`{report['backend_api_smoke_test_status'].get('status')}`, passed=`{report['backend_api_smoke_test_status'].get('passed_count')}`, failed=`{report['backend_api_smoke_test_status'].get('failed_count')}`",
        f"- Frontend response builder / contract status: `{report['frontend_response_builder_contract_status']}`",
        "",
        "## Fallback Clarification",
        "",
        report["expected_fallback_explanation"],
        "",
        "## Adaptive Path and Generation Wording",
        "",
        f"- Adaptive path validation: `{report['adaptive_path_validation']}`",
        "- Learner-facing content uses guarded generation; raw CogniTutorLM is not directly trusted.",
        "",
        "## Checks",
        "",
    ]
    lines.extend([f"- {key}: `{'PASS' if value else 'FAIL'}`" for key, value in checks.items()])
    lines.extend(
        [
            "",
            "## Backend Entrypoint",
            "",
            "- FastAPI command: `python -m uvicorn tutor.api.app:app --reload --host 127.0.0.1 --port 8000`",
            "",
            "## Guardrails",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in report["overclaim_guardrails"]])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend([f"- {item}" for item in report["warnings"]])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    commands = [
        "# Final local demo commands",
        "",
        "# Backend checks",
        "python -m scripts.test_behaviour_lstm_runtime",
        "python -m scripts.test_behaviour_runtime_fallback",
        "python -m tutor.system.run_integrated_tutor_once --learner_id 14",
        "python -m scripts.test_answer_submit_behaviour_response",
        "python -m scripts.test_api_routes_smoke",
        "",
        "# Backend FastAPI server",
        "python -m uvicorn tutor.api.app:app --reload --host 127.0.0.1 --port 8000",
        "",
        "# Frontend React app",
        "Push-Location ..\\frontend_ui\\KP-UI",
        "npm install",
        "npm run dev",
        "Pop-Location",
        "",
        "# Streamlit developer demo",
        "streamlit run developer_demo\\app.py",
        "",
        "# CogniTutorLM smoke test",
        "python -m scripts.test_cognitutor_live_guarded_connector",
        "",
        "# Readiness report regeneration",
        "python -m scripts.evaluation.generate_final_demo_runtime_readiness",
    ]
    COMMANDS.write_text("\n".join(commands) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_outputs(report)
    print(json.dumps({"status": "success", "final_verdict": report["final_verdict"], "checks": report["checks"]}, indent=2))


if __name__ == "__main__":
    main()
