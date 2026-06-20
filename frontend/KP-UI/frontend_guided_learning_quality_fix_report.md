# Frontend Guided Learning Quality Fix Report

Date: 2026-05-12

## 1. Evaluator equivalence fixes

Backend now accepts equivalent MCQ/fill/output/debug answers and returns correct answer/explanation fields for the frontend.

## 2. Correct answer/explanation display

Assessment and guided feedback panels show score, correct/partial/wrong status, learner answer, correct answer, explanation, mistake type, behaviour summary, and next step.

## 3. Timer/behaviour tracking fields

Assessment cards show a visible `Time: mm:ss` timer. Submit payload includes confidence, time, hint usage/count, option changes, answer changes, run code count, attempts, and wrong attempts.

## 4. Hint button behavior

The hint button posts to `/hint/predict` with learner, subject, concept, difficulty, question type, answer, and hint count. HintPanel displays hint type, level, and text.

## 5. Question rotation

Frontend renders multiple assessment types from backend sequences: MCQ, fill blank, true/false, output prediction, debug, syntax completion, coding, transfer, challenge, drag order, match pairs, and explanations.

## 6. Teaching content grounding from concept_resources

Teaching cards now preserve backend key points/common mistakes and always show grounded sections for key points, example, mistakes to avoid, and “Why this?”.

## 7. Guided flow after correct/partial/wrong

Guided feedback shows next action clearly. Correct moves forward; partial/wrong route through revision/reteach style activities before reassessment.

## 8. Code console status

CodeConsole has editable code, Run, Submit, hint, confidence, stdout/stderr, error and test result display, and run-code tracking.

## 9. Mascot script coverage

Manual script bank was expanded for subject selection, hint, correct/partial/wrong, repeated mistakes, revision, flashcards, mindmap, rewards, and next concept.

## 10. Why-this/XAI coverage

Learner-facing “Why this?” appears in teaching. Reviewer evidence remains optional in XAI/reviewer views.

## 11. Generation/task coverage

Generation/task coverage is documented in the backend full model connection reports. Voice-ready scripts are text only.

## 12. Remaining limitations

Manual browser checks were not run. Some optional learned backend models may still report warning/fallback when artifacts are unavailable.

## 13. Build/test results

- Backend quality tests: passed.
- Backend smoke/response builder: passed.
- Frontend `npm run build`: passed.
- Frontend `npm run lint`: passed.
