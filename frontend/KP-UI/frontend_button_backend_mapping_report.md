# Frontend Button Backend Mapping Report

Generated: 2026-05-11

## 1. Overall Connection Status

- Frontend backend URL: `VITE_API_BASE_URL=http://127.0.0.1:8010`
- API wrapper: `src/lib/api.ts`
- Backend status model: frontend calls backend when `VITE_API_BASE_URL` exists and falls back to mock data on request failure.
- Development logs:
  - `[API] backend request: URL`
  - `[API] mock fallback used: reason`
- Sanvia status: comparison-only/pending; not connected to live runtime.
- Live backend services: CogniTutorLM connector, RAG/context modules, teaching strategy modules, assessment/evaluation modules, doubt handler, notebook/search, reward, XAI.

## 2. Backend URL Detected

`frontend_ui/KP-UI/.env.local` now points to `http://127.0.0.1:8010`.

## 3. Page-Wise Inventory

| Page | Buttons / Inputs / Cards | Data Source | Imports mockData directly | Calls api.ts | Backend route needed |
|---|---|---|---|---|---|
| LandingPage | Start/login/register navigation | Static | No | No | None |
| LoginPage | Email/password/login | Auth API | No | Yes | `POST /auth/login` |
| RegisterPage | Name/email/password/register | Auth API | No | Yes | `POST /auth/register` |
| DashboardPage | Continue Lesson, Start Review, Practice Weak Area cards/buttons | API with fallback | No | Yes | `/learner/profile`, `/tutor/adaptive-session`, `/revision`, `/retention`, `/assessment` |
| SubjectsPage | Subject cards, Open Path | API with fallback | No | Yes | `GET /subjects`, `GET /path/{learner_id}/{subject}` |
| LearningPathPage | Start Lesson, Review, Take Quiz, Challenge, View Notebook | API with fallback | No | Yes | `/lesson`, `/revision`, `/assessment`, `/puzzle`, `/notebook` |
| LessonPage | Teaching action cards, mini-check, Practice Concept, Ask Doubt | API with fallback | No | Yes | `GET /lesson/{learner_id}/{concept_id}?view=...`, `GET /assessment`, `POST /doubt/ask` |
| QuizPage | Answer inputs, submit, run code where applicable | API with fallback | No | Yes | `GET /assessment`, `POST /answer/submit`, `POST /code/run` |
| PuzzlePage | Puzzle cards/actions | API with fallback | No | Yes | `GET /puzzle/{learner_id}/{concept_id}` |
| FlashcardsPage | Show Answer, Again, Hard, Good, Easy | Mock/API fallback | No | Yes | Revision feedback endpoint missing |
| MindMapPage | Practice, save map | API with fallback | No | Yes | `GET /mindmap/{concept_id}`, `GET /assessment`; notebook save endpoint pending |
| NotebookPage | Search, revision plan, notebook cards | API with fallback | No | Yes | `GET /notebook`, `GET /learner/notebook/search`, `GET /revision` |
| ProgressPage | Progress cards/charts | API with fallback | No | Yes | `GET /learner/progress/{learner_id}` |
| RewardsPage | XP/streak/badges/cards | API with fallback | No | Yes | `GET /reward/{learner_id}` |
| MistakesPage | Try similar question, Review concept | API with fallback | No | Yes | `GET /mistakes`, `GET /assessment`, `GET /lesson` |
| XAIPage | Why this decision / evidence cards | API with fallback | No | Yes | `GET /xai/{learner_id}` |
| SettingsPage | Profile/preferences controls | Local/static | No | Partial | Preference persistence endpoint pending |
| DemoPage | Run demo/profile selector | API with fallback | No | Yes | `GET /tutor/adaptive-session/{learner_id}` |

## 4. LessonPage Button Mapping

