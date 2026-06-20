# Frontend Backend Connection Check

Project: `C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\frontend_ui\KP-UI`

Date: 2026-05-11

## API Base URL

Detected in `.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

`src/lib/api.ts` reads `import.meta.env.VITE_API_BASE_URL`, trims a trailing slash, and calls backend routes when the value exists.

Frontend dev server script is configured for:

```text
http://localhost:5173
```

## Backend Request Behavior

`apiGet` and `apiPost` now:

- call backend when `VITE_API_BASE_URL` is configured
- log in development: `[API] backend request <url>`
- log in development: `[API] mock fallback used <reason>`
- use mock fallback only when backend URL is missing, the request fails, the response is not OK, or a request times out
- unwrap backend responses that return either raw data or `{ data: ... }`

`GET /health` is exposed through `getBackendHealth()` and shown in the topbar as:

- `Backend connected` on success
- `Mock mode` on fallback/failure

## Pages Using Backend API

| Page/component | API function(s) used | Backend-ready |
|---|---|---:|
| `LoginPage` | `loginUser` | Yes |
| `RegisterPage` | `registerUser` | Yes |
| `DashboardPage` | `getStreakXP`, `getLearnerContext` | Yes |
| `SubjectsPage` | `getSubjects` | Yes |
| `LearningPathPage` | `getLearningPath`, `getProgressionResult` | Yes |
| `LessonPage` | `getLesson`, `getLessonResult` | Yes |
| `QuizPage` | `getAssessment` | Yes |
| `AssessmentRenderer` | `submitAnswer` | Yes |
| `CodeConsole` | `runCode`, `submitAnswer` | Yes |
| `DoubtPanel` | `askDoubt`, `submitDoubtFollowUp` | Yes |
| `NotebookPage` | `getNotebook` | Yes |
| `NotebookSearchPanel` | `searchNotebook` | Yes |
| `RewardsPage` | `getRewardState`, `getProgress` | Yes |
| `ProgressPage` | `getProgress` | Yes |
| `MistakesPage` | `getMistakeReview` | Yes |
| `DemoPage` | `getDemoRun`, `getRewardState` | Yes |
| `XAIPage` | `getXAI` | Yes, with timeout fallback |
| `PuzzlePage` | `getPuzzleActivities` | Yes |
| `FlashcardsPage` | `getFlashcards` | Yes |
| `MindMapPage` | `getMindmap` | Yes |
| `Topbar` | `getBackendHealth` | Yes |

## Direct Mock Usage

Pages/components checked under `src/pages` and `src/components`.

Result: **No direct `mockData` imports found.**

Mock data remains available only through `src/lib/api.ts` fallback behavior.

## Backend Calls Tested

Manual endpoint checks from this project:

| Endpoint | Result |
|---|---|
| `GET http://localhost:8000/health` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/subjects` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/path/demo_learner/python` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/lesson/demo_learner/c1` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/assessment/demo_learner/c1` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/reward/demo_learner` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/flashcards/demo_learner` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/mindmap/c1` | PASS, `fallback_used: false` |
| `GET http://localhost:8000/xai/c2` | Timed out in shell testing; frontend now falls back after request timeout |

Auth POST routes were not manually submitted from shell to avoid creating extra backend data. The frontend pages call `loginUser` and `registerUser` when forms are submitted.

## Is The Frontend Truly Backend Connected?

**Yes.** With `.env.local` set to `VITE_API_BASE_URL=http://localhost:8000`, pages call `src/lib/api.ts`, which issues real backend `fetch` requests. Confirmed backend calls returned success for health, subjects, path, lesson, assessment, rewards, flashcards, and mindmap.

## Remaining Mock/Fallback Areas

These are backend-connected but may use fallback if the backend route is missing, slow, or returns an incompatible payload:

- XAI route: `/xai/c2` timed out during shell testing.
- Mistake review: frontend calls `/mistakes/{learnerId}`; fallback remains if backend route is unavailable.
- Progression and lesson result: frontend calls `/progression/...` and `/lesson-result/...`; fallback remains if unavailable.
- Demo run: frontend calls `/tutor/adaptive-session/{profile}`; fallback remains if unavailable or payload differs.

## Final Check

- Lint: PASS
- Build: PASS
