# Frontend Full Feature Coverage Report

Generated: 2026-05-13 15:28:47 +05:30

## 1. Teaching Views Coverage

| View | Frontend support | Backend connected | Notes |
|---|---:|---:|---|
| explanation_view | Yes | GET `/lesson/{learner_id}/{concept_id}?view=explanation_view` | Replaces legacy `explanation`; highlighted as current method. |
| definition_view | Yes | Yes | Structured definition/explanation sections render when present. |
| simple_example_view | Yes | Yes | Examples render as section content. |
| step_by_step_view | Yes | Yes | Uses key points as ordered steps. |
| analogy_view | Yes | Yes | Single selected view only. |
| code_view | Yes | Yes | Code/syntax block supported. |
| misconception_view | Yes | Yes | Common mistakes and correction supported. |
| debug_view | Yes | Yes | Available as guided view button. |
| output_prediction_view | Yes | Yes | Available as guided view button. |
| transfer_view | Yes | Yes | Available as guided view button. |
| challenge_view | Yes | Yes | Available as guided view button. |
| revision_summary_view | Yes | Yes | Available as guided view button. |
| comparison_view | Yes | Yes | Available as guided view button. |
| real_world_connection_view | Yes | Yes | Available as guided view button. |

## 2. Assessment Types Coverage

| Type | Renderer support | Notes |
|---|---:|---|
| mcq | Yes | Option-change count tracked. |
| fill_in_the_blank | Yes | Blank answers and answer-change count tracked. |
| true_false | Yes | Defaults to True/False options when backend omits options. |
| output_prediction | Yes | Output input and tracing card supported. |
| debug_task | Yes | Uses `CodeConsole`. |
| syntax_completion | Yes | Syntax card and text answer supported. |
| coding_prompt | Yes | Uses `CodeConsole`. |
| code_reasoning_task | Yes | Uses coding card/console path. |
| explanation_check | Yes | Text answer path. |
| transfer_question | Yes | Transfer card. |
| challenge_question | Yes | Challenge card. |
| practice_question | Yes | Text fallback. |
| puzzle/gamified task | Yes | Challenge-style card fallback. |
| code_tracing/output reasoning | Yes | Output prediction renderer. |

## 3. Hint Types Coverage

| Hint type | UI support |
|---|---:|
| small_hint | Yes |
| guided_hint | Yes |
| worked_example_hint | Yes |
| debug_hint | Yes |
| syntax_hint | Yes |
| output_prediction_hint | Yes |
| misconception_hint | Yes |
| next_step_hint | Yes |
| analogy_hint | Yes |

Hints use POST `/hint/predict`, display type labels, and expose `Next hint` only when multiple levels are available.

## 4. Feedback Types Coverage

| Feedback type | UI support |
|---|---:|
| correct_answer_feedback | Yes |
| wrong_answer_feedback | Yes |
| partial_answer_feedback | Yes |
| debug_feedback | Yes |
| output_prediction_feedback | Yes |
| next_step_feedback | Yes |
| encouragement_feedback | Yes |
| mistake_feedback | Yes |

Feedback panels show score/label, learner answer, correct answer, explanation, mistake type, weakest skill, next action, mascot script, Try Similar Question, Review with Recommended Teaching View, and Continue.

## 5. Flashcard Types Coverage

| Type | UI support |
|---|---:|
| concept_recall_flashcard | Yes |
| misconception_flashcard | Yes |
| example_flashcard | Yes |
| debug_flashcard | Yes |
| syntax_flashcard | Yes |
| personal_flashcard | Yes |
| spaced_repetition_card | Yes |

Flashcards use GET `/flashcards/{learner_id}/{concept_id}`, show multiple cards, front/back flip, card counter, Again/Hard/Good/Easy rating, and a save-to-notebook affordance.

## 6. Mindmap Types Coverage

| Type | UI support |
|---|---:|
| concept_mindmap | Yes |
| comparison_mindmap | Yes |
| revision_mindmap | Yes |
| misconception_mindmap | Yes, if backend provides variant |

Mindmaps use GET `/mindmap/{concept_id}?subject=...`, render a visual central node with branch cards, and keep subject/concept context.

