# CogniTutorLM Frontend API Contract

## 1. Purpose

This contract tells the KP frontend how to consume the adaptive tutor backend without parsing the full raw integrated JSON response.

The frontend should use compact, stable response sections for teaching, assessment, learner state, feedback, adaptive hints, reward/progression, doubt handling, voice scripts, and optional CogniTutorLM comparison output. Full raw backend/module outputs can remain available for debug or teacher views, but normal learner screens should use the simplified contract below.

## 2. Backend Source Files

Primary backend entry points and source files:

- `tutor/system/run_integrated_tutor_once.py`
- `tutor/generation/cognitutor_lm_connector.py`
- `tutor/generation/voice_script_generator.py`
- `tutor/policy/adaptive_hint_policy.py`
- `tutor/policy/learned_hint_policy.py`
- `tutor/concept_dependency/learned_adaptive_path_ranker.py`
- `tutor/forgetting/retention_predictor.py`
- `scripts/data/export_behaviour_annotation_dataset.py` (offline behaviour annotation export)
- `docs/behaviour_human_labelling_guide.md` and `docs/behaviour_annotation_schema.md` (human validation workflow; not runtime API)
- `scripts/data/export_human_evaluation_items.py` plus `docs/human_evaluation_rubric.md` and `docs/human_evaluation_protocol.md` (offline human-rated evaluation sheets; not runtime API)
- `tutor/evaluation/hint_generator.py`
- `tutor/system/frontend_response_builder.py` if available or added later
- `CogniTutor_LM_from_scratch/src/tutor_lm_service.py` through the connector only

Important integration rule:

- The frontend should consume `cognitutor_lm_output` as optional comparison/demo output.
- The main teaching content, frontend teaching view, assessment, evaluation, KT, behaviour, reward, RAG, and XAI outputs remain the main project pipeline outputs.
- Do not call or depend on `CogniTutor_LM_from_scratch` directly from the frontend.
- Voice scripts are TTS-ready text only. The backend does not call external TTS, train a voice model, or generate audio files.

## 3. Core Frontend Flow

1. Learner opens app.
2. Backend returns adaptive session.
3. Frontend shows one selected teaching card.
4. Frontend shows one question at a time.
5. Learner submits answer.
6. Backend evaluates answer.
7. Frontend shows feedback and next action.
8. Learner can run code for coding/debug/output tasks.
9. Learner can ask a doubt.
10. Returning learner can receive comeback/revision packet.

## 4. API Endpoint Contract

### POST `/auth/register`

Purpose:

Create a learner account using local salted PBKDF2 password hashing and return a token-ready auth payload.

Request body:

- `name`
- `email`
- `password`

Response fields:

- `status`
- `user_id`
- `learner_id`
- `access_token`
- `token_type`
- `auth_mode`

Example response:

```json
{
  "status": "success",
  "user_id": "user_abc123",
  "learner_id": "learner_def456",
  "access_token": "base64payload.signature",
  "token_type": "bearer",
  "auth_mode": "pbkdf2_local"
}
```

Duplicate emails return an error-style response and should be shown as an account-already-exists message.

### POST `/auth/login`

Purpose:

Verify email/password using the stored PBKDF2 password hash and return a token-ready auth payload.

Request body:

- `email`
- `password`

Response fields:

- `status`
- `user_id`
- `learner_id`
- `access_token`
- `token_type`
- `auth_mode`
- `last_login_at`

Wrong passwords return HTTP 401.

### Authorization Header

Future protected routes should receive the token as:

```http
Authorization: Bearer <access_token>
```

Frontend behavior:

- Store the token safely for the current user session.
- Send the bearer token to protected routes once backend route protection is enabled.
- Treat `auth_mode: "pbkdf2_local"` as local project authentication, not OAuth.

### GET `/api/adaptive-session`

Purpose:

Return current teaching view, assessment questions, learner state, reward/progression, and CogniTutorLM output.

Request query:

- `learner_id`
- `subject` optional
- `concept_id` optional

Response fields:

- `learner_id`
- `demo_summary`
- `cognitutor_lm_output`
- `teaching_card`
- `assessment`
- `frontend_teaching_view_output`
- `reward`
- `progress`
- `xai`
- `voice_script`
- `voice_scripts`
- `notebook_summary`
- `next_action`

### POST `/api/submit-answer`

Purpose:

Submit learner answer and get evaluation, feedback, and progression update.

Request body:

- `learner_id`
- `question_id`
- `question_type`
- `concept_id`
- `concept_name`
- `learner_answer`
- `code` optional
- `selected_view` optional

Response fields:

- `status`
- `score`
- `is_correct`
- `mistake_type`
- `feedback`
- `adaptive_hint`
- `next_signal`
- `progression_action`
- `reward_xp_awarded`
- `next_recommended_view`

