# Frontend Guided Tutor Flow Report

Generated: 2026-05-11

## 1. First-Time Learner Flow

Register and login still use `POST /auth/register` and `POST /auth/login`. The frontend stores `access_token`, `user_id`, and `learner_id`, then sends the learner to subject selection. The learner chooses only a subject; the backend chooses the first concept and returns `/lesson/{concept_id}`.

## 2. Returning Learner Flow

After login, the frontend calls `GET /learner/context/{learner_id}`. If `active_subject` and `current_concept_id` exist, the learner enters `/lesson/{current_concept_id}`. The guided session checks retention and adaptive session state; due revision starts `returning_revision` before normal teaching.

## 3. Mascot Guide Scripts

`TutorGuideCard` introduces Cogni and displays the current step, guide message, backend/mock mode, and next action reason. Messages cover welcome, teaching, quick check, correct/partial/wrong answers, syntax/output mistakes, revision, reward, and concept completion.

## 4. Subject Selection To First Concept

`SubjectsPage` renders the five subject cards as guided session starters. Clicking a card calls `selectSubject(learner_id, subject)` -> `POST /learner/select-subject`. Backend updates `learner_profile`, unlocks the first concept in `concept_unlock_state`, logs the event in `learner_session_log`, and returns `next_route`.

## 5. Teaching View Behavior

`LessonPage` now hosts `GuidedTutorJourney`. It shows one selected teaching view through `SelectedTeachingViewRenderer`. Optional override buttons request a specific view through `GET /lesson/{learner_id}/{concept_id}?view=...` and update in place.

## 6. Automatic Assessment Behavior

The guided `NextActionCard` moves from teaching to assessment without navigating to `QuizPage`. `GuidedTutorJourney` calls `getAssessment`, renders 2-3 questions in sequence via `AssessmentRenderer`, and submits answers through `POST /answer/submit`.

## 7. Adaptive Loop After Evaluation

After answer submission, backend returns score, label, mistake type, weakest skill, guide message, memory update, and `recommended_next_activity`. The frontend follows that recommendation:

- high score -> reward / next concept
- partial score -> flashcard revision
- syntax mistake -> misconception/syntax review
- output mistake -> mindmap/overview revision
- weak score -> reteach and reassess

## 8. Flashcard Visual UI

`src/components/visual/FlashcardDeck.tsx` provides a guided flashcard deck with a centered card, front/back flip, card count, progress bar, and Again/Hard/Good/Easy buttons. It is used by `FlashcardsPage` and automatically by the guided journey.

## 9. Mindmap Visual UI

`src/components/visual/MindMapView.tsx` renders a central concept node, connector lines, and branch cards for definition, examples, key points, mistakes, real-world use, and related structure. It is used by `MindMapPage` and automatically by the guided journey.

## 10. Notebook Background Memory Update

The guided feedback panel shows notebook/memory status after submissions. Backend writes through existing persistence paths: `learner_session_log`, `learner_mistake_log`, `learner_doubt_log`, `revision_card`, and `revision_schedule`.

## 11. Reward / Unlock Flow

High-score feedback recommends reward. `GuidedTutorJourney` calls `GET /reward/{learner_id}` and renders `SessionCelebration` with XP, streak, and level. Backend sources include `reward_event_log`, `learner_xp_state`, `learner_streak_state`, `learner_badges`, and `concept_unlock_state`.

## 12. Page Role Clarification

- Dashboard: recommended next session, XP, streak, backend status.
- Subjects: choose/switch subject only.
- Learning path: optional progress graph/manual navigation.
- Lesson/session: primary guided tutor flow.
- Quiz: optional direct route; guided session renders assessments in place.
- Flashcards: revision library; also automatic guided remediation.
- Mindmap: concept overview; also automatic guided remediation.
- Notebook: memory/search/history, not blocking the flow.
- Rewards: gamification detail.
- XAI: why the tutor decided.

## 13. Backend Routes Used

`POST /auth/register`, `POST /auth/login`, `GET /learner/context/{learner_id}`, `POST /learner/select-subject`, `GET /tutor/adaptive-session/{learner_id}`, `GET /lesson/{learner_id}/{concept_id}?view=...`, `GET /assessment/{learner_id}/{concept_id}`, `POST /answer/submit`, `POST /code/run`, `POST /doubt/ask`, `GET /flashcards/{learner_id}`, `GET /flashcards/{learner_id}/{concept_id}`, `GET /mindmap/{concept_id}`, `GET /reward/{learner_id}`, `GET /xai/{learner_id}`, `GET /revision/{learner_id}`, `GET /retention/{learner_id}`, `POST /hint/predict`.

## 14. DB Tables Used

`users`, `learner_profile`, `learner_session_log`, `quiz_results`, `knowledge_state`, `behaviour_state`, `learner_mistake_log`, `learner_doubt_log`, `revision_card`, `revision_schedule`, `reward_event_log`, `learner_xp_state`, `learner_streak_state`, `achievement_badges`, `learner_badges`, `daily_goal_state`, `concept_unlock_state`, `teaching_strategy_log`, `xai_log`, `concept_id_map`, and subject DB `concept_resources`.

## 15. Remaining Mock-Only Parts

Flashcard rating persistence is visual/local until a revision feedback endpoint is added. Some advanced recovery decisions use frontend fallback logic when backend recommendation fields are absent. Sanvia remains comparison-only and is not live runtime.

## 16. Demo Readiness

Ready for guided demo with backend on `http://127.0.0.1:8010`. The learner is guided by Cogni from subject choice to teaching, quick check, adaptive remediation, reward, and next step.

Build/test result:

- `npm run build`: passed.
- `npm run lint`: passed.
- `python -m scripts.test_api_routes_smoke`: passed.
- `python -m scripts.test_frontend_response_builder`: passed.
