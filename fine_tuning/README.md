<p align="center">
  <img src="../docs/assets/cognitutor-logo.svg" alt="Cognition-Adaptive AI Tutor logo and adaptive learning banner" width="100%">
</p>

# Fine Tuning and Pretrained Model Comparison

This folder contains fine-tuning and pretrained model comparison experiments for the Cognition-Adaptive AI Tutor project.

The goal of this part is to compare generated tutoring support from pretrained/fine-tuned models against CogniTutorLM from scratch, RAG-grounded content, guarded generation, and template or validated content-bank fallback.

## Purpose

This folder supports research comparison and experimentation. It helps answer:

- How does pretrained model output compare with from-scratch CogniTutorLM output?
- Does fine-tuning improve tutor-style generation?
- Does generated content follow required task format?
- Does generated content stay grounded in concept resources?
- Does generated content require repair or fallback?
- Can generated explanations, hints, revision notes, or feedback be made learner-ready?

## Important Interpretation

Fine-tuned or pretrained model output should not be directly exposed to learners without validation.

The final integrated tutor uses guarded validation and fallback before any generated output becomes learner-facing content.

## Suggested Folder Structure

```text
fine_tuning/
│
├── data/                      # Fine-tuning data or samples; usually ignored if large/private
├── scripts/                   # Training, evaluation, and conversion scripts
├── notebooks/                 # Experiments if available
├── models/                    # Fine-tuned artifacts; usually ignored
├── outputs/                   # Generated outputs; usually ignored if large
├── reports/                   # Comparison summaries
├── requirements.txt
└── README.md
```

## Possible Experiments

- prompt-based baseline generation
- fine-tuned generation
- comparison with CogniTutorLM
- comparison with template/RAG-grounded service
- validation pass/fail analysis
- fallback analysis
- task-format checking
- grounding checking
- repetition checking
- brevity/readability checking

## Setup

From this folder:

```powershell
cd fine_tuning
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Commands depend on the actual scripts. Common examples:

```powershell
python scripts/train.py
```

```powershell
python scripts/evaluate.py
```

```powershell
python scripts/compare_generation.py
```

If the scripts are named differently, check the folder contents and update this README.

## Evaluation

Fine-tuning comparison may include validation pass rate, grounding score, schema validity, repetition rate, fallback requirement, learner-facing readiness, qualitative examples, and comparison against RAG/template outputs.

Do not claim human-level tutor quality unless human evaluation was actually performed.

## What Not to Commit

Do not commit:

```text
.venv/
__pycache__/
.env
*.pt
*.pth
*.h5
*.keras
*.pkl
*.joblib
*.bin
*.safetensors
models/
checkpoints/
large datasets/
outputs/
runs/
wandb/
```

If a small sample dataset is included, ensure it does not contain private learner data.

## Status

Research comparison component. This folder supports experimentation and reporting, not the primary runtime path unless explicitly connected through the backend.

## Reviewer Questions

### What problem does this solve?

This module compares pretrained/fine-tuned generation against CogniTutorLM, RAG-grounded content, and validated fallback so the project can evaluate generation quality instead of assuming one model path is best.

### Can someone run it?

Some inspection and comparison scripts can run locally after installing the required ML dependencies. Full inference or fine-tuning may require base models, LoRA adapters, checkpoints, or datasets that are intentionally not committed.

### What did I build?

A fine-tuning and comparison workspace with scripts for LoRA-style training, inference checks, generated-output comparison, validation, human-evaluation preparation, and report generation.

### What is completed?

The experiment structure, comparison scripts, README, safety guidance, and artifact-ignore rules are in place. The module clearly separates research comparison from the main learner-facing runtime.

### What is still limited?

Local full-model execution may not work without external model files. Results should be treated as experimental evidence, not production validation. Private human-evaluation mappings and large artifacts are excluded.

### Why should a recruiter care?

This folder shows the ability to evaluate AI choices critically: comparing pretrained/fine-tuned generation, checking grounding/schema quality, managing model artifacts, and documenting limitations instead of making unsupported claims.