### `adaptive_hint` in submit-answer responses

```json
{
  "status": "success",
  "hint_type": "guided_hint",
  "hint_text": "Try this in two steps. First, identify what the question is asking about Variables. Next, use this clue: variables are names linked to values. What would change in your answer?",
  "support_need": 0.52,
  "frontend_component": "AdaptiveHintCard"
}
```

The backend selects hints using evaluation score, mistake type, weakest skill, behaviour risk, mastery score, and previous hint usage. It should not reveal the full answer unless the selected hint is a `worked_example`.

### POST `/api/run-code`

Purpose:

Run code safely for debug, coding, and output questions.

Request body:

- `learner_id`
- `code`
- `expected_output` optional
- `question_id` optional

Response fields:

- `status`
- `stdout`
- `stderr`
- `error`
- `score`
- `test_results`
- `safety_status`

### POST `/api/ask-doubt`

Purpose:

Send learner doubt and receive RAG-grounded explanation.

Request body:

- `learner_id`
- `learner_doubt`
- `concept_id` optional
- `concept_name` optional
- `domain` optional

Response fields:

- `status`
- `doubt_type`
- `concept_id`
- `concept_name`
- `domain`
- `context_source`
- `rag_connected`
- `rag_success`
- `doubt_answer`
- `retrieved_sections`
- `code_snippet`
- `followup_check`
- `next_action`

### POST `/api/voice-script`

Purpose:

Generate short, learner-friendly text that the frontend can pass to browser Text-to-Speech or a speech service.

Request body:

- `script_type`
- `concept_name`
- `teaching_view` optional
- `difficulty` optional
- `learner_level` optional
- `mistake_type` optional
- `weakest_skill` optional
- `evaluation_label` optional
- `doubt_intent` optional
- `next_action` optional
- `key_points` optional
- `example` optional

Supported `script_type` values:

- `teaching_explanation`
- `revision_summary`
- `mistake_feedback`
- `doubt_explanation`
- `encouragement`
- `next_step_guidance`

Response fields:

- `status`
- `module`
- `script_type`
- `concept_name`
- `text`
- `tts_ready`
- `estimated_duration_sec`
- `tone`
- `frontend_component`
- `limitations`

### GET `/api/returning-learner`

Purpose:

Return comeback/revision packet for a returning learner.

Request query:

- `learner_id`

Response fields:

- `mode`
- `time_gap_category`
- `last_concept`
- `comeback_summary`
- `weak_concepts`
- `weak_question_types`
- `recommended_views`
- `selected_view`
- `teaching_card`
- `warmup_questions`
- `next_action`

### GET `/learner/notebook/search/{learner_id}`

Purpose:

Search learner-specific notebook memory such as mistakes, doubts, revision cards, session notes, and weak concepts.

Request query:

- `q`
- `top_k` optional, default `5`
- `source_filter` optional

Example:

```http
GET /learner/notebook/search/learner_14?q=debug%20mistakes&top_k=5
```

Response fields:

- `status`
- `module`
- `learner_id`
- `query`
- `method`
- `result_count`
- `results`
- `fallback_used`

Sample response:

```json
{
  "status": "success",
  "module": "SemanticNotebookSearch",
  "learner_id": "learner_14",
  "query": "debug mistakes",
  "method": "tfidf_cosine",
  "result_count": 2,
  "results": [
    {
      "source_table": "learner_mistake_log",
      "record_id": "101",
      "concept_id": "variables",
      "concept_name": "Variables",
      "summary": "Variables mistake: syntax_misunderstanding. Variable names cannot start with a number.",
      "score": 0.72,
      "timestamp": "2026-05-09T12:00:00+00:00",
      "tags": ["mistake", "weakness", "syntax_misunderstanding"]
    }
  ],
  "fallback_used": false
}
```

Frontend behavior:

- Render the search UI as `NotebookSearchPanel`.
- Render each result as `LearnerMemoryResultCard`.
- Show `method` and `fallback_used` only in debug/teacher mode unless needed.

### GET `/learner/notebook/summary/{learner_id}`

Purpose:

Return a NotebookLM-style summary of learner weaknesses, recent doubts, and revision focus.

Response fields:

- `status`
- `module`
- `learner_id`
- `weak_concepts`
- `dominant_mistake_types`
- `weak_question_types`
- `recent_doubts`
- `recommended_revision_focus`

Frontend behavior:

- Render summary as `WeaknessSummaryCard`.
- Use `weak_concepts` and `recommended_revision_focus` to suggest revision tabs or cards.
- Keep retrieved memory learner-specific and do not mix it with another learner's context.

### RAG Semantic Grounding Support

