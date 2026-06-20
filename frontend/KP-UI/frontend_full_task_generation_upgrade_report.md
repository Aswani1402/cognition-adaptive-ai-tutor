# Frontend Full Task Generation Upgrade Report

## Concept and Subject Flow
- Existing pages remain unchanged. Task types are exposed inside current lesson, assessment, flashcards, mindmap, feedback, hint, doubt, and notebook surfaces.
- Lesson, assessment, flashcards, mindmap, hint, doubt, and XAI requests keep using `active_subject`, `current_concept_id`, `current_concept_name`, and `current_difficulty`.

## Teaching Rendering
- Guided lesson now shows buttons for all 14 teaching views.
- `SelectedTeachingViewRenderer` reads `contentByView` and renders rich selected-view content with code/example/key points/mistakes.

## Assessment Rendering
- Assessment sequence now uses up to 10 questions.
- Existing `AssessmentRenderer` supports MCQ, fill blank, true/false, output prediction, debug, syntax, coding prompt, code reasoning, transfer, challenge, explanation, and multi-step style prompts.
- `CodeConsole` receives the full question payload so backend answer evaluation has correct expected answers.

## Behaviour Tracking
- Timer, confidence, hint count, answer changes, option changes, run-code count, attempts, and wrong attempts are sent to `/answer/submit`.

## Hints and Feedback
- `Need a hint` continues to call `/hint/predict`.
- Feedback panel shows learner answer, correct answer, explanation, next step, mistake type, and behaviour summary.

## Flashcards
- `FlashcardDeck` now has type tabs/filters and shows card type badges.
- Again/Hard/Good/Easy buttons remain available, plus Save to notebook action.

## Mindmap
- `MindMapView` now has tabs for concept, comparison, and revision maps when backend variants are present.

## Cogni Mascot
- Existing `CogniGuideCard` remains in guided flow and uses backend/flow messages. Backend now returns voice-ready script fields for lesson, doubt, and feedback packets.

## Build Results
- `npm run build`: passed.
- `npm run lint`: passed.
