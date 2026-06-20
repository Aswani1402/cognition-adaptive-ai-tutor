# LLM From Scratch / CogniTutorLM

This folder contains the CogniTutorLM / tutor language model from scratch work.

CogniTutorLM is used as a project-specific tutor generation component. It is not claimed to be a large commercial-scale LLM. It supports the research goal of exploring how a small tutor language model can be connected with RAG, validation, fallback, and adaptive tutoring logic.

## Purpose

The purpose of this folder is to show language-model-from-scratch learning and implementation work, tutor-specific generation experiments, concept explanation generation, doubt response generation, hint or feedback generation attempts, integration with the main tutoring system through a safe connector, and comparison against RAG-grounded templates and fine-tuned/pretrained baselines.

## Important Interpretation

Raw CogniTutorLM output is not directly trusted for learner-facing use.

In the full project, CogniTutorLM output is treated as a candidate response and passed through guarded validation:

- schema validation
- required-field checks
- task-format checks
- grounding checks
- semantic relevance checks
- repetition checks
- safety checks
- learner-facing readiness checks

If raw output fails validation, the system uses guarded product generation, prevalidated content banks, RAG-grounded resources, concept-resource fallback, or template fallback.

This is intentional because educational content must be reliable, grounded, concise, and suitable for learners.

## Suggested Folder Structure

```text
llm_from_scratch/
│
├── src/                       # Model, tokenizer, training, and generation source code
├── data/                      # Training or sample data; usually ignored if large
├── checkpoints/               # Model checkpoints; usually ignored
├── notebooks/                 # Experiments if available
├── scripts/                   # Train/test/generate scripts
├── reports/                   # Experiment notes and outputs
├── requirements.txt
└── README.md
```

## Possible Components

- tokenizer
- vocabulary builder
- dataset preparation
- model architecture
- training script
- generation script
- tutor service wrapper
- doubt handler
- connector to main backend
- sample prompts
- validation test scripts

## Setup

From this folder:

```powershell
cd llm_from_scratch
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run / Test

Exact commands depend on the actual scripts. Common patterns:

```powershell
python src/train.py
```

```powershell
python src/generate.py
```

```powershell
python -m src.tutor_lm_service
```

If the service is connected from backend, run the backend connector test from the backend folder.

## Integration With Main Project

```text
Selected concept + task type + learner state
        ↓
RAG retrieves concept context
        ↓
CogniTutorLM attempts generation
        ↓
Parser and validator check output
        ↓
If valid: use generated output
If invalid: use guarded fallback
        ↓
Return validated tutoring response
```

## Evaluation

CogniTutorLM-related evaluation may include raw valid rate, guarded valid rate, schema validity, fallback rate, grounding checks, repetition checks, learner-facing readiness, and safe response rate.

Important: guarded output success should not be presented as raw model success. It means the complete guarded pipeline produced usable learner-facing output.

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
checkpoints/
large model files/
large datasets/
outputs/
runs/
wandb/
```

If small sample files are useful, keep them small and clearly documented.

## Status

Research and integration component for tutor-specific generation. It demonstrates from-scratch language model learning and safe integration with RAG and validation. It is not claimed as a production-grade LLM.

## Reviewer Questions

### What problem does this solve?

This module explores whether a small tutor-specific language model can generate educational content, while avoiding unsafe direct use through RAG grounding, validation, and fallback.

### Can someone run it?

Some scripts can run locally after installing Python dependencies. Full training or reproduction may require datasets, tokenizer artifacts, checkpoints, or generated outputs that are intentionally excluded from GitHub because they are large.

### What did I build?

A CogniTutorLM experiment track with from-scratch model code, tokenizer/training scripts, generation scripts, guarded output validation, RAG connector logic, safe code runner support, and evaluation/reporting utilities.

### What is completed?

The source code, script structure, run documentation, integration explanation, and safety notes are organized. The module documents how raw model output is treated as a candidate and validated before learner-facing use.

### What is still limited?

The model is not a commercial-scale LLM and should not be treated as production-ready. Reproducing full results may need ignored datasets/checkpoints. Guarded success means the pipeline produced safe output, not that raw model output was always correct.

### Why should a recruiter care?

This module shows ML engineering curiosity beyond API usage: model training structure, generation validation, RAG grounding, artifact management, and honest reporting about model limitations.