Backend RAG responses may include a semantic grounding support payload when generated answers are checked against retrieved concept context.

```json
{
  "status": "success",
  "module": "RAGSemanticSupportChecker",
  "support_score": 0.82,
  "context_similarity": 0.76,
  "keypoint_coverage": 0.71,
  "unsupported_terms_count": 1,
  "unsupported_terms": ["reassignment"],
  "safe_to_generate": true,
  "verdict": "supported",
  "evidence_sections_used": ["definition", "key_points"],
  "fallback_used": false
}
```

Frontend behavior:

- Render semantic grounding details as `RAGGroundingEvidenceCard`.
- Show `verdict`, `support_score`, `evidence_sections_used`, and `unsupported_terms` in a collapsible evidence panel.
- If `safe_to_generate` is false, show a cautious answer or ask the backend for a safer grounded response.
- Treat `unsupported_terms` as evidence warnings, not automatic proof that the answer is wrong.

### GET `/api/progress`

Purpose:

Return XP, streak, path, and progress state.

Request query:

- `learner_id`

Response fields:

- `total_xp`
- `daily_xp`
- `weekly_xp`
- `current_level`
- `current_streak`
- `longest_streak`
- `concept_cleared`
- `promotion_allowed`
- `next_concept_unlocked`
- `path_nodes`

## 5. Frontend Component Mapping

### Teaching

- `definition_view` -> `TeachingCard`
- `simple_example_view` -> `ExampleTeachingCard`
- `step_by_step_view` -> `StepTeachingCard`
- `code_view` -> `CodeTeachingCard`
- `analogy_view` -> `AnalogyCard`
- `misconception_view` -> `MisconceptionCard`
- `debug_view` -> `DebugTeachingCard`
- `output_prediction_view` -> `OutputPredictionTeachingCard`
- `transfer_view` -> `TransferCard`
- `challenge_view` -> `ChallengeCard`
- `revision_summary_view` -> `RevisionSummaryCard`
- `flashcard_view` -> `FlashcardDeck`
- `mindmap_view` -> `MindmapView`

### Assessment

- `mcq` -> `MCQQuestionCard`
- `debug_task` / `debug` -> `DebugQuestionCard`
- `output_prediction` -> `OutputPredictionCard`
- `transfer_question` / `transfer` -> `TransferQuestionCard`
- `challenge_question` / `challenge` -> `ChallengeQuestionCard`
- `explanation_check` / `explanation` -> `ExplanationAnswerCard`
- `coding_question` -> `CodeEditorQuestionCard`
- `syntax_completion` -> `SyntaxCompletionCard`
- `code_tracing` -> `CodeTracingCard`
- `fill_blank` -> `FillBlankCard`
- `arrange_steps` -> `ArrangeStepsCard`
- `match_pairs` -> `MatchPairsCard`
- `drag_order` -> `DragOrderCard`
- `code_puzzle` -> `CodePuzzleCard`

### Voice

- `teaching_explanation` -> `VoiceScriptCard`
- `revision_summary` -> `VoiceScriptCard`
- `mistake_feedback` -> `VoiceScriptCard`
- `doubt_explanation` -> `VoiceScriptCard`
- `encouragement` -> `VoiceScriptCard`
- `next_step_guidance` -> `VoiceScriptCard`

### Hints

- `small_hint` -> `AdaptiveHintCard`
- `guided_hint` -> `AdaptiveHintCard`
- `worked_example` -> `AdaptiveHintCard`
- `misconception_hint` -> `AdaptiveHintCard`
- `debug_hint` -> `AdaptiveHintCard`
- `output_prediction_hint` -> `AdaptiveHintCard`
- `syntax_hint` -> `AdaptiveHintCard`
- `next_step_hint` -> `AdaptiveHintCard`

### Notebook Memory

- Notebook search panel -> `NotebookSearchPanel`
- Notebook memory result -> `LearnerMemoryResultCard`
- Weakness summary -> `WeaknessSummaryCard`

### RAG Evidence

- Semantic grounding support -> `RAGGroundingEvidenceCard`

## 6. Required Frontend Rules

- Show only the selected teaching view first.
- Do not render every available view at once.
- Show questions one at a time.
- If `adaptive_hint.status == "success"`, render the hint with `AdaptiveHintCard` after an answer attempt or when the learner asks for help.
- For `small_hint` and `guided_hint`, keep the answer hidden and prompt the learner to retry.
- For `worked_example`, show a similar example and still let the learner answer the current question.
- If `frontend_contract.show_puzzle_panel` is true, render `assessment.puzzle_questions` with the mapped interactive card components.
- If `frontend_contract.show_voice_script_card` is true, render `voice_script` with `VoiceScriptCard`.
- Use `voice_script.text` for browser Text-to-Speech or a frontend speech service only when `voice_script.tts_ready` is true.
- Do not expect backend audio URLs or audio files in the voice script payload.
- Show code editor only for debug, coding, output prediction, syntax completion, or code tracing tasks.
- Show RAG source/evidence only in a collapsible source panel.
- Show XAI explanation as "Why this recommendation?".
- Show comeback summary only for returning learner mode.
- Keep fallback/error messages user-friendly.

