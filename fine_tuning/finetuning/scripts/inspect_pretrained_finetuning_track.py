from pathlib import Path

from scripts.pretrained_track_utils import REPO_ROOT, classify_files, write_json, write_md


def main() -> None:
    classes = classify_files(REPO_ROOT)
    missing = []
    if not classes["train_scripts"]:
        missing.append("No obvious training script found")
    if not classes["inference_generation_scripts"]:
        missing.append("No obvious inference/generation script found")
    if not classes["dataset_files"]:
        missing.append("No dataset files found")
    if not classes["checkpoint_model_files"]:
        missing.append("No checkpoint/model files found")
    command = "python -m scripts.check_pretrained_finetuning_environment"
    data = {
        "status": "PASS" if classes["python_files"] else "FAIL",
        "repo_path": str(REPO_ROOT),
        **classes,
        "training_code_evidence": classes["train_scripts"],
        "inference_code_evidence": classes["inference_generation_scripts"],
        "expected_model_checkpoint": classes["checkpoint_model_files"],
        "expected_dataset": classes["dataset_files"],
        "missing_files_or_evidence": missing,
        "first_command_to_run": command,
    }
    write_json(REPO_ROOT / "outputs/inspection/pretrained_finetuning_folder_inspection.json", data)
    write_md(
        REPO_ROOT / "outputs/inspection/pretrained_finetuning_folder_inspection.md",
        "Pretrained Fine-Tuning Track Folder Inspection",
        {
            "Status": data["status"],
            "Repo Path": data["repo_path"],
            "What files exist": {k: len(v) for k, v in classes.items()},
            "Training Code": classes["train_scripts"],
            "Inference Code": classes["inference_generation_scripts"],
            "Expected Model Or Checkpoint": classes["checkpoint_model_files"],
            "Expected Dataset": classes["dataset_files"],
            "Missing Files": missing,
            "First Command": command,
        },
    )
    print(data["status"], "folder inspection saved")


if __name__ == "__main__":
    main()

