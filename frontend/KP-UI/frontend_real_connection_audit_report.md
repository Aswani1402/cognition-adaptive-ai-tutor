# Frontend Real Connection Audit Report

Date: 2026-05-12

## 1. Proper website flow status

The main frontend remains a learner website, not a technical module dashboard. The normal path is Register/Login -> Subject -> Guided Session/Lesson -> Assessment -> Feedback -> Revision -> Progress. AI evidence is exposed through small "Why this?" explanations in guided flow and fuller reviewer cards on XAI/Demo routes.

## 2. Frontend-backend connection status

`src/lib/api.ts` uses `VITE_API_BASE_URL` and logs `[API] backend request: URL` for backend calls and `[API] mock fallback used: reason` when a fallback is used. `Topbar` now shows a small backend status badge: Backend connected, Backend error, Mock mode, or Checking backend.

## 3. Subject context status

`LearnerSessionContext` stores and persists `learner_id`, `active_subject`, `current_concept_id`, `current_concept_name`, `current_difficulty`, and `selected_teaching_view`. Dashboard, navigation, Learning Path, Lesson, Quiz, Puzzle, Flashcards, Mindmap, Notebook, Rewards, Progress, Mistakes, Doubt, and XAI use this context. Remaining C2/Python navigation defaults were removed from Sidebar, BottomNav, Dashboard, Puzzle, Notebook, Rewards, Mistakes, and LessonResultCard.

## 4. Auth/user DB status

Frontend auth calls `POST /auth/register` and `POST /auth/login`. Backend route smoke tests passed. The frontend stores the returned user/session identifiers and uses `learner_id` for learner routes instead of hardcoded learner `14`.

## 5. Guided session status

Guided flow remains learner-facing. It can render teaching, assessment, feedback, hint, flashcard revision, mindmap revision, revision summaries, weakness review, comeback summary, code practice, reward, XAI explanation, and next-step guidance. The added "Why this?" card is collapsible and learner-friendly by default.

## 6. Assessment/evaluation status

Assessment calls are subject/concept/difficulty aware. Answer submission includes behaviour evidence and backend persistence now writes available quiz, KT, behaviour, reward, session, unlock, and learner profile state tables safely when those tables exist.

## 7. Behaviour payload status

Assessment cards collect and send: `time_taken_sec`, `confidence`, `hint_used`, `hint_count`, `option_change_count`, `answer_change_count`, `run_code_count`, `attempt_count`, `wrong_attempt_count`, `question_type`, `difficulty`, `subject`, and `concept_id`.

## 8. KT/Behaviour/Teaching/RAG/LLM usage status

Lesson, assessment, hint, XAI, and AI evidence routes are connected to backend integration routes. When a module is unavailable, the backend returns warning/fallback evidence rather than crashing. Fallback content is subject-aware and grounded through the concept content resolver.

## 9. Policy/RL evidence status

Policy/RL is reviewer-visible only through XAI/Demo/AIEvidencePanel. It is presented as safe decision evidence and comparison status, not as a learner-controlled page.

## 10. XAI/Why-this status

Learner flow uses short "Why this?" explanations. Full KT, Behaviour, Concept Dependency, Adaptive Path, Teaching Strategy, Policy/RL, RAG, LLM, Agentic Trace, Personalization, Retention, Evaluation/Fusion, and Reward cards are available on optional XAI/Demo routes.

## 11. Long-term personalization status

Notebook, mistake review, personalization, retention, and revision routes are represented through learner pages and AI evidence. Notebook search uses the current learner id.

## 12. Forgetting/revision status

Flashcards, mistakes, revision guidance, and retention evidence are connected. Progress defaults for new users initialize to level 1, XP 0, streak 0, and zero mastery rather than fake high demo values.

## 13. Flashcard/mindmap content status

Flashcards and mindmap calls include the selected subject and current concept. Backend fallbacks use concept resources and subject-aware generated content, not generic C2 placeholders.

## 14. Coding console status

Code/debug/coding/output prediction cards expose editable code where needed, Run Code, Submit, stdout/stderr, syntax/runtime error display, and test result display. Run Code calls `POST /code/run`.

## 15. Remaining issues

Manual browser/network verification was not run in this pass. Backend smoke tests report scikit-learn model pickle version warnings; route checks still passed. Demo/XAI intentionally contain reviewer-facing technical evidence, but they are optional routes and not the default learner flow.

## 16. Demo readiness

Demo route is clearly reviewer/demo-oriented. Sanvia remains comparison-only and is not connected as the live tutor runtime.

## Connection Table