## 7. Sample Adaptive Session Response

```json
{
  "learner_id": "14",
  "demo_summary": {
    "concept_id": "1",
    "concept_name": "Variables",
    "domain": "Python",
    "teaching_view": "definition_view",
    "frontend_selected_view": "definition_view",
    "difficulty": "easy",
    "assessment_types": ["mcq", "explanation_check"],
    "next_action": "answer_warmup_question"
  },
  "cognitutor_lm_output": {
    "status": "success",
    "mode": "optional_connector_demo",
    "source": "cognitutor_lm_connector",
    "adaptive_session": {
      "selected_view": "definition_view",
      "assessment_count": 2
    }
  },
  "teaching_card": {
    "title": "Variables",
    "content": "A variable is a name that stores a value so it can be reused later.",
    "display_type": "teaching_card"
  },
  "assessment": {
    "question_count": 2,
    "questions": [
      {
        "question_id": "Q1",
        "question_type": "mcq",
        "prompt": "What does a variable do?",
        "options": ["Stores a value", "Deletes a program", "Runs the internet", "Changes Python syntax"]
      },
      {
        "question_id": "Q2",
        "question_type": "explanation_check",
        "prompt": "Explain why variables are useful."
      }
    ]
  },
  "frontend_teaching_view_output": {
    "selected_teaching_view": "definition_view",
    "selected_view": {
      "title": "Variables",
      "content": "A variable is a named storage location for a value.",
      "display_type": "teaching_card"
    }
  },
  "reward": {
    "reward_xp_awarded": 5
  },
  "progress": {
    "progression_action": "same_level_change_view_or_practice",
    "promotion_allowed": false
  },
  "xai": {
    "top_factors": ["mastery_need", "evaluation_need"],
    "reason": "The tutor selected a definition view because mastery is partial and review is useful."
  },
  "adaptive_hint": {
    "status": "success",
    "hint_type": "guided_hint",
    "hint_text": "Try this in two steps. First, identify what the question is asking about Variables. Next, use this clue: variables are names linked to values. What would change in your answer?",
    "support_need": 0.52,
    "frontend_component": "AdaptiveHintCard"
  },
  "voice_script": {
    "status": "success",
    "module": "VoiceScriptGenerator",
    "script_type": "teaching_explanation",
    "concept_name": "Variables",
    "text": "Let's learn Variables using the definition view. At easy, focus on this: a variable is a name linked to a value. Quick check: can you say the main rule of Variables in one sentence?",
    "tts_ready": true,
    "estimated_duration_sec": 13,
    "tone": "supportive",
    "frontend_component": "VoiceScriptCard",
    "limitations": [
      "No external TTS service is called.",
      "No audio file is generated."
    ]
  },
  "notebook_summary": "Variables need light revision before moving ahead.",
  "next_action": "show_first_question"
}
```

## 8. Puzzle / Gamified Assessment Schemas

The backend can expose puzzle-style activities in `assessment.puzzle_questions`.
These are data schemas only; the frontend decides the actual interaction pattern.

The compact frontend response can also expose a richer top-level
`puzzle_activities` list and mirrors it under `assessment.puzzle_activities`.
This section is intended for gamified rendering where the frontend wants a
stable puzzle schema instead of adapting normal assessment questions.

### `puzzle_activities` payload

```json
{
  "puzzle_activities": [
    {
      "puzzle_id": "py_variables_fill_blank_1234abcd",
      "question_type": "puzzle",
      "puzzle_type": "fill_blank",
      "frontend_component": "FillBlankPuzzleCard",
      "prompt": "A Python variable stores a ____.",
      "instructions": "Fill the blank with the most accurate term.",
      "options": [],
      "blanks": ["value"],
      "pairs": [],
      "correct_order": [],
      "code_snippet": null,
      "expected_output": null,
      "hints": ["Use the key concept definition."],
      "difficulty": "easy",
      "concept_id": "py_variables",
      "concept_name": "Python Variables",
      "domain": "Python",
      "validation_mode": "normalized_blank_match",
      "max_score": 1.0
    }
  ]
}
```

Frontend puzzle components:

- `fill_blank` -> `FillBlankPuzzleCard`
- `arrange_steps` -> `ArrangeStepsPuzzleCard`
- `match_pairs` -> `MatchPairsPuzzleCard`
- `drag_order` -> `DragOrderPuzzleCard`
- `code_puzzle` -> `CodePuzzleCard`
- `syntax_completion` -> `SyntaxCompletionCard`

