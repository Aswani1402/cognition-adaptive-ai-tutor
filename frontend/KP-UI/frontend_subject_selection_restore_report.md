# Frontend Subject Selection Restore Report

## Files changed
- `src/components/layout/Sidebar.tsx`
- `src/pages/DashboardPage.tsx`
- `src/pages/SubjectsPage.tsx`
- `src/context/LearnerSessionContext.tsx`
- `src/lib/types.ts`

## Routes added/verified
- Verified existing route in `src/App.tsx`: `/subjects` renders `SubjectsPage`.
- Existing learner routes were left in place for dashboard, guided lesson, learning path, assessment, flashcards, mindmap, notebook, mistakes, revision, rewards, XAI, and reviewer evidence.

## Sidebar item added
- Added visible learner navigation item after Dashboard:
  - Label: `Subject Selection`
  - Icon: `BookOpen`
  - Route: `/subjects`
- Updated sidebar nav item identity to use a unique `id` for each item.
- Updated `uniqueNavItems` to filter duplicate items by `id` only, so fallback routes that point to `/subjects` do not remove the real Subject Selection item.

## Dashboard Change Subject button
- Added a visible `Change Subject` button in `DashboardPage.tsx`.
- The button navigates to `/subjects`.

## Subject switching behavior
- `SubjectsPage.tsx` still calls `getSubjects()` to load subject cards.
- Selecting a subject calls `selectSubject(learnerId, subject.name)`.
- After selection, `LearnerSessionContext.setSubjectContext()` updates only:
  - `active_subject`
  - `current_concept_id`
  - `current_concept_name`
  - `current_difficulty`
  - `selected_teaching_view`, when returned as `selected_teaching_view` or `current_teaching_view`
- The page now says: `Choose or change your subject.`
- Existing subject mastery/progress is not deleted from localStorage or backend during subject switching.
- The app navigates to `result.next_route`, or `/lesson/<current_concept_id>`, or `/dashboard` if no concept id is returned.
- Subject cards continue to display returned progress/mastery fields through `subject.progress`, `unlockedConcepts`, and `totalConcepts` when available from the backend or mock data.

## Backend endpoint used
- Subject selection uses `POST /learner/select-subject` through `selectSubject()` in `src/lib/api.ts`.
- Subject list uses `GET /subjects` through `getSubjects()` in `src/lib/api.ts`.

## Mock fallback behavior
- Existing API mock fallback behavior was preserved.
- If `VITE_API_BASE_URL` is missing or backend requests fail, `apiGet()` and `apiPost()` continue returning mock data.
- `selectSubject()` still falls back to a mock first concept and `next_route` when backend is unavailable.

## Build result
- Ran `npm run build`.
- Result: passed.