| Feature/Page | Frontend file | API function | Backend route | Backend module | DB table | Connected? | Mock-only? | Issue | Fix done |
|---|---|---|---|---|---|---|---|---|---|
| Register/Login | `src/pages/RegisterPage.tsx`, `src/pages/LoginPage.tsx` | `register`, `login` | `POST /auth/register`, `POST /auth/login` | Auth | `users`, `learner_profile` | Yes | No | Must use returned learner id | Uses session/localStorage ids |
| Subject selection | `src/pages/SubjectsPage.tsx` | `selectSubject` | `POST /learner/select-subject` | Concept dependency, unlock | `learner_profile`, `concept_unlock_state`, `concept_id_map` | Yes | No | Python fallback risk | Stores selected subject/concept |
| Dashboard | `src/pages/DashboardPage.tsx` | `getLearnerContext`, `getStreakXP` | `GET /learner/context/{id}`, reward/streak route | Profile, reward | `learner_profile`, reward tables | Yes | No | Hardcoded Python lesson | Uses current subject/concept |
| Learning Path | `src/pages/LearningPathPage.tsx` | `getLearningPath` | `GET /path/{learner_id}/{subject}` | Adaptive path, dependency | `knowledge_state`, `concept_unlock_state` | Yes | No | Python default | Redirects to subject selection if no subject |
| Lesson/Guided | `src/pages/LessonPage.tsx` | `getLesson`, `getAIEvidence` | `GET /lesson/{learner_id}/{concept_id}` | Teaching strategy, RAG, CogniTutorLM, KT, Behaviour | `concept_resources`, `knowledge_state`, `behaviour_state` | Yes | No | Needs learner-friendly evidence | Uses collapsible Why-this |
| Assessment/Quiz | `src/pages/QuizPage.tsx` | `getAssessment`, `submitAnswer` | `GET /assessment/...`, `POST /answer/submit` | Question bank, evaluator, fusion, KT, Behaviour | `quiz_results`, `knowledge_state`, `behaviour_state` | Yes | No | Behaviour evidence required | Payload includes behaviour fields |
| Hint | Assessment cards | `predictHint` | `POST /hint/predict` | LearnedHintPolicy, AdaptiveHintPolicy | hint/memory logs when available | Yes | No | Hidden/empty hint risk | Visible hint panel and fallback |
| Doubt | `DoubtPanel` | `askDoubt` | `POST /doubt/ask` | Doubt classifier, RAG, LLM | `learner_doubt_log` | Yes | No | Undefined concept risk | Uses session concept |
| Puzzle | `src/pages/PuzzlePage.tsx` | `getPuzzleActivities` | `GET /puzzle/{learner_id}/{concept_id}` | Puzzle generator | concept resources | Yes | No | `c2` fallback | Uses session subject/concept |
| Flashcards | `src/pages/FlashcardsPage.tsx` | `getFlashcards` | `GET /flashcards/{learner_id}/{concept_id}` | Revision card, LLM, fallback | `revision_card` | Yes | No | Python/mock fallback risk | Subject-aware fallback |
| Mindmap | `src/pages/MindMapPage.tsx` | `getMindmap` | `GET /mindmap/{concept_id}` | Concept resources, RAG, LLM | subject concept DB | Yes | No | C2 placeholder risk | Concept resolver used |
| Notebook | `src/pages/NotebookPage.tsx` | `getNotebook`, `searchNotebook` | `GET /notebook/{id}`, `GET /learner/notebook/search/{id}` | Memory, search | `learner_mistake_log`, `learner_doubt_log`, `learner_session_log` | Yes | No | learner `14` default | Uses current learner |
| Rewards | `src/pages/RewardsPage.tsx` | `getRewardState`, `getProgress` | `GET /reward/{id}`, `GET /learner/progress/{id}` | Reward, progress | `learner_xp_state`, `reward_event_log`, `learner_badges` | Yes | No | Fake XP/achievements | Uses backend state/default zero |
| Progress | `src/pages/ProgressPage.tsx` | `getProgress` | `GET /learner/progress/{id}` | KT/progress aggregation | `learner_concept_progress`, `quiz_results`, `concept_unlock_state` | Yes | No | Missing route | Backend route added |
| Mistakes | `src/pages/MistakesPage.tsx` | `getMistakeReview` | `GET /mistakes/{id}` | Mistake analysis | `learner_mistake_log` | Yes | No | learner `14` default | Uses current learner |
| XAI/AI evidence | `src/pages/XAIPage.tsx` | `getAIEvidence`, `getXAI` | `GET /ai/evidence/{id}`, `GET /xai/{id}` | XAI, KT, Behaviour, RAG, policy, retention | module logs/state tables | Yes | No | Too technical in main flow | Optional/reviewer view |
| Demo | `src/pages/DemoPage.tsx` | demo/evidence APIs | `/ai/evidence`, `/generation/coverage`, `/agentic/trace` | Reviewer evidence | mixed | Yes | No | Could confuse learner | Kept as Demo Panel route |
| Code Console | `CodeConsole`, code question cards | `runCode`, `submitAnswer` | `POST /code/run`, `POST /answer/submit` | SafeCodeRunner, code evaluator | `quiz_results`, session logs | Yes | No | Missing for code questions | Wired into code/debug cards |

## Build/test result

- Frontend `npm run build`: passed.
- Frontend `npm run lint`: passed (`tsc --noEmit`).
- Backend `python -m scripts.test_api_routes_smoke`: passed.
- Backend `python -m scripts.test_frontend_response_builder`: passed.
- Manual browser check: not run in this pass.
