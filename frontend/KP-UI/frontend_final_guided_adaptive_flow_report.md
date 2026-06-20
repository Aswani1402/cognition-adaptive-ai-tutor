# Final Guided Adaptive Flow Report

Generated: 2026-05-12

## 1. First-Time Learner Flow

Register/login use the existing secure auth routes and PBKDF2/salted password hashing. After auth, learners choose one subject only. `POST /learner/select-subject` saves `active_subject`, sets `current_concept_id`, initializes `current_difficulty = easy`, unlocks the first concept, and returns `/lesson/{concept_id}`.

## 2. Returning Learner Flow

Login calls `GET /learner/context/{learner_id}`. If an active subject/concept exists, the learner continues in `GuidedTutorJourney`; if revision is due or retention risk is high, the session starts with revision/flashcards before assessment.

## 3. Difficulty Progression

The guided session now tracks `easy -> medium -> hard -> next concept` with `DifficultyProgressTracker`.

- score >= 0.8 on easy: move to medium
- score >= 0.8 on medium: move to hard
- score >= 0.8 on hard: concept complete and next concept unlock path
- partial/weak: stay on current difficulty and use revision/reteaching

## 4. Mascot Guide Scripts

Cogni uses deterministic scripts from `src/components/mascot/cogniScripts.ts`, selected by `useCogniGuide`. Backend `guide_message` is preferred when available; mock mode overrides with a backend fallback message.

## 5. Subject Selection To First Concept

`SubjectsPage` shows subject cards and calls `selectSubject`. The learner does not manually choose concepts first.

## 6. Teaching View Behavior

Lesson/session page shows one selected teaching view. Optional override buttons call `GET /lesson/{learner_id}/{concept_id}?view=...&difficulty=...`.

## 7. Automatic Assessment

The Continue/Try Quick Check action calls `getAssessment(conceptId, { difficulty })` and renders assessment inside the guided session. Direct `QuizPage` remains optional.

## 8. Adaptive Loop

`POST /answer/submit` returns score, mistake type, weakest skill, difficulty pass state, next difficulty/concept, memory update, XAI reason, and next recommended activity. The frontend follows that action in place.

## 9. Flashcard Visual UI

`FlashcardDeck` shows a centered flashcard, flip state, progress bar, count, and Again/Hard/Good/Easy buttons. It is used directly and inside guided revision.

## 10. Mindmap Visual UI

`MindMapView` shows a central concept node, connector lines, and branch cards for definition, examples, key points, mistakes, and real-world use.

## 11. Notebook Memory

Answer submission and doubt handling persist to learner memory tables. The guided UI shows notebook/memory messages after feedback.

## 12. Reward / Unlock Flow

On high-score progression, the guided session can show `SessionCelebration` and fetch `GET /reward/{learner_id}` for XP/streak/level.

## 13. XAI Reviewer Explanation

XAI remains available through `XAIPage` and `GET /xai/{learner_id}`. Cogni’s XAI message explains why the tutor chose an activity.

## 14. Page Roles

Dashboard is overview; Subjects starts/switches subject; Learning Path is optional graph; Lesson is primary guided flow; Quiz/Flashcards/Mindmap are optional direct pages and guided-session renderers; Notebook/Rewards/XAI remain supporting pages.

## 15. Backend Routes Used

`POST /auth/register`, `POST /auth/login`, `GET /learner/context/{learner_id}`, `POST /learner/select-subject`, `GET /tutor/adaptive-session/{learner_id}`, `GET /lesson/{learner_id}/{concept_id}?view=...&difficulty=...`, `GET /assessment/{learner_id}/{concept_id}?difficulty=...`, `POST /answer/submit`, `POST /code/run`, `POST /doubt/ask`, `GET /flashcards/{learner_id}`, `GET /flashcards/{learner_id}/{concept_id}`, `GET /mindmap/{concept_id}`, `GET /reward/{learner_id}`, `GET /xai/{learner_id}`, `GET /revision/{learner_id}`, `GET /retention/{learner_id}`.

## 16. DB Tables Used

`users`, `learner_profile`, `learner_session_log`, `quiz_results`, `knowledge_state`, `behaviour_state`, `learner_mistake_log`, `learner_doubt_log`, `revision_card`, `revision_schedule`, `reward_event_log`, `learner_xp_state`, `learner_streak_state`, `learner_badges`, `concept_unlock_state`, `teaching_strategy_log`, `xai_log`, `concept_id_map`, and subject DB `concept_resources`.

## 17. Remaining Mock-Only Parts

Flashcard rating persistence does not yet write a dedicated revision-feedback endpoint. Some repeated-failure escalation is deterministic frontend logic when backend model output is absent. Sanvia remains comparison-only.

## 18. Demo Readiness

Ready for final guided demo with backend `http://127.0.0.1:8010`.

## 19. Build And Test Results

- Frontend `npm run build`: passed
- Frontend `npm run lint`: passed
- Backend `python -m scripts.test_api_routes_smoke`: passed
- Backend `python -m scripts.test_frontend_response_builder`: passed
- Notes: backend checks emitted existing ML/library warnings only; no route/test failure.
