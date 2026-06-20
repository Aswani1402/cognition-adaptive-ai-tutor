# Cogni Mascot Flow Report

Generated: 2026-05-12

## 1. Mascot Components Created

- `CogniParrot.tsx`
- `CogniGuideCard.tsx`
- `CogniSpeechBubble.tsx`
- `cogniScripts.ts`
- `useCogniGuide.ts`

## 2. Pages Using Cogni

Login, Register, Subjects, Dashboard, GuidedTutorJourney/LessonPage, Flashcards, Mindmap, Notebook mobile banner, Rewards, and XAI.

## 3. Script Categories

Auth, subject selection, teaching, teaching view switch, assessment intro, correct/partial/wrong answer, difficulty progression, concept completion, returning learner, revision, flashcard, mindmap, notebook memory, doubt, hint, rewards, XAI, encouragement, and error/mock mode.

## 4. Script Selection

`getCogniMessage(context)` prioritizes backend `guide_message`, then mock fallback, then deterministic rules based on page, activity, difficulty, score, mistake type, weakest skill, time gap, selected view, and next action.

## 5. Guided Flow Support

Cogni appears at the top of the guided session and updates for teaching, assessment, feedback, revision, flashcards, mindmap, rewards, and mock mode.

## 6. First-Time Learner Messages

Subject selection says the learner chooses one subject and Cogni/backend choose the first concept.

## 7. Returning Learner Messages

Scripts cover minutes, hours, days, and weeks/months return patterns, with revision-first guidance for longer gaps.

## 8. Difficulty Progression Messages

Easy passed -> medium, medium passed -> hard, hard passed -> next concept unlocked.

## 9. Assessment Feedback Messages

High score, partial score, weak score, syntax mistake, and output prediction mistake all get distinct deterministic messages.

## 10. Flashcard / Mindmap Messages

Flashcard and mindmap scripts guide revision without requiring manual page selection.

## 11. Manual vs Generated Scripts

Manual scripts are used now for reliability, consistency, and final-demo explainability.

## 12. Future Upgrade

CogniTutorLM can later generate personalized guide scripts from learner state. That is not live in this version.

## 13. Build And Test Results

- Frontend `npm run build`: passed
- Frontend `npm run lint`: passed
- Backend `python -m scripts.test_api_routes_smoke`: passed
- Backend `python -m scripts.test_frontend_response_builder`: passed
- Notes: Cogni uses manual deterministic scripts now; CogniTutorLM script generation remains a future upgrade, not live runtime.
