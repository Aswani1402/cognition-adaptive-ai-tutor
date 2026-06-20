# Full Frontend/Backend Model Connection Report

- Status: success
- Website flow: Register/Login -> Subject -> Guided Session -> Teaching -> Assessment -> Feedback -> Revision -> Progress
- Streamlit decision: A separate Streamlit dashboard is not required because the project already has a web frontend. Streamlit may be used only as an optional internal debugging tool.

## Module Connection Table

| Module | Backend files | API route | Frontend component/page | DB table | Inputs required | Inputs currently received? | Output produced | Connected? | Missing/Issue | Fix recommendation |
|---|---|---|---|---|---|---|---|---|---|---|
| Authentication | tutor.api.auth_routes | /auth/register, /auth/login | src/pages/RegisterPage.tsx, src/pages/LoginPage.tsx | users, learner_profile | name, email, password | yes | user_id, learner_id, access_token | True | none | No action required. |
| Learner profile/session | tutor.api.learner_routes | /learner/context/{learner_id}, /learner/session/{learner_id} | src/context/LearnerSessionContext.tsx, src/pages/DashboardPage.tsx | learner_profile, learner_session_log | learner_id | yes | active subject, concept, returning learner context | True | none | No action required. |
| Knowledge Tracing | tutor.knowledge_state, tutor.api.evaluation_routes | /answer/submit, /ai/evidence/{learner_id} | src/components/assessment/AssessmentRenderer.tsx | knowledge_state, quiz_results | learner_id, concept_id, score, difficulty, question_type | yes | kt_update and mastery state | True | none | No action required. |
| Behaviour Modeling | tutor.behaviour, tutor.api.evaluation_routes | /answer/submit | src/components/assessment/AssessmentRenderer.tsx, src/components/assessment/CodeConsole.tsx | behaviour_state | time_taken_sec, confidence, hint_count, option_change_count, answer_change_count, run_code_count, attempt_count | yes | behaviour_update | True | none | No action required. |
| Concept Dependency | tutor.concept_dependency | /learner/select-subject, /path/{learner_id}/{subject:path} | src/pages/SubjectsPage.tsx, src/pages/LearningPathPage.tsx | concept_unlock_state, concept_id_map | subject, concept_id, difficulty_passed | yes | locked/current/mastered path nodes | True | none | No action required. |
| Adaptive Path | tutor.concept_dependency.learned_adaptive_path_ranker | /adaptive-path/{learner_id}, /answer/submit | src/pages/LearningPathPage.tsx | knowledge_state, behaviour_state, concept_unlock_state | mastery, behaviour risk, revision due | yes | path_update | True | none | No action required. |
| Teaching Strategy | tutor.strategy, tutor.api.integration_routes | /lesson/{learner_id}/{concept_id} | src/pages/LessonPage.tsx | teaching_strategy_log | learner_id, subject, concept_id, difficulty | yes | selected teaching view | True | none | No action required. |
| Policy/RL | tutor.policy, tutor.RL, tutor.api.evaluation_routes | /answer/submit, /ai/evidence/{learner_id} | src/components/ai/PolicyDecisionCard.tsx | concept_unlock_state | path candidates, safe action mask | yes | policy_update warning/safe decision | True | none | No action required. |
| RAG | tutor.rag, tutor.api.integration_routes | /lesson/{learner_id}/{concept_id}, /doubt/ask, /mindmap/{concept_id} | src/components/ai/RAGGroundingCard.tsx | concept_resources | subject, concept_id | yes | rag_update/source sections | True | none | No action required. |
| CogniTutorLM connector / generation artifacts | tutor.generation.cognitutor_lm_connector | /generation/cognitutor, /generation/coverage/{learner_id} | src/components/ai/GenerationCoverageCard.tsx | concept_resources | task_type, concept content | yes | llm_generation or warning fallback | True | none | No action required. |
| LLM generation task coverage | tutor.generation | /generation/coverage/{learner_id} | src/components/ai/GenerationCoverageCard.tsx | n/a | task categories | yes | coverage report/card | True | none | No action required. |
| Agentic orchestration trace | tutor.agents.orchestration_trace | /agentic/trace/{learner_id} | src/components/ai/AgentTraceCard.tsx | learner_session_log | module outputs | yes | orchestration trace warning/success | True | none | No action required. |
| Long-term personalization / Notebook memory | tutor.memory, tutor.api.learner_routes | /notebook/{learner_id}, /learner/notebook/search/{learner_id}, /learner/personalization/{learner_id} | src/pages/NotebookPage.tsx | learner_mistake_log, learner_doubt_log, learner_session_log, revision_card | mistakes, doubts, sessions | yes | notebook/search/personalization | True | none | No action required. |
| Forgetting / Retention | tutor.forgetting.retention_predictor | /retention/{learner_id}, /revision/{learner_id} | src/pages/FlashcardsPage.tsx, src/pages/ReviewerInsightsPage.tsx | revision_schedule, knowledge_state | last_active_at, mastery, revision due | yes | retention/revision packet | True | none | No action required. |
| Assessment generator/question bank | tutor.assessment, tutor.api.integration_routes | /assessment/{learner_id}/{concept_id} | src/pages/QuizPage.tsx | concept_resources | subject, concept_id, difficulty | yes | subject-specific questions | True | none | No action required. |
| Answer evaluator | tutor.evaluation.answer_evaluator | /answer/submit | src/components/assessment/AssessmentRenderer.tsx | quiz_results | answer, correct answer, question type | yes | score, feedback, mistake type | True | none | No action required. |
| Safe code runner | tutor.evaluation.code_runner | /code/run | src/components/assessment/CodeConsole.tsx | n/a | code, language, test_cases | yes | stdout/stderr/test results | True | none | No action required. |
| Code/debug/output evaluator | tutor.evaluation.code_runner, tutor.evaluation.answer_evaluator | /answer/submit, /code/run | src/components/assessment/CodeConsole.tsx | quiz_results | code, expected output | yes | code score/feedback | True | none | No action required. |
| Mistake analysis | tutor.evaluation, tutor.system.user_persistence_store | /answer/submit, /mistakes/{learner_id} | src/pages/MistakesPage.tsx | learner_mistake_log | evaluation result | yes | mistake log/review | True | none | No action required. |
| Hint policy | tutor.api.integration_routes | /hint/predict | src/components/assessment/AssessmentRenderer.tsx | behaviour_state | question context, hint_count, mastery, behaviour risk | yes | hint response | True | none | No action required. |
| Doubt handler | tutor.doubt.doubt_intent_classifier, tutor.api.doubt_routes | /doubt/ask | src/components/doubt/DoubtPanel.tsx | learner_doubt_log | doubt_text, subject, concept_id | yes | classified/grounded answer | True | none | No action required. |
| Flashcards | tutor.api.integration_routes | /flashcards/{learner_id}/{concept_id} | src/pages/FlashcardsPage.tsx | revision_card, concept_resources | learner_id, concept_id, subject | yes | flashcards | True | none | No action required. |
| Mindmap | tutor.api.integration_routes | /mindmap/{concept_id} | src/pages/MindMapPage.tsx | concept_resources | concept_id, subject | yes | mindmap | True | none | No action required. |
| Revision summary / revision plan | tutor.memory.revision_scheduler, tutor.api.revision_routes | /revision/{learner_id} | src/pages/ReviewerInsightsPage.tsx | revision_schedule, revision_card | mistakes, retention, mastery | yes | revision plan | True | none | No action required. |
| Rewards / XP / streak | tutor.api.reward_routes | /reward/{learner_id}, /answer/submit | src/pages/RewardsPage.tsx | learner_xp_state, learner_streak_state, reward_event_log, learner_badges | score, concept, activity | yes | reward state | True | none | No action required. |
| XAI | tutor.api.xai_routes | /xai/{learner_id}, /ai/evidence/{learner_id} | src/pages/XAIPage.tsx | knowledge_state, behaviour_state | decision evidence | yes | learner/reviewer explanation | True | none | No action required. |
| Frontend API connection | n/a | n/a | src/lib/api.ts | n/a | VITE_API_BASE_URL | yes | backend requests/fallback logging | True | none | No action required. |
| Database persistence | tutor.api.dependencies | /answer/submit, /learner/select-subject | src/lib/api.ts | users, learner_profile, quiz_results, knowledge_state, behaviour_state, learner_mistake_log, revision_schedule, reward_event_log, learner_session_log | learner events | yes | SQLite state | True | none | No action required. |
| Evaluation reports/charts | n/a | n/a | src/pages/ReviewerInsightsPage.tsx | n/a | evaluation_outputs | yes | report/chart inventory | True | none | No action required. |

