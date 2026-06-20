# Frontend Behaviour Input Coverage Report

## Summary

Behaviour evidence is collected for all submitted learning activities, not only QuizPage/MCQ.

Before this patch:
- `AssessmentRenderer` collected timer, confidence, hints, option changes, answer changes, and submitted behaviour for standard assessment cards.
- `CodeConsole` collected confidence, hints, answer changes, run count, and submitted behaviour.
- `PuzzlePage` checked answers locally and did not submit behaviour evidence.
- `FlashcardDeck` ratings advanced cards locally and did not submit behaviour evidence.

Fixed:
- `PuzzlePage` now sends `puzzle_*` answer submissions through `submitAnswer()` with confidence, timer, hint count, answer changes, attempt count, and wrong attempt count.
- `FlashcardDeck` now sends `flashcard_recall` submissions through `submitAnswer()` on rating.
- `AssessmentRenderer` now recognizes `true_false` as a multiple-choice style question.
- `submitAnswer()` now fills missing behaviour fields with safe defaults before calling the backend.

## Coverage Table

| Assessment Type | Frontend Component | Timer | Confidence | Hint Count | Option Changes | Answer Changes | Run Code Count | Sent to API | Stored in DB | Behaviour Module Uses It | Status | Fix Applied |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mcq | `AssessmentRenderer` / `MCQQuestionCard` | Yes | Yes | Yes | Yes | N/A | 0 | Yes | Yes | Yes | Connected | None frontend-side |
| fill_in_the_blank | `AssessmentRenderer` / `FillBlankQuestionCard` | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | None frontend-side |
| true_false | `AssessmentRenderer` / `MCQQuestionCard` | Yes | Yes | Yes | Yes | N/A | 0 | Yes | Yes | Yes | Fixed | Added `true_false` support |
| output_prediction | `AssessmentRenderer` / `OutputPredictionCard` | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | None frontend-side |
| debug_task | `AssessmentRenderer` / `CodeConsole` | Yes | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Connected | None frontend-side |
| syntax_completion | `AssessmentRenderer` / `CodeConsole` | Yes | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Connected | None frontend-side |
| coding_prompt | `AssessmentRenderer` / `CodeConsole` | Yes | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Connected | None frontend-side |
| code_reasoning_task | `AssessmentRenderer` text fallback | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | Covered by shared fallback |
| explanation_check | `AssessmentRenderer` text fallback | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | Covered by shared fallback |
| transfer_question | `AssessmentRenderer` / `TransferQuestionCard` | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | Covered by shared fallback/input |
| challenge_question | `AssessmentRenderer` / `ChallengeQuestionCard` | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | Covered by shared fallback/input |
| practice_question | `AssessmentRenderer` text fallback | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Connected | Covered by shared fallback |
| puzzle / gamified assessment | `PuzzlePage` | Yes | Yes | Yes | N/A | Yes | 0 | Yes | Yes | Yes | Fixed | Added `submitAnswer()` call |
| flashcard recall | `FlashcardDeck` | Yes | Rating-derived | Show-answer tracked | N/A | Flip/rating tracked | 0 | Yes | Yes | Yes | Fixed | Added `submitAnswer()` call |
| code console submissions | `CodeConsole` | Yes | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes | Connected | None frontend-side |

## Manual Browser Checklist

- Not executed in this terminal-only run.
- Build and type-check verify the frontend compiles after the behaviour wiring.
- Network-panel verification should confirm `option_change_count`, `answer_change_count`, `hint_count`, and `run_code_count` on the relevant interactions.

## Commands Run

- `npm run build`: success.
- `npm run lint`: success.