| Button | Current file | onClick present | API called | Backend route | Backend module | DB table | Columns read/write | Status |
|---|---|---:|---|---|---|---|---|---|
| Explain simpler | `src/pages/LessonPage.tsx` | Yes | `getLesson(conceptId, { view: "simple_example_view" })` | `GET /lesson/{learner_id}/{concept_id}?view=simple_example_view` | `tutor.api.integration_routes`, teaching strategy/RAG/CogniTutorLM-ready contract | `concept_id_map`, subject `concept_resources`, `knowledge_state`, `behaviour_state`, optional `teaching_strategy_log` | Read concept/domain/resource/mastery/behavior; optional write learner_id, concept_id, strategy, timestamp | Connected with safe mock fallback |
| Give analogy | `src/pages/LessonPage.tsx` | Yes | `getLesson(... analogy_view)` | `GET /lesson/{learner_id}/{concept_id}?view=analogy_view` | Same as above | Same as above | Same as above | Connected with safe mock fallback |
| Show code example | `src/pages/LessonPage.tsx` | Yes | `getLesson(... code_view)` | `GET /lesson/{learner_id}/{concept_id}?view=code_view` | Same as above | Same as above | Same as above | Connected with safe mock fallback |
| Step-by-step | `src/pages/LessonPage.tsx` | Yes | `getLesson(... step_by_step_view)` | `GET /lesson/{learner_id}/{concept_id}?view=step_by_step_view` | Same as above | Same as above | Same as above | Connected with safe mock fallback |
| Common Mistake | `src/pages/LessonPage.tsx` | Yes | `getLesson(... misconception_view)` | `GET /lesson/{learner_id}/{concept_id}?view=misconception_view` | Same as above | Same as above | Same as above | Connected with safe mock fallback |
| Ask me a question | `src/pages/LessonPage.tsx` | Yes | `getAssessment(conceptId)` | `GET /assessment/{learner_id}/{concept_id}` | `tutor.api.integration_routes`, assessment/question bank | `quiz_results` after submit; reads concept/question sources | Read concept/question; later write quiz_id, learner_id, concept_id, question_id, is_correct, timestamp | Connected; shows mini-check or quiz fallback |
| Ask a Doubt | `src/pages/LessonPage.tsx`, `src/components/doubt/DoubtPanel.tsx` | Yes | `askDoubt(payload)` | `POST /doubt/ask` | `tutor.api.doubt_routes`, DoubtIntentClassifier, CogniTutorLM doubt connector, RAG | `learner_doubt_log` | Write learner_id, session_id, concept_id, concept_name, domain, doubt_text, doubt_type, answer_summary, rag_grounded, created_at | Connected with safe mock fallback |
| Practice Concept | `src/pages/LessonPage.tsx` | Yes | Quiz page calls `getAssessment` | `GET /assessment/{learner_id}/{concept_id}` | Assessment/question bank | `quiz_results` after submission | Read question source; later write quiz result columns | Connected |
| Add to Notebook | Not visible on current LessonPage | N/A | Pending | Preferred `POST /notebook` if added | Notebook/memory | `revision_card` or `learner_session_log` | Pending | Missing endpoint/action |

## 5. API Function Mapping

| API function | Route | Backend connected | Mock fallback |
|---|---|---:|---:|
| `loginUser` | `POST /auth/login` | Yes | Yes |
| `registerUser` | `POST /auth/register` | Yes | Yes |
| `getLearnerContext` | `GET /learner/profile/{learner_id}` | Yes | Yes |
| `getSubjects` | `GET /subjects` | Yes | Yes |
| `getLearningPath` | `GET /path/{learner_id}/{subject}` | Yes | Yes |
| `getLesson` | `GET /lesson/{learner_id}/{concept_id}?view=...`; fallback `GET /tutor/adaptive-session/{learner_id}` | Yes | Yes |
| `getAssessment` | `GET /assessment/{learner_id}/{concept_id}` | Yes | Yes |
| `submitAnswer` | `POST /answer/submit` | Yes | Yes |
| `runCode` | `POST /code/run` | Yes | Yes |
| `askDoubt` | `POST /doubt/ask` | Yes | Yes |
| `searchNotebook` | `GET /learner/notebook/search/{learner_id}?q=...&top_k=5` | Yes | Yes |
| `getRewardState` | `GET /reward/{learner_id}` | Yes | Yes |
| `getXAI` | `GET /xai/{learner_id}` | Yes | Yes |

## 6. Database Table / Column Mapping

