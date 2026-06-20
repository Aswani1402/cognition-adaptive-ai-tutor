from scripts.pretrained_track_utils import REPO_ROOT, import_available, write_json, write_md


REQUIRED = ["torch", "transformers"]
OPTIONAL = ["datasets", "peft", "accelerate", "sentencepiece", "tokenizers", "pandas", "numpy", "sklearn"]


def main() -> None:
    imports = {name: import_available(name) for name in REQUIRED + OPTIONAL}
    missing_required = [name for name in REQUIRED if not imports[name]["available"]]
    missing_optional = [name for name in OPTIONAL if not imports[name]["available"]]
    status = "FAIL" if missing_required else ("WARN" if missing_optional else "PASS")
    data = {
        "status": status,
        "required_dependencies": REQUIRED,
        "optional_dependencies": OPTIONAL,
        "imports": imports,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }
    write_json(REPO_ROOT / "outputs/inspection/pretrained_finetuning_environment_check.json", data)
    write_md(
        REPO_ROOT / "outputs/inspection/pretrained_finetuning_environment_check.md",
        "Pretrained Fine-Tuning Track Environment Check",
        {
            "Status": status,
            "Missing Required": missing_required,
            "Missing Optional": missing_optional,
            "Import Results": {k: v for k, v in imports.items()},
        },
    )
    print(status, "environment check saved")


if __name__ == "__main__":
    main()

