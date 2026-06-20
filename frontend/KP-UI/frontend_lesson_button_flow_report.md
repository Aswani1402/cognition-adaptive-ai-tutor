# Frontend Lesson Button Flow Report

Generated: 2026-05-11

## 1. What Was Fixed

- `LessonPage` now shows one selected teaching view as the main lesson card.
- Teaching action cards call `src/lib/api.ts` instead of being dead buttons.
- `getLesson(conceptId, { view })` calls `GET /lesson/{learner_id}/{concept_id}?view=...`.
- Backend/mock status is shown on the lesson page.
- `Practice Concept` navigates to quiz/assessment.
- `Ask a Doubt` opens the doubt drawer and focuses the input.

## 2. Duplicate Buttons Removed / Merged

- Removed the duplicate selected-view pill row from `SelectedTeachingViewRenderer`.
- Removed the hard-coded extra adaptive explanation card from `LessonPage`.
- Kept the large teaching action cards as the single visible action area.

## 3. Teaching View Switching Behavior

`handleTeachingViewChange(view)`:

- Sets per-view loading state.
- Calls `getLesson(id, { view })`.
- Updates `lesson.selectedView`, `requestedView`, selected-view badge, and rendered content.
- Keeps the learner on the same lesson page.
- Shows mock/backend error status when fallback is used.

Supported view actions now wired from the lesson page:

- Explain simpler -> `simple_example_view`
- Give analogy -> `analogy_view`
- Show code example -> `code_view`
- Step-by-step -> `step_by_step_view`
- Common Mistake -> `misconception_view`

## 4. Backend Route Used

Primary route:

`GET http://127.0.0.1:8010/lesson/{learner_id}/{concept_id}?view={teaching_view}`

Fallback route inside `api.ts` if the lesson route fails:

`GET /tutor/adaptive-session/{learner_id}`

Backend route patched:

`cognition_adaptive_AI_tutor/tutor/api/integration_routes.py`

## 5. Mock Fallback Behavior

If the backend URL is missing or requests fail, `getLesson` returns safe local teaching content for the requested view and sets:

- `backendConnected: false`
- `mockFallbackUsed: true`
- `backendStatusReason: ...`

The lesson page displays `Mock fallback` and the reason.

## 6. Practice Flow

- `Practice Concept` links to `/quiz/{conceptId}`.
- Quiz page loads assessment through `getAssessment`.
- `Ask me a question` first calls `getAssessment(conceptId)` and shows one mini-check card; if no question is available it navigates to quiz.

## 7. Doubt Flow

- `Ask a Doubt` opens the drawer.
- `DoubtPanel` submits through `askDoubt`.
- Quick actions send their actual button text:
  - Explain this simply
  - Show me an example
  - Debug my code
  - What should I revise?
- Backend route: `POST /doubt/ask`
- DB write: `learner_doubt_log`

## 8. Remaining Limitations

- Add to Notebook is not visible on the current LessonPage; a save endpoint is still pending.
- `teaching_strategy_log` write on view switch is documented but not forced from this safe wiring patch.
- Some advanced teaching views are supported by contract but not exposed as visible action cards on the current lesson screen.

## 9. Build / Test Results

- `npm run build`: passed.
- `npm run lint`: passed.
- `python -m scripts.test_api_routes_smoke`: passed.
- `python -m scripts.test_frontend_response_builder`: passed.
- Backend route syntax check: passed.
- Direct HTTP check to `http://127.0.0.1:8010/lesson/14/c2?view=analogy_view`: could not connect from this shell at check time; frontend fallback remains active if the browser cannot reach the server.