| UI Action | Frontend file | API function | Backend route | Backend module | DB table | Columns read/write | Status |
|---|---|---|---|---|---|---|---|
| Login | `LoginPage.tsx` | `loginUser` | `POST /auth/login` | `auth_routes` | `users`, `learner_profile` | Read/write `users.last_login_at`; read `user_id`, `email`, `password_hash`, `role`; read learner profile | Connected/fallback |
| Register | `RegisterPage.tsx` | `registerUser` | `POST /auth/register` | `auth_routes` | `users`, `learner_profile` | Write user identity/profile columns | Connected/fallback |
| Lesson view switch | `LessonPage.tsx` | `getLesson` | `GET /lesson/{learner_id}/{concept_id}?view=...` | `integration_routes`; teaching strategy/RAG contract | `concept_id_map`, subject `concept_resources`, `knowledge_state`, `behaviour_state`, optional `teaching_strategy_log`, `learner_session_log`, `xai_log` | Read concept/resource/mastery/behavior/explanations; optional write view/session logs | Connected/fallback |
| Ask doubt | `DoubtPanel.tsx` | `askDoubt` | `POST /doubt/ask` | `doubt_routes`, classifier, CogniTutorLM/RAG | `learner_doubt_log` | Write doubt and answer summary columns | Connected/fallback |
| Practice concept | `LessonPage.tsx`, `QuizPage.tsx` | `getAssessment`, `submitAnswer` | `GET /assessment`, `POST /answer/submit` | assessment/evaluation routes | `quiz_results`, `learner_mistake_log`, `knowledge_state`, `behaviour_state`, `reward_event_log`, `teaching_strategy_log` | Read questions; write result, mistakes, state, reward | Connected/fallback |
| Rewards | `RewardsPage.tsx` | `getRewardState` | `GET /reward/{learner_id}` | reward routes | `learner_xp_state`, `learner_streak_state`, `achievement_badges`, `learner_badges`, `daily_goal_state`, `concept_unlock_state`, `reward_event_log` | Read XP/streak/badges/goals/unlocks/events | Connected/fallback |
| XAI | `XAIPage.tsx` | `getXAI` | `GET /xai/{learner_id}` | xai routes | `xai_log`, `teaching_strategy_log`, `knowledge_state`, `behaviour_state` | Read explanation/evidence/state | Connected/fallback |
| Notebook search | `NotebookPage.tsx` | `searchNotebook` | `GET /learner/notebook/search/{learner_id}` | semantic notebook search | `learner_doubt_log`, `learner_mistake_log`, `learner_session_log`, `revision_card` | Read summaries, mistakes, doubts, sessions, cards | Connected/fallback |

Subject DB `concept_resources` columns:
`concept_id`, `topic`, `base_content`, `examples`, `key_points`, `misconceptions`, `real_world_use`, `next_concept_link`; `data_structures.db` also has `id`.

## 7. Connected vs Mock-Only Features

Connected with fallback: auth, dashboard/profile, subjects, path, lesson, lesson view switching, assessment, answer submit, code run, doubt, notebook, notebook search, progress, rewards, mistakes, XAI, demo, puzzle, flashcards/mindmap read.

Mock-only or partially pending: flashcard spaced-repetition feedback, notebook save from lesson/mindmap, settings persistence, Sanvia live runtime.

## 8. Buttons That Still Do Nothing

No dead buttons were left on LessonPage. Some non-lesson pages may still contain purely local visual controls, especially Settings and flashcard rating actions where backend endpoints are pending.

## 9. Buttons Using Wrong Route

LessonPage view actions now use `/lesson/{learner_id}/{concept_id}?view=...`. Practice Concept uses the quiz route, whose page calls `/assessment/{learner_id}/{concept_id}`.

## 10. Missing Backend Endpoints

- `POST /notebook/save` or similar for Add to Notebook / save map.
- Revision-card feedback endpoint for Flashcards: Again/Hard/Good/Easy.
- Settings preference persistence endpoint.

## 11. Missing Frontend API Functions

- `saveNotebookItem` pending backend save endpoint.
- `submitRevisionFeedback` pending revision feedback endpoint.
- `saveUserPreferences` pending settings endpoint.

## 12. Recommended Fixes Before Final Demo

- Keep backend on `http://127.0.0.1:8010`.
- Demo LessonPage with `code_view`, `simple_example_view`, `analogy_view`, `step_by_step_view`, and `misconception_view`.
- Add notebook save and revision feedback endpoints only if those actions must be live in the demo.

## 13. Ready / Not Ready Status

Ready for lesson button flow demo with backend/API or safe mock fallback. Not ready for live notebook-save and flashcard-feedback persistence because endpoints are missing.