## Required Status Sections

1. Proper website flow status: learner-first flow preserved.
2. Frontend-backend connection status: API layer uses `VITE_API_BASE_URL`, status badge, request logs, and fallback logs.
3. Auth and user DB persistence: register/login routes use `users` and `learner_profile`; password hash is required.
4. Subject context status: global learner session context drives subject/concept/difficulty.
5. Guided session flow status: guided teaching/assessment/feedback/revision path remains the primary UX.
6. Difficulty easy->medium->hard status: `/answer/submit` enforces next concept only after hard pass.
7. Assessment type coverage: MCQ, fill blank, true/false, debug, output prediction, syntax, coding, transfer, challenge, explanation, drag, match, puzzle, flashcard recall are rendered or warning/fallback documented.
8. Behaviour input collection status: frontend sends time, confidence, hint, option, answer, code-run, attempt, and wrong-attempt signals.
9. KT input/output status: answer submit returns `kt_update` and writes `knowledge_state` when available.
10. Concept dependency/adaptive path status: answer submit returns `path_update`; subject selection updates first concept/unlock state.
11. Policy/RL status: safe bridge/warning evidence only, not raw final authority.
12. RAG status: concept resources/RAG grounding are exposed through lesson/doubt/mindmap/evidence routes.
13. LLM/CogniTutorLM status: connector/artifact/fallback is reported honestly.
14. LLM generation task coverage: see generation coverage table below.
15. Agentic orchestration status: shown as orchestration trace, not fully autonomous agent.
16. Long-term personalization status: notebook, mistakes, doubts, and revision routes connected.
17. Forgetting/retention status: retention/revision routes connected or warning/fallback.
18. Notebook memory status: notebook/search pages use current learner.
19. Hint/doubt status: hint and doubt routes connected with fallback warnings.
20. Flashcard/mindmap/revision status: subject-aware routes connected.
21. Code console status: run/submit/output/error/test panels and run count tracking present.
22. XAI/Why-this status: compact learner Why-this and reviewer XAI/evidence only.
23. Teacher/reviewer analytics status: `ReviewerInsightsPage` is available inside the web app.
24. DB tables/columns used: listed in module table and JSON report.
25. Per-module evaluation/chart inventory: see inventory section.
26. Missing features: warnings are listed per row; unavailable models remain fallback/warning.
27. Fixes applied: code console metadata/tracking, answer response contracts, reviewer insights, audit/tests/reports.
28. Remaining limitations: manual browser checks are still required; warnings do not imply live model support.
29. Demo readiness: Sanvia remains comparison-only/pending because base model is missing.

