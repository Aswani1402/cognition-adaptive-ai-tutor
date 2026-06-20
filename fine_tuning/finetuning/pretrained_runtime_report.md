# Pretrained Runtime Report

Generated UTC: `2026-05-11T17:27:10.579566+00:00`
Project root: `C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\fine_tuing_llm\pretrained_finetuning`
Inspection status: `warning`

## Pretrained folder structure summary

- Folder exists: `True`
- LoRA adapter folders: `4`
- Checkpoint folders: `2`
- Full local model folders: `0`
- Merged model folders: `0`

## Adapter artifacts found

- `models/llm_finetuned/qwen_coder_05b_lora` (base: `Qwen/Qwen2.5-Coder-0.5B-Instruct`)
- `models/llm_finetuned/qwen_coder_05b_lora/checkpoint-20` (base: `Qwen/Qwen2.5-Coder-0.5B-Instruct`)
- `models/llm_finetuned/smollm2_135m_lora` (base: `HuggingFaceTB/SmolLM2-135M`)
- `models/llm_finetuned/smollm2_135m_lora/checkpoint-20` (base: `HuggingFaceTB/SmolLM2-135M`)

## Base model status

- None detected

## Merged model status

- None detected

## Inference script status

- `cogni_lm/generate.py`
- `scripts/run_pretrained_local_inference.py`
- `tutor/llm_finetune/generate_samples.py`
- `tutor/llm_finetune/generate_test.py`
- `tutor/llm_finetune/model_loader.py`
- `tutor/llm_finetune/pretrained_generator.py`

## Dataset files

- `training_data/llm_tutor/tutor_test.jsonl`
- `training_data/llm_tutor/tutor_train.jsonl`
- `training_data/llm_tutor/tutor_val.jsonl`

## Runnable status

Runnable status: unavailable. Pretrained's fine-tuned LLM folder contains LoRA adapter checkpoints and inference-related scripts, but no complete local base model or merged model folder was detected. Since external downloads are disabled, the model cannot be safely run for local comparison yet. To enable runtime comparison, the matching base model must be placed locally and configured in pretrained_inference_config.json, or the LoRA adapter must be merged into a full local model artifact.

## What is missing

What is missing: a complete matching local base model folder or merged model folder containing the required files below.

Required local model files:

- `config.json`
- `tokenizer.json or tokenizer.model`
- `tokenizer_config.json`
- `model.safetensors or pytorch_model.bin`

## Exact instructions for making it runnable

1. Place the matching base model folder inside this project or another local path.
2. Set `base_model_path` in `pretrained_inference_config.json` to that local folder.
3. Keep `local_files_only` set to `true`.
4. Run `python -m scripts.merge_lora_if_base_available` to create a merged model, or run `python -m scripts.run_pretrained_local_inference` to load base plus adapter directly.

## Comparison readiness

Comparison readiness: pending. Backend comparison should mark Pretrained as unavailable until available=true is returned by the local inference script.

## For main backend comparison

- If `available=true`, backend connector can call `scripts/run_pretrained_local_inference.py` through subprocess.
- If `available=false`, backend comparison should mark Pretrained as unavailable/pending.

## Runtime inference check

- Inference runnable: `False`
- Runtime status: `unavailable`
- Reason: `base_model_path_missing_or_invalid`
- Exact next step needed: Place the matching base model folder locally and set base_model_path in pretrained_inference_config.json, or create a merged full model folder at merged_model_path.

Pretrained's fine-tuned LLM folder contains LoRA adapter checkpoints and inference-related scripts, but no complete local base model or merged model folder was detected. Since external downloads are disabled, the model cannot be safely run for local comparison yet. To enable runtime comparison, the matching base model must be placed locally and configured in pretrained_inference_config.json, or the LoRA adapter must be merged into a full local model artifact.
