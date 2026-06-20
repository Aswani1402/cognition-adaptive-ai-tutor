from __future__ import annotations

import os
from pathlib import Path

from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_BASE_MODEL = (
    "Qwen/Qwen2.5-Coder-0.5B-Instruct"
)

DEFAULT_MODEL_DIR = (
    ROOT
    / "models"
    / "llm_finetuned"
    / "qwen_coder_05b_lora"
)


def load_model():

    base_model_name = os.getenv(
        "TUTOR_BASE_MODEL",
        DEFAULT_BASE_MODEL
    )

    model_dir = os.getenv(
        "TUTOR_MODEL_DIR",
        str(DEFAULT_MODEL_DIR)
    )

    offline_mode = os.getenv(
        "PRETRAINED_OFFLINE_MODE",
        "0"
    )

    model_dir = Path(model_dir)

    print("\nLoading model configuration...\n")

    print(f"Base model: {base_model_name}")
    print(f"Model directory: {model_dir}")
    print(f"Offline mode: {offline_mode}")

    # ==================================================
    # CHECK LOCAL MODEL DIRECTORY
    # ==================================================

    if not model_dir.exists():

        return {
            "status": "warning",

            "generation_status":
                "unavailable_local_model_missing",

            "model": None,

            "tokenizer": None,

            "error_message":
                f"Model directory not found: {model_dir}"
        }

    # ==================================================
    # OFFLINE MODE
    # ==================================================

    local_files_only = False

    if offline_mode == "1":

        local_files_only = True

        print("\nOffline mode enabled.")

    # ==================================================
    # LOAD TOKENIZER
    # ==================================================

    try:

        print("\nLoading tokenizer...")

        tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            local_files_only=local_files_only,
        )

        print("Tokenizer loaded.")

    except Exception as e:

        return {

            "status": "warning",

            "generation_status":
                "unavailable_remote_fetch_failed",

            "model": None,

            "tokenizer": None,

            "error_message":
                f"Tokenizer load failed: {str(e)}"
        }

    # ==================================================
    # LOAD BASE MODEL
    # ==================================================

    try:

        print("\nLoading base model...")

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            local_files_only=local_files_only,
        )

        print("Base model loaded.")

    except Exception as e:

        return {

            "status": "warning",

            "generation_status":
                "unavailable_remote_fetch_failed",

            "model": None,

            "tokenizer": tokenizer,

            "error_message":
                f"Base model load failed: {str(e)}"
        }

    # ==================================================
    # APPLY LORA ADAPTER
    # ==================================================

    try:

        print("\nApplying LoRA adapter...")

        model = PeftModel.from_pretrained(
            base_model,
            model_dir,
        )

        print("LoRA adapter loaded successfully.")

    except Exception as e:

        return {

            "status": "warning",

            "generation_status":
                "adapter_load_failed",

            "model": None,

            "tokenizer": tokenizer,

            "error_message":
                f"Adapter load failed: {str(e)}"
        }

    model.eval()

    return {

        "status": "success",

        "generation_status": "ready",

        "model": model,

        "tokenizer": tokenizer,

        "error_message": None,
    }


if __name__ == "__main__":

    result = load_model()

    print("\nLoad Result:\n")

    print(result["generation_status"])

    if result["error_message"]:
        print(result["error_message"])