## Generation Coverage

| Task category | Task type | Frontend renderer | Backend source | Status | Missing/limitation |
|---|---|---|---|---|---|
| Teaching views | explanation | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | definition_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | simple_example_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | step_by_step_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | analogy_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | code_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | misconception_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | debug_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | output_prediction_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | transfer_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | challenge_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | revision_summary_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | comparison_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Teaching views | real_world_connection_view | SelectedTeachingViewRenderer/LessonPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | mcq | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | debug_task | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | output_prediction | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | transfer_question | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | challenge_question | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | explanation_check | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | syntax_completion | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | coding_prompt | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | code_reasoning_task | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | fill_in_the_blank | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Assessment | true_or_false | AssessmentRenderer | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | revision_note | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | revision_summary | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | weakness_review | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | daily_review | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | personal_revision_plan | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | recommended_revision_views | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Revision | spaced_repetition_card | ReviewerInsightsPage/FlashcardDeck/MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | concept_recall_flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | misconception_flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | example_flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | debug_flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | personal_flashcards | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Flashcards | syntax_flashcard | FlashcardDeck | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Mindmaps | mindmap | MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Mindmaps | concept_mindmap | MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Mindmaps | comparison_mindmap | MindMapView | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | correct_answer_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | wrong_answer_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | partial_answer_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | debug_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | output_prediction_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | next_step_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Feedback | encouragement_feedback | FeedbackCard | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | small_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | guided_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | worked_example_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | debug_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | syntax_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | output_prediction_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | misconception_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | next_step_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Hints | analogy_hint | HintPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | concept_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | syntax_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | debug_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | output_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | example_request_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | revision_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | next_step_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Doubt answers | comparison_doubt_answer | DoubtPanel | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | notebook_summary | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | mistake_summary | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | revision_plan | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | comeback_summary | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | returning_learner_summary | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Notebook/memory | progress_insight | NotebookPage | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | practice_question | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | transfer_task | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | real_world_application_question | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | debug_challenge | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | output_prediction_challenge | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Practice/challenge | multi_step_challenge | PuzzlePage/CodeConsole | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | If CogniTutorLM artifact is unavailable, backend must return warning/fallback. |
| Voice-ready scripts | voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | teaching_voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | revision_voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | mistake_feedback_voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | doubt_explanation_voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | encouragement_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | next_step_guidance_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |
| Voice-ready scripts | concept_intro_voice_script | text script only | CogniTutorLM/RAG/concept_resources/fallback | connected_or_warning_fallback | Voice-ready scripts are text only, not audio/TTS. |

## Per-module Evaluation/Chart Inventory

- KT model comparison: success (38 artifacts)
- Behaviour model comparison: success (38 artifacts)
- Teaching strategy model: success (15 artifacts)
- XAI/surrogate: success (23 artifacts)
- RL/policy comparison: success (26 artifacts)
- RAG retrieval/grounding: success (27 artifacts)
- LLM generation comparison: success (19 artifacts)
- Answer evaluator: success (10 artifacts)
- Hint policy: success (18 artifacts)
- Adaptive path: success (11 artifacts)
- Retention/forgetting: success (7 artifacts)
- Notebook search: success (34 artifacts)
- Reward/gamification: success (13 artifacts)
- Human evaluation setup: success (8 artifacts)
- Full backend smoke test: success (2 artifacts)
- Overall system evaluation: success (7 artifacts)
- Final chart inventory: success (7 artifacts)
- Final evidence pack: success (16 artifacts)
