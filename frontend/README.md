# Frontend

This folder contains the learner-facing interface for the Cognition-Adaptive AI Tutor Personalized Learning System.

The frontend connects to the backend and presents guided learning, assessment, feedback, hints, doubts, notebook memory, revision, rewards, progress, and explainable recommendations.

## Main Responsibilities

- User registration and login
- Subject selection
- Guided learning session
- Concept lesson display
- Teaching view rendering
- Dynamic assessment display
- Answer submission
- Feedback and expected-answer display
- Hint request and hint-level selection
- Doubt support
- Safe code task interface if enabled
- Flashcards
- Mindmap
- Notebook memory
- Mistakes and weakness review
- Revision plan
- Rewards and progress view
- XAI / “why this” explanation display
- Backend health/status display

## Suggested Structure

The exact structure may vary, but the frontend usually includes:

```text
frontend/
│
├── src/
│   ├── pages/                 # Main route pages
│   ├── components/            # Reusable UI components
│   ├── services/              # API calls to backend
│   ├── hooks/                 # Custom React hooks if used
│   ├── utils/                 # Helper functions
│   ├── assets/                # Images/icons
│   ├── App.tsx
│   └── main.tsx
│
├── public/
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## Important Pages / Features

Depending on your current implementation, the frontend may include Dashboard, Subject Selection, Learn / Guided Session, Learning Path, Assessment, Challenges / Puzzle, Flashcards, Mindmap, Notebook, Mistakes and Weakness, Revision, Doubts, Rewards, Progress, Settings / Profile, and Developer or Reviewer evidence page if linked.

## Backend Connection

The frontend should call the backend API for login/register, subject selection, concept loading, assessment loading, answer submission, hint request, doubt request, code execution, notebook save/load, revision recommendations, reward state, XAI explanation, and progress state.

Common local backend URL:

```text
http://localhost:8088
```

## Setup

From the frontend folder:

```powershell
cd frontend
npm install
```

## Run Frontend

```powershell
npm run dev
```

Usually opens at:

```text
http://localhost:5173
```

If the port is different, check the terminal output.

## Build

```powershell
npm run build
```

## Common Issues

### Backend is not reachable

Make sure backend is running:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn api.main:app --reload --host localhost --port 8088
```

Then check:

```text
http://localhost:8088/docs
```

### Wrong API URL

Check frontend API configuration in `src/services`, `.env`, or config files.

Do not commit private `.env` files.

### Vite import error

If a page import fails, check that the file exists and the filename matches exactly, including capitalization.

## What Not to Commit From Frontend

Do not commit:

```text
node_modules/
dist/
build/
.env
.env.local
.vite/
.cache/
*.log
```

## Frontend Status

Research prototype learner interface for demonstrating the adaptive tutoring workflow. It is intended for project review, demonstration, and integration testing. It is not claimed as a production learning platform.