## 7. Voice/Mascot Script Coverage

| Script type | UI support |
|---|---:|
| concept_intro_voice_script | Yes |
| teaching_voice_script | Yes |
| revision_voice_script | Yes |
| mistake_feedback_voice_script | Yes |
| doubt_explanation_voice_script | Yes |
| encouragement_script | Yes |
| next_step_guidance_script | Yes |
| reward_celebration_script | Yes |

Cogni guide cards and teaching/feedback panels show backend scripts when present and deterministic safe text otherwise. The UI labels these as guide messages or voice-ready scripts; it does not claim audio/TTS.

## 8. Notebook/Revision/Retention Coverage

Notebook uses GET `/notebook/{learner_id}` and shows weak concepts, mistakes, doubts, summaries, plans, flashcards, and search. Revision uses GET `/revision/{learner_id}` in reviewer/guided flow. Retention uses GET `/retention/{learner_id}` to route returning/high-risk learners to revision before new content.

## 9. KT/Behaviour/RL/XAI Frontend Visibility

Learner-friendly reasoning appears as "Why this?" and "Why this view?". Reviewer/XAI pages show KT, behaviour, adaptive path, policy/RL, model/fallback/decision reason, reward, revision, RAG, generation status, and agentic trace when backend provides them.

## 10. RAG Evidence Visibility

Teaching content displays learner-friendly RAG grounding summaries. XAI/Reviewer analytics expose detailed RAG evidence through `AIEvidencePanel`.

## 11. Agentic Trace Frontend Visibility

XAI and Reviewer pages call GET `/agentic/trace/{learner_id}` and merge the trace into evidence if `/ai/evidence/{learner_id}` does not already include it.

## 12. API Functions Added/Updated

Updated `src/lib/api.ts`: `registerUser`, `loginUser`, `selectSubject`, `getLearnerContext`, `getAdaptiveSession`, `getLesson`, `getAssessment`, `submitAnswer`, `getSimilarQuestion`, `runCode`, `askDoubt`, `getHint`, `getFlashcards`, `getMindmap`, `getNotebook`, `getRevision`, `getRetentionPrediction`, `getRewardState`, `getXAI`, `getAIEvidence`, `getAgenticTrace`, `getGenerationCoverage`. All use `VITE_API_BASE_URL` through shared helpers.

## 13. Backend Routes Used

GET `/lesson/{learner_id}/{concept_id}?view=...`; GET `/assessment/{learner_id}/{concept_id}`; POST `/answer/submit`; POST `/hint/predict`; POST `/question/similar`; POST `/code/run`; GET `/flashcards/{learner_id}/{concept_id}`; GET `/mindmap/{concept_id}?subject=...`; GET `/notebook/{learner_id}`; GET `/revision/{learner_id}`; GET `/retention/{learner_id}`; GET `/reward/{learner_id}`; GET `/xai/{learner_id}`; GET `/ai/evidence/{learner_id}`; GET `/agentic/trace/{learner_id}`; GET `/generation/coverage/{learner_id}`.

## 14. Mock-Only/Fallback Parts

Fallback lesson/assessment/flashcard/mindmap content remains only for backend unavailable states and is marked as fallback/mock mode. No Sanvia live connection was added. Save-to-notebook for flashcards remains an affordance unless the backend persists that action through answer/notebook routes.

## 15. Remaining Issues

Manual browser checklist was not fully automated in this run. Similar-question route is called as POST `/question/similar`; if the backend exposes a different path, add an alias or adjust `getSimilarQuestion`. Some backend model warnings report scikit-learn pickle version mismatch during smoke tests, but tests still passed.

## 16. Build/Lint/Test Results

| Check | Result |
|---|---|
| `npm run build` | Passed |
| `npm run lint` | Passed |
| `python -m scripts.test_api_routes_smoke` | Passed |
| `python -m scripts.test_frontend_response_builder` | Passed |
| `python -m scripts.test_ai_evidence_route` | Passed |
| `python -m scripts.test_agentic_trace_route` | Passed |
| `python -m scripts.test_agentic_answer_submit_connection` | Passed |
| Vite dev server | Running at `http://127.0.0.1:5173` |
