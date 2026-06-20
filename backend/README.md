# Backend

This folder contains the main adaptive tutor backend for the Cognition-Adaptive AI Tutor Personalized Learning System.

The backend is responsible for learner-state management, adaptive intelligence modules, answer evaluation, safe code execution, RAG retrieval, guarded generation, policy/RL safe decision support, notebook memory, revision support, rewards, XAI, runtime logs, and evaluation evidence.

## Main Responsibilities

- Receive learner actions from the interface
- Load learner profile, subject, current concept, difficulty, and previous state
- Select teaching view and assessment task
- Evaluate learner answers by task type
- Update mastery and behaviour evidence
- Track mistakes, doubts, notes, revision needs, and rewards
- Retrieve concept-grounded resources using local RAG
- Validate CogniTutorLM-supported generation before learner-facing use
- Apply safe policy/RL action masking
- Generate XAI explanations for adaptive decisions
- Store runtime traces and evidence reports

## Important Modules

The exact internal structure may vary, but the backend generally includes:

```text
backend/
│
├── api/                       # FastAPI application and route entry points
├── tutor/                     # Core tutor/adaptive intelligence modules
├── scripts/                   # Training, loading, testing, evaluation, and demo scripts
├── external/                  # Local models, datasets, concept DBs, runtime data; usually not committed if large/private
├── reports/                   # Backend-generated evaluation summaries and charts
├── tests/                     # Unit or integration tests if available
├── requirements.txt           # Python dependencies
└── README.md
```

## Core Backend Components

### Authentication / Learner Profile

Stores or loads learner identity, learning goal, selected subject, and learner level. This supports returning learner personalization.

### Learner Context

Keeps active concept, subject, difficulty, mastery state, previous mistakes, revision need, and unlock status.

### Knowledge Tracing

Estimates learner mastery using sequence-aware learner response evidence when trained artifacts are available.

Supported logic may include:

- DKT runtime
- BKT or cumulative mastery baseline
- fallback mastery estimation

### Behaviour Modelling

Uses learner interaction signals such as response time, confidence, hint usage, attempt count, wrong attempts, answer changes, option changes, code-run count, difficulty level, and mistake evidence.

Behaviour output is treated as interaction-risk evidence, not psychological diagnosis.

### Concept Dependency and Adaptive Path

Checks prerequisite relationships and prevents unsafe progression when required concepts are not ready.

### Teaching Strategy

Chooses teaching view based on mastery, behaviour risk, mistake type, difficulty, and revision need.

Teaching views may include definition, explanation, example, step-by-step, analogy, code-focused view, misconception correction, debugging support, output prediction support, transfer, challenge, revision summary, and real-world connection.

### Dynamic Assessment

Selects or generates tasks based on learner state, concept, and difficulty.

Supported task types may include MCQ, true/false schema support, fill-in-the-blank schema support, syntax completion, output prediction, debugging, coding, explanation check, transfer question, challenge question, and real-world application task.

### Answer Evaluation

Evaluates submitted answers using task-specific logic and returns score, correctness label, mistake type, weakest skill, expected answer or expected idea, feedback, and next-step signal.

### Safe Code Runner

Prototype controlled execution for programming-related tasks.

It may handle output capture, syntax errors, timeouts, blocked unsafe operations, and test-case comparison.

Important: this is prototype-level controlled execution and not production-grade sandboxing.

### RAG Retrieval

Retrieves local concept resources such as definitions, examples, key points, misconceptions, real-world uses, and next-concept links.

RAG supports lessons, hints, doubt answers, revision notes, flashcards, mindmaps, and generation prompts.

### CogniTutorLM Guarded Generation

Raw generation is treated only as a candidate output. The backend validates it using schema checks, required-field checks, task-format checks, grounding checks, semantic relevance checks, repetition checks, safety checks, and learner-facing readiness checks.

If invalid, the system uses guarded product generation, prevalidated content banks, RAG-grounded concept resources, or templates.

### Policy/RL Safe Decision Support

Policy/RL is used as safe decision support, not autonomous control.

The safe action mask checks mastery, behaviour risk, difficulty, prerequisite status, mistake type, and revision need.

### Notebook Memory and Revision

Stores and retrieves weak concepts, mistakes, doubts, saved notes, flashcards, revision needs, and comeback summaries.

### Rewards

Supports XP, streaks, badges, daily goals, reward events, and concept unlock progress. Rewards support engagement but should not override mastery or prerequisites.

### XAI

Generates “why-this” explanations for teaching view, hint, revision suggestion, difficulty movement, next activity, progression, or blocked progression.

## Setup

From the backend folder:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

If there is no `requirements.txt`, generate one only after confirming the actual dependencies:

```powershell
pip freeze > requirements.txt
```

## Run Backend

Common FastAPI command:

```powershell
uvicorn api.main:app --reload --host localhost --port 8088
```

API docs:

```text
http://localhost:8088/docs
```

If the backend entry file is different, locate the FastAPI app using:

```powershell
dir api
```

or search for:

```text
FastAPI()
```

## Useful Checks

```powershell
python -m compileall .
```

```powershell
git status
```

## What Not to Commit From Backend

Do not commit:

```text
.venv/
__pycache__/
.env
*.pyc
*.db
*.sqlite
*.db-shm
*.db-wal
*.pt
*.pth
*.h5
*.keras
*.pkl
*.joblib
datasets/
external/
model_artifacts/
checkpoints/
outputs/
private/
secrets/
```

If a small sample database is required for demo, document it clearly and avoid including private learner data.

## Backend Status

Research prototype backend for an integrated cognition-adaptive tutoring framework. It is intended to demonstrate module integration, adaptive decision support, guarded generation, and runtime evidence. It is not yet a production deployment.
