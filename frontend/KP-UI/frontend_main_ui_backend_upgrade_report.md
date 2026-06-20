# Frontend Main UI Backend Upgrade Report

## Routes Checked
- Frontend API client maps auth, subject selection, learner context, lesson, assessment, answer submit, hint, code run, doubt, flashcards, mindmap, notebook, revision, retention, reward, XAI, AI evidence, generation coverage, and agentic trace routes.

## Frontend Pages Checked
- LessonPage / GuidedTutorJourney
- AssessmentRenderer / CodeConsole / HintPanel
- FlashcardsPage / FlashcardDeck
- MindMapPage / MindMapView
- NotebookPage / NotebookPanel
- DoubtPanel
- CogniGuideCard
- XAI / Reviewer analytics pages

## Rendering Status
- Teaching views render from `content_by_view` or selected teaching content.
- Assessment cards show type, difficulty, prompt, timer, confidence, hint, submit, feedback, learner answer, correct answer, explanation, and next step.
- Code/debug tasks show editable console, run, submit, stdout/stderr, and run-code tracking.
- Flashcards expose multiple card types with filters, difficulty, explanation, rating buttons, and save action.
- Mindmaps expose concept, comparison, and revision variants.
- Doubts show type, answer, example/code, grounding summary, follow-up, and notebook-save signal.
- Notebook/revision surfaces summary, mistakes, revision plan, comeback/returning learner, progress insight, doubts, and saved flashcards.

## Behaviour Payload Status
- `submitAnswer` sends learner, subject, concept, question, answer, confidence, time, hint, option/answer change, run-code, and attempt fields.
- Development builds log `[submitAnswer payload]`.

## Remaining Warnings
- Optional LLM/model services can still return backend warning/fallback status.
- Manual browser verification is still required for visual confirmation across the full guided flow.
