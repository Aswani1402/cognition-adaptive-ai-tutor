# Frontend Final Connection Report

## Summary
KP-UI remains separate and calls the main backend through `VITE_API_BASE_URL=http://localhost:8000`. Mock fallback remains available when the backend is not configured or a request fails.

## Connected Functions
`registerUser`, `loginUser`, `getLearnerContext`, `getSubjects`, `getLearningPath`, `getLesson`, `getAssessment`, `submitAnswer`, `runCode`, `askDoubt`, `submitDoubtFollowUp`, `getNotebook`, `searchNotebook`, `getProgress`, `getStreakXP`, `getMistakeReview`, `getRewardState`, `getXAI`, `getDemoRun`, `getPuzzleActivities`, `getFlashcards`, and `getMindmap`.

## Auth
Login/register pages call the API helpers, store `access_token`, `user_id`, and `learner_id`, then redirect to dashboard. Mock fallback is preserved.

## Runtime Boundary
The frontend does not call Sanvia directly. Sanvia is not used for live lesson, assessment, doubt, hint, or frontend runtime generation. It is comparison-only and pending because a local base model or merged model is missing.

## Build Results
- `npm install`: success, 0 vulnerabilities.
- `npm run build`: success.
- `npm run lint`: success.

## Commands
- Backend: `python -m uvicorn tutor.api.main:app --reload --host 127.0.0.1 --port 8000`
- Backend venv fallback: `.\.venv\Scripts\python.exe -m uvicorn tutor.api.main:app --reload --host 127.0.0.1 --port 8000`
- Frontend: `npm run dev`

## Status
Demo-ready with warning: active system Python lacks `uvicorn`, and Sanvia is comparison-only/pending runtime availability.

