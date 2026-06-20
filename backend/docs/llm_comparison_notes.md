# LLM Comparison Notes

## Sanvia Folder Structure Summary
- Project path: `C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\fine_tuing_llm\sanvia_finetuning`
- Folder exists: `True`
- Detected inference scripts: `cogni_lm/generate.py, cogni_lm/test_model.py`
- Detected config files: `models/llm_finetuned/qwen_coder_05b_lora/adapter_config.json, models/llm_finetuned/qwen_coder_05b_lora/checkpoint-20/adapter_config.json, models/llm_finetuned/smollm2_135m_lora/adapter_config.json, models/llm_finetuned/smollm2_135m_lora/checkpoint-20/adapter_config.json`

## Detected Model Artifacts
- HuggingFace full local model folders: `none`
- LoRA adapter folders: `models/llm_finetuned/qwen_coder_05b_lora, models/llm_finetuned/qwen_coder_05b_lora/checkpoint-20, models/llm_finetuned/smollm2_135m_lora, models/llm_finetuned/smollm2_135m_lora/checkpoint-20`

## Detected Inference Method
- Sanvia includes `tutor/llm_finetune/pretrained_generator.py` and `model_loader.py`.
- The loader applies a LoRA adapter to a configured base model and supports offline mode.

## Runnable Status
- Available: `False`
- Reason: `base_model_path_missing_or_invalid`

## Missing Requirements
- A complete local base model path is required for LoRA inference when external downloads are disabled.
- `transformers`, `torch`, and `peft` are required only if Sanvia local inference is attempted.

## Safe Integration Decision
- Do not replace the current backend generation pipeline.
- Use Sanvia only as an optional comparison service when local model loading succeeds.
- Keep template/RAG fallback active for safety.
