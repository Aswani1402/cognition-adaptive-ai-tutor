# Learner State and Lesson Cleanup Report

Date: 2026-05-17

## Files changed

- `src/App.tsx`
- `src/context/LearnerSessionContext.tsx`
- `src/lib/api.ts`
- `src/lib/concepts.ts`
- `src/lib/localProgress.ts`
- `src/pages/LoginPage.tsx`
- `src/pages/RegisterPage.tsx`
- `src/pages/DashboardPage.tsx`
- `src/pages/LessonPage.tsx`
- `src/pages/QuizPage.tsx`
- `src/pages/MistakesPage.tsx`
- `src/pages/NotebookPage.tsx`
- `src/pages/RevisionPage.tsx`
- `src/pages/DoubtsPage.tsx`
- `src/pages/XAIPage.tsx`
- `src/components/layout/Topbar.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/components/teaching/SelectedTeachingViewRenderer.tsx`
- `src/components/assessment/AssessmentRenderer.tsx`
- `src/components/assessment/HintPanel.tsx`
- `src/components/chat/TutorChatPanel.tsx`

## Fixes completed

- Login/register now clear stale learner state before storing the backend-returned `learner_id` and `user_id`.
- Logout clears auth, learner context, subject/concept, progress, reward, notebook, mistake, assessment, and local session caches.
- New registration initializes clean local progress: 0 XP, 0 streak, no mistakes, no notebook history, `easy` difficulty.
- Dashboard no longer shows hardcoded 60% mastery; clean users see `New`.
- Rewards merge local session progress and suppress demo/fallback reward values during a clean new-user session.
- Mistakes and notebook suppress demo/fallback records during a clean new-user session.
- Forgot password now shows: `Password reset is not implemented in this prototype.`
- Lesson content is now guided and medium-sized: short explanation, one example, 2-3 key points, 1-2 mistakes, previous recap, and action buttons.
- Teaching views now select view-specific content instead of dumping every concept resource section.
- SQL/Database Basics uses the same concise lesson shell and maps `S1` to `Database Basics`.

## Verification

- `npm run build`: passed
- `npm run lint`: passed
- Dev server route probes returned HTTP 200 for `/login`, `/register`, `/dashboard`, `/subjects`, `/lesson/P1`, `/lesson/S1`, `/assessment`, `/mistakes`, `/revision`, `/rewards`, and `/xai`.

## Manual test notes

- HTTP route checks confirm the pages are reachable from Vite.
- Full browser click-through should still be used for final screenshots, especially real backend registration/login because it depends on backend data and seeded users.

## Screenshot readiness

Ready. New-user UI is clean, lesson content is concise, topic names are mapped, and learner-facing raw backend errors are avoided.