Puzzle answer submission format:

```json
{
  "learner_id": "14",
  "puzzle_id": "py_variables_fill_blank_1234abcd",
  "puzzle_type": "fill_blank",
  "concept_id": "py_variables",
  "learner_answer": {
    "blanks": ["value"]
  }
}
```

Other `learner_answer` shapes:

- `arrange_steps`: `{ "order": ["s1", "s2", "s3"] }`
- `drag_order`: `{ "order": ["i1", "i2", "i3"] }`
- `match_pairs`: `{ "pairs": [{"left_id": "l1", "right_id": "r1"}] }`
- `code_puzzle`: `{ "answer": "print(n)" }` or `{ "code": "..." }`
- `syntax_completion`: `{ "completion": "in" }`

Puzzle evaluator response format:

```json
{
  "status": "success",
  "question_type": "puzzle",
  "puzzle_type": "arrange_steps",
  "score": 0.666667,
  "label": "partial",
  "correct": false,
  "feedback": "Partial arrange_steps answer. Some positions or matches need correction.",
  "mistake_type": "arrange_steps_structured_error",
  "details": {
    "correct_positions": 2,
    "total_positions": 3,
    "sequence_accuracy": 0.666667
  }
}
```

Scoring is deterministic and transparent:

- Fill blank: `correct_blanks / total_blanks`
- Arrange steps and drag order: `correct_positions / total_positions`
- Match pairs: `correct_pairs / total_pairs`
- Code puzzle: SafeCodeRunner pass rate when executable Python exists, otherwise normalized answer match
- Syntax completion: normalized exact completion match
- Labels: `strong >= 0.8`, `partial >= 0.45`, `weak < 0.45`

### `fill_blank`

```json
{
  "question_type": "fill_blank",
  "concept_id": "1",
  "concept_name": "Variables",
  "domain": "Python",
  "prompt": "Complete the missing part.",
  "text_with_blank": "A Python variable name cannot start with ____.",
  "answer": "a digit",
  "hint": "Think about naming rules.",
  "frontend_component": "FillBlankCard"
}
```

### `arrange_steps`

```json
{
  "question_type": "arrange_steps",
  "prompt": "Arrange the steps in correct order.",
  "steps": [
    {"id": "s1", "text": "Write the loop header"},
    {"id": "s2", "text": "Indent the loop body"},
    {"id": "s3", "text": "Update or process the item"}
  ],
  "correct_order": ["s1", "s2", "s3"],
  "frontend_component": "ArrangeStepsCard"
}
```

### `match_pairs`

```json
{
  "question_type": "match_pairs",
  "prompt": "Match each term with its meaning.",
  "left_items": [
    {"id": "l1", "text": "commit"},
    {"id": "l2", "text": "branch"}
  ],
  "right_items": [
    {"id": "r1", "text": "saved project snapshot"},
    {"id": "r2", "text": "separate line of development"}
  ],
  "correct_pairs": [
    ["l1", "r1"],
    ["l2", "r2"]
  ],
  "frontend_component": "MatchPairsCard"
}
```

### `drag_order`

```json
{
  "question_type": "drag_order",
  "prompt": "Drag the code lines into the correct order.",
  "items": [
    {"id": "i1", "text": "name = \"Alice\""},
    {"id": "i2", "text": "print(name)"}
  ],
  "correct_order": ["i1", "i2"],
  "frontend_component": "DragOrderCard"
}
```

### `code_puzzle`

```json
{
  "question_type": "code_puzzle",
  "prompt": "Fix the missing line/code block.",
  "starter_code": "numbers = [1, 2, 3]\nfor n in numbers:\n    ____",
  "answer": "print(n)",
  "expected_output": "1\n2\n3",
  "frontend_component": "CodePuzzleCard"
}
```

## 9. Sample Ask Doubt Response

Learner doubt:

```text
I don't understand why 2score = 10 is wrong.
```

Response:

```json
{
  "status": "success",
  "doubt_type": "debug_doubt",
  "concept_id": "1",
  "concept_name": "Variables",
  "domain": "Python",
  "context_source": "local_rag",
  "rag_connected": true,
  "rag_success": true,
  "doubt_answer": "In Python, variable names cannot start with a number. The name 2score is invalid because it begins with 2. Use a name like score2 or score instead.",
  "retrieved_sections": ["definition", "misconceptions", "examples"],
  "code_snippet": "2score = 10\n# use this instead\nscore2 = 10",
  "followup_check": "Which variable name is valid: 2score or score2?",
  "next_action": "show_variable_naming_example"
}
```

Frontend behavior:

