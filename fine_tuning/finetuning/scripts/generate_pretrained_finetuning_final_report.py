from scripts.pretrained_track_utils import REPO_ROOT, read_json, write_json, write_md


def _status(path, default="MISSING"):
    data = read_json(REPO_ROOT / path) or {}
    return data.get("status", default), data


def _final_status(env, artifact, generation, backend):
    if env.get("status") == "FAIL":
        return "PENDING_DEPENDENCIES"
    if artifact.get("runtime_status") == "WARN/PENDING_LOCAL_MODEL" or artifact.get("remote_model_dependency"):
        return "PENDING_MODEL_ARTIFACTS"
    if generation.get("status") != "PASS":
        return "NOT_READY_FOR_RUNTIME"
    if backend.get("status") == "PASS":
        return "READY_FOR_RUNTIME"
    return "READY_FOR_COMPARISON"


def main() -> None:
    folder_status, folder = _status("outputs/inspection/pretrained_finetuning_folder_inspection.json")
    env_status, env = _status("outputs/inspection/pretrained_finetuning_environment_check.json")
    artifact_status, artifact = _status("outputs/inspection/pretrained_model_artifact_check.json")
    generation_status, generation = _status("outputs/evaluation/pretrained_finetuned_generation_test.json")
    comparison_status, comparison = _status("outputs/evaluation/generation_track_comparison.json")
    backend_status, backend = _status("outputs/evaluation/backend_pretrained_track_integration_check.json")
    final = _final_status(env, artifact, generation, backend)
    runtime_recommendation = "READY_FOR_RUNTIME" if final == "READY_FOR_RUNTIME" else ("COMPARISON_ONLY" if final in {"READY_FOR_COMPARISON", "PENDING_MODEL_ARTIFACTS", "NOT_READY_FOR_RUNTIME"} else "PENDING")
    data = {
        "status": "PASS",
        "final_status": final,
        "runtime_recommendation": runtime_recommendation,
        "folder_inspection": folder,
        "environment": env,
        "model_artifacts": artifact,
        "inference_runner_status": (generation.get("model_load") or {}).get("status", "unknown"),
        "generation_task_test": generation,
        "comparison": comparison,
        "backend_integration": backend,
        "limitations": [
            "The pretrained fine-tuning track is local-only and remote model download is disabled.",
            "Adapter-only LoRA artifacts require matching local base model weights before runtime use.",
            "The backend connector is comparison-only and does not replace learner-facing generation.",
        ],
        "recommended_report_wording": (
            "The pretrained fine-tuned model track is a comparison-only track until local base model/checkpoint "
            "artifacts are present, the model loads locally, and generated tutor outputs pass validation."
        ),
    }
    write_json(REPO_ROOT / "outputs/final_reports/pretrained_finetuning_track_report.json", data)
    write_md(
        REPO_ROOT / "outputs/final_reports/pretrained_finetuning_track_report.md",
        "Pretrained Fine-Tuning Track Report",
        {
            "Folder Inspection Summary": folder_status,
            "Environment Dependency Status": env_status,
            "Model Checkpoint Artifact Status": f"{artifact_status} / {artifact.get('runtime_status')}",
            "Inference Runner Status": data["inference_runner_status"],
            "Generation Task Test Results": generation_status,
            "Output Validation Results": {
                "valid_count": generation.get("valid_count", 0),
                "task_count": generation.get("task_count", 0),
                "average_quality_score": generation.get("average_quality_score", 0.0),
            },
            "Comparison With Other Generation Tracks": comparison_status,
            "Backend Integration Check": backend_status,
            "Final Status": final,
            "Runtime Recommendation": runtime_recommendation,
            "Limitations": data["limitations"],
            "Recommended Report Wording": data["recommended_report_wording"],
        },
    )
    print("PASS final report saved", final, runtime_recommendation)


if __name__ == "__main__":
    main()

