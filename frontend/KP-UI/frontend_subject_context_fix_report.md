# Frontend Subject Context Fix Report

## Root Cause
- Pages and API fallbacks used hardcoded Python/default learner values instead of selected subject/session state.

## Fixed
- `LearnerSessionContext` stores and persists learner id, active subject, concept id/name, difficulty, teaching view, and backend flags.
- Subject selection updates backend, context, and localStorage.
- Lesson, path, quiz, flashcards, mindmap, progress, doubt, and guided journey calls now pass selected subject/concept.
- Fallbacks are subject-aware.

## Remaining Demo-Only Areas
- Demo page is explicitly reviewer/demo mode and may show raw JSON tabs.

## Build/Test Results
- `npm run build`: passed.
- `npm run lint`: passed.
- Backend smoke and frontend response builder scripts: passed.