- Show the answer in simple language.
- Show the code snippet in a code block.
- Put retrieved sections in a collapsible "Sources" panel.
- Mention that variable names cannot start with a number.

## 10. Voice Script Schema

The backend can expose `voice_script` for the currently selected teaching, revision, feedback, doubt, encouragement, or next-step moment.

```json
{
  "status": "success",
  "module": "VoiceScriptGenerator",
  "script_type": "mistake_feedback",
  "concept_name": "Python Variables",
  "text": "Your answer is marked as partial. The main issue looks like variable naming error. Go back to syntax accuracy and use the rule for Python Variables slowly. Small check: which part of your answer should change first?",
  "tts_ready": true,
  "estimated_duration_sec": 16,
  "tone": "supportive",
  "frontend_component": "VoiceScriptCard",
  "limitations": [
    "No external TTS service is called.",
    "No audio file is generated.",
    "Script quality depends on the evidence supplied by the tutor pipeline."
  ]
}
```

Frontend behavior:

- Render the script as short spoken text.
- Use browser Text-to-Speech or a speech service outside the backend.
- Keep the same text visible for accessibility.
- Treat `estimated_duration_sec` as an estimate, not an exact audio duration.

## 11. Adaptive Hint Schema

The backend can expose `adaptive_hint` after answer evaluation or inside the compact frontend response.

Full policy output may also be available as `adaptive_hint_output`.

```json
{
  "status": "success",
  "module": "AdaptiveHintPolicy",
  "hint_type": "output_prediction_hint",
  "hint_level": "guided_hint",
  "hint_text": "For output prediction, trace Variables one step at a time. Write each variable value after every line. What value changes just before the print or final output?",
  "support_need": 0.58,
  "evidence": {
    "weakness_pressure": 0.7,
    "mastery_need": 0.55,
    "behaviour_pressure": 0.3,
    "repeat_hint_pressure": 0.0,
    "question_type": "output_prediction",
    "mistake_type": "wrong_output"
  },
  "frontend_component": "AdaptiveHintCard",
  "fallback_used": false
}
```

Frontend behavior:

- Show `hint_text` in `AdaptiveHintCard`.
- Use `hint_type` to choose icon and display style.
- Use `support_need` only as an internal/teacher-visible signal unless a learner-facing meter is intentionally designed.
- If `fallback_used` is true, show the hint normally but avoid claiming high personalization.

## Learned / Model-Supported Hint Policy Payload

The deterministic `AdaptiveHintPolicy` remains the **fallback** when learned model artifacts are missing, fail to load, or when the learned selector’s confidence is below the configured threshold. In the integrated tutor flow, the backend may first compute `adaptive_hint_output`, then run `LearnedHintPolicy` to obtain `learned_hint_output` (or the compact `learned_hint` field in the frontend builder). **Learner-facing UI still uses `AdaptiveHintCard`**; the module name in the payload distinguishes the source.

`LearnedHintPolicy` predicts **`hint_type`** and **`hint_level`** (`low` | `medium` | `high`) from the same learner evidence family used for adaptive scoring (mastery, behaviour risk, score, mistake type, question type, difficulty, prior hints, etc.). **`predicted_success_probability`** is the model’s estimate that the chosen hint will help the learner improve or reach a correct or partial next attempt; it is suitable for **teacher or admin** dashboards rather than as a hard guarantee to the learner.

Full raw output may appear as `learned_hint_output` next to `adaptive_hint_output` on the integrated payload.

Example payload:

```json
{
  "status": "success",
  "module": "LearnedHintPolicy",
  "model_used": true,
  "fallback_used": false,
  "hint_type": "guided_hint",
  "hint_level": "medium",
  "hint_text": "Trace the variable value line by line before predicting output.",
  "predicted_success_probability": 0.72,
  "confidence": 0.81,
  "top_features": ["score", "mastery_score", "mistake_type_encoded"],
  "frontend_component": "AdaptiveHintCard"
}
```

Frontend behavior:

- Prefer `learned_hint` / `learned_hint_output` when present and `model_used` is true for the model-supported path; if `fallback_used` is true or `status` is `"warning"`, treat the hint text as aligned with the deterministic adaptive policy output.
- Render hints in **`AdaptiveHintCard`** regardless of `module`.
- Optionally surface `predicted_success_probability` and `confidence` only in teacher or admin views.

## Retention / Forgetting Prediction Payload

The existing **revision scheduler** in `tutor/memory/revision_scheduler.py` remains the primary **fallback**: it still builds spaced-repetition cards, daily/weekly plans, and the `frontend_revision_packet` using deterministic rules. When trained artifacts and sufficient learner evidence are available, **`RetentionPredictor`** (see `tutor/forgetting/retention_predictor.py`) adds a parallel, model-supported readout of **retention risk**, **review due**, **revision priority** (for example `high_priority` / `medium_priority` / `low_priority`), and **recommended review interval** buckets. If models are missing or evidence is thin, the predictor returns `model_used: false` and `fallback_used: true` and should be shown together with—not instead of—the scheduler output.

