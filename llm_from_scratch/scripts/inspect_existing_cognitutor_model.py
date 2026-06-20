import json
from pathlib import Path

from src.cognitutor_lm_config import ALL_TASK_OUTPUT, CORE_OUTPUT, MODEL_CHECKPOINT, PACKET_OUTPUT, RAW_GENERATED_OUTPUT, ROOT
from src.tokenizer_wrapper import TOKENIZER_MODEL_PATH

OUT_DIR = ROOT / "outputs" / "rag_llm_live_guarded" / "inspection"
OUT_JSON = OUT_DIR / "existing_model_inspection.json"
OUT_MD = OUT_DIR / "existing_model_inspection.md"


def main():
    guarded_generator_available = ALL_TASK_OUTPUT.exists() and PACKET_OUTPUT.exists()
    rag_available = (ROOT / "src" / "rag_connector.py").exists()
    api_service_available = (ROOT / "src" / "cognitutor_lm_api_service.py").exists()
    report = {
        "model_exists": MODEL_CHECKPOINT.exists(),
        "checkpoint_path": str(MODEL_CHECKPOINT) if MODEL_CHECKPOINT.exists() else None,
        "tokenizer_path": str(TOKENIZER_MODEL_PATH) if TOKENIZER_MODEL_PATH.exists() else None,
        "models_dir_files": [str(p.relative_to(ROOT)) for p in (ROOT / "models").rglob("*") if p.is_file()],
        "structured_generation_checkpoint": CORE_OUTPUT.exists(),
        "structured_model_generated_core_json": str(CORE_OUTPUT),
        "raw_live_generation_files": [str(p.relative_to(ROOT)) for p in (ROOT / "outputs" / "model_generated").glob("*raw*")],
        "raw_generated_output": str(RAW_GENERATED_OUTPUT),
        "guarded_generator_available": guarded_generator_available,
        "rag_available": rag_available,
        "api_service_available": api_service_available,
        "status": "PASS" if MODEL_CHECKPOINT.exists() and TOKENIZER_MODEL_PATH.exists() and guarded_generator_available and rag_available and api_service_available else "WARN",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Existing CogniTutorLM Model Inspection", ""]
    for key in ["model_exists", "checkpoint_path", "tokenizer_path", "guarded_generator_available", "rag_available", "api_service_available", "status"]:
        lines.append(f"- {key}: {report.get(key)}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    for key in ["model_exists", "checkpoint_path", "tokenizer_path", "guarded_generator_available", "rag_available", "api_service_available", "status"]:
        print(f"{key}: {report.get(key)}")


if __name__ == "__main__":
    main()