Integrated or revision API responses may include `retention_prediction` on the scheduler object and, in the compact frontend builder, under **`revision.retention_prediction`**. The frontend can surface **`RetentionRiskCard`** for the overall risk/readiness signal, or **`RevisionPriorityCard`** when emphasizing scheduling priority.

Example payload:

```json
{
  "status": "success",
  "module": "RetentionPredictor",
  "model_used": true,
  "fallback_used": false,
  "retention_risk_label": "high",
  "review_due": true,
  "revision_priority": "high_priority",
  "recommended_review_interval": "next_day",
  "confidence": 0.82,
  "top_features": ["time_gap_days", "recent_score", "mastery_score"],
  "frontend_component": "RetentionRiskCard"
}
```

## Behaviour human annotation (offline workflow)

Runtime learner responses still use the existing **behaviour models and proxy labels** in the integrated pipeline. For **teacher / research validation**, the repo exports an **annotation-ready CSV** (`evaluation_outputs/csv/behaviour_annotation_dataset.csv`) plus a **demo sample sheet** with placeholder “human” columns (`behaviour_annotation_sample_labelled.csv`). The sample file is **not** a completed human study—see `docs/behaviour_human_labelling_guide.md`. The frontend contract does **not** require new fields for normal learner screens; ingestion of merged human labels is **future work** after annotators finish sheets.

## Learned Adaptive Path Ranker Payload

Prerequisite **graph and unlock rules stay authoritative**: the `LearnedAdaptivePathRanker` only scores **already safe** candidates (unlocked, not blocked). It must **not** unlock concepts the dependency module has blocked. When model artifacts are missing or confidence is low, the backend falls back to the existing **`AdaptivePathSelector`** / validation path.

The ranker predicts a **`recommended_action`** (for example `review_current`, `next_unlocked_concept`, `wait_locked_prerequisite`), a **`recommended_node_type`** (lesson, practice, quiz, challenge, revision, boss_test), and a **`rank_score_bucket`** (`low_priority` | `medium_priority` | `high_priority`). Integrated runs may expose `learned_path_ranker_output`; the compact frontend contract includes **`decision.learned_path_ranker`**.

`safety_violation` should remain false when filtering is applied; `safe_candidates_count` and `blocked_candidates_count` summarize filtering.

Example payload:

```json
{
  "status": "success",
  "module": "LearnedAdaptivePathRanker",
  "model_used": true,
  "fallback_used": false,
  "recommended_action": "review_current",
  "recommended_node_type": "revision",
  "recommended_concept_id": "P1",
  "rank_score_bucket": "high_priority",
  "confidence": 0.82,
  "safe_candidates_count": 4,
  "blocked_candidates_count": 2,
  "safety_violation": false,
  "top_features": ["current_mastery", "review_due", "behaviour_risk"],
  "frontend_component": "AdaptivePathRecommendationCard"
}
```

Frontend behavior:

- Render recommendations with **`AdaptivePathRecommendationCard`** when the product adds that card; until then, path fields may be shown in teacher or debug panels only.
- If `fallback_used` is true, align messaging with the deterministic adaptive path selection already in the payload.

## 12. Error/Fallback Handling

- If CogniTutorLM fails, frontend should still render old main pipeline teaching and assessment.
- If `cognitutor_lm_output.status == "error"`, show no learner-facing crash; optionally log the note in developer/teacher mode.
- If `adaptive_hint.status != "success"`, hide the hint card and keep normal feedback visible.
- If `voice_script.status != "success"` or `tts_ready` is false, hide playback and show normal teaching/feedback text.
- If RAG context is weak, show fallback explanation and do not claim strong grounding.
- If code runner blocks unsafe code, show a safety warning and explain that file/network/system operations are not allowed.
- If no learner history exists, start with default concept or subject selection.
- If optional fields are missing, use safe placeholders and continue rendering the main teaching/assessment flow.

## 13. Future Frontend Modules

- Subject selection
- Concept path graph
- Teaching card
- Assessment panel
- Code runner panel
- AdaptiveHintCard
- Doubt panel
- Returning learner comeback card
- Revision/flashcards/mindmap tabs
- VoiceScriptCard with browser Text-to-Speech playback controls
- XP/streak widget
- XAI explanation card
- Teacher/admin report later


## Model Attribution / XAI Payload

The backend can provide model-level attribution for trained machine-learning components using permutation importance. SHAP is optional and not required.

### Frontend component

`ModelAttributionCard`

### Payload

```json
{
  "status": "success",
  "module": "ModelAttributionExplainer",
  "target_name": "promotion_confidence_model",
  "model_type": "RandomForestClassifier",
  "method_used": "permutation_importance",
  "shap_available": false,
  "feature_importances": [
    {
      "feature": "mastery_score",
      "importance": 0.23,
      "importance_std": 0.02,
      "rank": 1
    }
  ],
  "top_features": ["mastery_score", "fused_score", "behaviour_risk"],
  "explanation_text": "For promotion_confidence_model, permutation attribution indicates that mastery_score, fused_score, and behaviour_risk are the strongest contributing features."
}
```

## Model-Based XAI Surrogate Payload

This section describes **model-based surrogate XAI**: separate from the evidence-card / normalized contribution layer. The existing XAI cards in the compact frontend response remain **readable display and fallback** only. Surrogate models are trained on tutor decision logs (features derived from SQLite logs and related aggregates) to **predict tutor decisions** such as teaching view, next action, difficulty, promotion, and revision need. **Feature attribution** (permutation importance by default, tree `feature_importances_` as fallback, SHAP only if installed) explains those **trained surrogate models**, not hand-authored scoring rules.

### Frontend components

- `ModelAttributionCard` — model-level feature importances for a chosen surrogate (same family as the general model attribution payload above).
- `XAISurrogateExplanationCard` — learner-facing summary of a surrogate prediction plus top drivers and caveats when labels were synthetic or derived from logs.

### Example `XAISurrogateExplanationCard` payload

```json
{
  "status": "success",
  "module": "XAISurrogateModel",
  "target_name": "selected_teaching_view",
  "prediction": "revision_view",
  "best_model": "RandomForestClassifier",
  "model_metrics": {
    "accuracy": 0.91,
    "macro_f1": 0.88
  },
  "top_features": [
    {
      "feature": "fused_score",
      "importance": 0.24,
      "rank": 1
    },
    {
      "feature": "mastery_score",
      "importance": 0.19,
      "rank": 2
    }
  ],
  "explanation_text": "The surrogate model predicts revision_view mainly because fused_score and mastery_score indicate the learner needs more support."
}
```

### Frontend display expectations

- Show **target decision** (which surrogate target is being explained) and **predicted decision** from the model.
- Show **model used** (best estimator name from training comparison).
- Show a **metric badge** using `model_metrics` (for example accuracy and macro F1).
- List **top features** with rank and importance.
- Render **explanation text** as the primary narrative.
- If the backend report indicates **synthetic** or **derived** training labels, show a **limitations** badge (for example “Derived from fusion logs” or “Includes synthetic demo rows”) and avoid claiming independent human ground truth.

## Learned teaching strategy selector (model-supported)

The compact frontend `decision` object may include **`learned_teaching_strategy`**: output from `LearnedTeachingStrategySelector` in **comparison / model-supported** mode. The rule-based **`recommend_evidence_aware_teaching_strategy`** (exposed as `TeachingStrategySelector.recommend` from `tutor.strategy.teaching_strategy_selector`) remains the **safety baseline** and continues to drive the primary teaching view in the pipeline when learned confidence is low or model files are missing.

### Behavior

- **`model_used: true`** only when all per-target artifacts exist under `models/strategy/` and predictions succeed.
- **`fallback_used: true`** when artifacts are missing, confidence is below the internal threshold, or the learned path errors; strategy fields should align with the rule-based output passed as fallback.
- **`top_features`** lists local evidence drivers (diagnostic magnitudes), not a second rule engine.

### Frontend component

`LearnedTeachingStrategyCard` (optional) — show teaching view, difficulty, next action, assessment group, confidence, and limitations.

### Example payload

```json
{
  "status": "success",
  "module": "LearnedTeachingStrategySelector",
  "model_used": true,
  "fallback_used": false,
  "teaching_view": "code_view",
  "difficulty": "medium",
  "next_action": "practice",
  "assessment_type_group": "output_prediction_practice",
  "confidence": 0.62,
  "model_versions": {
    "teaching_view": "RandomForestClassifier",
    "difficulty": "LogisticRegression"
  },
  "top_features": [
    {"feature": "mastery_score", "importance": 0.72, "rank": 1},
    {"feature": "fused_score", "importance": 0.65, "rank": 2}
  ],
  "limitations": []
}
```

### Final report wording (teaching strategy upgrade)

The teaching strategy module was upgraded from an evidence-aware rule baseline to a learned model-supported selector. Tutor decision logs and engineered learner evidence are converted into feature-label datasets, and supervised models are trained to predict teaching view, difficulty, assessment group, and next action. The existing rule-based selector is retained as a safety fallback when model confidence is low or artifacts are unavailable.